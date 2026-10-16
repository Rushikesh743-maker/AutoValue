"""
Unit tests for DriftDetector and PSI calculation.
"""
import pytest
import numpy as np
import pandas as pd
from ml.monitoring.drift_detector import DriftDetector, calculate_psi


class TestDriftDetector:
    def test_calculate_psi_identical_and_shifted(self):
        np.random.seed(42)
        base = np.random.normal(50000, 10000, 500)
        curr_same = np.random.normal(50000, 10000, 500)
        curr_shifted = np.random.normal(90000, 15000, 500)

        psi_same = calculate_psi(base, curr_same)
        psi_shifted = calculate_psi(base, curr_shifted)

        assert psi_same < 0.10, "Identical distribution should have PSI < 0.10"
        assert psi_shifted > 0.20, "Significantly shifted distribution should have high PSI"

    def test_drift_report_generation(self):
        base_df = pd.DataFrame({
            "km_driven": np.random.normal(50000, 10000, 100),
            "year": np.random.randint(2015, 2022, 100),
            "car_age": np.random.randint(2, 9, 100),
            "km_per_year": np.random.normal(10000, 2000, 100),
            "listed_price": np.random.normal(800000, 200000, 100)
        })

        curr_df = base_df.copy()
        detector = DriftDetector(base_df)
        report = detector.generate_drift_report(curr_df)

        assert report["overall_status"] == "HEALTHY"
        assert len(report["feature_audits"]) > 0
