"""
Unit tests for PredictionUncertaintyEstimator.
"""
import pytest
import numpy as np
from ml.evaluation.uncertainty import PredictionUncertaintyEstimator


class TestUncertainty:
    def test_fit_residuals_and_estimate_interval(self):
        y_true = np.array([500000, 600000, 700000, 800000, 900000])
        y_pred = np.array([520000, 580000, 710000, 760000, 950000])

        estimator = PredictionUncertaintyEstimator()
        stats = estimator.fit_residuals(y_true, y_pred)

        assert stats["residual_q80"] > 0
        assert stats["median_abs_residual"] > 0

        interval = estimator.estimate_interval(point_prediction=700000.0, confidence_level=0.80)

        assert interval["interval_low"] < 700000.0
        assert interval["interval_high"] > 700000.0
        assert interval["confidence_level"] == 0.80
        assert "residual quantile" in interval["method"].lower()
