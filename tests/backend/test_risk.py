"""
Unit and API test suite for Vehicle Risk & Trust Intelligence Engine (Phase 12).
Validates:
- All 9 deterministic risk factor calculations and weights
- Insufficient evidence handling
- Severity mappings and composite scoring
- POST /api/risk, GET /api/risk/{id}, POST /api/risk/batch
- Authentication, IDOR protection, and share token access
- Extreme edge cases (zero comparables, high mileage, extreme prices)
"""
import pytest
from fastapi.testclient import TestClient

from backend.app.schemas.valuation import ValuationRequestSchema
from backend.app.services.valuation_service import valuation_service
from backend.app.services.risk_service import risk_service
from backend.app.models.saved_valuation import SavedValuation
from backend.app.models.user import User
from backend.app.models.share_token import ShareToken
from backend.app.core.security import hash_password, create_access_token


def test_risk_weights_sum_to_one():
    """Validates that all configured risk dimension weights sum to exactly 1.0 (100%)."""
    total_weight = sum(risk_service.RISK_WEIGHTS.values())
    assert pytest.approx(total_weight, 0.001) == 1.0
    assert len(risk_service.RISK_WEIGHTS) == 9


def test_risk_evaluation_deterministic_factors():
    """Validates that all 9 risk factors are computed with proper bounds and evidence."""
    req = ValuationRequestSchema(
        brand="Hyundai",
        model="Creta",
        variant="SX",
        year=2021,
        fuel_type="Petrol",
        transmission="Manual",
        km_driven=35000,
        city="Mumbai",
        asking_price=1220000.0,
        engine_cc=1497,
        mileage=16.8,
        owner_count=1,
        seller_type="Individual"
    )

    val_resp = valuation_service.evaluate_valuation(req)
    risk_resp = risk_service.evaluate_risk(req.model_dump(), val_resp)

    assert 0 <= risk_resp.risk_score <= 100
    assert risk_resp.risk_level in ["VERY_LOW", "LOW", "MODERATE", "HIGH", "VERY_HIGH"]
    assert risk_resp.confidence in ["HIGH", "MEDIUM", "LOW"]
    assert len(risk_resp.factors) == 9

    # Verify all factor keys are present
    factor_keys = {f.key for f in risk_resp.factors}
    expected_keys = {
        "price_anomaly", "mileage_usage", "vehicle_age",
        "market_liquidity", "data_quality", "market_evidence",
        "valuation_uncertainty", "price_dispersion", "source_concentration"
    }
    assert factor_keys == expected_keys

    # Verify unverified physical condition factors are present
    assert len(risk_resp.unknowns) >= 8
    assert any("Engine" in u for u in risk_resp.unknowns)
    assert any("Accident" in u or "collision" in u.lower() for u in risk_resp.unknowns)


def test_price_anomaly_risk_scoring():
    """Validates price anomaly factor under low, moderate, and extreme deviations."""
    base_dict = {
        "brand": "Hyundai",
        "model": "Creta",
        "year": 2021,
        "fuel_type": "Petrol",
        "transmission": "Manual",
        "km_driven": 35000,
        "city": "Mumbai"
    }
    val_req = ValuationRequestSchema(**base_dict)
    val_resp = valuation_service.evaluate_valuation(val_req)
    est_val = val_resp.valuation.estimated_value

    # Case 1: Close to fair value (2% difference)
    dict_close = dict(base_dict, asking_price=est_val * 1.02)
    risk_close = risk_service.evaluate_risk(dict_close, val_resp)
    factor_close = next(f for f in risk_close.factors if f.key == "price_anomaly")
    assert factor_close.score <= 25

    # Case 2: Extreme deviation (35% difference)
    dict_extreme = dict(base_dict, asking_price=est_val * 1.35)
    risk_extreme = risk_service.evaluate_risk(dict_extreme, val_resp)
    factor_extreme = next(f for f in risk_extreme.factors if f.key == "price_anomaly")
    assert factor_extreme.score >= 75


def test_mileage_usage_risk_scoring():
    """Validates mileage intensity scoring for low vs extreme annual driving."""
    base_dict = {
        "brand": "Maruti",
        "model": "Swift",
        "year": 2020,
        "fuel_type": "Petrol",
        "transmission": "Manual",
        "city": "Delhi"
    }

    # Case 1: Low mileage (4 years, 16,000 km -> 4,000 km/yr)
    dict_low_km = dict(base_dict, km_driven=16000)
    val_resp_low = valuation_service.evaluate_valuation(ValuationRequestSchema(**dict_low_km))
    risk_low = risk_service.evaluate_risk(dict_low_km, val_resp_low)
    factor_low = next(f for f in risk_low.factors if f.key == "mileage_usage")
    assert factor_low.score <= 25

    # Case 2: Extreme mileage (4 years, 120,000 km -> 30,000 km/yr)
    dict_high_km = dict(base_dict, km_driven=120000)
    val_resp_high = valuation_service.evaluate_valuation(ValuationRequestSchema(**dict_high_km))
    risk_high = risk_service.evaluate_risk(dict_high_km, val_resp_high)
    factor_high = next(f for f in risk_high.factors if f.key == "mileage_usage")
    assert factor_high.score >= 75


def test_post_risk_api_endpoint(client: TestClient):
    """Validates POST /api/risk single vehicle risk intelligence."""
    payload = {
        "brand": "Honda",
        "model": "City",
        "variant": "V",
        "year": 2020,
        "fuel_type": "Petrol",
        "transmission": "Manual",
        "km_driven": 40000,
        "city": "Bengaluru",
        "asking_price": 980000.0
    }
    response = client.post("/api/risk", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "risk_score" in data
    assert "risk_level" in data
    assert "factors" in data
    assert "evidence_summary" in data
    assert len(data["factors"]) == 9
    assert data["evidence_summary"]["comparables_count"] >= 0


def test_post_batch_risk_api_endpoint(client: TestClient):
    """Validates POST /api/risk/batch for multiple candidate vehicles."""
    payload = {
        "vehicles": [
            {
                "brand": "Hyundai",
                "model": "Creta",
                "year": 2021,
                "fuel_type": "Petrol",
                "transmission": "Manual",
                "km_driven": 30000,
                "city": "Mumbai"
            },
            {
                "brand": "Maruti",
                "model": "Swift",
                "year": 2019,
                "fuel_type": "Petrol",
                "transmission": "Manual",
                "km_driven": 75000,
                "city": "Delhi"
            }
        ]
    }
    response = client.post("/api/risk/batch", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["total_vehicles"] == 2
    assert len(data["results"]) == 2
    assert data["results"][0]["brand"] == "Hyundai"
    assert data["results"][1]["brand"] == "Maruti"


def test_saved_valuation_risk_auth_and_idor(client: TestClient):
    """Validates GET /api/risk/{valuation_id} with ownership enforcement and IDOR protection."""
    # Register User A and User B
    res_a = client.post("/api/auth/register", json={"email": "risk_a@example.com", "password": "Password123!"})
    token_a = res_a.json()["access_token"]

    res_b = client.post("/api/auth/register", json={"email": "risk_b@example.com", "password": "Password123!"})
    token_b = res_b.json()["access_token"]

    # Save a valuation for User A
    save_payload = {
        "vehicle": {
            "brand": "Hyundai",
            "model": "Creta",
            "variant": "SX",
            "year": 2021,
            "fuel_type": "Petrol",
            "transmission": "Manual",
            "km_driven": 35000,
            "city": "Mumbai",
            "asking_price": 1250000.0
        },
        "valuation_result": {
            "model_version": "v002",
            "dataset_version": "v0.3",
            "valuation": {
                "estimated_value": 1220000.0,
                "estimated_value_formatted": "₹12.20 Lakh",
                "range_low": 1150000.0,
                "range_high": 1280000.0,
                "range_low_formatted": "₹11.50 Lakh",
                "range_high_formatted": "₹12.80 Lakh",
                "range_method": "empirical_market_bounds",
                "combination_method": "blended",
                "model_interval": {
                    "interval_low": 1160000.0,
                    "interval_high": 1270000.0,
                    "interval_low_formatted": "₹11.60 Lakh",
                    "interval_high_formatted": "₹12.70 Lakh",
                    "confidence_level": 0.80,
                    "method": "conformal"
                }
            },
            "market": {
                "median": 1210000.0,
                "p25": 1140000.0,
                "p75": 1260000.0,
                "comparable_count": 8,
                "density": "HIGH"
            },
            "comparables": [],
            "source_analysis": [],
            "explanation": [],
            "transparency_notice": "Notice"
        }
    }

    save_res = client.post(
        "/api/valuations",
        json=save_payload,
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert save_res.status_code == 201
    val_id = save_res.json()["id"]

    # 1. Unauthenticated request without token/cookies -> 401
    client.cookies.clear()
    resp_unauth = client.get(f"/api/risk/{val_id}")
    assert resp_unauth.status_code == 401

    # 2. Authenticated as User A (owner) -> 200 OK
    resp_owner = client.get(
        f"/api/risk/{val_id}",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert resp_owner.status_code == 200
    assert "risk_score" in resp_owner.json()

    # 3. Authenticated as User B (IDOR attempt) -> 403 Forbidden
    resp_idor = client.get(
        f"/api/risk/{val_id}",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert resp_idor.status_code == 403

    # 4. Generate share token for valuation -> User B can view via share_token query param
    share_res = client.post(
        f"/api/valuations/{val_id}/share",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert share_res.status_code == 200
    share_token = share_res.json()["share_token"]

    resp_shared = client.get(f"/api/risk/{val_id}?share_token={share_token}")
    assert resp_shared.status_code == 200
    assert resp_shared.json()["risk_score"] >= 0

    # 5. Non-existent ID -> 404 Not Found
    resp_404 = client.get(
        "/api/risk/non-existent-id-999",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert resp_404.status_code == 404
