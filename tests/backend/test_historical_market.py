"""
Integration and unit tests for HistoricalMarketService and GET /api/market/history.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.historical_market_service import HistoricalMarketService

client = TestClient(app)


class TestHistoricalMarket:
    def test_service_market_history_aggregation(self):
        service = HistoricalMarketService()
        res = service.get_market_history(brand="Maruti", model="Swift", time_period="all")

        assert res["status"] in ["AVAILABLE", "INSUFFICIENT_DATA"]
        if res["status"] == "AVAILABLE":
            assert len(res["history"]) > 0
            first = res["history"][0]
            assert "period" in first
            assert "median_price" in first
            assert "listing_count" in first
            assert res["disclaimer"] is not None

    def test_get_market_history_endpoint(self):
        response = client.get("/api/market/history?brand=Hyundai&model=Creta&time_period=all")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "history" in data
