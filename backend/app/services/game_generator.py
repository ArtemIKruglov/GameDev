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

SYSTEM_PROMPT = """You are a game developer creating fun, safe HTML5 games for children ages 8-14.

OUTPUT FORMAT:
- Generate a COMPLETE, SINGLE HTML file with ALL CSS and JavaScript inline.
- Wrap your output in a single ```html code fence. Nothing else before or after.

GAME REQUIREMENTS:
1. Must work IMMEDIATELY when opened — no external dependencies, no CDN links, no images from URLs.
2. Use Canvas 2D API or DOM manipulation with CSS shapes/emoji for graphics.
3. Must include: clear on-screen instructions, visible score/progress, restart button, win/lose condition.
4. Support BOTH keyboard (arrow keys/WASD/space) AND mouse/touch click controls.
5. Must be responsive — use percentage-based sizing or viewport units.
6. Keep total code under 15,000 characters.

STYLE:
- Bright, cheerful, colorful — use gradients, rounded corners, smooth CSS animations.
- Large readable text (minimum 16px equivalent).
- Show a brief instruction overlay when game starts (dismiss on first keypress/click).

SAFETY — STRICTLY FORBIDDEN:
- Violence with blood/gore, horror, scary content
- Sexual or romantic content, profanity, slurs, hate speech
- Drug/alcohol/gambling references
- alert(), prompt(), confirm() dialogs
- localStorage, sessionStorage, cookies, document.cookie
- fetch(), XMLHttpRequest, WebSocket, navigator.sendBeacon
- External URLs (http://, https://, //)
- iframe, form action=, eval(), Function(), setTimeout with string arg

Make the game FUN. Simple to learn, satisfying to play, with a clear feedback loop."""

MODELS = [
    "google/gemini-2.5-flash",
    "google/gemini-2.5-pro",
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
        return False, "Game HTML lacks interactivity signals (no event listeners, canvas, or animation)"

    return True, "ok"


async def generate_game(prompt: str, model: str | None = None) -> dict:
    """Call OpenRouter to generate a game. Tries model fallback chain on failure."""
    models_to_try = [model] if model else MODELS

    last_error = None
    for current_model in models_to_try:
        try:
            result = await _call_openrouter(prompt, current_model)
            logger.info("Generation succeeded: model=%s, time=%dms, tokens=%d", current_model, result["time_ms"], result["tokens"])
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
