"""
Integration tests for Vehicle and Valuation Comparison.
Validates side-by-side comparison matrix, empirical differences calculation,
and factual summaries without subjective winner rankings.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def auth_compare_user(client: TestClient):
    payload = {"email": "compare_user@example.com", "password": "Password12345!"}
    res = client.post("/api/auth/register", json=payload)
    token = res.json()["access_token"]
    return {"token": token, "headers": {"Authorization": f"Bearer {token}"}}


def test_compare_valuations_empirical_deltas(client: TestClient, auth_compare_user):
    headers = auth_compare_user["headers"]

    # Save Valuation 1 (Creta)
    val1_payload = {
        "vehicle": {
            "brand": "Hyundai",
            "model": "Creta",
            "variant": "SX",
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
            "valuation": {"estimated_value": 1300000.0, "estimated_value_formatted": "₹13.00 Lakh", "range_method": "empirical", "combination_method": "blended"},
            "market": {"median": 1320000.0, "comparable_count": 6},
            "comparables": [],
            "source_analysis": [],
            "explanation": [],
            "transparency_notice": "Empirical model estimate."
        }
    }
    v1_id = client.post("/api/valuations", json=val1_payload, headers=headers).json()["id"]

    # Save Valuation 2 (Seltos)
    val2_payload = {
        "vehicle": {
            "brand": "Kia",
            "model": "Seltos",
            "variant": "HTX",
            "year": 2022,
            "fuel_type": "Diesel",
            "transmission": "Manual",
            "km_driven": 20000,
            "city": "Bengaluru",
            "asking_price": 1450000.0
        },
        "valuation_result": {
            "model_version": "v002",
            "dataset_version": "v0.3",
            "valuation": {"estimated_value": 1420000.0, "estimated_value_formatted": "₹14.20 Lakh", "range_method": "empirical", "combination_method": "blended"},
            "market": {"median": 1440000.0, "comparable_count": 8},
            "comparables": [],
            "source_analysis": [],
            "explanation": [],
            "transparency_notice": "Empirical model estimate."
        }
    }
    v2_id = client.post("/api/valuations", json=val2_payload, headers=headers).json()["id"]

    # Compare 2 valuations
    cmp_payload = {"valuation_ids": [v1_id, v2_id]}
    cmp_res = client.post("/api/compare", json=cmp_payload, headers=headers)
    assert cmp_res.status_code == 200
    cmp_data = cmp_res.json()
    assert len(cmp_data["vehicles"]) == 2
    assert len(cmp_data["empirical_differences"]) >= 3

    # Check for factual delta description (higher or lower depending on base item order)
    diff_texts = [d["description"].lower() for d in cmp_data["empirical_differences"]]
    assert any("estimated value" in d for d in diff_texts)
    assert any("driven" in d for d in diff_texts)

    # Ensure NO subjective labels are used
    summary = cmp_data["factual_summary"].lower()
    assert "winner" not in summary
    assert "best car" not in summary


def test_compare_limit_bounds(client: TestClient, auth_compare_user):
    headers = auth_compare_user["headers"]

    # Less than 2 items -> 400
    res_under = client.post("/api/compare", json={"valuation_ids": ["val1"]}, headers=headers)
    assert res_under.status_code == 400

    # More than 3 items -> 422 or 400 validation error
    res_over = client.post("/api/compare", json={"valuation_ids": ["v1", "v2", "v3", "v4"]}, headers=headers)
    assert res_over.status_code in [400, 422]
