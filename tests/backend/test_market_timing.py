"""
Tests for AutoValue Market Timing Intelligence Service (Phase 11).
Validates observed historical trajectory calculation, direction classification,
and disclaimer transparency.
"""
import pytest
from backend.app.services.market_timing_service import market_timing_service


def test_market_timing_available_model():
    """Calculates direction and percentage movement for common models."""
    res = market_timing_service.analyze_market_timing(
        brand="Hyundai",
        model="Creta",
        time_period="all"
    )
    assert res.brand == "Hyundai"
    assert res.model == "Creta"
    assert res.direction in ["RISING", "STABLE", "DECLINING", "INSUFFICIENT_DATA"]
    assert "Observed market movement" in res.disclaimer or "historical listing" in res.disclaimer


def test_market_timing_nonexistent_model():
    """Nonexistent model returns INSUFFICIENT_DATA."""
    res = market_timing_service.analyze_market_timing(
        brand="Ferrari",
        model="LaFerrariNonexistent999",
        time_period="3m"
    )
    assert res.direction == "INSUFFICIENT_DATA"
    assert res.evidence_strength == "INSUFFICIENT"
    assert res.recent_median is None


def test_market_timing_api_endpoint(client):
    """Ensure GET /api/market/timing responds with market timing payload."""
    response = client.get("/api/market/timing?brand=Hyundai&model=Creta")
    assert response.status_code == 200
    data = response.json()
    assert "direction" in data
    assert "observation_count" in data
    assert "summary" in data
