from datetime import UTC, datetime, timedelta

import pytest

from app import database


@pytest.mark.asyncio
async def test_create_and_get_game():
    database._db = None
    try:
        game = await database.create_game("test-id-1", "a cat catching fish")
        assert game["id"] == "test-id-1"
        assert game["prompt"] == "a cat catching fish"
        assert game["status"] == "pending"

        fetched = await database.get_game("test-id-1")
        assert fetched is not None
        assert fetched["prompt"] == "a cat catching fish"
    finally:
        await database.close_db()


@pytest.mark.asyncio
async def test_update_game():
    database._db = None
    try:
        await database.create_game("test-id-2", "space shooter")
        updated = await database.update_game(
            "test-id-2",
            status="ready",
            html_content="<html>game</html>",
            generation_time_ms=5000,
        )
        assert updated["status"] == "ready"
        assert updated["html_content"] == "<html>game</html>"
        assert updated["generation_time_ms"] == 5000
    finally:
        await database.close_db()


@pytest.mark.asyncio
async def test_list_games():
    database._db = None
    try:
        await database.create_game("test-id-3", "puzzle game")
        await database.update_game("test-id-3", status="ready")
        await database.create_game("test-id-4", "racing game")
        await database.update_game("test-id-4", status="ready")

        games, total = await database.list_games(page=1, per_page=10)
        assert total >= 2
        assert len(games) >= 2
    finally:
        await database.close_db()


@pytest.mark.asyncio
async def test_flag_game():
    database._db = None
    try:
        await database.create_game("test-id-5", "flag test")
        await database.flag_game("test-id-5")
        game = await database.get_game("test-id-5")
        assert game["status"] == "flagged"
        assert game["is_public"] == 0
    finally:
        await database.close_db()


@pytest.mark.asyncio
async def test_rate_limiting():
    database._db = None
    try:
        count = await database.get_rate_count("session-1", "2026-04-10T12:00:00")
        assert count == 0

        new_count = await database.increment_rate_count("session-1", "2026-04-10T12:00:00")
        assert new_count == 1

        new_count = await database.increment_rate_count("session-1", "2026-04-10T12:00:00")
        assert new_count == 2
    finally:
        await database.close_db()


@pytest.mark.asyncio
async def test_get_nonexistent_game():
    database._db = None
    try:
        game = await database.get_game("nonexistent-id")
        assert game is None
    finally:
        await database.close_db()


@pytest.mark.asyncio
async def test_cleanup_expired_games():
    """Games older than 30 days should be cleaned up."""
    database._db = None
    try:
        # Create a game
        await database.create_game("cleanup-test-1", "old game")
        await database.update_game("cleanup-test-1", status="ready")

        # Manually set created_at to 31 days ago
        db = await database.get_db()
        old_date = (datetime.now(UTC) - timedelta(days=31)).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        await db.execute(
            "UPDATE games SET created_at = ? WHERE id = ?",
            (old_date, "cleanup-test-1"),
        )
        await db.commit()

        # Create a recent game
        await database.create_game("cleanup-test-2", "new game")
        await database.update_game("cleanup-test-2", status="ready")

        # Run cleanup
        deleted = await database.cleanup_expired_games(days=30)
        assert deleted == 1

        # Old game gone, new game still exists
        assert await database.get_game("cleanup-test-1") is None
        assert await database.get_game("cleanup-test-2") is not None
    finally:
        await database.close_db()
