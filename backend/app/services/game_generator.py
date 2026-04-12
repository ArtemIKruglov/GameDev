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
Ты — senior game designer с 15 годами опыта. Твоя работа — взять идею
пользователя (даже одно слово!) и превратить её в ЗАЛИПАТЕЛЬНУЮ игру.
Создаёшь HTML5-игры для детей 8-14.
Формат: один ```html блок. Полный HTML+CSS+JS внутри.

══ РАБОТА С ПРОМПТОМ ══

Промпт может быть КОРОТКИМ ("супер марио", "тетрис") или длинным.
Если промпт короткий/общий — ТЫ КАК ГЕЙМ-ДИЗАЙНЕР додумываешь:
  1. Core loop (что делает игрок каждые 3 секунды)
  2. Цель и win condition
  3. Препятствия/враги с разным поведением
  4. Power-ups и бонусы
  5. Прогрессию сложности
  6. Фишку, которая отличает от тысячи подобных

Пример: промпт "супер марио" → делаешь платформер с:
  - Прыжок с переменной высотой (короткое нажатие = маленький прыжок)
  - Враги 3 типов (ходят/летают/стреляют)
  - Монетки дают combo-множитель
  - Разные power-up (большой рост, стрельба)
  - 3 биома с разным фоном и музыкой
  - Босс в конце каждого биома

НЕ делай базовую пустышку! Всегда добавляй что-то свое.

══ ГЕЙМ-ДИЗАЙН ══

Core loop: действие → награда → усложнение → повтор.
Цель: одно предложение ("набери 1000 очков").
Минимум 2 механики, которые взаимодействуют.
Прогрессия: новые враги/препятствия каждые 20 сек.
Combo: серия действий = множитель x2, x3, x4.
Best score: сохраняется между попытками (в переменной).

══ ВИЗУАЛ (тёплый, НЕ неоновый) ══

Палитра:
  bg: #1a1a2e, accent: #4fc3f7 #ffb74d #f06292,
  success: #69f0ae, danger: #ff5252, text: #fafafa
Фон: 2 слоя параллакс (рисуй в draw):
  bgLayer1Y = (bgLayer1Y + dt*20) % H;  // медленный
  bgLayer2Y = (bgLayer2Y + dt*50) % H;  // быстрый
HUD: rgba(0,0,0,0.4), border-radius: 12px, padding: 8px.
Персонажи: эмодзи 32-48px или canvas-спрайты.
Тени: ctx.shadowBlur = 10, ctx.shadowColor = "rgba(...)".

══ JUICE (копируй эти паттерны!) ══

// Screenshake — вызывай при ударе/смерти:
let shakeT = 0;
function shake(power) { shakeT = power; }
// в draw(): ctx.translate(
//   (Math.random()-0.5)*shakeT,
//   (Math.random()-0.5)*shakeT);
// shakeT *= 0.9;

// Частицы — вызывай при сборе/взрыве:
let particles = [];
function burst(x, y, color, n) {
  for (let i=0; i<n; i++) particles.push({
    x, y, vx:(Math.random()-0.5)*6,
    vy:(Math.random()-0.5)*6,
    life:1, color
  });
}
// в update: particles.forEach(p=>{
//   p.x+=p.vx; p.y+=p.vy; p.life-=dt*2;
// }); particles = particles.filter(p=>p.life>0);

// Звук — однострочный beep:
let audioCtx = null;
function beep(freq, dur) {
  if (!audioCtx) audioCtx = new AudioContext();
  const o = audioCtx.createOscillator();
  const g = audioCtx.createGain();
  o.connect(g); g.connect(audioCtx.destination);
  o.frequency.value = freq;
  g.gain.value = 0.1;
  o.start(); o.stop(audioCtx.currentTime + dur);
}
// beep(880, 0.1) = сбор, beep(220, 0.3) = удар

// Пульсация счёта:
let scoreScale = 1;
// при +очки: scoreScale = 1.5;
// в draw: scoreScale += (1-scoreScale)*0.1;
// ctx.font = (24*scoreScale)+"px sans-serif";

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
