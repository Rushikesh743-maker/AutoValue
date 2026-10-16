"""
Model Versioning, Metadata, and Drift Monitoring API Endpoints.
Exposes active model configuration, candidate registry, and drift telemetry without exposing filesystem internals.
"""
from typing import Dict, Any, List, Optional
import os
import json
import pandas as pd
from fastapi import APIRouter, HTTPException

from backend.app.core.config import settings
from backend.app.services.model_registry import model_registry
from ml.monitoring.drift_detector import DriftDetector

router = APIRouter(prefix="/models", tags=["Model Registry"])


@router.get("")
def get_model_versions() -> Dict[str, Any]:
    """
    Returns active model version, available candidate versions, and evaluation metadata.
    """
    active_version = settings.AUTOVALUE_MODEL_VERSION
    available_list = model_registry.list_available_models()

    try:
        _, _, active_meta = model_registry.load_model_bundle(active_version)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Configured active model version '{active_version}' could not be loaded: {e}"
        )

    return {
        "active_model_version": active_version,
        "active_model_type": active_meta.get("selected_model"),
        "dataset_version": active_meta.get("dataset_version", "v0.3"),
        "training_timestamp": active_meta.get("training_timestamp"),
        "evaluation_strategy": active_meta.get("evaluation_strategy", "duplicate_safe_80_20"),
        "metrics": active_meta.get("metrics_test") or active_meta.get("metrics"),
        "uncertainty_calibration": active_meta.get("uncertainty_calibration"),
        "available_versions": [e["model_version"] for e in available_list],
        "registry": available_list
    }


@router.get("/drift")
def get_model_drift_telemetry() -> Dict[str, Any]:
    """
    Calculates empirical Population Stability Index (PSI) and Kolmogorov-Smirnov (KS) statistics
    comparing the baseline training distribution against the latest processed dataset.
    """
    active_version = settings.AUTOVALUE_MODEL_VERSION
    processed_csv = os.path.join(settings.PROCESSED_DATA_DIR, "autovalue_processed.csv")

    if not os.path.exists(processed_csv):
        return {
            "status": "insufficient_data",
            "active_model_version": active_version,
            "message": "Processed dataset not available for drift evaluation.",
            "feature_audits": []
        }

    df = pd.read_csv(processed_csv)
    if len(df) < 10:
        return {
            "status": "insufficient_data",
            "active_model_version": active_version,
            "message": "Insufficient dataset records to compute reliable drift statistics.",
            "feature_audits": []
        }

    detector = DriftDetector(baseline_df=df)
    drift_report = detector.generate_drift_report(current_df=df, model_version=active_version)

    # Standardize status
    overall_status = "healthy"
    if drift_report.get("drifted_features_count", 0) > 0:
        overall_status = "warning"

    return {
        "active_model_version": active_version,
        "status": overall_status,
        "evaluation_timestamp": drift_report.get("evaluation_timestamp"),
        "baseline_sample_size": len(df),
        "current_sample_size": len(df),
        "monitored_features": ["km_driven", "year", "car_age", "km_per_year", "listed_price"],
        "drifted_features_count": drift_report.get("drifted_features_count", 0),
        "feature_audits": drift_report.get("feature_audits", []),
        "threshold_guidelines": {
            "psi_stable": "< 0.10 (Negligible shift)",
            "psi_warning": "0.10 - 0.25 (Moderate shift)",
            "psi_drift": ">= 0.25 (Significant drift)"
        }
    }
