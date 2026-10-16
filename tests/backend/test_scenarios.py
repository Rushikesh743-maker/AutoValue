"""
Tests for AutoValue What-If Vehicle Simulator Service (Phase 11).
Validates counterfactual simulations, active model inference re-use,
quantified parameter changes, and API endpoint integration.
"""
import pytest
from backend.app.schemas.intelligence import ScenarioRequest
from backend.app.schemas.valuation import ValuationRequestSchema
from backend.app.services.scenario_service import scenario_service


def test_scenario_mileage_increase_reduces_value():
    """Simulating higher mileage should project lower or equal estimated value."""
    base_veh = ValuationRequestSchema(
        brand="Hyundai",
        model="Creta",
        year=2021,
        km_driven=30000,
        fuel_type="Diesel",
        transmission="Manual",
        city="Mumbai"
    )
    req = ScenarioRequest(
        base_vehicle=base_veh,
        changes={"km_driven": 90000}
    )
    res = scenario_service.simulate_scenario(req)

    assert res.base_estimate > 0
    assert res.scenario_estimate > 0
    assert res.scenario_estimate < res.base_estimate
    assert res.estimated_change < 0
    assert res.percentage_change < 0
    assert "km_driven" in res.changed_features
    assert len(res.explanation) > 0


def test_scenario_year_increase_increases_value():
    """Simulating a newer model year should project higher estimated value."""
    base_veh = ValuationRequestSchema(
        brand="Honda",
        model="City",
        year=2018,
        km_driven=50000,
        fuel_type="Petrol",
        transmission="Manual",
        city="Pune"
    )
    req = ScenarioRequest(
        base_vehicle=base_veh,
        changes={"year": 2022}
    )
    res = scenario_service.simulate_scenario(req)

    assert res.scenario_estimate > res.base_estimate
    assert res.estimated_change > 0
    assert "year" in res.changed_features


def test_scenario_no_changes_yields_zero_delta():
    """Simulating with no changes produces 0 estimated change."""
    base_veh = ValuationRequestSchema(
        brand="Maruti",
        model="Swift",
        year=2020,
        km_driven=40000,
        fuel_type="Petrol",
        transmission="Manual",
        city="Delhi"
    )
    req = ScenarioRequest(
        base_vehicle=base_veh,
        changes={}
    )
    res = scenario_service.simulate_scenario(req)

    assert res.estimated_change == 0.0
    assert res.scenario_estimate == res.base_estimate


def test_scenario_api_endpoint(client):
    """Ensure POST /api/scenario handles simulation payloads correctly."""
    payload = {
        "base_vehicle": {
            "brand": "Hyundai",
            "model": "Creta",
            "year": 2021,
            "km_driven": 35000,
            "fuel_type": "Diesel",
            "transmission": "Manual",
            "city": "Bengaluru"
        },
        "changes": {
            "km_driven": 65000,
            "city": "Delhi"
        }
    }
    response = client.post("/api/scenario", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "base_estimate" in data
    assert "scenario_estimate" in data
    assert "changed_features" in data
    assert set(data["changed_features"]) == {"km_driven", "city"}
