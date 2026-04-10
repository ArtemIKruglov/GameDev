from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openrouter_api_key: str = ""
    database_path: str = "./data/games.db"
    environment: str = "development"
    cors_origins: str = "http://localhost:5173"
    rate_limit_per_hour: int = 10
    rate_limit_per_day: int = 30
    session_secret: str = "change-me-to-a-random-string"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @field_validator("openrouter_api_key")
    @classmethod
    def openrouter_key_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError(
                "OPENROUTER_API_KEY must be set — the app cannot generate games without it"
            )
        return v


settings = Settings()
