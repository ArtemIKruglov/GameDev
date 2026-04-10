
from pydantic import BaseModel, Field

# --- Request Models ---


class GameCreateRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=500, description="Game idea description")


class GameRefineRequest(BaseModel):
    modification: str = Field(
        ..., min_length=3, max_length=500, description="What to change about the game"
    )


# --- Response Models ---


class GameResponse(BaseModel):
    id: str
    prompt: str
    status: str
    play_url: str
    created_at: str
    generation_time_ms: int | None = None
    parent_game_id: str | None = None


class GameListResponse(BaseModel):
    games: list[GameResponse]
    total: int
    page: int
    per_page: int


class GameHTMLResponse(BaseModel):
    html: str


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    database: str
    version: str


class ErrorResponse(BaseModel):
    error: str
    message: str
    retry_after_seconds: int | None = None
