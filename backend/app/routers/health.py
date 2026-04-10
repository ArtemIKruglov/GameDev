from datetime import UTC, datetime

from fastapi import APIRouter

from app.database import get_db
from app.models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    db_status = "ok"
    try:
        db = await get_db()
        await db.execute("SELECT 1")
    except Exception:
        db_status = "error"

    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        timestamp=datetime.now(UTC).isoformat(),
        database=db_status,
        version="0.1.0",
    )
