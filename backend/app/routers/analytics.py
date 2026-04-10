from fastapi import APIRouter, Request

from app.database import get_analytics, track_event

router = APIRouter()


@router.get("/analytics")
async def analytics_dashboard():
    """Public analytics dashboard — no PII, just aggregate numbers."""
    return await get_analytics()


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
