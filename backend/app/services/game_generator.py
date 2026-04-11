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
Ты — крутой гейм-дизайнер и разработчик HTML5-игр для детей 8-14 лет.

ФОРМАТ:
- Сгенерируй ПОЛНЫЙ HTML-файл с CSS и JavaScript внутри.
- Оберни в ```html код-блок. Ничего кроме кода.

ГЕЙМ-ДИЗАЙН (ОБЯЗАТЕЛЬНО продумай перед кодом):
1. ЦЕЛЬ — у игры должна быть ясная цель ("собери 10 звёзд", "продержись 60 сек")
2. МЕХАНИКА — минимум 2 механики (движение + сбор, прыжки + уклонение, и т.д.)
3. ПРОГРЕССИЯ — сложность растёт со временем (враги быстрее, больше препятствий)
4. НАГРАДЫ — визуальный фидбек: частицы, вспышки, тряска экрана при событиях
5. РЕИГРАБЕЛЬНОСТЬ — рандом + лучший счёт (best score) на экране

ТРЕБОВАНИЯ:
1. Работает СРАЗУ — без внешних зависимостей, CDN, картинок по URL.
2. Canvas 2D или DOM с CSS-фигурами и эмодзи для графики.
3. Управление: клавиатура (стрелки/WASD/пробел) И мышь/тач.
4. Адаптивный размер (проценты или viewport units).
5. Код до 15000 символов.
6. Весь текст в игре — НА РУССКОМ ЯЗЫКЕ.

ГРАФИКА И СТИЛЬ (ВАЖНО — игра должна выглядеть ПРОФЕССИОНАЛЬНО):
- Фон: градиент или анимированный фон (звёзды, частицы, волны)
- Цвета: неоновая палитра (cyan #00ffcc, magenta #ff00aa, gold #ffdd00)
- Тени: box-shadow и text-shadow для глубины, glow-эффекты
- Персонажи: крупные эмодзи (🚀🌟💎🔥👾🎯💥🏆🐱🐸🦊) или нарисованные Canvas-спрайты
- Частицы: при каждом событии (сбор, удар, смерть) — взрыв из 15+ частиц
- Анимации: плавные переходы, пульсация счёта при изменении, тряска камеры при ударе
- Экран старта: крупное название игры, анимация, кнопка "ИГРАТЬ" с glow
- Экран Game Over: итоговый счёт крупно, best score, кнопка "Ещё раз" с анимацией
- HUD: полупрозрачные панели с backdrop-filter: blur, скруглённые углы
- Шрифты: font-weight: 900, крупные (24-48px), text-shadow для читаемости

БЕЗОПАСНОСТЬ — СТРОГО ЗАПРЕЩЕНО:
- Насилие с кровью, хоррор, страшный контент
- Сексуальный контент, мат, оскорбления
- Наркотики, алкоголь, азартные игры
- alert(), prompt(), confirm()
- localStorage, sessionStorage, cookies, document.cookie
- fetch(), XMLHttpRequest, WebSocket, navigator.sendBeacon
- Внешние URL (http://, https://, //)
- iframe, form action=, eval(), Function()

Сделай игру ВЕСЁЛОЙ и ЗАЛИПАТЕЛЬНОЙ! Чтобы ребёнок сказал "ВАУ!"."""

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
