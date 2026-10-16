"""
AutoValue FastAPI Application Entry Point.
Production-hardened with structured logging, request correlation tracing,
centralized exception handling, rate limiting, and Prometheus observability.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response, Request
from fastapi.responses import PlainTextResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.logging import setup_logging
from .core.exceptions import register_exception_handlers
from .core.middleware import (
    RequestCorrelationMiddleware,
    ValuationRateLimitMiddleware,
    RequestBodyLimitMiddleware
)
from .api.routes import api_router
from .db.session import engine
from .db.base import Base
from .models import (
    CarListing,
    Source,
    CollectionRun,
    User,
    SavedValuation,
    SavedVehicle,
    ShareToken,
    GarageVehicle
)
from .services.telemetry import metrics_collector
from .services.model_registry import model_registry

# Initialize structured logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verify active model integrity on startup
    try:
        model_registry.verify_artifact_integrity(settings.AUTOVALUE_MODEL_VERSION)
    except Exception as e:
        print(f"[AutoValue Startup] Warning: Active model integrity check encountered issue: {e}")

    # Ensure database tables exist ONLY if explicitly enabled or in local SQLite development/testing.
    # In production, Alembic migrations are the strict and sole schema source of truth.
    if settings.ENVIRONMENT.lower() != "production" and (
        settings.AUTO_CREATE_TABLES or settings.ENVIRONMENT.lower() in ["development", "testing"]
    ):
        try:
            Base.metadata.create_all(bind=engine)
        except Exception as e:
            print(f"[AutoValue Startup] Note: Could not auto-create database tables on startup ({e}).")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="ML-powered used-car valuation system, comparable market analysis, and intelligence API.",
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.DOCS_ENABLED else None,
    docs_url=f"{settings.API_V1_STR}/docs" if settings.DOCS_ENABLED else None,
    redoc_url=f"{settings.API_V1_STR}/redoc" if settings.DOCS_ENABLED else None,
    lifespan=lifespan
)

# 1. Register Global Centralized Exception Handlers
register_exception_handlers(app)

# 2. Register Middleware Stack (LIFO execution order in Starlette)
# Trusted host middleware (if configured)
if settings.TRUSTED_HOSTS and "*" not in settings.TRUSTED_HOSTS:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.TRUSTED_HOSTS)

# Body size limit middleware
app.add_middleware(RequestBodyLimitMiddleware)

# Rate limiting middleware
app.add_middleware(ValuationRateLimitMiddleware)

# Request correlation & tracing middleware
app.add_middleware(RequestCorrelationMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Retry-After"]
)

# 3. Mount API Routers
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {
        "service": "AutoValue API",
        "status": "online",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": f"{settings.API_V1_STR}/docs" if settings.DOCS_ENABLED else "disabled",
        "health": f"{settings.API_V1_STR}/health",
        "ready": f"{settings.API_V1_STR}/ready"
    }


@app.get("/metrics", response_class=PlainTextResponse)
def get_metrics():
    """Prometheus-compatible application metrics endpoint."""
    if not settings.ENABLE_PROMETHEUS_METRICS:
        return PlainTextResponse("# Metrics collection disabled in configuration\n", status_code=404)
    return PlainTextResponse(metrics_collector.generate_prometheus_text())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
