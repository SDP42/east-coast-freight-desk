from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Central application configuration, sourced from environment variables / .env."""

    # Anchored to the backend directory (not the process's cwd) so scripts run
    # from anywhere — e.g. scripts/run_all.py — resolve the same .env and the
    # same SQLite file as the API server does.
    model_config = SettingsConfigDict(env_file=BACKEND_DIR.parent / ".env", extra="ignore")

    PROJECT_NAME: str = "East Coast Freight Forecasting & Chartering Platform"
    ENVIRONMENT: str = "development"

    # SQLite by default for zero-setup local dev; point at a real Postgres
    # (ideally with the TimescaleDB extension) for anything beyond a laptop demo —
    # e.g. postgresql+psycopg2://freight:freight@localhost:5432/freight_forecast
    DATABASE_URL: str = f"sqlite:///{BACKEND_DIR / 'freight_forecast.db'}"
    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET_KEY: str = "changeme-dev-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # Target p95 latency (ms) for cached read endpoints — used by the low-latency
    # benchmark check added in Section 16, referenced here so the number lives in one place.
    LATENCY_TARGET_MS: int = 200

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
