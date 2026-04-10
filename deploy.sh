#!/bin/bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# GameSpark → Yandex Cloud deployment script
# VM: 2 vCPU / 4 GB RAM / 30 GB disk / Ubuntu 22.04
# ─────────────────────────────────────────────────────────────────────────────

FOLDER_ID="b1gjdelvlk6hahaqll8b"
ZONE="ru-central1-a"
VM_NAME="gamespark-prod"
CORES=2
MEMORY=4
DISK_GB=30
SSH_KEY="$HOME/.ssh/gamespark_deploy"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}[deploy]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC}   $*"; }
die()  { echo -e "${RED}[error]${NC}  $*"; exit 1; }

# ── 1. Check / install yc CLI ────────────────────────────────────────────────
if ! command -v yc &>/dev/null; then
    log "Installing Yandex Cloud CLI..."
    curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash -s -- -a
    export PATH="$HOME/yandex-cloud/bin:$PATH"
    command -v yc &>/dev/null || die "yc install failed. Please install manually: https://yandex.cloud/docs/cli/quickstart"
fi
log "yc version: $(yc version 2>/dev/null || echo 'ok')"

# ── 2. Check authentication ──────────────────────────────────────────────────
if ! yc config list 2>/dev/null | grep -qE "token|service-account-key"; then
    warn "Not authenticated with Yandex Cloud."
    echo ""
    echo "  Run:  yc init"
    echo "  Then re-run this script."
    exit 1
fi
log "Authenticated ✓"

# ── 3. SSH key ───────────────────────────────────────────────────────────────
if [ ! -f "$SSH_KEY" ]; then
    log "Generating SSH key at $SSH_KEY"
    ssh-keygen -t ed25519 -f "$SSH_KEY" -N "" -C "gamespark-deploy"
fi
log "SSH key: $SSH_KEY ✓"

# ── 4. Get or create VM ──────────────────────────────────────────────────────
EXISTING=$(yc compute instance list --folder-id "$FOLDER_ID" --format json 2>/dev/null \
    | python3 -c "import sys,json; vms=[v for v in json.load(sys.stdin) if v['name']=='$VM_NAME']; print(vms[0]['id'] if vms else '')" 2>/dev/null || echo "")

if [ -n "$EXISTING" ]; then
    warn "VM '$VM_NAME' already exists (id=$EXISTING). Skipping creation."
else
    log "Creating VM '$VM_NAME'..."
    yc compute instance create \
        --folder-id   "$FOLDER_ID" \
        --name        "$VM_NAME" \
        --zone        "$ZONE" \
        --platform    "standard-v3" \
        --cores       "$CORES" \
        --memory      "${MEMORY}GB" \
        --create-boot-disk "image-family=ubuntu-2204-lts,image-folder-id=standard-images,size=${DISK_GB},auto-delete=true,type=network-ssd" \
        --network-interface "subnet-name=default-$ZONE,nat-ip-version=ipv4" \
        --metadata     "ssh-keys=yc-user:$(cat ${SSH_KEY}.pub)" \
        --async
    log "VM creation started (async)..."
fi

# ── 5. Wait for public IP ────────────────────────────────────────────────────
log "Waiting for VM to get a public IP..."
VM_IP=""
for i in $(seq 1 30); do
    VM_IP=$(yc compute instance get "$VM_NAME" \
        --folder-id "$FOLDER_ID" --format json 2>/dev/null \
        | python3 -c "
import sys, json
data = json.load(sys.stdin)
for iface in data.get('network_interfaces', []):
    nat = iface.get('primary_v4_address', {}).get('one_to_one_nat', {})
    addr = nat.get('address', '')
    if addr:
        print(addr)
        break
" 2>/dev/null || echo "")
    if [ -n "$VM_IP" ]; then break; fi
    echo "  attempt $i/30 — waiting 10s..."
    sleep 10
done
[ -n "$VM_IP" ] || die "Could not get public IP after 5 minutes."
log "VM public IP: $VM_IP ✓"

# ── 6. Wait for SSH ──────────────────────────────────────────────────────────
log "Waiting for SSH to become available..."
for i in $(seq 1 24); do
    if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=6 \
           -i "$SSH_KEY" "yc-user@$VM_IP" "echo ok" 2>/dev/null | grep -q ok; then
        log "SSH ready ✓"
        break
    fi
    echo "  attempt $i/24 — waiting 10s..."
    sleep 10
    [ "$i" -eq 24 ] && die "SSH never became available. Check the VM in the console."
done

SSH_CMD="ssh -o StrictHostKeyChecking=no -i $SSH_KEY yc-user@$VM_IP"
SCP_CMD="scp -o StrictHostKeyChecking=no -i $SSH_KEY"

# ── 7. Install Docker on VM ──────────────────────────────────────────────────
log "Installing Docker on VM..."
$SSH_CMD bash <<'REMOTE'
set -e
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -qq
sudo apt-get install -y -qq ca-certificates curl gnupg lsb-release rsync
# Docker official repo
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update -qq
sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker yc-user
echo "Docker installed ✓"
REMOTE
log "Docker installed ✓"

# ── 8. Copy project to VM ────────────────────────────────────────────────────
log "Copying project files to VM..."
$SSH_CMD "mkdir -p ~/app"

rsync -az --delete \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='*.egg-info' \
    --exclude='.env' \
    --exclude='data/' \
    -e "ssh -o StrictHostKeyChecking=no -i $SSH_KEY" \
    "$SCRIPT_DIR/" "yc-user@$VM_IP:~/app/"
log "Files copied ✓"

# ── 9. Write .env on server ──────────────────────────────────────────────────
log "Configuring environment..."
OPENROUTER_KEY=$(grep -E '^OPENROUTER_API_KEY=' "$SCRIPT_DIR/.env" | cut -d= -f2-)
RATE_HOUR=$(grep -E '^RATE_LIMIT_PER_HOUR=' "$SCRIPT_DIR/.env" | cut -d= -f2- || echo "10")
RATE_DAY=$(grep -E '^RATE_LIMIT_PER_DAY=' "$SCRIPT_DIR/.env" | cut -d= -f2- || echo "30")
SESSION_SECRET=$(openssl rand -hex 32)

$SSH_CMD bash <<REMOTE
cat > ~/app/.env <<'EOF'
OPENROUTER_API_KEY=${OPENROUTER_KEY}
DATABASE_PATH=/app/data/games.db
ENVIRONMENT=production
CORS_ORIGINS=http://${VM_IP}
RATE_LIMIT_PER_HOUR=${RATE_HOUR}
RATE_LIMIT_PER_DAY=${RATE_DAY}
SESSION_SECRET=${SESSION_SECRET}
EOF
echo ".env written ✓"
REMOTE

# ── 10. Build & start containers ─────────────────────────────────────────────
log "Building and starting containers (this takes ~3 minutes)..."
$SSH_CMD bash <<'REMOTE'
cd ~/app
# newgrp docker won't work in non-interactive SSH; use sudo for this run
sudo docker compose -f docker-compose.prod.yml up -d --build
REMOTE
log "Containers started ✓"

# ── 11. Health check ─────────────────────────────────────────────────────────
log "Waiting 15s for services to warm up..."
sleep 15
if curl -sf --max-time 10 "http://$VM_IP/api/games" > /dev/null 2>&1; then
    log "Health check passed ✓"
else
    warn "Health check returned non-200 — app may still be starting. Check with:"
    warn "  ssh -i $SSH_KEY yc-user@$VM_IP 'sudo docker compose -f ~/app/docker-compose.prod.yml logs --tail 50'"
fi

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅  Deployment complete!                                ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  🌐  App URL:   http://${VM_IP}                          ${NC}"
echo -e "${GREEN}║  🔑  SSH:       ssh -i $SSH_KEY yc-user@${VM_IP}         ${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
