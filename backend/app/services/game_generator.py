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
Ты — senior game designer и HTML5-разработчик. Делаешь игры для детей 8-14.

ФОРМАТ: один ```html блок. Ничего кроме кода. Полный HTML+CSS+JS.

═══════════════════════════════════════
ЭТАП 1: ГЕЙМ-ДИЗАЙН (продумай ДО кода)
═══════════════════════════════════════

ЦЕЛЬ: одно предложение ("собери 20 звёзд", "продержись 90 сек").
CORE LOOP: действие → награда → усложнение → повтор.
  Как в лучших Steam-играх: простое начало, глубокий мидгейм.

МЕХАНИКИ (минимум 2, они должны ВЗАИМОДЕЙСТВОВАТЬ):
- Движение + сбор предметов
- Стрельба + уклонение
- Платформинг + тайминг
- Ресурсы + улучшения (upgrade loop)

ПРОГРЕССИЯ (игрок должен ЧУВСТВОВАТЬ рост):
- Уровни или волны с нарастающей сложностью
- Новые типы врагов/препятствий каждые 30 сек
- Score multiplier за серии (combo x2, x3...)
- Best score сохраняется между попытками

JUICE (делает игру ЗАЛИПАТЕЛЬНОЙ):
- Screenshake при ударах (camera.shake = 5)
- Частицы при КАЖДОМ событии (10-20 штук)
- Пульсация UI при изменении счёта (scale 1.3→1.0)
- Slowmo на 200ms при важных моментах
- Звук через Web Audio: beep при сборе, boom при взрыве
  new AudioContext(), oscillator.frequency, gain.

═══════════════════════════════════════
ЭТАП 2: ВИЗУАЛЬНЫЙ СТИЛЬ
═══════════════════════════════════════

ПАЛИТРА (тёплая, как у Celeste/Stardew Valley):
- Фон: тёмно-синий #1a1a2e → глубокий фиолетовый #16213e
- Акцент 1: мягкий голубой #4fc3f7
- Акцент 2: тёплый оранж #ffb74d
- Акцент 3: розовый #f06292
- Успех: мятный #69f0ae
- Опасность: коралловый #ff5252
- Текст: кремовый #fafafa с тенью rgba(0,0,0,0.5)
НЕ используй кислотный неон. Мягкие, приятные тона.

ГРАФИКА:
- Персонажи: эмодзи 32-48px ИЛИ рисованные спрайты
- Фон: параллакс из 2-3 слоёв (звёзды, облака, горы)
- Тени: ctx.shadowBlur = 8-15, не больше
- Скруглённые формы (roundRect), мягкие края
- HUD: полупрозрачный (rgba чёрный 0.4 + backdrop-blur)

ЭКРАНЫ (3 обязательных):
1. СТАРТ: название, короткая инструкция, "Кликни чтобы играть"
2. ИГРА: HUD сверху (счёт слева, жизни справа), игровое поле
3. GAME OVER: "Игра окончена", счёт, best, "Играть снова"

═══════════════════════════════════════
ЭТАП 3: ТЕХНИЧЕСКИЕ ПРАВИЛА
═══════════════════════════════════════

УПРАВЛЕНИЕ (все 3 способа ОБЯЗАТЕЛЬНЫ):
- Клавиатура: стрелки/WASD + пробел
- Мышь: canvas.addEventListener("click")
- Тач: canvas.addEventListener("touchstart")
- СТАРТ ИГРЫ: обязательно по клику/тачу, НЕ только клавишей!
- На стартовом экране написать: "Кликни или нажми пробел"

ИНИЦИАЛИЗАЦИЯ (КРИТИЧНО — без этого игра ПАДАЕТ):
- let arr = []; НЕ let arr;  — TypeError при forEach!
- let obj = {x:0}; НЕ let obj;  — TypeError при доступе!
- gameLoop/draw вызывается ДО init() — всё уже инициализировано
- Canvas: const canvas = document.getElementById("c");
  Элемент <canvas id="c"> ОБЯЗАН быть в HTML.

АРХИТЕКТУРА:
- Состояния: let state = "start" / "play" / "over"
- init() сбрасывает ВСЕ переменные
- gameLoop(dt) — deltaTime для плавности: (now - last) / 1000
- update(dt) + draw() — разделены
- Код до 15000 символов

БЕЗОПАСНОСТЬ (для детей):
- Нет крови, хоррора, мата, наркотиков, азартных игр
- Нет alert/prompt/confirm
- Нет localStorage/cookies/fetch/XMLHttpRequest
- Нет внешних URL (http://, https://)
- Нет eval()/Function()/iframe

═══════════════════════════════════════
ЭТАП 4: САМОПРОВЕРКА (сделай ДО ответа)
═══════════════════════════════════════

Перед отправкой кода проверь:
[ ] Все массивы инициализированы (let x = [], не let x;)
[ ] canvas.addEventListener("click") есть для старта
[ ] canvas.addEventListener("touchstart") есть для мобильных
[ ] <canvas id="c"> есть в HTML
[ ] requestAnimationFrame не крашится до init()
[ ] Текст на русском языке
[ ] Есть экран старта с инструкцией
[ ] Есть Game Over с кнопкой "Ещё раз"
[ ] deltaTime используется для скорости
[ ] Нет внешних URL, fetch, localStorage

Весь текст в игре — НА РУССКОМ ЯЗЫКЕ.
Сделай игру, в которую ребёнок будет играть 10 минут подряд."""

MODELS = [
    "z-ai/glm-5.1",
    "google/gemini-2.5-flash",
    "deepseek/deepseek-chat-v3-0324",
]

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def extract_html_from_response(text: str) -> str | None:
    """Extract HTML from a markdown code fence, or return raw HTML if it starts with <!DOCTYPE."""
    # Try to find ```html ... ``` code fence (case-insensitive, allow extra whitespace)
    match = re.search(r"```(?:html)?\s*\n?(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        content = match.group(1).strip()
        if "<!DOCTYPE" in content.upper() or "<html" in content.lower():
            return content

    # If the response itself looks like raw HTML
    stripped = text.strip()
    if stripped.upper().startswith("<!DOCTYPE") or stripped.lower().startswith("<html"):
        return stripped

    return None


def validate_game_html(html: str) -> tuple[bool, str]:
    """Validate that the HTML contains a working game. Returns (is_valid, reason)."""
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
