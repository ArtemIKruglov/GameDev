from datetime import UTC, datetime

from app.config import settings
from app.database import get_rate_count, increment_rate_counts_atomic


async def check_rate_limit(session_id: str) -> tuple[bool, int]:
    """Check if session is within rate limits (read-only).

    Returns (is_allowed, retry_after_seconds).
    """
    now = datetime.now(UTC)

    # Hourly window
    hour_window = now.strftime("%Y-%m-%dT%H:00:00")
    hour_count = await get_rate_count(session_id, hour_window)
    if hour_count >= settings.rate_limit_per_hour:
        seconds_left = 3600 - now.minute * 60 - now.second
        return False, max(seconds_left, 1)

    # Daily window
    day_window = now.strftime("%Y-%m-%d")
    day_count = await get_rate_count(session_id, day_window)
    if day_count >= settings.rate_limit_per_day:
        seconds_left = 86400 - now.hour * 3600 - now.minute * 60 - now.second
        return False, max(seconds_left, 1)

    return True, 0


async def record_rate_usage(session_id: str) -> None:
    """Atomically increment rate limit counters for both windows.

    Call only after successful generation.
    """
    now = datetime.now(UTC)
    hour_window = now.strftime("%Y-%m-%dT%H:00:00")
    day_window = now.strftime("%Y-%m-%d")
    await increment_rate_counts_atomic(session_id, [hour_window, day_window])
