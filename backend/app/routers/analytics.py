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


@router.get("/analytics/engagement")
async def analytics_engagement():
    """Per-game engagement: views, plays, play time, interactions."""
    db = await get_db()

    # Game views (how many times each game page was opened)
    cur = await db.execute(
        "SELECT e.game_id, g.prompt, "
        "  SUM(CASE WHEN e.event='game_view' THEN 1 ELSE 0 END) as views, "
        "  SUM(CASE WHEN e.event='game_play' THEN 1 ELSE 0 END) as plays, "
        "  COUNT(CASE WHEN e.event='game_activity' THEN 1 END) as activity_pings "
        "FROM events e "
        "LEFT JOIN games g ON g.id = e.game_id "
        "WHERE e.game_id IS NOT NULL "
        "GROUP BY e.game_id "
        "ORDER BY plays DESC, views DESC"
    )
    games = []
    for r in await cur.fetchall():
        games.append(dict(r))

    # Parse activity meta to get total play seconds per game
    for game in games:
        cur2 = await db.execute(
            "SELECT meta FROM events "
            "WHERE game_id = ? AND event = 'game_activity' "
            "ORDER BY created_at DESC LIMIT 1",
            (game["game_id"],),
        )
        row = await cur2.fetchone()
        if row and row["meta"]:
            # meta format: "clicks=5,keys=12,sec=30"
            parts = dict(p.split("=") for p in row["meta"].split(",") if "=" in p)
            game["total_clicks"] = int(parts.get("clicks", 0))
            game["total_keys"] = int(parts.get("keys", 0))
            game["play_seconds"] = int(parts.get("sec", 0))
        else:
            game["total_clicks"] = 0
            game["total_keys"] = 0
            game["play_seconds"] = 0

        # Truncate prompt for readability
        if game.get("prompt"):
            game["prompt"] = game["prompt"][:80]

    # Summary
    total_play_sec = sum(g["play_seconds"] for g in games)
    total_interactions = sum(g["total_clicks"] + g["total_keys"] for g in games)

    return {
        "games": games,
        "summary": {
            "total_games_viewed": len(games),
            "total_play_seconds": total_play_sec,
            "total_interactions": total_interactions,
            "avg_play_seconds": (round(total_play_sec / len(games)) if games else 0),
        },
    }


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
