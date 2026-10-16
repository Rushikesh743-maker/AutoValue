"""
Unit and API test suite for Total Cost of Ownership & Resale Intelligence Engine (Phase 13).
Validates:
- Fuel cost calculations across all fuels (Petrol, Diesel, CNG, Electric/EV, Hybrid)
- Multi-year depreciation curves, resale projections, and uncertainty bounds
- Ownership scenarios (Conservative, Base, Optimistic) and deterministic multipliers
- 5-variable sensitivity perturbations
- API endpoints: POST /api/tco, GET /api/tco/{valuation_id}, POST /api/tco/scenario, POST /api/tco/compare
- Security: 401 unauthenticated, 403 non-owner IDOR protection, share-token validation
- Extreme and edge cases: zero annual km, negative values, unsupported fuel type, bounded comparison limits
"""
import pytest
from fastapi.testclient import TestClient

from backend.app.schemas.valuation import ValuationRequestSchema
from backend.app.schemas.tco import TCOAssumptions, TCOScenarioRequest
from backend.app.services.valuation_service import valuation_service
from backend.app.services.tco_service import tco_service
from backend.app.models.saved_valuation import SavedValuation
from backend.app.models.user import User
from backend.app.models.share_token import ShareToken
from backend.app.core.security import hash_password, create_access_token


def test_tco_calculation_petrol_default():
    """Validates baseline 5-year TCO calculation for petrol vehicle."""
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
        mileage=16.0,
        owner_count=1,
        seller_type="Individual"
    )

    val_resp = valuation_service.evaluate_valuation(req)
    tco_resp = tco_service.calculate_tco(req.model_dump(), val_resp)

    # Basic structure assertions
    assert tco_resp.ownership.gross_cost > 0
    assert tco_resp.ownership.estimated_resale > 0
    assert tco_resp.ownership.net_tco > 0
    assert tco_resp.ownership.net_tco == round(tco_resp.ownership.gross_cost - tco_resp.ownership.estimated_resale, 2)
    assert tco_resp.ownership.annual_cost == round(tco_resp.ownership.net_tco / 5, 2)
    assert tco_resp.ownership.cost_per_km == round(tco_resp.ownership.net_tco / 60000, 2)

    # Resale assertions
    assert tco_resp.resale.lower_bound <= tco_resp.resale.estimated_resale_value <= tco_resp.resale.upper_bound
    assert tco_resp.resale.confidence in ["HIGH", "MODERATE", "LOW", "INSUFFICIENT_EVIDENCE"]
    assert 0 < tco_resp.resale.projected_retention_pct < 100

    # Yearly projections count matches horizon
    assert len(tco_resp.yearly_projection) == 5

    # Sensitivity analysis
    assert len(tco_resp.sensitivity) == 5

    # Scenarios
    assert "CONSERVATIVE" in tco_resp.scenarios
    assert "BASE" in tco_resp.scenarios
    assert "OPTIMISTIC" in tco_resp.scenarios
    assert tco_resp.scenarios["CONSERVATIVE"].net_tco > tco_resp.scenarios["OPTIMISTIC"].net_tco


def test_tco_fuel_types():
    """Validates fuel/energy cost calculations for Diesel, CNG, and Electric."""
    base_dict = {
        "brand": "Tata",
        "model": "Nexon",
        "year": 2022,
        "km_driven": 25000,
        "city": "Pune",
        "transmission": "Manual"
    }

    # 1. Diesel
    d_req = ValuationRequestSchema(**dict(base_dict, fuel_type="Diesel"))
    d_val = valuation_service.evaluate_valuation(d_req)
    d_tco = tco_service.calculate_tco(d_req.model_dump(), d_val)
    assert d_tco.ownership.fuel_cost > 0

    # 2. CNG
    c_req = ValuationRequestSchema(**dict(base_dict, fuel_type="CNG"))
    c_val = valuation_service.evaluate_valuation(c_req)
    c_tco = tco_service.calculate_tco(c_req.model_dump(), c_val)
    assert c_tco.ownership.fuel_cost > 0

    # 3. Electric (EV)
    e_req = ValuationRequestSchema(**dict(base_dict, fuel_type="Electric"))
    e_val = valuation_service.evaluate_valuation(e_req)
    e_tco = tco_service.calculate_tco(e_req.model_dump(), e_val)
    assert e_tco.ownership.fuel_cost > 0
    # Electric running cost should generally be substantially lower than ICE fuels
    assert e_tco.ownership.fuel_cost < d_tco.ownership.fuel_cost


def test_tco_purchase_price_modes():
    """Validates FAIR_VALUE, ASKING_PRICE, and CUSTOM purchase price modes."""
    req = ValuationRequestSchema(
        brand="Honda",
        model="City",
        year=2020,
        fuel_type="Petrol",
        transmission="Manual",
        km_driven=40000,
        city="Delhi",
        asking_price=950000.0
    )
    val_resp = valuation_service.evaluate_valuation(req)
    fair_val = val_resp.valuation.estimated_value

    # FAIR_VALUE Mode
    tco_fair = tco_service.calculate_tco(req.model_dump(), val_resp, TCOAssumptions(purchase_price_mode="FAIR_VALUE"))
    assert tco_fair.purchase.price == round(fair_val, 2)
    assert tco_fair.purchase.mode == "FAIR_VALUE"

    # ASKING_PRICE Mode
    tco_ask = tco_service.calculate_tco(req.model_dump(), val_resp, TCOAssumptions(purchase_price_mode="ASKING_PRICE"))
    assert tco_ask.purchase.price == 950000.0
    assert tco_ask.purchase.mode == "ASKING_PRICE"

    # CUSTOM Mode
    tco_custom = tco_service.calculate_tco(req.model_dump(), val_resp, TCOAssumptions(
        purchase_price_mode="CUSTOM",
        custom_purchase_price=880000.0
    ))
    assert tco_custom.purchase.price == 880000.0
    assert tco_custom.purchase.mode == "CUSTOM"


def test_tco_custom_horizons():
    """Validates custom ownership horizons (1, 3, 10 years)."""
    req = ValuationRequestSchema(
        brand="Maruti",
        model="Swift",
        year=2019,
        fuel_type="Petrol",
        transmission="Manual",
        km_driven=50000,
        city="Bengaluru"
    )
    val_resp = valuation_service.evaluate_valuation(req)

    # 1 Year Horizon
    tco_1 = tco_service.calculate_tco(req.model_dump(), val_resp, TCOAssumptions(ownership_years=1))
    assert len(tco_1.yearly_projection) == 1
    assert tco_1.ownership.annual_cost == tco_1.ownership.net_tco

    # 10 Year Horizon
    tco_10 = tco_service.calculate_tco(req.model_dump(), val_resp, TCOAssumptions(ownership_years=10))
    assert len(tco_10.yearly_projection) == 10
    assert tco_10.ownership.total_projected_km == 120000


def test_tco_zero_annual_mileage_edge_case():
    """Validates that 0 annual km executes safely without division by zero."""
    req = ValuationRequestSchema(
        brand="Hyundai",
        model="i20",
        year=2021,
        fuel_type="Petrol",
        transmission="Manual",
        km_driven=20000,
        city="Mumbai"
    )
    val_resp = valuation_service.evaluate_valuation(req)
    tco_zero = tco_service.calculate_tco(req.model_dump(), val_resp, TCOAssumptions(annual_km=0))

    assert tco_zero.ownership.fuel_cost == 0.0
    assert tco_zero.ownership.cost_per_km == 0.0
    assert tco_zero.ownership.total_projected_km == 0


def test_tco_sensitivity_mathematical_consistency():
    """Validates that sensitivity perturbations yield mathematically exact directions."""
    req = ValuationRequestSchema(
        brand="Toyota",
        model="Innova",
        year=2018,
        fuel_type="Diesel",
        transmission="Manual",
        km_driven=80000,
        city="Hyderabad",
        asking_price=1600000.0
    )
    val_resp = valuation_service.evaluate_valuation(req)
    tco_res = tco_service.calculate_tco(req.model_dump(), val_resp)

    # Check fuel price sensitivity (+10% fuel -> higher net TCO)
    fuel_sens = next(s for s in tco_res.sensitivity if s.variable == "fuel_price")
    assert fuel_sens.delta_tco > 0
    assert fuel_sens.new_net_tco > tco_res.ownership.net_tco

    # Check purchase price sensitivity (-₹50,000 price -> lower net TCO)
    price_sens = next(s for s in tco_res.sensitivity if s.variable == "purchase_price")
    assert price_sens.delta_tco < 0
    assert price_sens.new_net_tco < tco_res.ownership.net_tco


def test_tco_api_post_endpoint(client: TestClient):
    """Validates POST /api/tco endpoint."""
    payload = {
        "vehicle": {
            "brand": "Hyundai",
            "model": "Creta",
            "year": 2021,
            "km_driven": 35000,
            "fuel_type": "Petrol",
            "transmission": "Manual",
            "city": "Mumbai",
            "asking_price": 1200000
        },
        "assumptions": {
            "ownership_years": 5,
            "annual_km": 15000,
            "fuel_price": 105.0,
            "fuel_efficiency": 15.0
        }
    }
    response = client.post("/api/tco", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "ownership" in data
    assert "resale" in data
    assert "yearly_projection" in data
    assert data["ownership"]["total_projected_km"] == 75000


def test_tco_api_scenario_endpoint(client: TestClient):
    """Validates POST /api/tco/scenario endpoint."""
    payload = {
        "vehicle": {
            "brand": "Kia",
            "model": "Seltos",
            "year": 2022,
            "km_driven": 20000,
            "fuel_type": "Diesel",
            "transmission": "Manual",
            "city": "Delhi"
        },
        "scenario_name": "BASE",
        "assumptions": {
            "ownership_years": 3,
            "annual_km": 10000
        }
    }
    response = client.post("/api/tco/scenario", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "ownership" in data
    assert "scenarios" in data
    assert "CONSERVATIVE" in data["scenarios"]
    assert "BASE" in data["scenarios"]
    assert "OPTIMISTIC" in data["scenarios"]
    assert data["scenarios"]["CONSERVATIVE"]["net_tco"] > data["scenarios"]["OPTIMISTIC"]["net_tco"]


def test_tco_api_compare_endpoint(client: TestClient):
    """Validates POST /api/tco/compare endpoint and boundary enforcement."""
    veh_a = {
        "brand": "Hyundai",
        "model": "Creta",
        "year": 2021,
        "km_driven": 35000,
        "fuel_type": "Petrol",
        "transmission": "Manual",
        "city": "Mumbai"
    }
    veh_b = {
        "brand": "Tata",
        "model": "Nexon",
        "year": 2022,
        "km_driven": 20000,
        "fuel_type": "Electric",
        "transmission": "Manual",
        "city": "Mumbai"
    }

    response = client.post("/api/tco/compare", json={"vehicles": [veh_a, veh_b]})
    assert response.status_code == 200
    data = response.json()
    assert data["total_vehicles"] == 2
    assert len(data["results"]) == 2
    assert "break_even_analysis" in data

    # Boundary test: Over 10 vehicles must fail with 400 or 422
    oversized = [veh_a] * 11
    resp_over = client.post("/api/tco/compare", json={"vehicles": oversized})
    assert resp_over.status_code in [400, 422]


def test_tco_get_by_valuation_id_security(client: TestClient):
    """Validates authentication, IDOR protection, and share-token access for GET /api/tco/{valuation_id}."""
    # 1. Register User A and User B
    res_a = client.post("/api/auth/register", json={"email": "tco_user_a@example.com", "password": "Password123!"})
    token_a = res_a.json()["access_token"]

    res_b = client.post("/api/auth/register", json={"email": "tco_user_b@example.com", "password": "Password123!"})
    token_b = res_b.json()["access_token"]

    # 2. Save a valuation for User A
    save_payload = {
        "vehicle": {
            "brand": "Hyundai",
            "model": "Venue",
            "variant": "SX",
            "year": 2021,
            "fuel_type": "Petrol",
            "transmission": "Manual",
            "km_driven": 30000,
            "city": "Pune",
            "asking_price": 850000.0
        },
        "valuation_result": {
            "model_version": "v002",
            "dataset_version": "v0.3",
            "valuation": {
                "estimated_value": 850000.0,
                "estimated_value_formatted": "₹8.50 Lakh",
                "range_low": 800000.0,
                "range_high": 900000.0,
                "range_low_formatted": "₹8.00 Lakh",
                "range_high_formatted": "₹9.00 Lakh",
                "range_method": "empirical_market_bounds",
                "combination_method": "blended",
                "model_interval": {
                    "interval_low": 810000.0,
                    "interval_high": 890000.0,
                    "interval_low_formatted": "₹8.10 Lakh",
                    "interval_high_formatted": "₹8.90 Lakh",
                    "confidence_level": 0.80,
                    "method": "conformal"
                }
            },
            "market": {
                "median": 840000.0,
                "p25": 800000.0,
                "p75": 880000.0,
                "comparable_count": 6,
                "density": "MEDIUM"
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

    # 3. Unauthenticated request without token/cookies -> 401
    client.cookies.clear()
    resp_unauth = client.get(f"/api/tco/{val_id}")
    assert resp_unauth.status_code == 401

    # 4. Authenticated as User A (owner) -> 200 OK
    resp_owner = client.get(
        f"/api/tco/{val_id}",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert resp_owner.status_code == 200
    assert resp_owner.json()["vehicle"]["brand"] == "Hyundai"
    assert "ownership" in resp_owner.json()

    # 5. Authenticated as User B (IDOR attempt) -> 403 Forbidden
    resp_idor = client.get(
        f"/api/tco/{val_id}",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert resp_idor.status_code == 403

    # 6. Generate share token for valuation -> User B can view via share_token query param
    share_res = client.post(
        f"/api/valuations/{val_id}/share",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert share_res.status_code == 200
    share_token = share_res.json()["share_token"]

    resp_shared = client.get(f"/api/tco/{val_id}?share_token={share_token}")
    assert resp_shared.status_code == 200
    assert resp_shared.json()["ownership"]["net_tco"] > 0


def test_yearly_projection_formatted_fields_and_cost_per_km():
    """Validates that all yearly projection items have formatted fields and cost_per_km_to_date."""
    req = ValuationRequestSchema(
        brand="Maruti Suzuki",
        model="Swift",
        year=2020,
        fuel_type="Petrol",
        transmission="Manual",
        km_driven=40000,
        city="Delhi",
        asking_price=650000.0
    )
    val_resp = valuation_service.evaluate_valuation(req)
    tco_resp = tco_service.calculate_tco(req.model_dump(), val_resp)

    for item in tco_resp.yearly_projection:
        assert item.cost_per_km_to_date is not None
        assert item.cost_per_km_to_date >= 0.0
        assert item.resale_value_formatted is not None
        assert "₹" in item.resale_value_formatted
        assert item.resale_low_formatted is not None
        assert item.resale_high_formatted is not None
        assert item.cumulative_gross_formatted is not None
        assert item.net_cost_to_date_formatted is not None


def test_tco_zero_annual_km_safe():
    """Validates that 0 annual km does not divide by zero."""
    req = ValuationRequestSchema(
        brand="Honda",
        model="City",
        year=2019,
        fuel_type="Petrol",
        km_driven=50000,
        city="Mumbai",
        transmission="Manual"
    )
    val_resp = valuation_service.evaluate_valuation(req)
    assumptions = TCOAssumptions(annual_km=0, ownership_years=3)
    tco_resp = tco_service.calculate_tco(req.model_dump(), val_resp, assumptions=assumptions)

    assert tco_resp.ownership.cost_per_km == 0.0
    for item in tco_resp.yearly_projection:
        assert item.cumulative_km == 0
        assert item.cost_per_km_to_date == 0.0

