import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import close_db, get_db
from app.middleware.session import SessionMiddleware
from app.routers import analytics, games, health
from app.services.game_generator import close_client

logger = logging.getLogger(__name__)


async def _periodic_cleanup():
    """Run game cleanup every 24 hours."""
    while True:
        await asyncio.sleep(86400)  # 24 hours
        try:
            from app.database import cleanup_expired_games

            deleted = await cleanup_expired_games()
            if deleted:
                logger.info("Cleaned up %d expired games", deleted)
        except Exception:
            logger.exception("Cleanup failed")


async def _recover_pending_games():
    """On startup, retry any games stuck in 'pending' from a previous crash."""
    from app.database import get_db
    from app.routers.games import _generate_in_background

    db = await get_db()
    cur = await db.execute("SELECT id, prompt, session_id FROM games WHERE status = 'pending'")
    pending = await cur.fetchall()
    if not pending:
        return

    logger.info("Recovering %d pending games from previous run", len(pending))
    for row in pending:
        game = dict(row)
        asyncio.create_task(
            _generate_in_background(game["id"], game["prompt"], game["session_id"] or "recovered")
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_db()
    cleanup_task = asyncio.create_task(_periodic_cleanup())
    await _recover_pending_games()
    yield
    cleanup_task.cancel()
    await close_client()
    await close_db()


app = FastAPI(
    title="GameSpark API",
    description="AI-powered game creation platform for kids",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware)

app.include_router(health.router, prefix="/api")
app.include_router(games.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")

# Serve static frontend files if they exist (production mode)
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
