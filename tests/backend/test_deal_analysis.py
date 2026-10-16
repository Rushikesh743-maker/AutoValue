"""
Tests for AutoValue Smart Deal Analysis Engine (Phase 11).
Validates deterministic price classification, threshold boundaries, mathematical evidence,
sparse segment handling, and missing asking price states.
"""
import pytest
from backend.app.services.deal_analysis_service import deal_analysis_service


def test_deal_analysis_fairly_priced():
    """Asking price within fair range (+/- 4%) should be classified as FAIRLY_PRICED."""
    res = deal_analysis_service.evaluate_deal(
        asking_price=1200000,
        estimated_value=1215000,
        market_median=1200000,
        market_p25=1140000,
        market_p75=1260000,
        comparables=[{"id": f"c{i}"} for i in range(6)]
    )
    assert res.classification == "FAIRLY_PRICED"
    assert res.evidence_strength == "HIGH"
    assert res.asking_price_vs_market_median == 0.0
    assert res.percentage_difference_from_market_median == 0.0
    assert res.price_position in ["BETWEEN_P25_AND_MEDIAN", "BETWEEN_MEDIAN_AND_P75"]


def test_deal_analysis_significantly_below_market():
    """Asking price > 12% below market benchmark should be classified as SIGNIFICANTLY_BELOW_MARKET."""
    res = deal_analysis_service.evaluate_deal(
        asking_price=950000,
        estimated_value=1200000,
        market_median=1200000,
        market_p25=1100000,
        market_p75=1300000,
        comparables=[{"id": f"c{i}"} for i in range(8)]
    )
    assert res.classification == "SIGNIFICANTLY_BELOW_MARKET"
    assert res.price_position == "BELOW_P25"
    assert res.percentage_difference_from_market_median < -12.0
    assert res.evidence_strength == "HIGH"


def test_deal_analysis_significantly_above_market():
    """Asking price > 12% above market benchmark should be classified as SIGNIFICANTLY_ABOVE_MARKET."""
    res = deal_analysis_service.evaluate_deal(
        asking_price=1450000,
        estimated_value=1200000,
        market_median=1200000,
        market_p25=1100000,
        market_p75=1300000,
        comparables=[{"id": f"c{i}"} for i in range(7)]
    )
    assert res.classification == "SIGNIFICANTLY_ABOVE_MARKET"
    assert res.price_position == "ABOVE_P75"
    assert res.percentage_difference_from_market_median > 12.0


def test_deal_analysis_missing_asking_price():
    """When asking price is None or 0, return INSUFFICIENT_EVIDENCE with explanation."""
    res = deal_analysis_service.evaluate_deal(
        asking_price=None,
        estimated_value=1200000,
        market_median=1200000,
        comparables=[{"id": "c1"}]
    )
    assert res.classification == "INSUFFICIENT_EVIDENCE"
    assert res.asking_price is None
    assert "No asking price provided" in res.explanation


def test_deal_analysis_zero_comparables_sparse_segment():
    """Sparse segment with zero comparables flags low/insufficient evidence."""
    res = deal_analysis_service.evaluate_deal(
        asking_price=1220000,
        estimated_value=1200000,
        market_median=None,
        comparables=[]
    )
    assert res.evidence_strength == "INSUFFICIENT"
    assert res.comparable_support_score == 0.0
    assert res.asking_price_vs_ml == 20000.0


def test_deal_analysis_endpoint_integration(client):
    """Ensure /api/intelligence evaluates deal analysis correctly."""
    payload = {
        "brand": "Hyundai",
        "model": "Creta",
        "year": 2021,
        "km_driven": 35000,
        "fuel_type": "Diesel",
        "transmission": "Manual",
        "city": "Mumbai",
        "asking_price": 1250000
    }
    response = client.post("/api/intelligence", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "deal_analysis" in data
    deal = data["deal_analysis"]
    assert "classification" in deal
    assert "evidence_strength" in deal
    assert deal["asking_price"] == 1250000
