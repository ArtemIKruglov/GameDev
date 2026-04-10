import logging
import uuid

from fastapi import APIRouter, HTTPException, Query, Request, Response

from app.database import create_game, flag_game, get_game, list_games, update_game
from app.models import (
    ErrorResponse,
    GameCreateRequest,
    GameListResponse,
    GameRefineRequest,
    GameResponse,
)
from app.services.content_filter import filter_input, filter_output
from app.services.game_generator import generate_game, validate_game_html
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

    # Create pending game
    game_id = str(uuid.uuid4())
    await create_game(game_id, body.prompt, session_id=session_id)
    logger.info("Game %s created (pending) for session %s", game_id, session_id)

    try:
        max_attempts = 2

        for attempt in range(max_attempts):
            prompt_text = body.prompt
            if attempt > 0:
                prompt_text = f"{body.prompt}\n\nIMPORTANT: Generate a working, complete HTML game. Ensure all JavaScript is correct."
                logger.info("Game %s: retry attempt %d", game_id, attempt + 1)

            result = await generate_game(prompt_text)

            # Filter output
            output_safe, output_reason = filter_output(result["html"])
            if not output_safe:
                logger.warning("Game %s: output filter failed (attempt %d): %s", game_id, attempt + 1, output_reason)
                if attempt < max_attempts - 1:
                    continue
                await update_game(game_id, status="failed", error_message=output_reason)
                raise HTTPException(
                    status_code=400,
                    detail={"error": "content_filtered", "message": f"Generated game failed safety check: {output_reason}"},
                )

            # Validate quality
            is_valid, validation_msg = validate_game_html(result["html"])
            if not is_valid:
                logger.warning("Game %s: validation failed (attempt %d): %s", game_id, attempt + 1, validation_msg)
                if attempt < max_attempts - 1:
                    continue
                await update_game(game_id, status="failed", error_message=validation_msg)
                raise HTTPException(
                    status_code=503,
                    detail={"error": "generation_failed", "message": "Game creation failed. Please try again!"},
                )

            # Success
            break

        game = await update_game(
            game_id,
            html_content=result["html"],
            status="ready",
            model_used=result["model"],
            generation_time_ms=result["time_ms"],
            token_count=result["tokens"],
        )

        # Record rate usage only after successful generation
        await record_rate_usage(session_id)
        logger.info("Game %s completed: model=%s, time=%dms, tokens=%d", game_id, result["model"], result["time_ms"], result["tokens"])

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Game generation failed for game %s", game_id)
        await update_game(game_id, status="failed", error_message=str(e))
        raise HTTPException(
            status_code=503,
            detail={"error": "generation_failed", "message": "Game creation failed. Please try again!"},
        )

    return _game_to_response(game)


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
            detail={"error": "generation_failed", "message": "Original game has no content to refine"},
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

    # Create new game linked to original
    new_game_id = str(uuid.uuid4())
    await create_game(
        new_game_id,
        f"{original['prompt']} (refined: {body.modification})",
        session_id=session_id,
        parent_game_id=game_id,
    )

    # Build refinement prompt — include original HTML + modification
    refine_prompt = (
        f"Here is an existing HTML game:\n\n"
        f"```html\n{original['html_content']}\n```\n\n"
        f"The player wants to change: {body.modification}\n\n"
        f"Generate the COMPLETE updated HTML game with this change applied. "
        f"Keep everything else the same."
    )

    try:
        result = await generate_game(refine_prompt)

        output_safe, output_reason = filter_output(result["html"])
        if not output_safe:
            await update_game(new_game_id, status="failed", error_message=output_reason)
            raise HTTPException(
                status_code=400,
                detail={"error": "content_filtered", "message": "Refined game failed safety check"},
            )

        is_valid, validation_msg = validate_game_html(result["html"])
        if not is_valid:
            await update_game(new_game_id, status="failed", error_message=validation_msg)
            raise HTTPException(
                status_code=503,
                detail={"error": "generation_failed", "message": "The refined game didn't come out right. Try again!"},
            )

        game = await update_game(
            new_game_id,
            html_content=result["html"],
            status="ready",
            model_used=result["model"],
            generation_time_ms=result["time_ms"],
            token_count=result["tokens"],
        )
        await record_rate_usage(session_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Game refinement failed for game %s", new_game_id)
        await update_game(new_game_id, status="failed", error_message=str(e))
        raise HTTPException(
            status_code=503,
            detail={"error": "generation_failed", "message": "Refinement failed. Please try again!"},
        )

    return _game_to_response(game)
