import logging
import uuid

from fastapi import APIRouter, HTTPException, Query, Request, Response

from app.database import (
    create_game,
    flag_game,
    get_game,
    list_games,
    track_event,
    update_game,
)
from app.models import (
    ErrorResponse,
    GameCreateRequest,
    GameListResponse,
    GameRefineRequest,
    GameResponse,
)
from app.services.content_filter import filter_input, filter_output
from app.services.game_generator import generate_game, validate_game_html
from app.services.game_validator import full_validate
from app.services.rate_limiter import check_rate_limit, record_rate_usage

logger = logging.getLogger(__name__)

router = APIRouter()


def _game_to_response(game: dict) -> GameResponse:
    return GameResponse(
        id=game["id"],
        prompt=game["prompt"],
        status=game["status"],
        play_url=f"/play/{game['id']}",
        created_at=game["created_at"],
        generation_time_ms=game.get("generation_time_ms"),
        parent_game_id=game.get("parent_game_id"),
    )


@router.post(
    "/games",
    response_model=GameResponse,
    responses={400: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
async def create_game_endpoint(body: GameCreateRequest, request: Request):
    session_id = getattr(request.state, "session_id", "anonymous")

    # Rate limit (read-only check — does NOT increment counters)
    allowed, retry_after = await check_rate_limit(session_id)
    if not allowed:
        logger.info("Rate limit hit for session %s, retry_after=%d", session_id, retry_after)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "message": "Too many requests. Please wait before creating another game.",
                "retry_after_seconds": retry_after,
            },
        )

    # Filter input
    is_safe, reason = filter_input(body.prompt)
    if not is_safe:
        logger.info("Input filtered for session %s: %s", session_id, reason)
        raise HTTPException(
            status_code=400,
            detail={"error": "content_filtered", "message": reason},
        )

    # Create pending game — return IMMEDIATELY, generate in background
    game_id = str(uuid.uuid4())
    await create_game(game_id, body.prompt, session_id=session_id)
    logger.info("Game %s created (pending) for session %s", game_id, session_id)

    # Launch background generation task
    import asyncio

    asyncio.create_task(_generate_in_background(game_id, body.prompt, session_id))
    await track_event("game_create", session_id, game_id)

    # Return pending game immediately — frontend will poll
    game = await get_game(game_id)
    return _game_to_response(game)


def _enrich_short_prompt(prompt: str) -> str:
    """For short prompts (<30 chars), add context to help the model
    generate a fuller, more engaging game.
    """
    p = prompt.strip()
    if len(p) >= 30:
        return p

    # Short prompt — add rich context
    enriched = (
        f"{p}\n\n"
        "Промпт короткий — сам придумай интересные детали! "
        "Добавь: минимум 2 механики (например, прыжки + сбор, "
        "или стрельба + уклонение), прогрессию сложности "
        "(враги быстрее со временем), score multiplier за серии, "
        "яркие анимации и частицы, звуки beep при событиях. "
        "Игра должна залипать на 5+ минут — придумай крутой core loop."
    )
    return enriched


async def _generate_in_background(game_id: str, prompt: str, session_id: str) -> None:
    """Background task: generate game via AI, validate, retry with error context, update DB."""
    # Enrich short prompts for richer games
    prompt = _enrich_short_prompt(prompt)

    try:
        max_attempts = (
            3  # Increased: original + retry with generic hint + retry with specific errors
        )
        result = None
        last_issues: list[str] = []

        for attempt in range(max_attempts):
            prompt_text = prompt
            if attempt == 1:
                # First retry — generic hint
                prompt_text = (
                    f"{prompt}\n\nIMPORTANT: Generate a working, "
                    "complete HTML game. Ensure all JavaScript is correct. "
                    "Initialize ALL arrays as `let arr = [];` NOT `let arr;`."
                )
                logger.info("Game %s: retry attempt %d (generic hint)", game_id, attempt + 1)
            elif attempt >= 2 and last_issues:
                # Second retry — specific errors from validation
                error_details = "\n".join(f"- {issue}" for issue in last_issues[:5])
                prompt_text = (
                    f"{prompt}\n\n"
                    "CRITICAL FIX REQUIRED — the previous version had these JavaScript errors:\n"
                    f"{error_details}\n\n"
                    "Fix ALL of these issues. Ensure every variable used in gameLoop/draw/update "
                    "is initialized at declaration time with a default value ([] for arrays, "
                    "{{}} for objects, 0 for numbers)."
                )
                logger.info(
                    "Game %s: retry attempt %d with %d specific errors",
                    game_id,
                    attempt + 1,
                    len(last_issues),
                )

            result = await generate_game(prompt_text)

            # --- Safety filter ---
            output_safe, _ = filter_output(result["html"])
            if not output_safe:
                if attempt < max_attempts - 1:
                    last_issues = ["Output failed safety filter"]
                    continue
                await update_game(game_id, status="failed", error_message="safety")
                return

            # --- Basic structure validation (fast) ---
            is_valid, reason = validate_game_html(result["html"])
            if not is_valid:
                if attempt < max_attempts - 1:
                    last_issues = [reason]
                    continue
                await update_game(game_id, status="failed", error_message="invalid")
                return

            # --- Deep validation: static + runtime (new!) ---
            passed, issues = await full_validate(result["html"])
            if not passed:
                logger.warning(
                    "Game %s failed deep validation (attempt %d): %s",
                    game_id,
                    attempt + 1,
                    "; ".join(issues[:3]),
                )
                if attempt < max_attempts - 1:
                    last_issues = issues
                    continue
                # Last attempt failed — save anyway but log warning
                logger.warning(
                    "Game %s: deep validation failed on final attempt, saving with issues",
                    game_id,
                )

            break

        if result:
            await update_game(
                game_id,
                html_content=result["html"],
                status="ready",
                model_used=result["model"],
                generation_time_ms=result["time_ms"],
                token_count=result["tokens"],
            )
            await record_rate_usage(session_id)
            await track_event("game_ready", session_id, game_id, result["model"])
            logger.info(
                "Game %s ready: model=%s, time=%dms",
                game_id,
                result["model"],
                result["time_ms"],
            )

    except Exception as e:
        logger.exception("Background generation failed for %s", game_id)
        await update_game(game_id, status="failed", error_message=str(e))
        await track_event("game_failed", session_id, game_id)


@router.get("/games", response_model=GameListResponse)
async def list_games_endpoint(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    mine: bool = False,
):
    session_id = getattr(request.state, "session_id", None)
    games, total = await list_games(
        page=page,
        per_page=per_page,
        session_id=session_id,
        mine_only=mine,
    )
    return GameListResponse(
        games=[_game_to_response(g) for g in games],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/games/{game_id}", response_model=GameResponse)
async def get_game_endpoint(game_id: str):
    game = await get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return _game_to_response(game)


@router.get("/games/{game_id}/html")
async def get_game_html(game_id: str):
    game = await get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game["status"] == "flagged":
        raise HTTPException(status_code=403, detail="This game has been flagged")
    if not game.get("html_content"):
        raise HTTPException(status_code=404, detail="Game HTML not available")

    return Response(
        content=game["html_content"],
        media_type="text/html",
        headers={
            "Content-Security-Policy": (
                "default-src 'unsafe-inline' data:; "
                "script-src 'unsafe-inline'; "
                "style-src 'unsafe-inline'; "
                "img-src data: blob:; "
                "connect-src 'none'; "
                "frame-src 'none'; "
                "frame-ancestors 'none'; "
                "form-action 'none'; "
                "base-uri 'none'"
            ),
        },
    )


@router.post("/games/{game_id}/flag")
async def flag_game_endpoint(game_id: str):
    game = await get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    await flag_game(game_id)
    return {"status": "flagged"}


@router.post(
    "/games/{game_id}/refine",
    response_model=GameResponse,
    responses={400: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
async def refine_game_endpoint(game_id: str, body: GameRefineRequest, request: Request):
    """Refine an existing game with a modification request."""
    session_id = getattr(request.state, "session_id", "anonymous")

    # Get original game
    original = await get_game(game_id)
    if not original:
        raise HTTPException(status_code=404, detail="Original game not found")
    if not original.get("html_content"):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "generation_failed",
                "message": "Original game has no content to refine",
            },
        )

    # Rate limit
    allowed, retry_after = await check_rate_limit(session_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "message": "Too many requests. Please wait before creating another game.",
                "retry_after_seconds": retry_after,
            },
        )

    # Filter the modification request
    is_safe, reason = filter_input(body.modification)
    if not is_safe:
        raise HTTPException(
            status_code=400,
            detail={"error": "content_filtered", "message": reason},
        )

    # Create new game linked to original — return immediately
    new_game_id = str(uuid.uuid4())
    new_prompt = f"{original['prompt']} (refined: {body.modification})"
    await create_game(
        new_game_id,
        new_prompt,
        session_id=session_id,
        parent_game_id=game_id,
    )

    # Build refinement prompt
    refine_prompt = (
        f"Вот существующая HTML-игра:\n\n"
        f"```html\n{original['html_content']}\n```\n\n"
        f"Игрок хочет изменить: {body.modification}\n\n"
        f"Сгенерируй ПОЛНУЮ обновлённую HTML-игру с этим изменением. "
        f"Остальное оставь как есть."
    )

    import asyncio

    asyncio.create_task(_generate_in_background(new_game_id, refine_prompt, session_id))

    game = await get_game(new_game_id)
    return _game_to_response(game)
