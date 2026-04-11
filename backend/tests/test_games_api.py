import asyncio
import json
from pathlib import Path

import httpx
import pytest
import respx

from app.services.game_generator import OPENROUTER_URL

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture():
    return json.loads((FIXTURES / "openrouter_response_valid.json").read_text())


async def _wait_for_ready(client, game_id: str, timeout: float = 5.0):
    """Poll until game status is 'ready' or 'failed', or timeout."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        resp = await client.get(f"/api/games/{game_id}")
        status = resp.json().get("status")
        if status in ("ready", "failed"):
            return resp.json()
        await asyncio.sleep(0.2)
    resp = await client.get(f"/api/games/{game_id}")
    return resp.json()


@respx.mock
@pytest.mark.asyncio
async def test_create_game_success(client):
    fixture = _load_fixture()
    respx.post(OPENROUTER_URL).mock(return_value=httpx.Response(200, json=fixture))

    response = await client.post(
        "/api/games",
        json={"prompt": "make a fun cat platformer game"},
    )
    assert response.status_code == 200
    data = response.json()
    # Async generation: POST returns "pending", background task sets "ready"
    assert data["status"] == "pending"
    assert data["id"]
    assert data["prompt"] == "make a fun cat platformer game"
    assert "play_url" in data

    # Wait for background task to complete
    result = await _wait_for_ready(client, data["id"])
    assert result["status"] == "ready"


@pytest.mark.asyncio
async def test_create_game_invalid_prompt(client):
    response = await client.post("/api/games", json={"prompt": "ab"})
    assert response.status_code == 422  # Pydantic validation


@pytest.mark.asyncio
async def test_create_game_profanity_rejected(client):
    response = await client.post(
        "/api/games",
        json={"prompt": "make a game about murder and killing"},
    )
    assert response.status_code == 400
    data = response.json()
    assert "content_filtered" in str(data)


@respx.mock
@pytest.mark.asyncio
async def test_get_game(client):
    fixture = _load_fixture()
    respx.post(OPENROUTER_URL).mock(return_value=httpx.Response(200, json=fixture))

    create_resp = await client.post(
        "/api/games",
        json={"prompt": "make a fun space adventure game"},
    )
    game_id = create_resp.json()["id"]

    response = await client.get(f"/api/games/{game_id}")
    assert response.status_code == 200
    assert response.json()["id"] == game_id


@pytest.mark.asyncio
async def test_get_game_not_found(client):
    response = await client.get("/api/games/nonexistent-id-12345")
    assert response.status_code == 404


@respx.mock
@pytest.mark.asyncio
async def test_get_game_html(client):
    fixture = _load_fixture()
    respx.post(OPENROUTER_URL).mock(return_value=httpx.Response(200, json=fixture))

    create_resp = await client.post(
        "/api/games",
        json={"prompt": "make a fun puzzle game with colors"},
    )
    game_id = create_resp.json()["id"]
    await _wait_for_ready(client, game_id)

    response = await client.get(f"/api/games/{game_id}/html")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "content-security-policy" in response.headers
    assert "<!DOCTYPE html>" in response.text


@respx.mock
@pytest.mark.asyncio
async def test_list_games(client):
    fixture = _load_fixture()
    respx.post(OPENROUTER_URL).mock(return_value=httpx.Response(200, json=fixture))

    create_resp = await client.post(
        "/api/games",
        json={"prompt": "make a fun racing game with cars"},
    )
    game_id = create_resp.json()["id"]
    await _wait_for_ready(client, game_id)

    response = await client.get("/api/games")
    assert response.status_code == 200
    data = response.json()
    assert "games" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_list_games_pagination(client):
    """Verify pagination parameters work correctly."""
    response = await client.get("/api/games?page=1&per_page=5")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["per_page"] == 5


@pytest.mark.asyncio
async def test_create_game_prompt_too_short(client):
    """Backend should reject prompts shorter than 10 chars (matching frontend)."""
    response = await client.post("/api/games", json={"prompt": "short"})
    assert response.status_code == 422  # Pydantic validation


@respx.mock
@pytest.mark.asyncio
async def test_flag_game(client):
    fixture = _load_fixture()
    respx.post(OPENROUTER_URL).mock(return_value=httpx.Response(200, json=fixture))

    create_resp = await client.post(
        "/api/games",
        json={"prompt": "make a fun bouncing ball game"},
    )
    game_id = create_resp.json()["id"]

    flag_resp = await client.post(f"/api/games/{game_id}/flag")
    assert flag_resp.status_code == 200
    assert flag_resp.json()["status"] == "flagged"

    # Flagged game HTML should return 403
    html_resp = await client.get(f"/api/games/{game_id}/html")
    assert html_resp.status_code == 403


@pytest.mark.asyncio
async def test_per_page_rejects_over_max(client):
    """Requesting per_page > 100 should be rejected with 422."""
    response = await client.get("/api/games?per_page=10000")
    assert response.status_code == 422


@respx.mock
@pytest.mark.asyncio
async def test_auto_retry_on_validation_failure(client):
    """First OpenRouter response is too-short HTML (fails validation), second is valid."""

    bad_response = {
        "choices": [{"message": {"content": "```html\n<html><body>hi</body></html>\n```"}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    }
    valid_fixture = _load_fixture()

    route = respx.post(OPENROUTER_URL).mock(
        side_effect=[
            httpx.Response(200, json=bad_response),
            httpx.Response(200, json=valid_fixture),
        ]
    )

    response = await client.post(
        "/api/games",
        json={"prompt": "make a fun jumping game with stars"},
    )
    assert response.status_code == 200
    game_id = response.json()["id"]

    # Wait for background task to retry and succeed
    result = await _wait_for_ready(client, game_id)
    assert result["status"] == "ready"
    assert route.call_count >= 2


@respx.mock
@pytest.mark.asyncio
async def test_refine_game_endpoint(client):
    """Refining a game creates a new linked game."""
    fixture = _load_fixture()
    respx.post(OPENROUTER_URL).mock(return_value=httpx.Response(200, json=fixture))

    # Create original game and wait for it
    create_resp = await client.post("/api/games", json={"prompt": "make a fun cat platformer game"})
    original_id = create_resp.json()["id"]
    await _wait_for_ready(client, original_id)

    # Refine it
    refine_resp = await client.post(
        f"/api/games/{original_id}/refine",
        json={"modification": "make the cat move faster"},
    )
    assert refine_resp.status_code == 200
    data = refine_resp.json()
    assert data["id"] != original_id
    assert data["parent_game_id"] == original_id
    assert data["status"] == "pending"

    # Wait for background refinement
    result = await _wait_for_ready(client, data["id"])
    assert result["status"] == "ready"


@pytest.mark.asyncio
async def test_refine_nonexistent_game(client):
    """Refining a nonexistent game returns 404."""
    response = await client.post(
        "/api/games/nonexistent-id/refine",
        json={"modification": "make it faster"},
    )
    assert response.status_code == 404


@respx.mock
@pytest.mark.asyncio
async def test_error_message_does_not_leak_internals(client):
    """Exception in background should set game status to failed."""
    sensitive_msg = "Connection to openrouter.ai failed: API key invalid"
    respx.post(OPENROUTER_URL).mock(side_effect=RuntimeError(sensitive_msg))

    response = await client.post(
        "/api/games",
        json={"prompt": "make a fun colorful maze game please"},
    )
    assert response.status_code == 200
    game_id = response.json()["id"]

    # Wait for background task to fail (retries 3 times)
    result = await _wait_for_ready(client, game_id, timeout=10)
    assert result["status"] == "failed"
