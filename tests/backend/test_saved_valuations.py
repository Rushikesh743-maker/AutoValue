"""
Integration tests for Saved Valuations, Valuation History, and IDOR Security.
Validates immutable snapshot storage, pagination, detail retrieval,
and strict access controls across multiple users.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def auth_user_a(client: TestClient):
    payload = {"email": "user_a@example.com", "password": "Password12345!"}
    res = client.post("/api/auth/register", json=payload)
    token = res.json()["access_token"]
    return {"token": token, "headers": {"Authorization": f"Bearer {token}"}, "user": res.json()["user"]}


@pytest.fixture
def auth_user_b(client: TestClient):
    payload = {"email": "user_b@example.com", "password": "Password12345!"}
    res = client.post("/api/auth/register", json=payload)
    token = res.json()["access_token"]
    return {"token": token, "headers": {"Authorization": f"Bearer {token}"}, "user": res.json()["user"]}


def generate_sample_valuation_save_payload():
    return {
        "vehicle": {
            "brand": "Hyundai",
            "model": "Creta",
            "variant": "1.5 CRDi SX",
            "year": 2021,
            "fuel_type": "Diesel",
            "transmission": "Manual",
            "km_driven": 35000,
            "city": "Bengaluru",
            "asking_price": 1350000.0
        },
        "valuation_result": {
            "model_version": "v002",
            "dataset_version": "v0.3",
            "valuation": {
                "estimated_value": 1320000.0,
                "estimated_value_formatted": "₹13.20 Lakh",
                "range_low": 1240000.0,
                "range_high": 1400000.0,
                "range_low_formatted": "₹12.40 Lakh",
                "range_high_formatted": "₹14.00 Lakh",
                "range_method": "empirical_market_bounds",
                "combination_method": "blended",
                "model_interval": {
                    "interval_low": 1250000.0,
                    "interval_high": 1390000.0,
                    "interval_low_formatted": "₹12.50 Lakh",
                    "interval_high_formatted": "₹13.90 Lakh",
                    "confidence_level": 0.90,
                    "method": "conformal_residual_quantile"
                }
            },
            "market": {
                "median": 1340000.0,
                "comparable_count": 5
            },
            "comparables": [],
            "source_analysis": [],
            "explanation": [
                {
                    "feature": "km_driven",
                    "impact_inr": -35000.0,
                    "direction": "decreases_price",
                    "human_readable_text": "35,000 km odometer reading reduces estimated value by ₹35,000"
                }
            ],
            "transparency_notice": "Empirical model estimate.",
            "request_id": "req-test-12345"
        },
        "notes": "Verified pre-purchase inspection report"
    }


def test_save_valuation_unauthenticated(client: TestClient):
    payload = generate_sample_valuation_save_payload()
    response = client.post("/api/valuations", json=payload)
    assert response.status_code == 401


def test_save_valuation_authenticated(client: TestClient, auth_user_a):
    payload = generate_sample_valuation_save_payload()
    response = client.post("/api/valuations", json=payload, headers=auth_user_a["headers"])
    assert response.status_code == 201
    data = response.json()
    assert data["brand"] == "Hyundai"
    assert data["model"] == "Creta"
    assert data["estimated_value"] == 1320000.0
    assert data["notes"] == "Verified pre-purchase inspection report"
    assert data["id"] is not None


def test_valuation_history_pagination(client: TestClient, auth_user_a):
    # Save multiple valuations
    for i in range(5):
        payload = generate_sample_valuation_save_payload()
        payload["vehicle"]["km_driven"] = 30000 + i * 5000
        client.post("/api/valuations", json=payload, headers=auth_user_a["headers"])

    # Page 1 with page_size=2
    res = client.get("/api/valuations?page=1&page_size=2", headers=auth_user_a["headers"])
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["total_pages"] == 3


def test_valuation_detail_and_idor_protection(client: TestClient, auth_user_a, auth_user_b):
    # User A saves a valuation
    save_payload = generate_sample_valuation_save_payload()
    save_res = client.post("/api/valuations", json=save_payload, headers=auth_user_a["headers"])
    val_id = save_res.json()["id"]

    # User A accesses own valuation
    get_res_a = client.get(f"/api/valuations/{val_id}", headers=auth_user_a["headers"])
    assert get_res_a.status_code == 200
    data_a = get_res_a.json()
    assert data_a["id"] == val_id
    assert data_a["payload"] is not None
    assert len(data_a["payload"]["explanation"]) == 1

    # User B attempts to access User A's valuation (IDOR test)
    get_res_b = client.get(f"/api/valuations/{val_id}", headers=auth_user_b["headers"])
    assert get_res_b.status_code in [403, 404]

    # User B attempts to delete User A's valuation (IDOR test)
    del_res_b = client.delete(f"/api/valuations/{val_id}", headers=auth_user_b["headers"])
    assert del_res_b.status_code in [403, 404]

    # User A deletes own valuation
    del_res_a = client.delete(f"/api/valuations/{val_id}", headers=auth_user_a["headers"])
    assert del_res_a.status_code == 200

    # Ensure valuation is gone
    get_after_del = client.get(f"/api/valuations/{val_id}", headers=auth_user_a["headers"])
    assert get_after_del.status_code == 404
