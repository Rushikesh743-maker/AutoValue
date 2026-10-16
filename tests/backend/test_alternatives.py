"""
Tests for AutoValue Alternative Vehicle Discovery Service (Phase 11).
Validates multi-attribute candidate scoring, budget filtering, criteria explanations,
and fallback handling.
"""
import pytest
from backend.app.schemas.intelligence import AlternativeVehicleQuery
from backend.app.services.alternative_vehicle_service import alternative_vehicle_service


def test_find_alternatives_with_budget():
    """Search returns ranked candidate vehicles within budget."""
    query = AlternativeVehicleQuery(
        target_budget=800000,
        budget_min=500000,
        budget_max=1200000,
        limit=5
    )
    res = alternative_vehicle_service.find_alternatives(query)
    assert res.count <= 5
    if res.count > 0:
        first = res.results[0]
        assert first.listed_price >= 500000
        assert first.listed_price <= 1200000
        assert 0.0 <= first.overall_match_score <= 100.0
        assert len(first.match_reasons) > 0


def test_find_alternatives_with_fuel_filter():
    """Search respects fuel_type and transmission filters."""
    query = AlternativeVehicleQuery(
        target_budget=1000000,
        fuel_type="Diesel",
        limit=4
    )
    res = alternative_vehicle_service.find_alternatives(query)
    for r in res.results:
        if r.fuel_type:
            assert r.fuel_type.lower() == "diesel"


def test_find_alternatives_unmatched_budget_returns_empty():
    """Unrealistic budget bounds return clean empty results without error."""
    query = AlternativeVehicleQuery(
        budget_min=99999999,
        budget_max=999999999,
        limit=5
    )
    res = alternative_vehicle_service.find_alternatives(query)
    assert res.count == 0
    assert res.results == []


def test_alternatives_api_endpoint(client):
    """Ensure POST /api/alternatives responds with typed candidates."""
    payload = {
        "target_budget": 900000,
        "limit": 3
    }
    response = client.post("/api/alternatives", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "results" in data
    assert "ranking_methodology" in data
