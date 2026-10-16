"""
Data Quality and Ingestion Telemetry API Endpoints.
Reuses existing transformation and ML readiness metadata to expose dataset quality indicators.
"""
from typing import Dict, Any, List
import os
import json
import pandas as pd
from fastapi import APIRouter, HTTPException

from backend.app.core.config import settings

router = APIRouter(prefix="/data-quality", tags=["Data Quality"])


@router.get("")
def get_data_quality_report() -> Dict[str, Any]:
    """
    Returns empirical quality metrics, field completeness, source distribution,
    duplicate filtering statistics, and ML readiness gate status for the processed dataset.
    """
    meta_path = os.path.join(settings.PROCESSED_DATA_DIR, "dataset_metadata.json")
    csv_path = os.path.join(settings.PROCESSED_DATA_DIR, "autovalue_processed.csv")

    if not os.path.exists(meta_path) or not os.path.exists(csv_path):
        raise HTTPException(
            status_code=503,
            detail="Processed dataset or metadata is unavailable. Please run 'python data_pipeline/run_transformations.py'."
        )

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    # Compute live source distribution from processed CSV
    df = pd.read_csv(csv_path)
    source_dist = {}
    if "source" in df.columns:
        counts = df["source"].value_counts()
        total = len(df)
        for src, cnt in counts.items():
            source_dist[str(src)] = {
                "count": int(cnt),
                "percentage": round((cnt / total) * 100.0, 2)
            }

    # Brand diversity
    brands_count = int(df["brand"].nunique()) if "brand" in df.columns else 0

    return {
        "dataset_version": meta.get("dataset_version", "v0.3"),
        "transformation_version": meta.get("transformation_version", "1.0.0"),
        "last_transformed_at": meta.get("created_at"),
        "raw_record_count": meta.get("raw_record_count", len(df)),
        "processed_record_count": meta.get("processed_record_count", len(df)),
        "duplicates_filtered": meta.get("duplicates_filtered", 0),
        "distinct_brands_count": brands_count,
        "source_distribution": source_dist,
        "missingness_summary": meta.get("missing_value_summary", {}),
        "features_engineered": meta.get("features_engineered", ["car_age", "km_per_year"]),
        "ml_readiness": meta.get("ml_readiness", {
            "status": "READY",
            "is_ready": True
        })
    }
