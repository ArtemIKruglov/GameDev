import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import aiosqlite

from app.config import settings

_db: aiosqlite.Connection | None = None
_write_lock = asyncio.Lock()

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
    global _db
    if _db is not None:
        await _db.close()
        _db = None


# --- Game CRUD ---


async def create_game(
    game_id: str,
    prompt: str,
    session_id: str | None = None,
    parent_game_id: str | None = None,
) -> dict:
    db = await get_db()
    async with _write_lock:
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
    async with _write_lock:
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
    async with _write_lock:
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
    async with _write_lock:
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
    async with _write_lock:
        await db.execute(
            """INSERT INTO rate_limits (session_id, window_start, request_count)
               VALUES (?, ?, 1)
               ON CONFLICT (session_id, window_start) DO UPDATE SET request_count = request_count + 1""",
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
    async with _write_lock:
        for window_start in windows:
            await db.execute(
                """INSERT INTO rate_limits (session_id, window_start, request_count)
                   VALUES (?, ?, 1)
                   ON CONFLICT (session_id, window_start) DO UPDATE SET request_count = request_count + 1""",
                (session_id, window_start),
            )
        await db.commit()
