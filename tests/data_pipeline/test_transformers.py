"""
Unit tests for transformation pipeline, missing value analysis, outlier auditing, and ML readiness gate.
"""
import pytest
import os
import json
import pandas as pd
import numpy as np
from data_pipeline.transformers.missing_values import MissingValueAnalyzer
from data_pipeline.transformers.outliers import OutlierDetector
from data_pipeline.transformers.readiness_gate import MLReadinessGate
from data_pipeline.transformers.pipeline import DatasetTransformationPipeline


class TestTransformers:
    def test_missing_value_analysis_and_imputation(self):
        analyzer = MissingValueAnalyzer()
        df = pd.DataFrame([
            {"brand": "Hyundai", "model": "Creta", "year": 2021, "listed_price": 1200000.0, "km_driven": 30000.0, "variant": "SX"},
            {"brand": "Honda", "model": "City", "year": 2020, "listed_price": 900000.0, "km_driven": 50000.0, "variant": None}, # Missing variant
            {"brand": "Tata", "model": "Nexon", "year": 2022, "listed_price": 1100000.0, "km_driven": np.nan, "variant": "XZ"} # Missing km
        ])

        summary = analyzer.analyze(df)
        assert summary.total_records == 3
        assert summary.missing_counts["variant"] == 1
        assert summary.missing_counts["km_driven"] == 1

        imputed_df, medians = analyzer.handle_missing_values(df, is_training=True)
        assert imputed_df.loc[1, "variant"] == "Unspecified"
        assert imputed_df.loc[2, "km_driven"] == 40000.0  # Median of 30,000 and 50,000

    def test_outlier_detection_domain_and_iqr(self):
        detector = OutlierDetector(min_price=25000, max_price=25000000, min_year=1995, max_year=2026)
        df = pd.DataFrame([
            {"brand": "Hyundai", "year": 2021, "km_driven": 35000, "listed_price": 1200000.0},
            {"brand": "Maruti", "year": 1980, "km_driven": 35000, "listed_price": 100000.0}, # Invalid year (<1995)
            {"brand": "Honda", "year": 2020, "km_driven": -500, "listed_price": 800000.0}, # Negative KM
            {"brand": "BMW", "year": 2022, "km_driven": 20000, "listed_price": 500.0}, # Unrealistic price (<25000)
        ])

        audited_df, result = detector.audit_dataframe(df)
        assert result.outlier_count == 3
        assert audited_df.loc[0, "is_outlier"] == False
        assert audited_df.loc[1, "is_outlier"] == True
        assert audited_df.loc[2, "is_outlier"] == True
        assert audited_df.loc[3, "is_outlier"] == True

    def test_ml_readiness_gate_evaluation(self):
        gate = MLReadinessGate(min_records=10)

        # Small dataframe (3 records < 10)
        df_small = pd.DataFrame([
            {"brand": "Hyundai", "model": "Creta", "year": 2021, "km_driven": 30000, "car_age": 3, "km_per_year": 10000, "listed_price": 1200000.0},
            {"brand": "Honda", "model": "City", "year": 2020, "km_driven": 40000, "car_age": 4, "km_per_year": 10000, "listed_price": 900000.0},
            {"brand": "Tata", "model": "Nexon", "year": 2022, "km_driven": 20000, "car_age": 2, "km_per_year": 10000, "listed_price": 1100000.0},
        ])

        report = gate.evaluate(df_small)
        assert report.is_ready is False
        assert report.status == "NOT READY"
        assert any("Insufficient dataset volume" in f for f in report.failed_checks)

    def test_dataset_transformation_pipeline_end_to_end(self, tmp_path):
        pipeline = DatasetTransformationPipeline(output_dir=str(tmp_path))
        raw_df = pd.DataFrame([
            {
                "id": 1,
                "listing_id": "item-1",
                "source": "open_research",
                "brand": "Hyundai",
                "model": "Creta",
                "variant": "1.5 CRDi SX",
                "year": 2021,
                "fuel_type": "Diesel",
                "transmission": "Manual",
                "km_driven": 36000,
                "city": "Bengaluru",
                "listed_price": 1350000.0,
                "is_duplicate_candidate": False
            },
            {
                "id": 2,
                "listing_id": "item-2",
                "source": "dealer_feed",
                "brand": "Hyundai",
                "model": "Creta",
                "variant": "1.5 CRDi SX",
                "year": 2021,
                "fuel_type": "Diesel",
                "transmission": "Manual",
                "km_driven": 36100,
                "city": "Bengaluru",
                "listed_price": 1360000.0,
                "is_duplicate_candidate": True  # Duplicate
            }
        ])

        processed_df, csv_path, metadata_path = pipeline.run_pipeline_and_save(raw_df)

        assert len(processed_df) == 1 # Duplicate filtered out
        assert os.path.exists(csv_path)
        assert os.path.exists(metadata_path)

        with open(metadata_path, "r") as f:
            meta = json.load(f)
            assert meta["raw_record_count"] == 2
            assert meta["processed_record_count"] == 1
            assert meta["duplicates_filtered"] == 1
            assert "car_age" in meta["features_engineered"]
