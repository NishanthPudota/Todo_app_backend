from typing import List
from pathlib import Path
from pydantic_settings import BaseSettings

# Resolve the directory this file lives in (app/) and look for .env there.
# This works regardless of which directory you run uvicorn from.
_ENV_FILE = Path(__file__).parent / ".env"


class Settings(BaseSettings):

    APP_NAME: str = "TODO Backend"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    DATABASE_URL: str = "postgresql://todo_user:todo_password@localhost:5432/todo_db"
    DATABASE_ECHO: bool = False

    # JWT settings
    SECRET_KEY: str = "a3b2c1d0e9f8g7h6i5j4k3l2m1n0o9p8q7r6s5t4u3v2w1x0y9z8a7b6c5d4e3f2"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS — list the origins allowed to call this API
    CORS_ORIGINS: List[str] = [
        "http://localhost:5000",
        "http://127.0.0.1:5000",
    ]

    class Config:
        env_file = str(_ENV_FILE)


settings = Settings()
