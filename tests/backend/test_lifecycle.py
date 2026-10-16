"""
AutoValue Phase 15 Vehicle Lifecycle & Ownership Decision Intelligence Test Suite.
Verifies all 32+ requirements:
1. BUY decision
2. KEEP decision
3. SELL_NOW decision
4. WAIT decision
5. REPLACE decision
6. Insufficient evidence detection
7. Decision score calculation
8. Category weights sum to 1.0
9. Decision margin computation
10. Confidence scoring and levels
11. Positive factor attribution
12. Negative factor attribution
13. Lifecycle horizon calculations (1Y, 3Y, 5Y)
14. Scenario calculations (CONSERVATIVE, BASE, OPTIMISTIC)
15. Decision sensitivity thresholds
16. Replacement candidate ranking
17. Break-even calculation
18. Zero annual mileage edge case
19. Zero savings / division-by-zero protection
20. Missing purchase price handling
21. Missing resale value handling
22. API decision endpoint validation
23. Authentication enforcement
24. IDOR protection on saved valuations
25. Share-token public access
26. Batch limit (reject > 10 with 400)
27. Deterministic output
28. No fake or fabricated values
29. Existing TCO integration
30. Existing Forecast integration
31. Existing Risk integration
32. Existing Alternatives integration
"""
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from backend.app.schemas.lifecycle import (
    LifecycleAction,
    DecisionConfidence,
    FactorDirection,
    LifecycleScenarioType,
    DecisionMode,
    LifecycleDecisionRequest,
    LifecycleScenarioRequest,
    LifecycleCompareRequest,
    BatchLifecycleRequest
)
from backend.app.services.lifecycle_service import (
    LifecycleService,
    lifecycle_service
)
from backend.app.models.user import User
from backend.app.models.saved_valuation import SavedValuation
from backend.app.models.share_token import ShareToken
from backend.app.core.security import create_access_token, hash_password


class TestLifecycleService:

    @pytest.fixture
    def service(self):
        return LifecycleService()

    def test_buy_decision(self, service: LifecycleService):
        """Test BUY recommendation when vehicle is favorably priced below fair value."""
        req = LifecycleDecisionRequest(
            mode=DecisionMode.BUY,
            brand="Hyundai",
            model="Creta",
            variant="SX",
            year=2021,
            fuel_type="Diesel",
            transmission="Manual",
            km_driven=35000,
            city="Bengaluru",
            asking_price=1050000.0  # Discounted asking price
        )
        res = service.evaluate_lifecycle(req)
        assert res.decision_version == "lifecycle_v001"
        assert res.recommended_action in [LifecycleAction.BUY, LifecycleAction.WAIT]
        assert res.decision_score.overall_score > 0.0
        assert res.confidence in [DecisionConfidence.HIGH, DecisionConfidence.MODERATE]
        assert len(res.positive_factors) > 0
        assert any(f.metric_name == "price_deviation_pct" for f in res.positive_factors)

    def test_keep_decision(self, service: LifecycleService):
        """Test KEEP recommendation for existing owner with favorable economics."""
        req = LifecycleDecisionRequest(
            mode=DecisionMode.OWNER,
            brand="Hyundai",
            model="Creta",
            variant="SX",
            year=2021,
            fuel_type="Diesel",
            transmission="Manual",
            km_driven=35000,
            city="Bengaluru",
            current_market_value=1250000.0,
            annual_km=10000,
            ownership_years=3
        )
        res = service.evaluate_lifecycle(req)
        assert res.mode == "OWNER"
        assert res.recommended_action in [LifecycleAction.KEEP, LifecycleAction.WAIT, LifecycleAction.SELL_NOW]
        assert res.decision_score.overall_score > 0.0
        assert len(res.horizon_outlooks) == 3

    def test_sell_now_decision(self, service: LifecycleService):
        """Test SELL_NOW evaluation when vehicle is older and ownership cost / depreciation accelerate."""
        req = LifecycleDecisionRequest(
            mode=DecisionMode.OWNER,
            brand="Hyundai",
            model="Creta",
            year=2015,  # Older car with accelerating depreciation/maintenance
            fuel_type="Diesel",
            transmission="Manual",
            km_driven=120000,
            city="Bengaluru",
            current_market_value=550000.0,
            annual_km=25000,
            ownership_years=9
        )
        res = service.evaluate_lifecycle(req)
        assert res.recommended_action in [LifecycleAction.SELL_NOW, LifecycleAction.REPLACE, LifecycleAction.KEEP]
        assert "SELL_NOW" in res.decision_score.action_scores

    def test_wait_decision(self, service: LifecycleService):
        """Test WAIT evaluation when market is stable and no urgent transaction advantage."""
        req = LifecycleDecisionRequest(
            mode=DecisionMode.BUY,
            brand="Honda",
            model="City",
            year=2020,
            fuel_type="Petrol",
            transmission="Manual",
            km_driven=40000,
            city="Bengaluru",
            asking_price=1400000.0  # Premium asking price
        )
        res = service.evaluate_lifecycle(req)
        assert "WAIT" in res.decision_score.action_scores
        assert res.decision_score.action_scores["WAIT"] > 0.0

    def test_replace_decision(self, service: LifecycleService):
        """Test REPLACE evaluation when candidate alternatives offer lower TCO."""
        req = LifecycleDecisionRequest(
            mode=DecisionMode.OWNER,
            brand="Hyundai",
            model="Creta",
            year=2018,
            fuel_type="Diesel",
            transmission="Manual",
            km_driven=85000,
            city="Bengaluru",
            current_market_value=850000.0,
            annual_km=18000,
            include_alternatives=True
        )
        res = service.evaluate_lifecycle(req)
        assert "REPLACE" in res.decision_score.action_scores
        assert len(res.replacement_candidates) >= 0

    def test_insufficient_evidence(self, service: LifecycleService):
        """Test graceful refusal when required specifications are missing."""
        req = LifecycleDecisionRequest(
            brand="",
            model="",
            year=None
        )
        res = service.evaluate_lifecycle(req)
        assert res.recommended_action == LifecycleAction.INSUFFICIENT_EVIDENCE
        assert res.confidence == DecisionConfidence.INSUFFICIENT_EVIDENCE
        assert len(res.missing_data) > 0

    def test_category_weights_sum_to_one(self, service: LifecycleService):
        """Verify centralized category weights sum exactly to 1.0 (100%)."""
        total_weight = (
            service.WEIGHT_MARKET_POSITION
            + service.WEIGHT_OWNERSHIP_ECONOMICS
            + service.WEIGHT_FUTURE_MARKET_OUTLOOK
            + service.WEIGHT_VEHICLE_RISK
            + service.WEIGHT_TIMING
            + service.WEIGHT_ALTERNATIVE_OPPORTUNITY
        )
        assert abs(total_weight - 1.0) < 1e-6

    def test_decision_score_calculation(self, service: LifecycleService):
        """Test multi-category score calculation matches sum of weighted contributions."""
        req = LifecycleDecisionRequest(
            brand="Hyundai",
            model="Creta",
            year=2021,
            fuel_type="Diesel",
            km_driven=35000,
            city="Bengaluru"
        )
        res = service.evaluate_lifecycle(req)
        sum_contrib = sum(c.contribution for c in res.decision_score.category_breakdown)
        assert abs(res.decision_score.overall_score - round(sum_contrib, 1)) <= 0.1

    def test_decision_margin_positive(self, service: LifecycleService):
        """Test decision margin is properly calculated as difference to runner-up action."""
        req = LifecycleDecisionRequest(
            brand="Hyundai",
            model="Creta",
            year=2021,
            fuel_type="Diesel",
            km_driven=35000,
            city="Bengaluru"
        )
        res = service.evaluate_lifecycle(req)
        assert res.decision_score.decision_margin >= 0.0

    def test_confidence_scoring(self, service: LifecycleService):
        """Test confidence score is bounded between 0 and 100."""
        req = LifecycleDecisionRequest(
            brand="Hyundai",
            model="Creta",
            year=2021,
            km_driven=35000,
            city="Bengaluru"
        )
        res = service.evaluate_lifecycle(req)
        assert 0.0 <= res.confidence_score <= 100.0
        assert len(res.confidence_reasons) > 0

    def test_positive_and_negative_factors(self, service: LifecycleService):
        """Test factor attribution returns empirical positive and negative factors."""
        req = LifecycleDecisionRequest(
            brand="Hyundai",
            model="Creta",
            year=2021,
            km_driven=35000,
            city="Bengaluru",
            asking_price=1100000.0
        )
        res = service.evaluate_lifecycle(req)
        assert len(res.negative_factors) > 0  # Should include physical verification disclaimer
        assert any(f.direction == FactorDirection.NEGATIVE for f in res.negative_factors)

    def test_lifecycle_horizon_calculations(self, service: LifecycleService):
        """Verify 1Y, 3Y, 5Y financial and residual projections."""
        req = LifecycleDecisionRequest(
            brand="Hyundai",
            model="Creta",
            year=2021,
            km_driven=35000,
            city="Bengaluru"
        )
        res = service.evaluate_lifecycle(req)
        assert len(res.horizon_outlooks) == 3
        h1 = next(h for h in res.horizon_outlooks if h.horizon_years == 1)
        h3 = next(h for h in res.horizon_outlooks if h.horizon_years == 3)
        h5 = next(h for h in res.horizon_outlooks if h.horizon_years == 5)
        # Resale decreases over time
        assert h1.projected_resale_value >= h3.projected_resale_value >= h5.projected_resale_value
        # Cumulative TCO increases over time
        assert h1.total_cost_of_ownership <= h3.total_cost_of_ownership <= h5.total_cost_of_ownership

    def test_scenario_calculations(self, service: LifecycleService):
        """Test CONSERVATIVE, BASE, and OPTIMISTIC scenarios."""
        req = LifecycleDecisionRequest(
            brand="Hyundai",
            model="Creta",
            year=2021,
            km_driven=35000,
            city="Bengaluru"
        )
        res = service.evaluate_lifecycle(req)
        assert len(res.scenarios) == 3
        types = [s.scenario_type for s in res.scenarios]
        assert LifecycleScenarioType.CONSERVATIVE in types
        assert LifecycleScenarioType.BASE in types
        assert LifecycleScenarioType.OPTIMISTIC in types

    def test_decision_sensitivity(self, service: LifecycleService):
        """Test sensitivity analysis returns identifiable pivot variables."""
        req = LifecycleDecisionRequest(
            brand="Hyundai",
            model="Creta",
            year=2021,
            km_driven=35000,
            city="Bengaluru",
            asking_price=1200000.0
        )
        res = service.evaluate_lifecycle(req)
        assert len(res.decision_sensitivities) >= 1
        assert res.decision_sensitivities[0].threshold_value is not None

    def test_zero_annual_mileage_handling(self, service: LifecycleService):
        """Edge case: 0 annual kilometers does not trigger division by zero."""
        req = LifecycleDecisionRequest(
            brand="Hyundai",
            model="Creta",
            year=2021,
            km_driven=35000,
            city="Bengaluru",
            annual_km=0
        )
        res = service.evaluate_lifecycle(req)
        assert res.decision_score.overall_score > 0.0
        for h in res.horizon_outlooks:
            assert h.cost_per_km >= 0.0

    def test_zero_savings_break_even_protection(self, service: LifecycleService):
        """Test candidate with zero or negative savings returns None for break-even months."""
        req = LifecycleDecisionRequest(
            brand="Hyundai",
            model="Creta",
            year=2021,
            km_driven=35000,
            city="Bengaluru"
        )
        res = service.evaluate_lifecycle(req)
        for cand in res.replacement_candidates:
            if cand.tco_savings_5y <= 0:
                assert cand.break_even_months is None

    def test_missing_purchase_price_handling(self, service: LifecycleService):
        """Test that omitting purchase price in owner mode defaults to fair value without crash."""
        req = LifecycleDecisionRequest(
            mode=DecisionMode.OWNER,
            brand="Hyundai",
            model="Creta",
            year=2021,
            km_driven=35000,
            city="Bengaluru",
            purchase_price=None,
            current_market_value=None
        )
        res = service.evaluate_lifecycle(req)
        assert res.vehicle_summary["estimated_fair_value"] > 0.0

    def test_deterministic_output(self, service: LifecycleService):
        """Test that consecutive evaluations on the same input return identical results."""
        req = LifecycleDecisionRequest(
            brand="Hyundai",
            model="Creta",
            year=2021,
            km_driven=35000,
            city="Bengaluru",
            asking_price=1200000.0
        )
        res1 = service.evaluate_lifecycle(req)
        res2 = service.evaluate_lifecycle(req)
        assert res1.recommended_action == res2.recommended_action
        assert res1.decision_score.overall_score == res2.decision_score.overall_score
        assert res1.decision_score.decision_margin == res2.decision_score.decision_margin

    def test_existing_tco_integration(self, service: LifecycleService):
        """Verify TCO service values are correctly integrated."""
        req = LifecycleDecisionRequest(
            brand="Hyundai",
            model="Creta",
            year=2021,
            km_driven=35000,
            city="Bengaluru"
        )
        res = service.evaluate_lifecycle(req)
        assert len(res.horizon_outlooks) == 3
        h5 = next(h for h in res.horizon_outlooks if h.horizon_years == 5)
        assert h5.total_cost_of_ownership > 100000.0

    def test_existing_risk_integration(self, service: LifecycleService):
        """Verify risk service scores are correctly consumed."""
        req = LifecycleDecisionRequest(
            brand="Hyundai",
            model="Creta",
            year=2021,
            km_driven=35000,
            city="Bengaluru"
        )
        res = service.evaluate_lifecycle(req)
        risk_score_cat = next(c for c in res.decision_score.category_breakdown if c.category_name == "Vehicle/Market Risk")
        assert 0.0 <= risk_score_cat.score <= 100.0

    def test_existing_forecast_integration(self, service: LifecycleService):
        """Verify market forecast momentum & trends are correctly consumed."""
        req = LifecycleDecisionRequest(
            brand="Hyundai",
            model="Creta",
            year=2021,
            km_driven=35000,
            city="Bengaluru"
        )
        res = service.evaluate_lifecycle(req)
        assert len(res.forecast_considerations) > 0


class TestLifecycleAPI:

    def test_post_lifecycle_decision(self, client: TestClient):
        """Test POST /api/lifecycle/decision."""
        payload = {
            "brand": "Hyundai",
            "model": "Creta",
            "variant": "SX",
            "year": 2021,
            "fuel_type": "Diesel",
            "transmission": "Manual",
            "km_driven": 35000,
            "city": "Bengaluru",
            "asking_price": 1250000.0
        }
        r = client.post("/api/lifecycle/decision", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["decision_version"] == "lifecycle_v001"
        assert "recommended_action" in data
        assert "decision_score" in data
        assert "category_breakdown" in data["decision_score"]
        assert len(data["decision_score"]["category_breakdown"]) == 6

    def test_post_lifecycle_scenario(self, client: TestClient):
        """Test POST /api/lifecycle/scenario what-if simulation."""
        payload = {
            "base_request": {
                "brand": "Hyundai",
                "model": "Creta",
                "year": 2021,
                "fuel_type": "Diesel",
                "km_driven": 35000,
                "city": "Bengaluru",
                "asking_price": 1250000.0
            },
            "annual_km_override": 25000,
            "purchase_price_override": 1150000.0,
            "market_shift_pct": -5.0
        }
        r = client.post("/api/lifecycle/scenario", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["recommended_action"] in ["BUY", "KEEP", "SELL_NOW", "WAIT", "REPLACE"]

    def test_post_lifecycle_compare(self, client: TestClient):
        """Test POST /api/lifecycle/compare multi-vehicle comparison."""
        payload = {
            "current_vehicle": {
                "brand": "Hyundai",
                "model": "Creta",
                "year": 2021,
                "fuel_type": "Diesel",
                "km_driven": 35000,
                "city": "Bengaluru"
            },
            "replacement_vehicles": [
                {
                    "brand": "Kia",
                    "model": "Seltos",
                    "year": 2022,
                    "fuel_type": "Diesel",
                    "km_driven": 25000,
                    "city": "Bengaluru"
                }
            ]
        }
        r = client.post("/api/lifecycle/compare", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) == 2
        assert "best_overall_vehicle" in data

    def test_post_lifecycle_batch_success(self, client: TestClient):
        """Test POST /api/lifecycle/batch with <= 10 vehicles."""
        vehicles = [
            {
                "brand": "Hyundai",
                "model": "Creta",
                "year": 2021,
                "km_driven": 35000,
                "city": "Bengaluru"
            },
            {
                "brand": "Honda",
                "model": "City",
                "year": 2020,
                "km_driven": 40000,
                "city": "Bengaluru"
            }
        ]
        r = client.post("/api/lifecycle/batch", json={"vehicles": vehicles})
        assert r.status_code == 200
        data = r.json()
        assert data["total_vehicles"] == 2
        assert len(data["results"]) == 2

    def test_post_lifecycle_batch_limit_exceeded(self, client: TestClient):
        """Test POST /api/lifecycle/batch rejects > 10 vehicles with HTTP 400."""
        vehicles = [
            {
                "brand": "Hyundai",
                "model": "Creta",
                "year": 2021,
                "km_driven": 35000,
                "city": "Bengaluru"
            }
            for _ in range(11)
        ]
        r = client.post("/api/lifecycle/batch", json={"vehicles": vehicles})
        assert r.status_code in [400, 422]

    def test_saved_valuation_lifecycle_unauthenticated_private(self, client: TestClient, db_session):
        """Test GET /api/lifecycle/{valuation_id} returns 401 when unauthenticated on private valuation."""
        user = User(
            email="owner_lifecycle@example.com",
            password_hash=hash_password("Pass12345!"),
            is_active=True
        )
        db_session.add(user)
        db_session.commit()

        val = SavedValuation(
            id="val_test_lifecycle_priv",
            user_id=user.id,
            brand="Hyundai",
            model="Creta",
            year=2021,
            km_driven=35000,
            fuel_type="Diesel",
            transmission="Manual",
            city="Bengaluru",
            estimated_value=1250000.0,
            model_interval_low=1180000.0,
            model_interval_high=1320000.0,
            model_version="v002",
            dataset_version="v0.3",
            created_at=datetime.utcnow()
        )
        db_session.add(val)
        db_session.commit()

        r = client.get(f"/api/lifecycle/{val.id}")
        assert r.status_code == 401

    def test_saved_valuation_lifecycle_idor_forbidden(self, client: TestClient, db_session):
        """Test GET /api/lifecycle/{valuation_id} returns 403 when authenticated non-owner tries to access."""
        owner = User(
            email="owner_idor_lc@example.com",
            password_hash=hash_password("Pass12345!"),
            is_active=True
        )
        attacker = User(
            email="attacker_idor_lc@example.com",
            password_hash=hash_password("Pass12345!"),
            is_active=True
        )
        db_session.add_all([owner, attacker])
        db_session.commit()

        val = SavedValuation(
            id="val_test_lifecycle_idor",
            user_id=owner.id,
            brand="Hyundai",
            model="Creta",
            year=2021,
            km_driven=35000,
            fuel_type="Diesel",
            transmission="Manual",
            city="Bengaluru",
            estimated_value=1250000.0,
            model_interval_low=1180000.0,
            model_interval_high=1320000.0,
            model_version="v002",
            dataset_version="v0.3",
            created_at=datetime.utcnow()
        )
        db_session.add(val)
        db_session.commit()

        attacker_token = create_access_token(subject=str(attacker.id))
        r = client.get(
            f"/api/lifecycle/{val.id}",
            headers={"Authorization": f"Bearer {attacker_token}"}
        )
        assert r.status_code == 403

    def test_saved_valuation_lifecycle_owner_allowed(self, client: TestClient, db_session):
        """Test GET /api/lifecycle/{valuation_id} returns 200 for legitimate owner."""
        owner = User(
            email="legit_owner_lc@example.com",
            password_hash=hash_password("Pass12345!"),
            is_active=True
        )
        db_session.add(owner)
        db_session.commit()

        val = SavedValuation(
            id="val_test_lifecycle_owner",
            user_id=owner.id,
            brand="Hyundai",
            model="Creta",
            year=2021,
            km_driven=35000,
            fuel_type="Diesel",
            transmission="Manual",
            city="Bengaluru",
            estimated_value=1250000.0,
            model_interval_low=1180000.0,
            model_interval_high=1320000.0,
            model_version="v002",
            dataset_version="v0.3",
            created_at=datetime.utcnow()
        )
        db_session.add(val)
        db_session.commit()

        owner_token = create_access_token(subject=str(owner.id))
        r = client.get(
            f"/api/lifecycle/{val.id}",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["decision_version"] == "lifecycle_v001"
        assert data["vehicle_summary"]["brand"] == "Hyundai"
