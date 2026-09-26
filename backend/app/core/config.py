from functools import lru_cache
from pathlib import Path

from pydantic import field_validator, model_validator
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

    # Compute the slowest model endpoints once at start-up (in the background) so the first visitor is fast.
    PREWARM: bool = True
    # Train the small assistant language model right after start-up (in the background) so the first question is not slow.
    PREWARM_ASSISTANT: bool = True
    # Refit the forecast model in the background when drift is flagged. Off by default: on a small free server the refit starves
    # everything else. Retraining is still one click on the Model Monitor page.
    SCHEDULED_RETRAIN: bool = False
    LIVE_REFRESH: bool = True  # pull the latest public series on start and then every REFRESH_HOURS
    REFRESH_HOURS: float = 6.0

    # One-click sign-in for the seeded demo accounts (see scripts/seed_demo_users.py). Turn off for a real deployment.
    ALLOW_DEMO_LOGIN: bool = True
    # Live ship feed from a public web page whose reuse terms we could not confirm. Off unless you decide otherwise.
    LIVE_SHIP_FEED: bool = False
    # Simulated demo feeds (moving dots and anchorage queues on the port map, minute ticks on the Live Desk). Off by default: no mock data in a deployment.
    SHOW_SIMULATED_FEEDS: bool = False
    WEATHER_SERVER_SIDE: bool = True  # False = never call Open-Meteo from the server (some shared hosts are rate-limited); the browser fetches it instead

    @field_validator("DATABASE_URL")
    @classmethod
    def normalise_postgres_url(cls, v: str) -> str:
        # Neon and Render hand out "postgres://" / "postgresql://"; SQLAlchemy needs the driver named.
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):
            v = "postgresql+psycopg2://" + v[len("postgresql://"):]
        return v

    @model_validator(mode="after")
    def require_real_secret_in_production(self) -> "Settings":
        if self.ENVIRONMENT.lower() == "production" and (self.JWT_SECRET_KEY == "changeme-dev-secret" or len(self.JWT_SECRET_KEY) < 32):
            raise ValueError("JWT_SECRET_KEY must be set to a random value of at least 32 characters when ENVIRONMENT=production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
