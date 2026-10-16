"""
Unit tests for AutoValuePredictor inference service.
"""
import pytest
import os
import pandas as pd
import numpy as np
from ml.training.train import train_and_evaluate_models
from ml.inference.predictor import AutoValuePredictor


class TestInference:
    def test_predictor_point_prediction(self, tmp_path):
        records = []
        brands = ["Hyundai", "Maruti Suzuki", "Honda", "Tata"]
        for i in range(52):
            b = brands[i % len(brands)]
            records.append({
                "id": i + 1,
                "listing_id": f"item-{i}",
                "source": "open_research",
                "brand": b,
                "model": "Creta" if b == "Hyundai" else "City",
                "variant": "SX",
                "year": 2020 + (i % 4),
                "fuel_type": "Petrol",
                "transmission": "Manual",
                "km_driven": 30000 + i * 500,
                "engine_cc": 1493,
                "mileage": 18.0,
                "owner_count": 1,
                "city": "Bengaluru",
                "state": "Karnataka",
                "seller_type": "Individual",
                "listed_price": 1000000.0 + i * 15000,
                "is_duplicate_candidate": False,
                "duplicate_of_id": None
            })

        sample_csv = os.path.join(tmp_path, "sample_processed.csv")
        models_out = os.path.join(tmp_path, "models")
        pd.DataFrame(records).to_csv(sample_csv, index=False)

        res = train_and_evaluate_models(
            processed_csv_path=sample_csv,
            models_dir=models_out,
            experiments_dir=str(tmp_path),
            model_version="inf_v01"
        )

        predictor = AutoValuePredictor(
            model_path=res["model_path"],
            preprocessor_path=res["preprocessor_path"],
            metadata_path=res["metadata_path"]
        )

        assert predictor.is_loaded

        pred_res = predictor.predict({
            "brand": "Hyundai",
            "model": "Creta",
            "year": 2021,
            "km_driven": 35000,
            "fuel_type": "Diesel",
            "transmission": "Manual",
            "city": "Bengaluru"
        })

        assert "predicted_price" in pred_res
        assert pred_res["predicted_price"] > 10000.0
        assert "predicted_price_formatted" in pred_res
        assert "₹" in pred_res["predicted_price_formatted"]
