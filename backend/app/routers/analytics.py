from fastapi import APIRouter, Query, Request

from app.database import get_analytics, get_db, track_event

router = APIRouter()


@router.get("/analytics")
async def analytics_dashboard():
    """Public analytics dashboard — no PII, just aggregate numbers."""
    return await get_analytics()


@router.get("/analytics/games")
async def analytics_games(
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
):
    """List all games with details (for debugging/monitoring)."""
    db = await get_db()
    if status:
        cur = await db.execute(
            "SELECT id, prompt, status, error_message, "
            "generation_time_ms, model_used, created_at, parent_game_id "
            "FROM games WHERE status = ? ORDER BY created_at DESC LIMIT ?",
            (status, limit),
        )
    else:
        cur = await db.execute(
            "SELECT id, prompt, status, error_message, "
            "generation_time_ms, model_used, created_at, parent_game_id "
            "FROM games ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
    rows = await cur.fetchall()
    return [dict(r) for r in rows]


@router.post("/analytics/event")
async def track(request: Request):
    """Track a frontend event (page view, share, play, etc.)."""
    body = await request.json()
    event = body.get("event", "unknown")
    session_id = getattr(request.state, "session_id", None)
    game_id = body.get("game_id")
    meta = body.get("meta")
    await track_event(event, session_id, game_id, meta)
    return {"ok": True}
