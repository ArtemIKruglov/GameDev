import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import aiosqlite

from app.config import settings

_db: aiosqlite.Connection | None = None
_write_lock: asyncio.Lock | None = None


def _get_lock() -> asyncio.Lock:
    global _write_lock
    if _write_lock is None:
        _write_lock = asyncio.Lock()
    return _write_lock


SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    id                 TEXT PRIMARY KEY,
    prompt             TEXT NOT NULL,
    html_content       TEXT,
    status             TEXT NOT NULL DEFAULT 'pending',
    error_message      TEXT,
    model_used         TEXT,
    generation_time_ms INTEGER,
    token_count        INTEGER,
    session_id         TEXT,
    parent_game_id     TEXT,
    is_public          INTEGER NOT NULL DEFAULT 1,
    created_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_games_created_at ON games(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_games_session_id ON games(session_id);
CREATE INDEX IF NOT EXISTS idx_games_status ON games(status);

CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    event      TEXT NOT NULL,
    session_id TEXT,
    game_id    TEXT,
    meta       TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_events_event ON events(event);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);

CREATE TABLE IF NOT EXISTS rate_limits (
    session_id    TEXT NOT NULL,
    window_start  TEXT NOT NULL,
    request_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (session_id, window_start)
);
"""


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        db_path = settings.database_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _db = await aiosqlite.connect(db_path)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
        await _db.executescript(SCHEMA)
        await _db.commit()
    return _db


async def close_db() -> None:
    global _db, _write_lock
    if _db is not None:
        await _db.close()
        _db = None
    _write_lock = None


# --- Game CRUD ---


async def create_game(
    game_id: str,
    prompt: str,
    session_id: str | None = None,
    parent_game_id: str | None = None,
) -> dict:
    db = await get_db()
    async with _get_lock():
        await db.execute(
            """INSERT INTO games (id, prompt, session_id, parent_game_id, status)
               VALUES (?, ?, ?, ?, 'pending')""",
            (game_id, prompt, session_id, parent_game_id),
        )
        await db.commit()
    return await get_game(game_id)


async def update_game(
    game_id: str,
    *,
    html_content: str | None = None,
    status: str | None = None,
    error_message: str | None = None,
    model_used: str | None = None,
    generation_time_ms: int | None = None,
    token_count: int | None = None,
) -> dict | None:
    db = await get_db()
    updates = []
    values = []
    for field, value in [
        ("html_content", html_content),
        ("status", status),
        ("error_message", error_message),
        ("model_used", model_used),
        ("generation_time_ms", generation_time_ms),
        ("token_count", token_count),
    ]:
        if value is not None:
            updates.append(f"{field} = ?")
            values.append(value)
    if not updates:
        return await get_game(game_id)
    values.append(game_id)
    async with _get_lock():
        await db.execute(
            f"UPDATE games SET {', '.join(updates)} WHERE id = ?",
            values,
        )
        await db.commit()
    return await get_game(game_id)


async def get_game(game_id: str) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM games WHERE id = ?", (game_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def list_games(
    page: int = 1,
    per_page: int = 20,
    session_id: str | None = None,
    mine_only: bool = False,
) -> tuple[list[dict], int]:
    db = await get_db()
    conditions = []
    params: list = []

    if mine_only and session_id:
        conditions.append("session_id = ?")
        params.append(session_id)
    else:
        conditions.append("status = 'ready'")
        conditions.append("is_public = 1")

    where = " AND ".join(conditions) if conditions else "1=1"

    # Count
    cursor = await db.execute(f"SELECT COUNT(*) FROM games WHERE {where}", params)
    row = await cursor.fetchone()
    total = row[0]

    # Fetch page
    offset = (page - 1) * per_page
    cursor = await db.execute(
        f"SELECT * FROM games WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [per_page, offset],
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows], total


async def flag_game(game_id: str) -> bool:
    db = await get_db()
    async with _get_lock():
        await db.execute(
            "UPDATE games SET status = 'flagged', is_public = 0 WHERE id = ?",
            (game_id,),
        )
        await db.commit()
    return True


async def cleanup_expired_games(days: int = 30) -> int:
    """Delete games older than N days. Returns count of deleted games."""
    db = await get_db()
    cutoff = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")
    async with _get_lock():
        cursor = await db.execute(
            "DELETE FROM games WHERE created_at < ? AND status != 'flagged'",
            (cutoff,),
        )
        await db.commit()
        return cursor.rowcount


# --- Rate Limiting ---


async def get_rate_count(session_id: str, window_start: str) -> int:
    db = await get_db()
    cursor = await db.execute(
        "SELECT request_count FROM rate_limits WHERE session_id = ? AND window_start = ?",
        (session_id, window_start),
    )
    row = await cursor.fetchone()
    return row["request_count"] if row else 0


async def increment_rate_count(session_id: str, window_start: str) -> int:
    db = await get_db()
    async with _get_lock():
        await db.execute(
            """INSERT INTO rate_limits (session_id, window_start, request_count)
               VALUES (?, ?, 1)
               ON CONFLICT (session_id, window_start)
               DO UPDATE SET request_count = request_count + 1""",
            (session_id, window_start),
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT request_count FROM rate_limits WHERE session_id = ? AND window_start = ?",
            (session_id, window_start),
        )
        row = await cursor.fetchone()
    return row["request_count"]


async def increment_rate_counts_atomic(session_id: str, windows: list[str]) -> None:
    """Atomically increment rate counters for multiple windows in a single transaction."""
    db = await get_db()
    async with _get_lock():
        for window_start in windows:
            await db.execute(
                """INSERT INTO rate_limits (session_id, window_start, request_count)
                   VALUES (?, ?, 1)
                   ON CONFLICT (session_id, window_start)
               DO UPDATE SET request_count = request_count + 1""",
                (session_id, window_start),
            )
        await db.commit()


# --- Analytics ---


async def track_event(
    event: str,
    session_id: str | None = None,
    game_id: str | None = None,
    meta: str | None = None,
) -> None:
    """Track an analytics event. Never raises — analytics must not break the app."""
    try:
        db = await get_db()
        async with _get_lock():
            await db.execute(
                "INSERT INTO events (event, session_id, game_id, meta) VALUES (?, ?, ?, ?)",
                (event, session_id, game_id, meta),
            )
            await db.commit()
    except Exception:
        pass  # Analytics should never break the main flow
        await db.commit()


async def get_analytics() -> dict:
    """Get analytics summary."""
    db = await get_db()

    result: dict = {}

    # Total games
    cur = await db.execute("SELECT COUNT(*) FROM games")
    result["total_games"] = (await cur.fetchone())[0]

    # Games by status
    cur = await db.execute("SELECT status, COUNT(*) as cnt FROM games GROUP BY status")
    result["games_by_status"] = {r["status"]: r["cnt"] for r in await cur.fetchall()}

    # Unique sessions
    cur = await db.execute(
        "SELECT COUNT(DISTINCT session_id) FROM games WHERE session_id IS NOT NULL"
    )
    result["unique_users"] = (await cur.fetchone())[0]

    # Returning users (sessions with >1 game)
    cur = await db.execute(
        "SELECT COUNT(*) FROM ("
        "  SELECT session_id FROM games"
        "  WHERE session_id IS NOT NULL"
        "  GROUP BY session_id HAVING COUNT(*) > 1"
        ")"
    )
    result["returning_users"] = (await cur.fetchone())[0]

    # Games today
    cur = await db.execute("SELECT COUNT(*) FROM games WHERE created_at >= date('now')")
    result["games_today"] = (await cur.fetchone())[0]

    # Games this week
    cur = await db.execute("SELECT COUNT(*) FROM games WHERE created_at >= date('now', '-7 days')")
    result["games_this_week"] = (await cur.fetchone())[0]

    # Avg generation time (ready games only)
    cur = await db.execute(
        "SELECT AVG(generation_time_ms), MIN(generation_time_ms), "
        "MAX(generation_time_ms) FROM games WHERE status = 'ready'"
    )
    row = await cur.fetchone()
    result["generation_time"] = {
        "avg_ms": round(row[0]) if row[0] else 0,
        "min_ms": row[1] or 0,
        "max_ms": row[2] or 0,
    }

    # Total tokens used
    cur = await db.execute("SELECT SUM(token_count) FROM games WHERE token_count IS NOT NULL")
    result["total_tokens"] = (await cur.fetchone())[0] or 0

    # Success rate
    cur = await db.execute("SELECT COUNT(*) FROM games WHERE status = 'ready'")
    ready = (await cur.fetchone())[0]
    cur = await db.execute("SELECT COUNT(*) FROM games WHERE status IN ('ready', 'failed')")
    total_finished = (await cur.fetchone())[0]
    result["success_rate"] = round(ready / total_finished * 100, 1) if total_finished > 0 else 0

    # Models used
    cur = await db.execute(
        "SELECT model_used, COUNT(*) as cnt FROM games "
        "WHERE model_used IS NOT NULL GROUP BY model_used "
        "ORDER BY cnt DESC"
    )
    result["models"] = {r["model_used"]: r["cnt"] for r in await cur.fetchall()}

    # Refinements count
    cur = await db.execute("SELECT COUNT(*) FROM games WHERE parent_game_id IS NOT NULL")
    result["refinements"] = (await cur.fetchone())[0]

    # Shares (from events)
    cur = await db.execute("SELECT COUNT(*) FROM events WHERE event = 'share'")
    result["shares"] = (await cur.fetchone())[0]

    # Page views (from events)
    cur = await db.execute(
        "SELECT event, COUNT(*) as cnt FROM events GROUP BY event ORDER BY cnt DESC"
    )
    result["events"] = {r["event"]: r["cnt"] for r in await cur.fetchall()}

    # Daily games (last 7 days)
    cur = await db.execute(
        "SELECT date(created_at) as day, COUNT(*) as cnt "
        "FROM games WHERE created_at >= date('now', '-7 days') "
        "GROUP BY day ORDER BY day"
    )
    result["daily_games"] = [{"date": r["day"], "count": r["cnt"]} for r in await cur.fetchall()]

    return result
