"""
Application configuration management using Pydantic Settings.
Hardened for production security, configurable rate limiting, CORS, and logging.
"""
from typing import List, Optional, Union
import json
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AutoValue API"
    VERSION: str = "0.9.0"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production, testing")
    DEBUG: bool = Field(default=True, description="Enable debug mode")
    DOCS_ENABLED: bool = Field(default=True, description="Enable Swagger/OpenAPI documentation")

    # Host & URL Configuration
    API_BASE_URL: str = Field(default="http://localhost:8000", description="Public backend API base URL")
    FRONTEND_BASE_URL: str = Field(default="http://localhost:5173", description="Frontend application base URL")
    TRUSTED_HOSTS: List[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed host headers (e.g. ['api.autovalue.com', 'localhost'])"
    )

    # Security & Secret Key
    SECRET_KEY: Optional[str] = Field(default=None, description="Cryptographic secret key for signing / security")
    AUTH_SECRET: str = Field(default="autovalue-dev-secret-key-do-not-use-in-prod-xyz-987654321", description="JWT auth secret key")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440, ge=5, description="Access token expiration in minutes")
    COOKIE_SECURE: bool = Field(default=False, description="Set Secure flag on cookies (must be True in production HTTPS)")
    COOKIE_SAMESITE: str = Field(default="lax", description="SameSite cookie policy: lax, strict, none")
    COOKIE_NAME: str = Field(default="autovalue_token", description="Session cookie name")

    # Database Settings
    DATABASE_URL: str = Field(
        default="sqlite:///data/autovalue.db",
        description="SQLAlchemy Database URL (PostgreSQL or local SQLite fallback)"
    )
    AUTO_CREATE_TABLES: bool = Field(
        default=False,
        description="Automatically create tables with Base.metadata.create_all on startup. Only permitted in development/testing."
    )
    DB_POOL_SIZE: int = Field(default=10, ge=1, le=50, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=20, ge=0, le=50, description="Max overflow connections")
    DB_POOL_TIMEOUT: int = Field(default=30, ge=1, description="Database connection pool timeout in seconds")
    DB_POOL_RECYCLE: int = Field(default=1800, ge=60, description="Recycle connections after N seconds")

    # Collection & Ingestion Pipeline Configuration
    COLLECTION_ENABLED: bool = False
    MAX_RECORDS_PER_SOURCE: int = 50
    REQUEST_TIMEOUT_SECONDS: int = 10
    REQUEST_DELAY_SECONDS: float = 2.0
    USER_AGENT: str = "AutoValue/0.9 (+https://github.com/autovalue; empirical-car-valuation)"
    
    # Paths & Artifacts
    RAW_DATA_DIR: str = "data/raw"
    PROCESSED_DATA_DIR: str = "data/processed"
    SAMPLE_DATA_DIR: str = "data/sample"
    MODELS_DIR: str = "models"
    AUTOVALUE_MODEL_VERSION: str = "v002"

    # CORS Settings
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )
    CORS_ORIGINS: Optional[Union[str, List[str]]] = Field(
        default=None,
        description="Alias for BACKEND_CORS_ORIGINS"
    )

    # Security & Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, ge=1, le=1000, description="Max requests per minute per IP on public valuation")
    RATE_LIMIT_REQUESTS: Optional[int] = Field(default=None, description="Alias for rate limit requests count")
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60, ge=1, description="Sliding window duration in seconds")
    MAX_REQUEST_BODY_BYTES: int = Field(default=1048576, ge=1024, description="Max request body size in bytes (1MB)")
    
    # Observability & Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)")
    LOG_FORMAT: str = Field(default="json", description="Log format (json or text)")
    ENABLE_PROMETHEUS_METRICS: bool = Field(default=True, description="Expose /metrics endpoint")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, str) and v.startswith("["):
            try:
                return json.loads(v)
            except Exception:
                return [v]
        elif isinstance(v, list):
            return v
        return []

    @field_validator("TRUSTED_HOSTS", mode="before")
    @classmethod
    def assemble_trusted_hosts(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, str) and v.startswith("["):
            try:
                return json.loads(v)
            except Exception:
                return [v]
        elif isinstance(v, list):
            return v
        return ["*"]

    @model_validator(mode="after")
    def validate_production_environment(self) -> "Settings":
        """Enforce strict configuration requirements when running in production."""
        if self.CORS_ORIGINS is not None:
            parsed_cors = self.assemble_cors_origins(self.CORS_ORIGINS)
            if parsed_cors:
                object.__setattr__(self, "BACKEND_CORS_ORIGINS", parsed_cors)

        if self.RATE_LIMIT_REQUESTS is not None:
            object.__setattr__(self, "RATE_LIMIT_PER_MINUTE", self.RATE_LIMIT_REQUESTS)

        if self.ENVIRONMENT.lower() == "production":
            if self.DEBUG:
                object.__setattr__(self, "DEBUG", False)
            if self.AUTO_CREATE_TABLES:
                raise ValueError("Production environment must not use AUTO_CREATE_TABLES; Alembic migrations are the required schema source of truth.")
            
            effective_secret = self.AUTH_SECRET or self.SECRET_KEY or ""
            if not effective_secret or effective_secret in [
                "autovalue-dev-secret-key-do-not-use-in-prod-xyz-987654321",
                "fallback-secret-autovalue-token-signing",
                "secret",
                "changeme",
                "default_secret"
            ] or len(effective_secret) < 32:
                raise ValueError("Production environment requires a strong, non-default AUTH_SECRET or SECRET_KEY environment variable (at least 32 characters).")
            if self.DATABASE_URL.startswith("sqlite"):
                raise ValueError("Production environment requires a managed PostgreSQL database URL (sqlite is not supported for production).")
            if "*" in self.BACKEND_CORS_ORIGINS:
                raise ValueError("Production CORS configuration must not include wildcard '*' origin.")
            if not self.COOKIE_SECURE:
                raise ValueError("Production environment requires COOKIE_SECURE=True to protect session cookies over HTTPS.")
            if "*" in self.TRUSTED_HOSTS and len(self.TRUSTED_HOSTS) == 1:
                pass
        return self


settings = Settings()
