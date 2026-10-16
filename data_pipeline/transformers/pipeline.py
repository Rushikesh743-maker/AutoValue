"""
End-to-End Dataset Transformation Pipeline.
Transforms raw/canonical listings into processed, reproducible ML-ready datasets with metadata versioning.
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import pandas as pd
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.listing import CarListing
from .missing_values import MissingValueAnalyzer, MissingValueSummary
from .outliers import OutlierDetector, OutlierAuditResult
from .readiness_gate import MLReadinessGate, ReadinessGateReport
from ..feature_engineering.features import CarFeatureEngineer

logger = logging.getLogger("autovalue.transformation_pipeline")


class DatasetTransformationPipeline:
    """
    Transforms raw/canonical listings into clean, standardized, ML-ready datasets.
    """

    TRANSFORMATION_VERSION = "1.0.0"

    def __init__(
        self,
        output_dir: Optional[str] = None,
        reference_year: int = 2024,
        deduplicate_strategy: str = "filter_duplicates", # "filter_duplicates" or "flag_only"
        missing_analyzer: Optional[MissingValueAnalyzer] = None,
        outlier_detector: Optional[OutlierDetector] = None,
        feature_engineer: Optional[CarFeatureEngineer] = None,
        readiness_gate: Optional[MLReadinessGate] = None,
    ):
        self.output_dir = output_dir or settings.PROCESSED_DATA_DIR
        self.reference_year = reference_year
        self.deduplicate_strategy = deduplicate_strategy
        self.missing_analyzer = missing_analyzer or MissingValueAnalyzer()
        self.outlier_detector = outlier_detector or OutlierDetector()
        self.feature_engineer = feature_engineer or CarFeatureEngineer(reference_year=reference_year)
        self.readiness_gate = readiness_gate or MLReadinessGate()
        os.makedirs(self.output_dir, exist_ok=True)

    def load_from_db(self, db: Session) -> pd.DataFrame:
        """Loads all listings from database into a pandas DataFrame."""
        listings = db.query(CarListing).all()
        if not listings:
            return pd.DataFrame()

        rows = []
        for l in listings:
            rows.append({
                "id": l.id,
                "listing_id": l.listing_id,
                "source": l.source,
                "listing_url": l.listing_url,
                "brand": l.brand,
                "model": l.model,
                "variant": l.variant,
                "year": l.year,
                "fuel_type": l.fuel_type,
                "transmission": l.transmission,
                "km_driven": l.km_driven,
                "engine_cc": l.engine_cc,
                "mileage": l.mileage,
                "owner_count": l.owner_count,
                "city": l.city,
                "state": l.state,
                "seller_type": l.seller_type,
                "listed_price": l.listed_price,
                "is_duplicate_candidate": l.is_duplicate_candidate,
                "duplicate_similarity": l.duplicate_similarity,
                "duplicate_of_id": l.duplicate_of_id,
                "duplicate_notes": l.duplicate_notes,
                "date_collected": l.date_collected.isoformat() if l.date_collected else None
            })
        return pd.DataFrame(rows)

    def transform_dataframe(self, raw_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Executes full transformation pipeline on input DataFrame.
        """
        if raw_df.empty:
            return pd.DataFrame(), {}

        df = raw_df.copy()
        raw_count = len(df)

        # 1. Duplicate Handling
        duplicate_count = int(df["is_duplicate_candidate"].sum()) if "is_duplicate_candidate" in df.columns else 0
        if self.deduplicate_strategy == "filter_duplicates" and "is_duplicate_candidate" in df.columns:
            df = df[df["is_duplicate_candidate"] == False].copy()
        post_dedup_count = len(df)

        # 2. Missing Value Analysis & Handling
        missing_summary = self.missing_analyzer.analyze(df)
        df, learned_medians = self.missing_analyzer.handle_missing_values(df, is_training=True)

        # 3. Outlier Audit
        df, outlier_result = self.outlier_detector.audit_dataframe(df)

        # 4. Feature Engineering
        df = self.feature_engineer.transform(df)

        # 5. ML Readiness Gate Evaluation
        readiness_report = self.readiness_gate.evaluate(df)

        # 6. Metadata Generation
        metadata = {
            "transformation_version": self.TRANSFORMATION_VERSION,
            "dataset_version": "v0.3",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "raw_record_count": raw_count,
            "processed_record_count": len(df),
            "duplicates_filtered": raw_count - post_dedup_count,
            "duplicate_strategy": self.deduplicate_strategy,
            "outliers_flagged": outlier_result.outlier_count,
            "missing_value_summary": {
                "counts": missing_summary.missing_counts,
                "percentages": missing_summary.missing_percentages
            },
            "features_engineered": ["car_age", "km_per_year"],
            "ml_readiness": {
                "status": readiness_report.status,
                "is_ready": readiness_report.is_ready,
                "failed_checks": readiness_report.failed_checks,
                "passed_checks": readiness_report.passed_checks
            }
        }

        return df, metadata

    def run_pipeline_and_save(self, input_df: pd.DataFrame) -> Tuple[pd.DataFrame, str, str]:
        """
        Transforms DataFrame and writes processed CSV and dataset_metadata.json to data/processed/.
        """
        processed_df, metadata = self.transform_dataframe(input_df)

        csv_path = os.path.join(self.output_dir, "autovalue_processed.csv")
        metadata_path = os.path.join(self.output_dir, "dataset_metadata.json")

        processed_df.to_csv(csv_path, index=False)
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Processed dataset saved to {csv_path} ({len(processed_df)} records)")
        logger.info(f"Metadata saved to {metadata_path}")

        return processed_df, csv_path, metadata_path
