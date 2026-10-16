"""
Tests for AutoValue Value-for-Money Scoring Service (Phase 11).
Validates transparent component scores, weight combinations, extreme value bounds,
and condition disclaimer distinctions.
"""
import pytest
from backend.app.services.value_score_service import value_score_service


def test_value_score_high_value_vehicle():
    """Low mileage, modern year, discounted price yields a high value score."""
    res = value_score_service.calculate_value_score(
        year=2022,
        km_driven=15000,
        estimated_value=1200000,
        asking_price=1050000,  # ~12.5% discount
        market_median=1200000,
        comparable_count=7
    )
    assert res.overall_value_score >= 80.0
    assert res.rating_label in ["EXCELLENT_VALUE", "GOOD_VALUE"]
    assert res.price_value_score > 75.0
    assert res.mileage_value_score > 75.0
    assert res.age_value_score > 75.0
    assert "weights_applied" in res.score_breakdown
    assert "PRICE VALUE from VEHICLE CONDITION" in res.disclaimer or "does NOT evaluate physical" in res.disclaimer


def test_value_score_overpriced_high_mileage():
    """High mileage, older year, and premium asking price yields lower value score."""
    res = value_score_service.calculate_value_score(
        year=2014,
        km_driven=160000,
        estimated_value=400000,
        asking_price=500000,  # 25% premium
        market_median=400000,
        comparable_count=3
    )
    assert res.overall_value_score < 55.0
    assert res.rating_label in ["BELOW_AVERAGE_VALUE", "POOR_VALUE", "FAIR_VALUE"]
    assert res.price_value_score < 50.0


def test_value_score_without_asking_price():
    """Calculates weighted score gracefully when asking price is omitted."""
    res = value_score_service.calculate_value_score(
        year=2020,
        km_driven=40000,
        estimated_value=900000,
        asking_price=None,
        market_median=900000,
        comparable_count=5
    )
    assert res.price_value_score is None
    assert 0.0 <= res.overall_value_score <= 100.0
    assert res.score_breakdown["weights_applied"]["price_weight"] == 0.0


def test_value_score_bounds_and_clipping():
    """Score remains strictly in [0, 100] even with extreme values."""
    res_extreme = value_score_service.calculate_value_score(
        year=1995,
        km_driven=999999,
        estimated_value=100000,
        asking_price=10000000,  # 9900% premium
        comparable_count=0
    )
    assert 0.0 <= res_extreme.overall_value_score <= 100.0
    assert res_extreme.price_value_score == 0.0
