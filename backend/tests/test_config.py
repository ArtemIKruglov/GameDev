import os

import pytest
from pydantic import ValidationError


def test_empty_openrouter_key_rejected():
    """App should refuse to start when OPENROUTER_API_KEY is empty."""
    env = {
        "OPENROUTER_API_KEY": "",
        "SESSION_SECRET": "test-secret",
        "DATABASE_PATH": ":memory:",
    }
    # Clear any cached module-level Settings instance
    old_env = {k: os.environ.get(k) for k in env}
    try:
        os.environ.update(env)
        # Re-import fresh to trigger validation
        from app.config import Settings

        with pytest.raises(ValidationError):
            Settings()
    finally:
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
