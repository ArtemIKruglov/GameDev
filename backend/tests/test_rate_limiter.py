import pytest

from app import database
from app.services.rate_limiter import check_rate_limit, record_rate_usage


@pytest.mark.asyncio
async def test_rate_limit_allows_first_request():
    database._db = None
    try:
        allowed, retry_after = await check_rate_limit("test-session-rl-1")
        assert allowed is True
        assert retry_after == 0
    finally:
        await database.close_db()


@pytest.mark.asyncio
async def test_rate_limit_blocks_after_limit():
    database._db = None
    try:
        session = "test-session-rl-block"
        for i in range(10):
            allowed, _ = await check_rate_limit(session)
            assert allowed is True, f"Request {i + 1} should be allowed"
            await record_rate_usage(session)

        # 11th request should be blocked
        allowed, retry_after = await check_rate_limit(session)
        assert allowed is False
        assert retry_after > 0
    finally:
        await database.close_db()


@pytest.mark.asyncio
async def test_rate_limit_not_charged_on_failure():
    """Verify that check_rate_limit does NOT increment counters.
    Only record_rate_usage should consume rate limit slots."""
    database._db = None
    try:
        session = "test-session-rl-no-charge"
        # Check 20 times without recording — should always be allowed
        for i in range(20):
            allowed, _ = await check_rate_limit(session)
            assert allowed is True, f"Check-only request {i + 1} should be allowed"

        # Now record once and verify we still have quota
        await record_rate_usage(session)
        allowed, _ = await check_rate_limit(session)
        assert allowed is True, "Should still be allowed after one recorded usage"
    finally:
        await database.close_db()
