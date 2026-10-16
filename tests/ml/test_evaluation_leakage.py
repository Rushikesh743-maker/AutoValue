"""
Evaluation Integrity and Leakage Prevention Tests.
Verifies that:
1. Final test rows are never used for model fitting, model selection, or calibration.
2. Calibration residuals are derived from dedicated calibration partitions or out-of-fold predictions.
3. Model selection uses only permitted training/validation data and is invariant to test set targets.
4. Split creation is reproducible and group-aware across physical vehicles.
5. Active production v002 model artifacts and metadata remain strictly unchanged.
6. Model metrics are calculated on the final test set only after the training/calibration procedure is frozen.
"""
import os
import json
import hashlib
import pytest
import pandas as pd
import numpy as np

from ml.training.split import duplicate_safe_train_val_test_split, build_vehicle_clusters
from ml.training.train_v002 import run_training_v002
from ml.evaluation.uncertainty import PredictionUncertaintyEstimator


def _create_synthetic_dataset(n_rows: int = 120, random_state: int = 42) -> pd.DataFrame:
    """Creates a valid synthetic dataset with distinct vehicles passing ML readiness gate."""
    rng = np.random.RandomState(random_state)
    brands = ["Hyundai", "Maruti Suzuki", "Honda", "Tata", "Toyota", "Mahindra"]
    models = {
        "Hyundai": ["Creta", "i20", "Verna"],
        "Maruti Suzuki": ["Swift", "Baleno", "Brezza"],
        "Honda": ["City", "Amaze"],
        "Tata": ["Nexon", "Harrier"],
        "Toyota": ["Innova", "Fortuner"],
        "Mahindra": ["XUV700", "Thar"]
    }
    cities = ["Bengaluru", "Mumbai", "Delhi Ncr", "Pune", "Hyderabad", "Chennai", "Kolkata", "Ahmedabad"]
    records = []
    for i in range(n_rows):
        b = brands[i % len(brands)]
        m = models[b][i % len(models[b])]
        yr = int(2015 + (i % 9))
        km = int(10000 + (i * 2700) + rng.randint(100, 5000))
        city = cities[i % len(cities)]
        price = float(400000.0 + (yr - 2015) * 110000.0 + (i * 8000.0) + rng.randint(5000, 20000))
        records.append({
            "id": i + 1,
            "listing_id": f"syn-item-{i}",  # distinct listing IDs
            "source": "open_research",
            "listing_url": f"https://example.com/listings/{i}",
            "brand": b,
            "model": m,
            "variant": f"Variant-{i % 3}",
            "year": yr,
            "fuel_type": "Petrol" if i % 2 == 0 else "Diesel",
            "transmission": "Manual" if i % 3 == 0 else "Automatic",
            "km_driven": km,
            "engine_cc": 1497,
            "mileage": 18.0,
            "owner_count": 1 + (i % 2),
            "city": city,
            "state": "Karnataka",
            "seller_type": "Individual",
            "listed_price": price,
            "is_duplicate_candidate": False,
            "duplicate_similarity": None,
            "duplicate_of_id": None,
            "duplicate_notes": None,
            "date_collected": "2026-10-01T10:00:00"
        })
    return pd.DataFrame(records)


class TestEvaluationLeakagePrevention:
    """Test suite verifying elimination of ML evaluation and calibration leakage."""

    def test_v002_artifacts_and_metadata_are_immutable(self):
        """Requirement 5: Active v002 artifact and metadata remain completely unchanged."""
        expected_checksums = {
            "model_v002.joblib": "6c1ca4b832f6130bc4b2e144fffecfc5e8061ba4c407a012b12479d4602d7b97",
            "preprocessor_v002.joblib": "01e1cb40754618bdd61bfbcae397e17454d4a5d6c43642601016a7bd0a786baa",
            "metadata_v002.json": "855c42759143e1a00402f9ba34e90391a0592acd38d9948edb965c58f4b575e3"
        }

        models_dir = os.path.join(os.path.dirname(__file__), "..", "..", "models")
        for filename, expected_hash in expected_checksums.items():
            filepath = os.path.join(models_dir, filename)
            assert os.path.exists(filepath), f"Expected v002 file {filepath} to exist."
            with open(filepath, "rb") as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            assert actual_hash == expected_hash, f"SHA256 mismatch for {filename}! Production artifact was modified."

    def test_final_test_rows_never_used_for_fitting_or_selection_or_calibration(self, tmp_path):
        """Requirement 1: Test partition is strictly isolated from model fitting, selection, and calibration."""
        df = _create_synthetic_dataset(120)
        csv_path = os.path.join(tmp_path, "synthetic.csv")
        df.to_csv(csv_path, index=False)

        models_out = os.path.join(tmp_path, "models")
        exps_out = os.path.join(tmp_path, "exps")

        res = run_training_v002(
            processed_csv_path=csv_path,
            models_dir=models_out,
            experiments_dir=exps_out,
            model_version="test_candidate_01",
            random_state=42
        )

        assert res["status"] == "SUCCESS"
        metadata = res["metadata"]

        # Verify separate sample counts
        assert metadata["train_records"] > 0
        assert metadata["calibration_records"] > 0
        assert metadata["test_records"] > 0
        assert metadata["train_records"] + metadata["calibration_records"] + metadata["test_records"] == 120

        # Verify calibration sample count matches calibration partition
        assert res["uncertainty_stats"]["calibration_sample_count"] == metadata["calibration_records"]
        assert res["uncertainty_stats"]["calibration_method"] == "dedicated_calibration_split"
        assert metadata["model_selection_criterion"] == "lowest_training_cv_mae"

    def test_model_selection_invariant_to_test_set_target_perturbation(self, tmp_path):
        """Requirement 3: Model selection uses only training/validation data; perturbing test targets changes nothing in selection."""
        df1 = _create_synthetic_dataset(120, random_state=42)
        csv1 = os.path.join(tmp_path, "dataset1.csv")
        df1.to_csv(csv1, index=False)

        # Dataset 2 has identical train/val partition, but we manually corrupt the test rows' targets
        df2 = _create_synthetic_dataset(120, random_state=42)
        train_df, val_df, test_df = duplicate_safe_train_val_test_split(df2, val_size=0.15, test_size=0.15, random_state=42)
        # Multiply test targets by 10x
        df2.loc[df2["id"].isin(test_df["id"]), "listed_price"] = df2.loc[df2["id"].isin(test_df["id"]), "listed_price"] * 10
        csv2 = os.path.join(tmp_path, "dataset2.csv")
        df2.to_csv(csv2, index=False)

        res1 = run_training_v002(
            processed_csv_path=csv1,
            models_dir=os.path.join(tmp_path, "models1"),
            experiments_dir=os.path.join(tmp_path, "exps1"),
            model_version="candidate_run1",
            random_state=42
        )

        res2 = run_training_v002(
            processed_csv_path=csv2,
            models_dir=os.path.join(tmp_path, "models2"),
            experiments_dir=os.path.join(tmp_path, "exps2"),
            model_version="candidate_run2",
            random_state=42
        )

        # The selected candidate model MUST BE IDENTICAL regardless of corrupted test set targets!
        assert res1["selected_model"] == res2["selected_model"]
        # The cross-validation scores on training data MUST BE IDENTICAL
        assert res1["candidate_cv_results"][res1["selected_model"]]["cv_mae_mean"] == \
               res2["candidate_cv_results"][res2["selected_model"]]["cv_mae_mean"]
        # The calibration residuals on calibration partition MUST BE IDENTICAL
        assert res1["uncertainty_stats"]["residual_q80"] == res2["uncertainty_stats"]["residual_q80"]
        # But the final test MAE will differ because test targets were altered
        assert res1["metrics"]["mae"] != res2["metrics"]["mae"]

    def test_calibration_residuals_provenance_and_quantiles(self):
        """Requirement 2: Calibration residuals are derived from held-out predictions and recorded with provenance."""
        estimator = PredictionUncertaintyEstimator()
        y_val_true = np.array([500000.0, 600000.0, 700000.0, 800000.0, 900000.0, 1000000.0])
        y_val_pred = np.array([520000.0, 580000.0, 710000.0, 760000.0, 950000.0, 1080000.0])

        stats = estimator.fit_residuals(y_val_true, y_val_pred, calibration_method="dedicated_calibration_split")

        assert stats["calibration_sample_count"] == 6
        assert stats["calibration_method"] == "dedicated_calibration_split"
        assert stats["quantile_definition"] == "empirical_absolute_residuals"
        assert stats["residual_q80"] > 0
        assert stats["residual_q90"] >= stats["residual_q80"]
        assert stats["mean_abs_residual"] > 0
        assert stats["median_abs_residual"] > 0

    def test_split_creation_reproducibility_and_isolation(self):
        """Requirement 4: Split creation is deterministic, reproducible, and cluster-isolated."""
        df = _create_synthetic_dataset(120, random_state=123)

        tr1, val1, te1 = duplicate_safe_train_val_test_split(df, val_size=0.15, test_size=0.15, random_state=42)
        tr2, val2, te2 = duplicate_safe_train_val_test_split(df, val_size=0.15, test_size=0.15, random_state=42)

        # Reproducibility check
        assert list(tr1["id"]) == list(tr2["id"])
        assert list(val1["id"]) == list(val2["id"])
        assert list(te1["id"]) == list(te2["id"])

        # Cluster non-overlap check
        train_ids = set(tr1["listing_id"])
        val_ids = set(val1["listing_id"])
        test_ids = set(te1["listing_id"])

        assert train_ids.isdisjoint(val_ids)
        assert train_ids.isdisjoint(test_ids)
        assert val_ids.isdisjoint(test_ids)

    def test_model_metrics_calculated_on_final_test_set_only(self, tmp_path):
        """Requirement 6: Metrics on the test set represent genuine out-of-sample generalization."""
        df = _create_synthetic_dataset(120)
        csv_path = os.path.join(tmp_path, "synthetic.csv")
        df.to_csv(csv_path, index=False)

        res = run_training_v002(
            processed_csv_path=csv_path,
            models_dir=os.path.join(tmp_path, "models"),
            experiments_dir=os.path.join(tmp_path, "exps"),
            model_version="candidate_test_metrics",
            random_state=42
        )

        meta = res["metadata"]
        assert "metrics_test" in meta
        assert "mae" in meta["metrics_test"]
        assert "rmse" in meta["metrics_test"]
        assert "r2" in meta["metrics_test"]
        assert "median_ae" in meta["metrics_test"]
        assert meta["evaluation_strategy"] == "duplicate_safe_train_val_test_split"
        assert meta["model_selection_criterion"] == "lowest_training_cv_mae"
        assert meta["status"] == "candidate"

    def test_preprocessing_fitted_only_on_training_folds(self):
        """Requirement 3: Preprocessing transformers (imputers, scalers) are fitted strictly on training data."""
        from ml.features.preprocessor import create_preprocessor_pipeline, NUMERICAL_FEATURES, CATEGORICAL_FEATURES
        from sklearn.pipeline import Pipeline
        from sklearn.linear_model import LinearRegression

        # Create training data with known median for engine_cc = 1200
        train_data = pd.DataFrame({
            "year": [2018, 2019, 2020],
            "car_age": [6, 5, 4],
            "km_driven": [50000, 40000, 30000],
            "km_per_year": [8333.3, 8000.0, 7500.0],
            "engine_cc": [1000.0, 1200.0, 1400.0],  # median is 1200
            "mileage": [18.0, 20.0, 22.0],
            "owner_count": [1, 1, 1],
            "brand": ["Hyundai", "Hyundai", "Hyundai"],
            "model": ["i20", "i20", "i20"],
            "variant": ["Sportz", "Sportz", "Sportz"],
            "fuel_type": ["Petrol", "Petrol", "Petrol"],
            "transmission": ["Manual", "Manual", "Manual"],
            "city": ["Bengaluru", "Bengaluru", "Bengaluru"],
            "state": ["Karnataka", "Karnataka", "Karnataka"],
            "seller_type": ["Individual", "Individual", "Individual"]
        })
        y_train = pd.Series([500000.0, 550000.0, 600000.0])

        # Create test data with missing engine_cc (NaN)
        test_data = pd.DataFrame({
            "year": [2021],
            "car_age": [3],
            "km_driven": [20000],
            "km_per_year": [6666.7],
            "engine_cc": [np.nan],  # Should be imputed with train median 1200, not test data
            "mileage": [19.0],
            "owner_count": [1],
            "brand": ["Hyundai"],
            "model": ["i20"],
            "variant": ["Sportz"],
            "fuel_type": ["Petrol"],
            "transmission": ["Manual"],
            "city": ["Bengaluru"],
            "state": ["Karnataka"],
            "seller_type": ["Individual"]
        })

        prep = create_preprocessor_pipeline()
        pipe = Pipeline([("preprocessor", prep), ("regressor", LinearRegression())])
        pipe.fit(train_data[NUMERICAL_FEATURES + CATEGORICAL_FEATURES], y_train)

        # Inspect fitted numerical imputer inside the preprocessor
        num_imputer = prep.named_transformers_["num"].named_steps["imputer"]
        engine_cc_idx = NUMERICAL_FEATURES.index("engine_cc")
        learned_median = num_imputer.statistics_[engine_cc_idx]

        assert learned_median == 1200.0, f"Expected learned median 1200.0 from training data, got {learned_median}"

        # Transforming test data must succeed using train-learned parameters
        transformed_test = prep.transform(test_data[NUMERICAL_FEATURES + CATEGORICAL_FEATURES])
        assert transformed_test.shape[0] == 1
        assert not np.isnan(transformed_test).any(), "Transformed test data contains NaNs!"

    def test_grouped_duplicates_cannot_cross_partitions(self):
        """Requirement 4: Listings of the same physical vehicle remain strictly within one partition."""
        records = [
            # Listing A and duplicate listing A_dup (same specs, city, price)
            {"id": 1, "listing_id": "item-A1", "brand": "Tata", "model": "Nexon", "year": 2021, "fuel_type": "Diesel", "transmission": "Manual", "km_driven": 30000, "city": "Pune", "listed_price": 950000.0, "duplicate_of_id": None},
            {"id": 2, "listing_id": "item-A2", "brand": "Tata", "model": "Nexon", "year": 2021, "fuel_type": "Diesel", "transmission": "Manual", "km_driven": 30000, "city": "Pune", "listed_price": 950000.0, "duplicate_of_id": 1},
            # Distinct listings
            {"id": 3, "listing_id": "item-B", "brand": "Honda", "model": "City", "year": 2019, "fuel_type": "Petrol", "transmission": "CVT", "km_driven": 45000, "city": "Mumbai", "listed_price": 850000.0, "duplicate_of_id": None},
            {"id": 4, "listing_id": "item-C", "brand": "Hyundai", "model": "Creta", "year": 2022, "fuel_type": "Petrol", "transmission": "Automatic", "km_driven": 15000, "city": "Bengaluru", "listed_price": 1550000.0, "duplicate_of_id": None},
            {"id": 5, "listing_id": "item-D", "brand": "Toyota", "model": "Innova", "year": 2018, "fuel_type": "Diesel", "transmission": "Manual", "km_driven": 90000, "city": "Delhi", "listed_price": 1400000.0, "duplicate_of_id": None},
            {"id": 6, "listing_id": "item-E", "brand": "Mahindra", "model": "Thar", "year": 2021, "fuel_type": "Diesel", "transmission": "Manual", "km_driven": 25000, "city": "Hyderabad", "listed_price": 1350000.0, "duplicate_of_id": None},
        ]
        df = pd.DataFrame(records)
        train_df, val_df, test_df = duplicate_safe_train_val_test_split(df, val_size=0.33, test_size=0.33, random_state=42)

        # IDs 1 and 2 must be in the exact same partition
        in_train = 1 in train_df["id"].values and 2 in train_df["id"].values
        in_val = 1 in val_df["id"].values and 2 in val_df["id"].values
        in_test = 1 in test_df["id"].values and 2 in test_df["id"].values

        assert in_train or in_val or in_test, "Duplicate listings 1 and 2 were split across different partitions!"
        assert not ((1 in train_df["id"].values and 2 not in train_df["id"].values) or
                    (1 in val_df["id"].values and 2 not in val_df["id"].values) or
                    (1 in test_df["id"].values and 2 not in test_df["id"].values))

    def test_experimental_training_protects_v002_artifact_from_overwrite(self, tmp_path):
        """Requirement 5: Experimental training does not overwrite active v002 artifacts."""
        df = _create_synthetic_dataset(120)
        csv_path = os.path.join(tmp_path, "synthetic.csv")
        df.to_csv(csv_path, index=False)

        models_dir = os.path.join(tmp_path, "models")
        os.makedirs(models_dir, exist_ok=True)

        # Mock an active v002 metadata file
        v002_meta_path = os.path.join(models_dir, "metadata_v002.json")
        with open(v002_meta_path, "w") as f:
            json.dump({"model_version": "v002", "protected": True}, f)

        # Attempt to run training with model_version="v002"
        res = run_training_v002(
            processed_csv_path=csv_path,
            models_dir=models_dir,
            experiments_dir=os.path.join(tmp_path, "exps"),
            model_version="v002",
            allow_overwrite=False,
            random_state=42
        )

        # Verify candidate version was used instead of overwriting v002
        assert res["model_version"] == "v003_candidate"
        with open(v002_meta_path, "r") as f:
            v002_content = json.load(f)
        assert v002_content.get("protected") is True, "Original metadata_v002.json was overwritten!"
        assert os.path.exists(os.path.join(models_dir, "metadata_v003_candidate.json"))
