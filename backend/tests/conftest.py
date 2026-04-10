import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Use in-memory SQLite for tests
os.environ["DATABASE_PATH"] = ":memory:"
os.environ["OPENROUTER_API_KEY"] = "test-key"
os.environ["SESSION_SECRET"] = "test-secret"

from app import database
from app.main import app
from app.services import game_generator


@pytest_asyncio.fixture(autouse=True)
async def _reset_shared_client():
    """Reset the shared httpx client before each test so respx mocking works."""
    game_generator._client = None
    yield
    await game_generator.close_client()


@pytest_asyncio.fixture
async def client():
    """Create a test client with a fresh in-memory database."""
    # Reset the database connection for each test
    database._db = None
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    await database.close_db()
