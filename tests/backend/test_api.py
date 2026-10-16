"""
Integration tests for FastAPI endpoints.
Tests health endpoint, placeholder routes, and source registration.
"""
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "autovalue-api"


def test_root_endpoint(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "AutoValue API"
    assert data["status"] == "online"


def test_valuation_active_response(client: TestClient):
    payload = {
        "brand": "Hyundai",
        "model": "Creta",
        "variant": "SX",
        "year": 2021,
        "km_driven": 35000,
        "fuel_type": "Diesel",
        "transmission": "Manual",
        "city": "Bengaluru",
        "asking_price": 1350000.0
    }
    response = client.post("/api/valuation", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["model_version"] in ["v001", "v002"]
    assert "valuation" in data
    assert data["valuation"]["estimated_value"] > 10000.0
    assert "market" in data
    assert "comparables" in data
    assert "source_analysis" in data
    assert "explanation" in data
    assert data["market_position"] is not None


def test_valuation_invalid_input(client: TestClient):
    # Negative KM
    payload = {
        "brand": "Hyundai",
        "model": "Creta",
        "year": 2021,
        "km_driven": -500,
        "fuel_type": "Petrol",
        "transmission": "Manual",
        "city": "Bengaluru"
    }
    response = client.post("/api/valuation", json=payload)
    assert response.status_code == 422


def test_comparables_placeholder_response(client: TestClient):
    response = client.get("/api/comparables?brand=Hyundai&model=Creta")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_implemented"


def test_sources_registration_and_list(client: TestClient):
    # Register a test source
    source_payload = {
        "name": "example_test_source",
        "base_url": "https://test-marketplace.example.com",
        "active": True
    }
    post_res = client.post("/api/sources", json=source_payload)
    assert post_res.status_code == 200
    created = post_res.json()
    assert created["name"] == "example_test_source"
    assert created["id"] > 0

    # Retrieve sources
    get_res = client.get("/api/sources")
    assert get_res.status_code == 200
    sources_list = get_res.json()
    assert len(sources_list) >= 1
    assert any(s["name"] == "example_test_source" for s in sources_list)
