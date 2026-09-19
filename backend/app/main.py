import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.compatibility import router as compatibility_router
from app.api.financial import router as financial_router
from app.api.forecast import router as forecast_router
from app.api.health import router as health_router
from app.api.market import router as market_router
from app.api.portmap import router as portmap_router
from app.api.haldia import router as haldia_router
from app.api.assistant import router as assistant_router
from app.api.recommendation import router as recommendation_router
from app.api.risk import router as risk_router
from app.api.scenario import router as scenario_router
from app.core.config import get_settings
from app.core.error_handlers import register_error_handlers
from app.core.logging_middleware import RequestLoggingMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

settings = get_settings()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "AI/ML-driven freight forecasting and dry bulk vessel chartering "
        "recommendation platform for coal procurement to India's East Coast ports."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
register_error_handlers(app)

app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(forecast_router, prefix="/api/v1")
app.include_router(compatibility_router, prefix="/api/v1")
app.include_router(market_router, prefix="/api/v1")
app.include_router(portmap_router, prefix="/api/v1")
app.include_router(haldia_router, prefix="/api/v1")
app.include_router(assistant_router, prefix="/api/v1")
app.include_router(recommendation_router, prefix="/api/v1")
app.include_router(risk_router, prefix="/api/v1")
app.include_router(financial_router, prefix="/api/v1")
app.include_router(scenario_router, prefix="/api/v1")


@app.get("/")
def root() -> dict:
    return {"service": settings.PROJECT_NAME, "docs": "/docs"}
