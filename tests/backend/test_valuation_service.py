"""
Unit tests for ValuationService coordinating inference, uncertainty intervals, comparables, and SHAP explanations.
"""
import pytest
import pandas as pd
from backend.app.schemas.valuation import ValuationRequestSchema
from backend.app.services.valuation_service import ValuationService


class TestValuationService:
    def test_evaluate_valuation_full_pipeline(self):
        service = ValuationService(model_version="v002")
        assert service.is_model_ready

        req = ValuationRequestSchema(
            brand="Hyundai",
            model="Creta",
            variant="1.5 CRDi SX",
            year=2021,
            fuel_type="Diesel",
            transmission="Manual",
            km_driven=38000,
            city="Pune",
            asking_price=1350000.0
        )

        response = service.evaluate_valuation(req)

        assert response.model_version == "v002"
        assert response.valuation.estimated_value > 10000.0
        assert "INR" in response.valuation.estimated_value_formatted
        assert response.valuation.model_interval is not None
        assert response.valuation.model_interval.interval_low < response.valuation.model_interval.interval_high
        assert response.market.comparable_count >= 1
        assert len(response.comparables) >= 1
        assert len(response.source_analysis) >= 1
        assert response.request_id is not None
        assert response.latency_ms is not None

        # Test market position calculation
        assert response.market_position is not None
        assert response.market_position.asking_price == 1350000.0
        assert response.market_position.position in [
            "Below observed comparable range",
            "Within observed comparable range",
            "Above observed comparable range"
        ]

    def test_human_readable_explanation_generation(self):
        service = ValuationService()
        text_age = service.generate_human_explanation("year", -120000.0, "decreases_price")
        assert "depreciation" in text_age or "year" in text_age.lower()
        assert "120,000" in text_age
