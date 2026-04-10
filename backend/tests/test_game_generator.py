import json
from pathlib import Path

import httpx
import pytest
import respx

from app.services.game_generator import (
    MODELS,
    OPENROUTER_URL,
    extract_html_from_response,
    generate_game,
    validate_game_html,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_html_from_code_fence():
    text = "```html\n<!DOCTYPE html><html><body><h1>Hello</h1></body></html>\n```"
    result = extract_html_from_response(text)
    assert result is not None
    assert result.startswith("<!DOCTYPE html>")


def test_extract_html_from_raw_response():
    text = "<!DOCTYPE html><html><body><h1>Hello</h1></body></html>"
    result = extract_html_from_response(text)
    assert result is not None
    assert "<!DOCTYPE html>" in result


def test_extract_html_returns_none_for_invalid():
    result = extract_html_from_response("This is just some plain text without any HTML.")
    assert result is None


def test_validate_game_html_valid():
    html = (
        "<!DOCTYPE html><html><head><title>Game</title></head>"
        "<body><canvas id='c'></canvas>"
        "<script>document.addEventListener('keydown', function(){}); "
        "requestAnimationFrame(function draw(){});</script></body></html>"
    )
    is_valid, reason = validate_game_html(html)
    assert is_valid is True
    assert reason == "ok"


def test_validate_game_html_no_script():
    # Must be > 200 chars to pass length check and hit the script check
    html = (
        "<!DOCTYPE html><html><head><title>Not A Game</title></head><body>"
        "<h1>This is just a webpage with no game at all, just lots of text content</h1>"
        "<p>There is plenty of content here but no script tags whatsoever. "
        "We need to make this longer than 200 characters to bypass the length check.</p>"
        "</body></html>"
    )
    assert len(html) > 200
    is_valid, reason = validate_game_html(html)
    assert is_valid is False
    assert "no JavaScript" in reason


def test_validate_game_html_too_short():
    html = "<script>x()</script>"
    is_valid, reason = validate_game_html(html)
    assert is_valid is False
    assert "too short" in reason


@respx.mock
@pytest.mark.asyncio
async def test_generate_game_with_mocked_api():
    fixture = json.loads((FIXTURES / "openrouter_response_valid.json").read_text())

    respx.post(OPENROUTER_URL).mock(return_value=httpx.Response(200, json=fixture))

    result = await generate_game("make a cat game")
    assert "html" in result
    assert "<!DOCTYPE html>" in result["html"]
    assert result["tokens"] == 800
    assert result["model"] == MODELS[0]
    assert result["time_ms"] >= 0


@respx.mock
@pytest.mark.asyncio
async def test_model_fallback_on_failure():
    """When primary model fails, fallback model should be tried."""
    from app.services.game_generator import MODELS

    fixture = json.loads((FIXTURES / "openrouter_response_valid.json").read_text())

    # First call fails (primary model), second succeeds (fallback)
    route = respx.post(OPENROUTER_URL)
    route.side_effect = [
        httpx.Response(500, json={"error": "model_overloaded"}),
        httpx.Response(200, json=fixture),
    ]

    result = await generate_game("make a cat game")
    assert result["html"] is not None
    # Should have used the fallback model
    assert result["model"] == MODELS[1]
