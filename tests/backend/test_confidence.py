"""
Tests for AutoValue Data Confidence and Condition Limitations Layer (Phase 11).
Validates completeness calculations, model confidence, and mandatory physical unknown warnings.
"""
import pytest
from backend.app.services.data_confidence_service import data_confidence_service


def test_confidence_evaluation_complete_data():
    """Complete vehicle specification returns high completeness and confidence."""
    veh_data = {
        "brand": "Hyundai",
        "model": "Creta",
        "variant": "SX",
        "year": 2021,
        "km_driven": 25000,
        "city": "Mumbai",
        "fuel_type": "Diesel",
        "transmission": "Manual",
        "engine_cc": 1493,
        "mileage": 18.5,
        "owner_count": 1,
        "seller_type": "Individual"
    }
    res = data_confidence_service.evaluate_confidence(
        vehicle_data=veh_data,
        comparable_count=8,
        estimated_value=1250000,
        interval_low=1180000,
        interval_high=1320000
    )
    assert res.data_completeness == 1.0
    assert res.market_confidence == "HIGH"
    assert res.comparable_quality == "HIGH"
    assert res.model_confidence == "HIGH"
    assert res.condition_unknown_warning is True
    assert len(res.unverified_factors) >= 8
    assert "flood damage" in " ".join(res.unverified_factors)
    assert "odometer" in " ".join(res.unverified_factors)


def test_confidence_evaluation_sparse_data():
    """Sparse vehicle input returns lower completeness score."""
    veh_data = {
        "brand": "Maruti",
        "model": "Swift",
        "year": 2018,
        "km_driven": 60000,
        "city": "Delhi"
    }
    res = data_confidence_service.evaluate_confidence(
        vehicle_data=veh_data,
        comparable_count=0,
        estimated_value=500000
    )
    assert res.data_completeness < 0.6
    assert res.comparable_quality == "INSUFFICIENT"
    assert res.market_confidence == "LOW"
    assert res.condition_unknown_warning is True
