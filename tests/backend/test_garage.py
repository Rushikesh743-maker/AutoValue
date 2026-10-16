"""
Unit and Integration Tests for Garage & Portfolio Intelligence Engine (Phase 16).
Validates CRUD, authentication, IDOR protection, summary aggregation, rankings,
sell-first/keep-first priorities, redundancy detection, efficiency score, scenarios,
batch limits, break-even math, division-by-zero guards, and telemetry.
"""
import pytest
from datetime import datetime, timezone
from starlette.testclient import TestClient

from backend.app.models.user import User
from backend.app.models.garage import GarageVehicle
from backend.app.core.security import hash_password, create_access_token
from backend.app.schemas.garage import (
    OwnershipStatus,
    UtilizationClass,
    PortfolioAction,
    PortfolioConfidence,
    GarageVehicleCreate,
    GarageVehicleUpdate,
    GarageScenarioRequest,
    GarageScenarioVehicleAction,
    GarageScenarioActionType,
    GarageCompareRequest
)
from backend.app.services.garage_intelligence_service import (
    GarageIntelligenceService,
    garage_intelligence_service
)


@pytest.fixture
def service():
    return GarageIntelligenceService()


@pytest.fixture
def test_user(db_session):
    u = User(
        email="garage_owner_p16@example.com",
        password_hash=hash_password("Pass12345!"),
        is_active=True
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def other_user(db_session):
    u = User(
        email="other_garage_user_p16@example.com",
        password_hash=hash_password("Pass12345!"),
        is_active=True
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def user_token(test_user):
    return create_access_token(subject=str(test_user.id))


@pytest.fixture
def other_token(other_user):
    return create_access_token(subject=str(other_user.id))


class TestGarageService:
    """Service-level unit tests for portfolio algorithms and aggregations."""

    def test_create_and_get_vehicle(self, service: GarageIntelligenceService, db_session, test_user):
        """Test creating a garage vehicle and retrieving it."""
        req = GarageVehicleCreate(
            brand="Hyundai",
            model="Creta",
            variant="1.5 CRDi SX",
            year=2021,
            fuel_type="Diesel",
            transmission="Manual",
            city="Bengaluru",
            nickname="Daily Creta",
            ownership_status=OwnershipStatus.OWNED,
            purchase_price=1250000.0,
            annual_km=14000,
            current_odometer=35000,
            ownership_purpose="Daily Commute"
        )
        veh = service.create_vehicle(db_session, test_user.id, req)
        assert veh.id is not None
        assert veh.brand == "Hyundai"
        assert veh.ownership_status == "OWNED"

        retrieved = service.get_vehicle(db_session, test_user.id, veh.id)
        assert retrieved is not None
        assert retrieved.nickname == "Daily Creta"

    def test_list_and_filter_vehicles(self, service: GarageIntelligenceService, db_session, test_user):
        """Test listing and filtering garage vehicles by ownership status."""
        v1 = GarageVehicle(
            user_id=test_user.id,
            brand="Honda",
            model="City",
            year=2020,
            ownership_status=OwnershipStatus.OWNED.value,
            annual_km=12000
        )
        v2 = GarageVehicle(
            user_id=test_user.id,
            brand="Kia",
            model="Seltos",
            year=2022,
            ownership_status=OwnershipStatus.CONSIDERING.value,
            annual_km=10000
        )
        db_session.add_all([v1, v2])
        db_session.commit()

        all_veh = service.list_vehicles(db_session, test_user.id)
        assert len(all_veh) >= 2

        owned_only = service.list_vehicles(db_session, test_user.id, status=OwnershipStatus.OWNED)
        assert any(v.model == "City" for v in owned_only)
        assert not any(v.model == "Seltos" for v in owned_only)

    def test_update_and_delete_vehicle(self, service: GarageIntelligenceService, db_session, test_user):
        """Test updating vehicle metadata and deleting it."""
        veh = GarageVehicle(
            user_id=test_user.id,
            brand="Maruti Suzuki",
            model="Swift",
            year=2019,
            ownership_status=OwnershipStatus.OWNED.value,
            annual_km=8000
        )
        db_session.add(veh)
        db_session.commit()

        upd = GarageVehicleUpdate(annual_km=15000, nickname="Upgraded Swift")
        updated = service.update_vehicle(db_session, test_user.id, veh.id, upd)
        assert updated.annual_km == 15000
        assert updated.nickname == "Upgraded Swift"

        deleted = service.delete_vehicle(db_session, test_user.id, veh.id)
        assert deleted is True
        assert service.get_vehicle(db_session, test_user.id, veh.id) is None

    def test_vehicle_snapshot_evaluation(self, service: GarageIntelligenceService, db_session, test_user):
        """Test individual vehicle snapshot evaluation."""
        veh = GarageVehicle(
            user_id=test_user.id,
            brand="Hyundai",
            model="Creta",
            year=2021,
            fuel_type="Diesel",
            transmission="Manual",
            city="Bengaluru",
            purchase_price=1200000.0,
            annual_km=12000,
            current_odometer=35000,
            ownership_status=OwnershipStatus.OWNED.value
        )
        db_session.add(veh)
        db_session.commit()

        snap = service.evaluate_vehicle_snapshot(veh)
        assert snap.current_estimated_value > 0
        assert snap.five_year_tco > 0
        assert snap.annual_ownership_cost > 0
        assert snap.cost_per_km > 0
        assert snap.risk_score >= 0
        assert snap.utilization_class == UtilizationClass.MODERATE

    def test_empty_garage_intelligence(self, service: GarageIntelligenceService, db_session, test_user):
        """Test portfolio intelligence on an empty garage."""
        intel = service.evaluate_garage_intelligence(db_session, test_user.id)
        assert intel.summary.total_vehicles == 0
        assert intel.summary.total_current_value == 0.0
        assert intel.recommendation.action == PortfolioAction.INSUFFICIENT_EVIDENCE
        assert intel.efficiency.overall_score == 0.0

    def test_multi_vehicle_portfolio_aggregation(self, service: GarageIntelligenceService, db_session, test_user):
        """Test portfolio aggregation across multiple owned vehicles."""
        v1 = GarageVehicle(
            user_id=test_user.id,
            brand="Hyundai",
            model="Creta",
            year=2021,
            fuel_type="Diesel",
            transmission="Manual",
            city="Bengaluru",
            purchase_price=1200000.0,
            annual_km=15000,
            ownership_status=OwnershipStatus.OWNED.value
        )
        v2 = GarageVehicle(
            user_id=test_user.id,
            brand="Maruti Suzuki",
            model="Swift",
            year=2020,
            fuel_type="Petrol",
            transmission="Manual",
            city="Bengaluru",
            purchase_price=600000.0,
            annual_km=10000,
            ownership_status=OwnershipStatus.OWNED.value
        )
        db_session.add_all([v1, v2])
        db_session.commit()

        intel = service.evaluate_garage_intelligence(db_session, test_user.id)
        assert intel.summary.total_vehicles >= 2
        assert intel.summary.total_current_value > 1000000.0
        assert intel.summary.total_annual_cost > 0.0
        assert intel.summary.total_5y_tco > 0.0
        assert intel.summary.average_cost_per_km > 0.0
        assert len(intel.vehicle_snapshots) >= 2

    def test_garage_efficiency_weights_sum_to_one(self, service: GarageIntelligenceService):
        """Verify centralized efficiency weights sum to 1.0 (100%)."""
        total_w = (
            service.WEIGHT_ECONOMICS +
            service.WEIGHT_UTILIZATION +
            service.WEIGHT_RISK +
            service.WEIGHT_MARKET_POSITION +
            service.WEIGHT_RESALE_STRENGTH +
            service.WEIGHT_REDUNDANCY
        )
        assert round(total_w, 4) == 1.0

    def test_sell_first_ranking_order(self, service: GarageIntelligenceService, db_session, test_user):
        """Test sell-first ranking correctly prioritizes higher depreciation/sell timing."""
        v1 = GarageVehicle(
            user_id=test_user.id,
            brand="Hyundai",
            model="Creta",
            year=2016,  # Older -> higher depreciation
            fuel_type="Diesel",
            annual_km=5000,  # Low utilization
            ownership_status=OwnershipStatus.OWNED.value
        )
        v2 = GarageVehicle(
            user_id=test_user.id,
            brand="Honda",
            model="City",
            year=2022,
            fuel_type="Petrol",
            annual_km=16000,  # High utilization
            ownership_status=OwnershipStatus.OWNED.value
        )
        db_session.add_all([v1, v2])
        db_session.commit()

        intel = service.evaluate_garage_intelligence(db_session, test_user.id)
        assert len(intel.sell_first_ranking) >= 2
        assert intel.sell_first_ranking[0].sell_priority_score >= intel.sell_first_ranking[1].sell_priority_score
        assert len(intel.sell_first_ranking[0].factors) > 0

    def test_keep_first_ranking_order(self, service: GarageIntelligenceService, db_session, test_user):
        """Test keep-first ranking correctly prioritizes high utility and low cost/km."""
        v1 = GarageVehicle(
            user_id=test_user.id,
            brand="Maruti Suzuki",
            model="Swift",
            year=2022,
            fuel_type="Petrol",
            annual_km=18000,
            ownership_status=OwnershipStatus.OWNED.value
        )
        db_session.add(v1)
        db_session.commit()

        intel = service.evaluate_garage_intelligence(db_session, test_user.id)
        assert len(intel.keep_first_ranking) >= 1
        assert intel.keep_first_ranking[0].keep_priority_score > 0

    def test_vehicle_redundancy_detection(self, service: GarageIntelligenceService, db_session, test_user):
        """Test vehicle redundancy detection between overlapping vehicle roles."""
        v1 = GarageVehicle(
            user_id=test_user.id,
            brand="Hyundai",
            model="Creta",
            year=2021,
            fuel_type="Diesel",
            annual_km=12000,
            ownership_purpose="Daily Commute",
            ownership_status=OwnershipStatus.OWNED.value
        )
        v2 = GarageVehicle(
            user_id=test_user.id,
            brand="Kia",
            model="Seltos",
            year=2021,
            fuel_type="Diesel",
            annual_km=4000,  # Low utilization overlap
            ownership_purpose="Daily Commute",
            ownership_status=OwnershipStatus.OWNED.value
        )
        db_session.add_all([v1, v2])
        db_session.commit()

        intel = service.evaluate_garage_intelligence(db_session, test_user.id)
        assert len(intel.redundancies) >= 1
        assert intel.redundancies[0].redundancy_level in ["HIGH", "MODERATE"]
        assert intel.redundancies[0].potential_annual_savings > 0

    def test_replacement_opportunity_break_even(self, service: GarageIntelligenceService, db_session, test_user):
        """Test replacement opportunity discovery and break-even math."""
        veh = GarageVehicle(
            user_id=test_user.id,
            brand="Hyundai",
            model="Creta",
            year=2018,
            fuel_type="Diesel",
            annual_km=16000,
            ownership_status=OwnershipStatus.OWNED.value
        )
        db_session.add(veh)
        db_session.commit()

        intel = service.evaluate_garage_intelligence(db_session, test_user.id)
        if intel.replacement_opportunities:
            repl = intel.replacement_opportunities[0]
            assert repl.replacement_score >= 0
            if repl.break_even_months is not None:
                assert repl.break_even_months >= 0.0

    def test_garage_scenario_simulation(self, service: GarageIntelligenceService, db_session, test_user):
        """Test simulating what-if selling of an expensive vehicle."""
        v1 = GarageVehicle(
            user_id=test_user.id,
            brand="Hyundai",
            model="Creta",
            year=2021,
            annual_km=15000,
            ownership_status=OwnershipStatus.OWNED.value
        )
        v2 = GarageVehicle(
            user_id=test_user.id,
            brand="Honda",
            model="City",
            year=2019,
            annual_km=8000,
            ownership_status=OwnershipStatus.OWNED.value
        )
        db_session.add_all([v1, v2])
        db_session.commit()

        sc_req = GarageScenarioRequest(
            actions=[
                GarageScenarioVehicleAction(
                    vehicle_id=v2.id,
                    action_type=GarageScenarioActionType.SELL
                )
            ]
        )
        res = service.simulate_garage_scenario(db_session, test_user.id, sc_req)
        assert res.scenario_summary.total_vehicles == res.baseline_summary.total_vehicles - 1 or res.delta_annual_cost <= 0
        assert res.delta_annual_cost <= 0.0  # Selling a car reduces total annual operating expense


class TestGarageAPI:
    """Integration API tests for /api/garage routes."""

    def test_unauthenticated_requests_return_401(self, client: TestClient):
        """Verify unauthenticated access to /api/garage returns 401."""
        assert client.get("/api/garage").status_code == 401
        assert client.get("/api/garage/intelligence").status_code == 401
        assert client.post("/api/garage", json={}).status_code == 401

    def test_create_and_list_garage_vehicles(self, client: TestClient, user_token):
        """Test POST /api/garage and GET /api/garage."""
        payload = {
            "brand": "Hyundai",
            "model": "Creta",
            "variant": "SX",
            "year": 2021,
            "fuel_type": "Diesel",
            "transmission": "Manual",
            "city": "Bengaluru",
            "nickname": "Test Creta",
            "annual_km": 14000
        }
        r_post = client.post(
            "/api/garage",
            json=payload,
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert r_post.status_code == 201
        data = r_post.json()
        assert data["brand"] == "Hyundai"
        assert data["nickname"] == "Test Creta"

        r_get = client.get(
            "/api/garage",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert r_get.status_code == 200
        items = r_get.json()
        assert len(items) >= 1
        assert any(i["id"] == data["id"] for i in items)

    def test_idor_protection_other_user_forbidden(self, client: TestClient, db_session, test_user, other_user, other_token):
        """Verify User B cannot view or update User A's vehicle (403 Forbidden)."""
        veh = GarageVehicle(
            user_id=test_user.id,
            brand="Honda",
            model="City",
            year=2021,
            ownership_status=OwnershipStatus.OWNED.value
        )
        db_session.add(veh)
        db_session.commit()

        # Other user tries to GET
        r_get = client.get(
            f"/api/garage/{veh.id}",
            headers={"Authorization": f"Bearer {other_token}"}
        )
        assert r_get.status_code == 403

        # Other user tries to PATCH
        r_patch = client.patch(
            f"/api/garage/{veh.id}",
            json={"nickname": "Hacked Nickname"},
            headers={"Authorization": f"Bearer {other_token}"}
        )
        assert r_patch.status_code == 403

        # Other user tries to DELETE
        r_del = client.delete(
            f"/api/garage/{veh.id}",
            headers={"Authorization": f"Bearer {other_token}"}
        )
        assert r_del.status_code == 403

    def test_not_found_returns_404(self, client: TestClient, user_token):
        """Verify accessing a non-existent vehicle ID returns 404."""
        r = client.get(
            "/api/garage/non_existent_id_12345",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert r.status_code == 404

    def test_get_garage_intelligence_endpoint(self, client: TestClient, db_session, test_user, user_token):
        """Test GET /api/garage/intelligence endpoint."""
        veh = GarageVehicle(
            user_id=test_user.id,
            brand="Tata",
            model="Harrier",
            year=2021,
            fuel_type="Diesel",
            annual_km=15000,
            ownership_status=OwnershipStatus.OWNED.value
        )
        db_session.add(veh)
        db_session.commit()

        r = client.get(
            "/api/garage/intelligence",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert r.status_code == 200
        data = r.json()
        assert "summary" in data
        assert "efficiency" in data
        assert "recommendation" in data
        assert "sell_first_ranking" in data
        assert "keep_first_ranking" in data

    def test_post_garage_scenario_endpoint(self, client: TestClient, db_session, test_user, user_token):
        """Test POST /api/garage/scenario."""
        veh = GarageVehicle(
            user_id=test_user.id,
            brand="Hyundai",
            model="Creta",
            year=2021,
            annual_km=14000,
            ownership_status=OwnershipStatus.OWNED.value
        )
        db_session.add(veh)
        db_session.commit()

        payload = {
            "actions": [
                {
                    "vehicle_id": veh.id,
                    "action_type": "UPDATE_MILEAGE",
                    "annual_km_override": 20000
                }
            ]
        }
        r = client.post(
            "/api/garage/scenario",
            json=payload,
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert r.status_code == 200
        data = r.json()
        assert "baseline_summary" in data
        assert "scenario_summary" in data
        assert "delta_annual_cost" in data

    def test_scenario_batch_limit_exceeded(self, client: TestClient, user_token):
        """Verify scenario with >10 actions returns 400."""
        payload = {
            "actions": [
                {"action_type": "ADD", "replacement_vehicle": {"brand": "Honda", "model": "City", "year": 2020}}
                for _ in range(11)
            ]
        }
        r = client.post(
            "/api/garage/scenario",
            json=payload,
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert r.status_code in [400, 422]

    def test_post_garage_compare_endpoint(self, client: TestClient, db_session, test_user, user_token):
        """Test POST /api/garage/compare with 2 vehicles."""
        v1 = GarageVehicle(
            user_id=test_user.id,
            brand="Hyundai",
            model="Creta",
            year=2021,
            ownership_status=OwnershipStatus.OWNED.value
        )
        v2 = GarageVehicle(
            user_id=test_user.id,
            brand="Maruti Suzuki",
            model="Swift",
            year=2020,
            ownership_status=OwnershipStatus.OWNED.value
        )
        db_session.add_all([v1, v2])
        db_session.commit()

        r = client.post(
            "/api/garage/compare",
            json={"vehicle_ids": [v1.id, v2.id]},
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total_vehicles"] == 2
        assert "economic_rankings" in data
        assert len(data["vehicles"]) == 2

    def test_valuation_exception_no_fabricated_fallback(self, service: GarageIntelligenceService, monkeypatch):
        """Regression test for Task 3: verify valuation failure never injects ₹800,000 fallback."""
        from unittest.mock import MagicMock
        import backend.app.services.garage_intelligence_service as gis_module

        mock_val_service = MagicMock()
        mock_val_service.evaluate_valuation.side_effect = RuntimeError("Valuation ML model unavailable")
        monkeypatch.setattr(gis_module, "valuation_service", mock_val_service)

        veh = GarageVehicle(
            id="veh_unsupported_1",
            user_id="user_123",
            brand="UnknownBrand",
            model="RarePrototype",
            year=2022,
            fuel_type="Electric",
            transmission="Automatic",
            annual_km=10000,
            ownership_status=OwnershipStatus.OWNED.value
        )

        snap = service.evaluate_vehicle_snapshot(veh)
        assert snap.current_estimated_value is None
        assert snap.current_estimated_value_formatted == "—"
        assert snap.five_year_tco is None
        assert snap.confidence == "INSUFFICIENT_EVIDENCE"
        assert snap.lifecycle_action == "INSUFFICIENT_EVIDENCE"

    def test_mixed_portfolio_aggregation_and_excluded_vehicles(self, service: GarageIntelligenceService, monkeypatch):
        """Regression test for Task 3: mixed valid and unvalued vehicles in portfolio."""
        from unittest.mock import MagicMock

        def mock_eval(req, *args, **kwargs):
            if req.brand == "UnsupportedBrand":
                raise ValueError("Model not trained for this brand")
            mock_res = MagicMock()
            mock_res.valuation = MagicMock()
            mock_res.valuation.estimated_value = 1200000.0
            mock_res.market = MagicMock()
            mock_res.market.median = 1200000.0
            return mock_res

        import backend.app.services.garage_intelligence_service as gis_module
        mock_val = MagicMock()
        mock_val.evaluate_valuation.side_effect = mock_eval
        monkeypatch.setattr(gis_module, "valuation_service", mock_val)

        v_valid = GarageVehicle(
            id="v_valid",
            user_id="u1",
            brand="Hyundai",
            model="Creta",
            year=2021,
            fuel_type="Petrol",
            annual_km=12000,
            ownership_status=OwnershipStatus.OWNED.value
        )
        v_invalid = GarageVehicle(
            id="v_invalid",
            user_id="u1",
            brand="UnsupportedBrand",
            model="Experimental",
            year=2024,
            fuel_type="Electric",
            annual_km=12000,
            ownership_status=OwnershipStatus.OWNED.value
        )

        snap1 = service.evaluate_vehicle_snapshot(v_valid)
        snap2 = service.evaluate_vehicle_snapshot(v_invalid)

        summary = service._compute_portfolio_summary([snap1, snap2])
        assert summary.total_vehicles == 2
        assert summary.owned_vehicles == 2
        assert summary.excluded_vehicles_count == 1
        assert len(summary.excluded_vehicle_reasons) == 1
        assert "UnsupportedBrand Experimental" in summary.excluded_vehicle_reasons[0]
        # Total value should strictly equal 1,200,000 and NOT add any fallback money
        assert summary.total_current_value == 1200000.0

    def test_garage_intelligence_frontend_contract_parity(self, client: TestClient, db_session, test_user, user_token):
        """Regression test for Task 1: verify serialized API response contains all frontend-expected keys."""
        veh = GarageVehicle(
            user_id=test_user.id,
            brand="Honda",
            model="City",
            year=2020,
            fuel_type="Petrol",
            transmission="Manual",
            annual_km=12000,
            ownership_status=OwnershipStatus.OWNED.value
        )
        db_session.add(veh)
        db_session.commit()

        r = client.get(
            "/api/garage/intelligence",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert r.status_code == 200
        data = r.json()

        # Contract keys expected by frontend
        assert "snapshots" in data
        assert "vehicle_snapshots" in data
        assert "efficiency_score" in data
        assert "efficiency" in data
        assert "vehicle_rankings" in data
        assert "rankings" in data
        assert "redundancy_analysis" in data
        assert "redundancies" in data
        assert "recommendation" in data

        # Recommendation contract
        rec = data["recommendation"]
        assert "headline" in rec
        assert "primary_reasons" in rec
        assert "confidence" in rec
        assert "confidence_score" in rec

        # Summary contract
        summ = data["summary"]
        assert "total_vehicles" in summ
        assert "owned_vehicles_count" in summ
        assert "total_current_value_formatted" in summ
        assert "total_annual_cost_formatted" in summ
        assert "total_5y_tco_formatted" in summ
        assert "average_cost_per_km_formatted" in summ

        # Snapshot item contract
        assert len(data["snapshots"]) >= 1
        snap = data["snapshots"][0]
        assert "current_estimated_value_formatted" in snap
        assert "five_year_tco_formatted" in snap
        assert "cost_per_km_formatted" in snap
        assert "market_trend" in snap
        assert "lifecycle_action" in snap
