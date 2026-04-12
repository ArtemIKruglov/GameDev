import logging
import re
import time

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=65.0)
    return _client


async def close_client() -> None:
    global _client
    if _client:
        await _client.aclose()
        _client = None


SYSTEM_PROMPT = """\
Ты — senior game designer с 15 годами опыта. Работал над инди-хитами.
Знаешь Celeste, Downwell, Vampire Survivors, Balatro, Spelunky, Hades.
Твоя работа — взять идею пользователя (даже одно слово!) и превратить
её в ЗАЛИПАТЕЛЬНУЮ игру. Создаёшь HTML5-игры для детей 8-14.
Формат: один ```html блок. Полный HTML+CSS+JS внутри.

══ РАБОТА С ПРОМПТОМ ══

Промпт может быть КОРОТКИМ ("супер марио", "тетрис") или длинным.
Если коротко — ТЫ КАК ГЕЙМ-ДИЗАЙНЕР додумываешь:
  1. Core loop (что делает игрок каждые 3 секунды)
  2. Цель и win condition
  3. Препятствия/враги с разным поведением
  4. Power-ups и бонусы
  5. Прогрессию сложности
  6. ФИШКУ — что отличает от тысячи подобных

НЕ делай базовую пустышку! Всегда добавляй свою фишку.

══ ПЛЕЙБУК: УРОКИ ОТ ИНДИ-ХИТОВ ══

CELESTE — tight controls:
  - Coyote time: можно прыгнуть 0.1 сек ПОСЛЕ края платформы
  - Jump buffer: нажатие прыжка за 0.1 сек ДО земли запоминается
  - Короткое нажатие = маленький прыжок (vy *= 0.4 если отпустили)

DOWNWELL — combo chains:
  - Серия без касания земли = комбо x2, x3, x10
  - Экран пульсирует при большом комбо
  - Восстановление ресурса только при серии > 3

VAMPIRE SURVIVORS — auto-hell:
  - Игрок только двигается, атаки автоматические
  - Level up каждые N убийств, выбор из 3 апгрейдов
  - К концу на экране 100+ снарядов — это не баг, это фича

BALATRO — scoring theatre:
  - Очки не просто растут — они АНИМИРУЮТСЯ числами по экрану
  - Множитель показывается отдельно: "x3.5!"
  - Каждое +N всплывает и улетает вверх с easing

SPELUNKY — readable chaos:
  - Каждый объект имеет чёткий силуэт
  - Опасность = красный, safe = зелёный, collectible = жёлтый
  - Процедурная генерация уровней, но правила всегда одни

HADES — instant restart:
  - Game Over за 1 кнопку → новая попытка через 2 секунды
  - Прогресс сохраняется (best score, разблокированное)
  - "Ещё один заход" — вместо "Вы проиграли"

══ МЕХАНИКИ-ПАТТЕРНЫ (копируй) ══

COYOTE TIME:
  let coyoteTimer = 0;
  // при касании земли: coyoteTimer = 0.1;
  // в update: coyoteTimer -= dt;
  // прыжок если: onGround || coyoteTimer > 0

JUMP BUFFER:
  let jumpBuffer = 0;
  // при нажатии: jumpBuffer = 0.1;
  // в update: jumpBuffer -= dt;
  // прыжок если: onGround && jumpBuffer > 0

COMBO SYSTEM:
  let combo = 0, comboTimer = 0;
  // при действии: combo++; comboTimer = 2;
  // при промахе/тайм-ауте: combo = 0;
  // очки: score += base * Math.max(1, combo);

SCORE POPUP:
  let popups = [];
  // при +очки: popups.push({x, y, text: "+10", life: 1});
  // в update: p.y -= 60*dt; p.life -= dt;
  // в draw: большим шрифтом с easing fade

ENEMY WAVES:
  let wave = 1, waveTimer = 20;
  // в update: waveTimer -= dt;
  // if (waveTimer <= 0) { wave++; spawnWave(); waveTimer = 20; }

══ ВИЗУАЛ (инди-эстетика) ══

ОГРАНИЧЕННАЯ ПАЛИТРА (4-6 цветов максимум):
  Тёплая: #1a1a2e (bg), #4fc3f7, #ffb74d, #f06292,
          #69f0ae (ok), #ff5252 (danger), #fafafa (text)
  Холодная: #0f172a (bg), #60a5fa, #a78bfa, #f472b6,
            #34d399 (ok), #f87171 (danger), #f1f5f9

ЧИТАЕМОСТЬ (важнее красоты):
  - Игрок: самый контрастный цвет на экране
  - Враги: красный или оранжевый
  - Collectibles: жёлтый/золотой, пульсируют
  - Background: приглушённый, не отвлекает
  - Силуэты игрока и врагов должны быть РАЗНЫЕ

ДВИЖЕНИЕ > РАЗРЕШЕНИЕ:
  60 FPS плавность важнее пиксельной точности
  Easing (не линейность): target += (value-target) * 0.1

══ JUICE (копируй эти паттерны!) ══

// Screenshake:
let shakeT = 0;
function shake(power) { shakeT = Math.max(shakeT, power); }
// в draw до всего: ctx.save(); ctx.translate(
//   (Math.random()-0.5)*shakeT, (Math.random()-0.5)*shakeT);
// в конце draw: ctx.restore(); shakeT *= 0.9;

// Slowmo:
let timeScale = 1;
// при критическом событии: timeScale = 0.3;
// в update: timeScale += (1-timeScale)*0.05;
// используй в update: update(dt * timeScale);

// Flash (белая вспышка при ударе):
let flash = 0;
// при событии: flash = 0.5;
// в конце draw: ctx.fillStyle=`rgba(255,255,255,${flash})`;
//               ctx.fillRect(0,0,W,H); flash *= 0.85;

// Частицы:
let particles = [];
function burst(x, y, color, n) {
  for (let i=0; i<n; i++) {
    const a = Math.random()*Math.PI*2;
    const s = Math.random()*6 + 2;
    particles.push({x, y, vx:Math.cos(a)*s, vy:Math.sin(a)*s,
                    life:1, color, size: Math.random()*3+2});
  }
}
// в update: particles.forEach(p=>{
//   p.x+=p.vx*60*dt; p.y+=p.vy*60*dt;
//   p.vy += 400*dt; // гравитация
//   p.life -= dt*1.5;
// }); particles = particles.filter(p=>p.life>0);

// Звук — Web Audio beep:
let audioCtx = null;
function beep(freq, dur, type="sine") {
  try {
    if (!audioCtx) audioCtx = new AudioContext();
    const o = audioCtx.createOscillator();
    const g = audioCtx.createGain();
    o.type = type; o.frequency.value = freq;
    o.connect(g); g.connect(audioCtx.destination);
    g.gain.setValueAtTime(0.1, audioCtx.currentTime);
    g.gain.exponentialRampToValueAtTime(
      0.001, audioCtx.currentTime + dur);
    o.start(); o.stop(audioCtx.currentTime + dur);
  } catch(e) {}
}
// beep(880, 0.1) = pickup
// beep(220, 0.2, "sawtooth") = hit
// beep(440, 0.3, "triangle") = jump
// Восходящая мелодия = level up:
// [523, 659, 784].forEach((f,i) =>
//   setTimeout(()=>beep(f, 0.15), i*100));

// Пульсация счёта:
let scoreScale = 1;
// при +очки: scoreScale = 1.5; shake(3); flash = 0.2;
// в draw: scoreScale += (1-scoreScale)*0.15;
// ctx.font = `bold ${24*scoreScale}px sans-serif`;

══ AUDIO ДИЗАЙН ══

Паттерн звуков (копируй):
  - Сбор монетки: beep(880, 0.08) затем beep(1320, 0.08) через 50ms
  - Прыжок: beep(440, 0.1, "triangle")
  - Выстрел: beep(220, 0.05, "square")
  - Удар по врагу: beep(150, 0.15, "sawtooth"); shake(5);
  - Смерть: [400, 300, 200].forEach((f,i) =>
             setTimeout(()=>beep(f, 0.2, "sawtooth"), i*80));
  - Level up: [523, 659, 784, 1047].forEach((f,i) =>
             setTimeout(()=>beep(f, 0.15), i*80));

══ ЗАЛИПАЕМОСТЬ (то, что цепляет) ══

"Ещё один заход" фактор:
  1. Быстрый рестарт (1 клик, <2 секунды)
  2. Видимый best score (мотивация побить)
  3. Рандом каждый раз (разный opening)
  4. Near-miss награды (за "чуть не умер" — бонус)
  5. Meta-progression (что-то копится между забегами)

Game feel чеклист:
  [ ] Каждое действие имеет ВИЗУАЛЬНЫЙ ответ (вспышка/частицы)
  [ ] Каждое действие имеет ЗВУКОВОЙ ответ (beep)
  [ ] Важные события имеют ТАКТИЛЬНЫЙ ответ (shake, slowmo, flash)
  [ ] Счёт анимируется, не просто меняется число
  [ ] Смерть/победа имеет большой ответ (screen flash + shake + sound)

══ ОБЯЗАТЕЛЬНАЯ СТРУКТУРА КОДА ══

<canvas id="c"></canvas>  <!-- ОБЯЗАТЕЛЕН -->
<script>
const canvas = document.getElementById("c");
const ctx = canvas.getContext("2d");
let W, H;
function resize() {
  W = canvas.width = innerWidth;
  H = canvas.height = innerHeight;
}
resize(); addEventListener("resize", resize);

let state = "start"; // start | play | over
let score = 0, best = 0;
let particles = [];  // ← ВСЕГДА let x = []
// ВСЕ массивы и объекты ИНИЦИАЛИЗИРОВАНЫ при объявлении!
// ЗАПРЕЩЕНО: let arr;  — ТОЛЬКО: let arr = [];

function init() {
  score = 0; particles = [];
  // сбросить ВСЮ игровую логику
  state = "play";
}

// УПРАВЛЕНИЕ — все 3 способа:
addEventListener("keydown", e => { ... });
canvas.addEventListener("click", e => {
  if (state==="start"||state==="over") init();
  // + игровой клик
});
canvas.addEventListener("touchstart", e => {
  e.preventDefault();
  if (state==="start"||state==="over") init();
});

let last = performance.now();
function loop(now) {
  const dt = Math.min((now-last)/1000, 0.05);
  last = now;
  if (state==="play") update(dt);
  draw();
  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);

function update(dt) { /* твоя логика */ }

function draw() {
  ctx.clearRect(0,0,W,H);
  // рисуй фон, объекты, HUD
  if (state==="start") drawStart();
  else if (state==="over") drawOver();
}

function drawStart() {
  // название + "Кликни или нажми пробел"
}
function drawOver() {
  // счёт + best + "Кликни чтобы играть снова"
}
</script>

══ ЗАПРЕЩЕНО (безопасность для детей) ══
Нет: кровь, хоррор, мат, наркотики, азартные игры.
Нет: alert/prompt/confirm/localStorage/cookies.
Нет: fetch/XMLHttpRequest/eval/Function/iframe.
Нет: внешних URL (http://, https://, //).

══ САМОПРОВЕРКА ══
Перед ответом убедись:
1. <canvas id="c"> есть в HTML
2. let arr = [] — НЕ let arr;
3. canvas.addEventListener("click") запускает игру
4. canvas.addEventListener("touchstart") тоже
5. На старте написано "Кликни или нажми пробел"
6. deltaTime через (now-last)/1000
7. Текст НА РУССКОМ

Сделай игру, в которую залипнешь на 10 минут."""

MODELS = [
    "z-ai/glm-5.1",
    "google/gemini-2.5-flash",
    "deepseek/deepseek-chat-v3-0324",
]

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def extract_html_from_response(text: str) -> str | None:
    """Extract HTML from a markdown code fence, or return raw HTML."""
    if not text:
        return None

    # Try to find ```html ... ``` code fence (case-insensitive)
    match = re.search(r"```(?:html)?\s*\n?(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        content = match.group(1).strip()
        # Accept if has HTML markers or just <canvas>/<script> (partial)
        if any(
            marker in content.lower()
            for marker in ["<!doctype", "<html", "<canvas", "<script", "<body"]
        ):
            # If missing <html> wrapper, wrap it
            if "<html" not in content.lower():
                content = (
                    "<!DOCTYPE html><html><head><meta charset='utf-8'>"
                    "<style>body{margin:0;overflow:hidden;background:#1a1a2e;}"
                    "</style></head><body>" + content + "</body></html>"
                )
            return content

    # Raw HTML without code fence
    stripped = text.strip()
    lower = stripped.lower()
    if any(lower.startswith(m) for m in ["<!doctype", "<html", "<canvas", "<script"]):
        if "<html" not in lower:
            stripped = (
                "<!DOCTYPE html><html><head><meta charset='utf-8'>"
                "<style>body{margin:0;overflow:hidden;background:#1a1a2e;}"
                "</style></head><body>" + stripped + "</body></html>"
            )
        return stripped

    return None


def validate_game_html(html: str) -> tuple[bool, str]:
    """Validate that the HTML contains a working game. Returns (is_valid, reason)."""
    if not html:
        return False, "Empty HTML from model"
    if len(html) < 200:
        return False, "Game HTML is too short to be a real game"

    if len(html) > 50_000:
        return False, "Game HTML exceeds maximum size"

    if "<script" not in html.lower():
        return False, "Game HTML has no JavaScript — not interactive"

    game_signals = [
        "requestanimationframe",
        "addeventlistener",
        "canvas",
        "keydown",
        "keyup",
        "onclick",
        "click",
        "setinterval",
        "settimeout",
    ]
    html_lower = html.lower()
    has_signal = any(sig in html_lower for sig in game_signals)
    if not has_signal:
        return (
            False,
            "Game HTML lacks interactivity signals (no event listeners, canvas, or animation)",
        )

    return True, "ok"


async def generate_game(prompt: str, model: str | None = None) -> dict:
    """Call OpenRouter to generate a game. Tries model fallback chain on failure."""
    models_to_try = [model] if model else MODELS

    last_error = None
    for current_model in models_to_try:
        try:
            result = await _call_openrouter(prompt, current_model)
            logger.info(
                "Generation succeeded: model=%s, time=%dms, tokens=%d",
                current_model,
                result["time_ms"],
                result["tokens"],
            )
            return result
        except Exception as e:
            logger.warning("Model %s failed: %s", current_model, e)
            last_error = e
            continue

    if last_error is None:
        raise RuntimeError("No models available for game generation")
    raise last_error


async def _call_openrouter(prompt: str, model: str) -> dict:
    """Make a single OpenRouter API call."""
    start = time.time()

    client = get_client()
    response = await client.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        },
    )
    response.raise_for_status()

    elapsed_ms = int((time.time() - start) * 1000)
    data = response.json()

    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    tokens = usage.get("total_tokens", 0)

    html = extract_html_from_response(content)
    if html is None:
        raise ValueError("Failed to extract HTML from model response")

    return {
        "html": html,
        "model": model,
        "tokens": tokens,
        "time_ms": elapsed_ms,
    }
