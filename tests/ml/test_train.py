"""
Unit tests for ML model training, cross-validation, and metrics.
"""
import pytest
import os
import json
import pandas as pd
import numpy as np
from ml.training.train import train_and_evaluate_models
from ml.evaluation.metrics import calculate_regression_metrics, format_metrics_table


class TestTraining:
    def test_metrics_calculation(self):
        y_true = [1000000.0, 1500000.0, 2000000.0]
        y_pred = [1050000.0, 1450000.0, 1900000.0]

        metrics = calculate_regression_metrics(y_true, y_pred)
        assert "mae" in metrics
        assert "rmse" in metrics
        assert "r2" in metrics
        assert "median_ae" in metrics
        assert metrics["mae"] == round((50000.0 + 50000.0 + 100000.0) / 3, 2)
        assert metrics["median_ae"] == 50000.0

        table = format_metrics_table({"TestModel": metrics})
        assert "TestModel" in table
        assert "INR" in table

    def test_training_pipeline_execution(self, tmp_path):
        # Create a synthetic test dataset that passes readiness gate (50+ rows)
        records = []
        brands = ["Hyundai", "Maruti Suzuki", "Honda", "Tata", "Toyota", "Mahindra"]
        for i in range(55):
            b = brands[i % len(brands)]
            yr = 2018 + (i % 6)
            km = 20000 + (i * 1000)
            price = 500000.0 + (yr - 2018) * 100000.0 + (i * 10000.0)
            records.append({
                "id": i + 1,
                "listing_id": f"item-{i}",
                "source": "open_research",
                "brand": b,
                "model": f"Model-{b}",
                "variant": "Top Variant",
                "year": yr,
                "fuel_type": "Petrol" if i % 2 == 0 else "Diesel",
                "transmission": "Manual" if i % 2 == 0 else "Automatic",
                "km_driven": km,
                "engine_cc": 1493,
                "mileage": 18.5,
                "owner_count": 1,
                "city": "Bengaluru",
                "state": "Karnataka",
                "seller_type": "Individual",
                "listed_price": price,
                "is_duplicate_candidate": False,
                "duplicate_of_id": None
            })

        sample_csv = os.path.join(tmp_path, "sample_processed.csv")
        models_out = os.path.join(tmp_path, "models")
        exps_out = os.path.join(tmp_path, "exps")

        pd.DataFrame(records).to_csv(sample_csv, index=False)

        res = train_and_evaluate_models(
            processed_csv_path=sample_csv,
            models_dir=models_out,
            experiments_dir=exps_out,
            model_version="test_v01"
        )

        assert res["status"] == "SUCCESS"
        assert "selected_model" in res
        assert os.path.exists(res["model_path"])
        assert os.path.exists(res["preprocessor_path"])
        assert os.path.exists(res["metadata_path"])

        with open(res["metadata_path"], "r") as f:
            meta = json.load(f)
            assert meta["model_version"] == "test_v01"
            assert "metrics_test" in meta
            assert meta["total_records"] == 55
