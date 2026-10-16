"""
Service Health, Liveness, and Readiness Probes.
"""
from typing import Dict, Any
import os
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.db.session import engine
from backend.app.services.model_registry import model_registry

router = APIRouter(tags=["Health & Reliability"])


@router.get("/health")
def health_check() -> Dict[str, Any]:
    """
    Liveness probe: Verifies that the API process is alive and responsive.
    """
    return {
        "status": "ok",
        "service": "autovalue-api",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }


@router.get("/ready")
def readiness_check(response: Response) -> Dict[str, Any]:
    """
    Readiness probe: Verifies that all required operational dependencies are ready:
    1. Database connection
    2. Active ML model artifacts and metadata
    3. Processed dataset presence
    """
    checks = {
        "database": False,
        "active_model_artifacts": False,
        "processed_dataset": False
    }
    details = {}

    # 1. Database Check
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            checks["database"] = True
            details["database"] = "Connected successfully"
    except Exception as e:
        checks["database"] = False
        details["database"] = f"Database connectivity error: {e}"

    # 2. Model Artifact Integrity Check
    try:
        ok, integrity_info = model_registry.verify_artifact_integrity(settings.AUTOVALUE_MODEL_VERSION)
        checks["active_model_artifacts"] = ok
        details["active_model"] = integrity_info
    except Exception as e:
        checks["active_model_artifacts"] = False
        details["active_model"] = f"Model artifact error: {e}"

    # 3. Processed Dataset Check
    csv_path = os.path.join(settings.PROCESSED_DATA_DIR, "autovalue_processed.csv")
    if os.path.exists(csv_path):
        checks["processed_dataset"] = True
        details["dataset"] = f"Dataset available at {csv_path}"
    else:
        checks["processed_dataset"] = False
        details["dataset"] = "Processed dataset file missing"

    all_ready = all(checks.values())
    if not all_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if all_ready else "not_ready",
        "service": "autovalue-api",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "active_model_version": settings.AUTOVALUE_MODEL_VERSION,
        "checks": checks,
        "details": details
    }
