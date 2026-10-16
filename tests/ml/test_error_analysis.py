"""
Unit tests for ErrorAnalyzer and segment metrics calculation.
"""
import pytest
import numpy as np
import pandas as pd
from ml.evaluation.error_analysis import ErrorAnalyzer


class TestErrorAnalysis:
    def test_residual_calculation_and_bands(self):
        y_true = np.array([400000.0, 750000.0, 1500000.0, 2500000.0])
        y_pred = np.array([380000.0, 720000.0, 1550000.0, 2400000.0])
        features_df = pd.DataFrame({
            "brand": ["Maruti", "Hyundai", "Mahindra", "BMW"],
            "year": [2018, 2021, 2022, 2023],
            "car_age": [6, 3, 2, 1],
            "km_driven": [65000, 35000, 25000, 15000],
            "fuel_type": ["Petrol", "Diesel", "Diesel", "Petrol"],
            "transmission": ["Manual", "Manual", "Automatic", "Automatic"],
            "city": ["Pune", "Pune", "Mumbai", "Delhi"]
        })

        analyzer = ErrorAnalyzer(min_segment_size=1)
        res_df = analyzer.calculate_residuals(y_true, y_pred, features_df)

        assert "residual" in res_df.columns
        assert "absolute_error" in res_df.columns
        assert "percentage_error" in res_df.columns
        assert "price_band" in res_df.columns
        assert "age_band" in res_df.columns
        assert "km_band" in res_df.columns

        # Verify exact math
        assert res_df.loc[0, "residual"] == 20000.0
        assert res_df.loc[0, "absolute_error"] == 20000.0
        assert res_df.loc[0, "percentage_error"] == 5.0

    def test_run_full_error_analysis(self):
        y_true = np.array([500000.0, 600000.0, 700000.0, 800000.0, 900000.0, 1000000.0])
        y_pred = np.array([480000.0, 610000.0, 690000.0, 780000.0, 910000.0, 980000.0])
        features_df = pd.DataFrame({
            "brand": ["Maruti"] * 6,
            "fuel_type": ["Petrol"] * 6,
            "transmission": ["Manual"] * 6,
            "city": ["Pune"] * 6,
            "car_age": [4] * 6,
            "km_driven": [40000] * 6
        })

        analyzer = ErrorAnalyzer(min_segment_size=3)
        report = analyzer.run_full_error_analysis(y_true, y_pred, features_df)

        assert "overall_metrics" in report
        assert report["overall_metrics"]["count"] == 6
        assert report["overall_metrics"]["mae"] > 0
        assert len(report["by_brand"]) > 0
        assert report["by_brand"][0]["status"] == "Adequate"
