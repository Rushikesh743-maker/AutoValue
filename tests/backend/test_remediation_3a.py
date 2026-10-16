"""
Regression test suite for Remediation 3A.
Verifies:
1. Single-pass pipeline execution in Garage vehicle snapshot extraction (no duplicate calls).
2. Parity between standalone lifecycle evaluation and lifecycle evaluation with precomputed responses.
3. SHAP bypass behavior when include_shap=False.
4. Transformed feature name resolution and non-generic human-readable explanations.
5. Single invocation of redundancy detection per garage intelligence synthesis.
"""
import pytest
from unittest.mock import MagicMock, patch

from backend.app.schemas.valuation import ValuationRequestSchema, ValuationResponse
from backend.app.schemas.garage import (
    OwnershipStatus,
    GarageVehicleCreate,
    GarageVehicleResponse,
    GarageVehicleSnapshot,
    GarageSummary
)
from backend.app.schemas.lifecycle import LifecycleDecisionRequest, DecisionMode
from backend.app.models.garage import GarageVehicle
from backend.app.services.valuation_service import ValuationService, valuation_service
from backend.app.services.garage_intelligence_service import GarageIntelligenceService, garage_intelligence_service
from backend.app.services.lifecycle_service import LifecycleService, lifecycle_service
from backend.app.services.market_forecast_service import market_forecast_service
from ml.evaluation.shap_explainer import AutoValueSHAPExplainer


class TestRemediation3APerformanceAndSHAP:
    """Test suite for performance optimizations and SHAP explanation fixes."""

    def test_include_shap_false_bypasses_explainer(self):
        """Task 2: Assert that include_shap=False does not execute explain_prediction and returns empty explanation."""
        req = ValuationRequestSchema(
            brand="Hyundai",
            model="Creta",
            variant="SX",
            year=2021,
            fuel_type="Diesel",
            transmission="Manual",
            km_driven=35000,
            city="Bengaluru"
        )
        
        with patch.object(valuation_service.shap_explainer, "explain_prediction", wraps=valuation_service.shap_explainer.explain_prediction) as mock_explain:
            resp = valuation_service.evaluate_valuation(req, include_shap=False)
            assert mock_explain.call_count == 0
            assert resp.explanation == []
            assert resp.valuation.estimated_value > 10000.0

    def test_include_shap_true_populates_meaningful_feature_names(self):
        """Task 3: Assert that include_shap=True returns real transformed feature names and no 'Feature_0' placeholders."""
        req = ValuationRequestSchema(
            brand="Hyundai",
            model="Creta",
            variant="SX",
            year=2021,
            fuel_type="Diesel",
            transmission="Manual",
            km_driven=35000,
            city="Bengaluru"
        )

        resp = valuation_service.evaluate_valuation(req, include_shap=True)
        assert len(resp.explanation) > 0

        # Verify that feature names are meaningful transformed names (e.g. year, km_driven, brand_Hyundai)
        for item in resp.explanation:
            assert not item.feature.startswith("Feature_"), f"Exposed generic placeholder: {item.feature}"
            assert not item.human_readable_text.startswith("Feature 'Feature_"), f"Generic text: {item.human_readable_text}"

    def test_shap_explainer_fallback_and_robustness(self):
        """Task 3: Assert that AutoValueSHAPExplainer can safely resolve feature names and handles unexpected names gracefully."""
        explainer = AutoValueSHAPExplainer(
            model=valuation_service.predictor.model,
            preprocessor=valuation_service.predictor.preprocessor
        )
        assert explainer.feature_names is not None
        assert len(explainer.feature_names) == 341
        assert "year" in explainer.feature_names
        assert "km_driven" in explainer.feature_names

        # Test explanation generator fallback for unknown features
        text_custom = valuation_service.generate_human_explanation("custom_addon_score", 15000.0, "increases_price")
        assert "custom_addon_score" in text_custom
        assert "15,000" in text_custom

    def test_lifecycle_precomputed_parity(self):
        """Task 1: Assert parity between standalone lifecycle execution and execution with precomputed pipeline objects."""
        lc_req = LifecycleDecisionRequest(
            mode=DecisionMode.OWNER,
            brand="Hyundai",
            model="Creta",
            variant="SX",
            year=2021,
            fuel_type="Diesel",
            transmission="Manual",
            km_driven=35000,
            city="Bengaluru",
            current_market_value=1350000.0,
            annual_km=12000,
            include_alternatives=False
        )

        # 1. Standalone execution
        standalone_resp = lifecycle_service.evaluate_lifecycle(lc_req)

        # 2. Compute components individually
        val_req = ValuationRequestSchema(
            brand="Hyundai",
            model="Creta",
            variant="SX",
            year=2021,
            fuel_type="Diesel",
            transmission="Manual",
            km_driven=35000,
            city="Bengaluru"
        )
        val_res = valuation_service.evaluate_valuation(val_req, include_shap=False)
        from backend.app.schemas.forecast import ForecastRequest
        fc_req = ForecastRequest(
            brand="Hyundai",
            model="Creta",
            variant="SX",
            year=2021,
            fuel_type="Diesel",
            transmission="Manual",
            km_driven=35000,
            city="Bengaluru",
            asking_price=1350000.0,
            horizon_days=365
        )
        fc_res = market_forecast_service.forecast_vehicle_market(fc_req)
        risk_res = lifecycle_service.risk_service.evaluate_risk(val_req, val_res)
        from backend.app.schemas.tco import TCOAssumptions
        tco_assump = TCOAssumptions(
            annual_km=12000,
            ownership_years=5,
            purchase_price_mode="FAIR_VALUE",
            custom_purchase_price=1350000.0
        )
        tco_res = lifecycle_service.tco_service.calculate_tco(val_req, val_res, tco_assump)

        # 3. Execution with precomputed objects
        precomputed_resp = lifecycle_service.evaluate_lifecycle(
            lc_req,
            valuation_response=val_res,
            forecast_response=fc_res,
            risk_response=risk_res,
            tco_response=tco_res
        )

        assert standalone_resp.recommended_action == precomputed_resp.recommended_action
        assert standalone_resp.confidence == precomputed_resp.confidence
        assert standalone_resp.decision_score.overall_score == precomputed_resp.decision_score.overall_score

    def test_evaluate_vehicle_snapshot_single_pass_call_counts(self):
        """Task 1: Assert that evaluate_vehicle_snapshot calls valuation, forecast, risk, and TCO exactly ONCE."""
        veh = GarageVehicle(
            id="test-v1",
            user_id="user-1",
            brand="Hyundai",
            model="Creta",
            variant="SX",
            year=2021,
            fuel_type="Diesel",
            transmission="Manual",
            city="Bengaluru",
            current_odometer=35000,
            annual_km=12000,
            purchase_price=1350000.0,
            ownership_status=OwnershipStatus.OWNED.value
        )

        with patch.object(valuation_service, "evaluate_valuation", wraps=valuation_service.evaluate_valuation) as mock_val, \
             patch.object(market_forecast_service, "forecast_vehicle_market", wraps=market_forecast_service.forecast_vehicle_market) as mock_fc, \
             patch.object(garage_intelligence_service.risk_service, "evaluate_risk", wraps=garage_intelligence_service.risk_service.evaluate_risk) as mock_risk, \
             patch.object(garage_intelligence_service.tco_service, "calculate_tco", wraps=garage_intelligence_service.tco_service.calculate_tco) as mock_tco:

            snapshot = garage_intelligence_service.evaluate_vehicle_snapshot(veh)

            assert mock_val.call_count == 1, f"Expected 1 valuation call, got {mock_val.call_count}"
            assert mock_fc.call_count == 1, f"Expected 1 forecast call, got {mock_fc.call_count}"
            assert mock_risk.call_count == 1, f"Expected 1 risk call, got {mock_risk.call_count}"
            assert mock_tco.call_count == 1, f"Expected 1 TCO call, got {mock_tco.call_count}"

            assert snapshot.current_estimated_value is not None
            assert snapshot.five_year_tco is not None
            assert snapshot.lifecycle_action is not None

    def test_garage_intelligence_redundancy_single_invocation(self):
        """Task 4: Assert that _detect_vehicle_redundancies is called exactly ONCE per evaluate_garage_intelligence."""
        mock_db = MagicMock()
        veh1 = GarageVehicle(
            id="test-v1",
            user_id="user-1",
            brand="Hyundai",
            model="Creta",
            year=2021,
            fuel_type="Diesel",
            transmission="Manual",
            city="Bengaluru",
            current_odometer=35000,
            annual_km=12000,
            purchase_price=1350000.0,
            ownership_status=OwnershipStatus.OWNED.value
        )
        veh2 = GarageVehicle(
            id="test-v2",
            user_id="user-1",
            brand="Honda",
            model="City",
            year=2020,
            fuel_type="Petrol",
            transmission="Manual",
            city="Bengaluru",
            current_odometer=30000,
            annual_km=10000,
            purchase_price=950000.0,
            ownership_status=OwnershipStatus.OWNED.value
        )

        with patch.object(garage_intelligence_service, "list_vehicles", return_value=[veh1, veh2]), \
             patch.object(garage_intelligence_service, "_detect_vehicle_redundancies", wraps=garage_intelligence_service._detect_vehicle_redundancies) as mock_red, \
             patch.object(garage_intelligence_service, "_discover_replacement_opportunities", return_value=[]):

            resp = garage_intelligence_service.evaluate_garage_intelligence(mock_db, "user-1")

            assert mock_red.call_count == 1, f"Expected exactly 1 redundancy detection call, got {mock_red.call_count}"
            assert resp.summary.total_vehicles == 2
            assert resp.efficiency.overall_score > 0.0
