import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.exceptions import DatabaseConnectionError, ModelNotFoundError
from backend.app.core.middleware import rate_limiter
from backend.app.services.comparable_service import ComparableService


@pytest.fixture
def client():
    return TestClient(app)


class TestSecurityAndResilience:

    def test_validation_negative_km_rejected(self, client):
        payload = {
            "brand": "Hyundai",
            "model": "Creta",
            "year": 2021,
            "km_driven": -5000,
            "fuel_type": "Diesel",
            "transmission": "Manual",
            "city": "Pune"
        }
        response = client.post("/api/valuation", json=payload)
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "request_id" in data["error"]

    def test_validation_impossible_year_rejected(self, client):
        payload = {
            "brand": "Hyundai",
            "model": "Creta",
            "year": 1850,
            "km_driven": 20000,
            "fuel_type": "Diesel",
            "transmission": "Manual",
            "city": "Pune"
        }
        response = client.post("/api/valuation", json=payload)
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_validation_future_year_rejected(self, client):
        payload = {
            "brand": "Hyundai",
            "model": "Creta",
            "year": 2035,
            "km_driven": 20000,
            "fuel_type": "Diesel",
            "transmission": "Manual",
            "city": "Pune"
        }
        response = client.post("/api/valuation", json=payload)
        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_validation_negative_price_rejected(self, client):
        payload = {
            "brand": "Hyundai",
            "model": "Creta",
            "year": 2021,
            "km_driven": 20000,
            "fuel_type": "Diesel",
            "transmission": "Manual",
            "city": "Pune",
            "asking_price": -50000
        }
        response = client.post("/api/valuation", json=payload)
        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_validation_invalid_owner_count_rejected(self, client):
        payload = {
            "brand": "Hyundai",
            "model": "Creta",
            "year": 2021,
            "km_driven": 20000,
            "fuel_type": "Diesel",
            "transmission": "Manual",
            "city": "Pune",
            "owner_count": -2
        }
        response = client.post("/api/valuation", json=payload)
        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_rate_limiting_enforcement(self, client):
        rate_limiter.reset()
        # Temporarily configure a low rate limit for testing
        with patch.object(settings, "RATE_LIMIT_PER_MINUTE", 2):
            payload = {
                "brand": "Hyundai",
                "model": "Creta",
                "year": 2021,
                "km_driven": 30000,
                "fuel_type": "Diesel",
                "transmission": "Manual",
                "city": "Pune"
            }
            # First request
            r1 = client.post("/api/valuation", json=payload)
            assert r1.status_code == 200

            # Second request
            r2 = client.post("/api/valuation", json=payload)
            assert r2.status_code == 200

            # Third request within same minute should be rate limited
            r3 = client.post("/api/valuation", json=payload)
            assert r3.status_code == 429
            data = r3.json()
            assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
            assert "Retry-After" in r3.headers
        rate_limiter.reset()

    def test_request_body_size_limit(self, client):
        # Send a payload that exceeds the max body size (e.g., limit to 50 bytes)
        with patch.object(settings, "MAX_REQUEST_BODY_BYTES", 50):
            large_payload = {
                "brand": "Hyundai",
                "model": "Creta Super Long Name That Exceeds The Byte Limit",
                "year": 2021,
                "km_driven": 30000,
                "fuel_type": "Diesel",
                "transmission": "Manual",
                "city": "Pune"
            }
            response = client.post("/api/valuation", json=large_payload)
            assert response.status_code == 413
            data = response.json()
            assert data["error"]["code"] == "REQUEST_TOO_LARGE"

    def test_model_not_found_global_error_handling(self, client):
        from backend.app.services.valuation_service import ValuationService
        val_svc = ValuationService()
        val_svc.predictor.model = None  # simulate model not ready
        with patch("backend.app.api.routes.valuation.valuation_service", val_svc):
            payload = {
                "brand": "Hyundai",
                "model": "Creta",
                "year": 2021,
                "km_driven": 30000,
                "fuel_type": "Diesel",
                "transmission": "Manual",
                "city": "Pune"
            }
            response = client.post("/api/valuation", json=payload)
            assert response.status_code == 503
            data = response.json()
            assert data["error"]["code"] == "MODEL_NOT_FOUND"
            assert "request_id" in data["error"]

    def test_database_connection_error_global_handling(self, client):
        with patch.object(ComparableService, "find_comparables", side_effect=DatabaseConnectionError("PostgreSQL connection refused")):
            payload = {
                "brand": "Hyundai",
                "model": "Creta",
                "year": 2021,
                "km_driven": 30000,
                "fuel_type": "Diesel",
                "transmission": "Manual",
                "city": "Pune"
            }
            response = client.post("/api/valuation", json=payload)
            assert response.status_code == 503
            data = response.json()
            assert data["error"]["code"] == "DATABASE_UNAVAILABLE"

    def test_not_found_endpoint_handling(self, client):
        response = client.get("/api/nonexistent_route_404")
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "NOT_FOUND"

    def test_cors_headers_handling(self, client):
        response = client.options("/api/health", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET"
        })
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
