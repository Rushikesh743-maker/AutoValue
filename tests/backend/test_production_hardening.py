import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from backend.app.main import app
from backend.app.services.model_registry import model_registry, ModelRegistry
from backend.app.core.exceptions import ModelIntegrityError, ModelNotFoundError


@pytest.fixture
def client():
    return TestClient(app)


class TestProductionHardening:

    def test_correlation_id_generation_and_propagation(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        request_id = response.headers.get("x-request-id")
        assert request_id is not None
        assert len(request_id) > 5

    def test_custom_correlation_id_preserved(self, client):
        custom_id = "custom-test-trace-id-12345"
        response = client.get("/api/health", headers={"X-Request-ID": custom_id})
        assert response.status_code == 200
        assert response.headers.get("x-request-id") == custom_id

    def test_readiness_probe_healthy_state(self, client):
        response = client.get("/api/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "checks" in data
        assert data["checks"]["database"] is True
        assert data["checks"]["active_model_artifacts"] is True
        assert data["checks"]["processed_dataset"] is True

    def test_readiness_probe_db_failure_state(self, client):
        with patch("backend.app.api.routes.health.engine.connect") as mock_connect:
            mock_connect.side_effect = Exception("DB Connection Refused")

            response = client.get("/api/ready")
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "not_ready"
            assert data["checks"]["database"] is False

    def test_model_registry_v001_and_v002_integrity(self):
        # Test v002 (active)
        m2, p2, meta2 = model_registry.load_model_bundle("v002")
        assert m2 is not None
        assert p2 is not None
        assert meta2.get("model_version") == "v002"

        # Test v001
        m1, p1, meta1 = model_registry.load_model_bundle("v001")
        assert m1 is not None
        assert p1 is not None
        assert meta1.get("model_version") == "v001"

    def test_model_registry_missing_version_raises(self):
        with pytest.raises(ModelNotFoundError):
            model_registry.load_model_bundle("v999_nonexistent")

    def test_model_registry_corrupted_checksum_raises(self):
        reg = ModelRegistry(models_dir="models")
        with patch("backend.app.services.model_registry.compute_file_sha256", return_value="0000000000000000000000000000000000000000000000000000000000000000"):
            with pytest.raises(ModelIntegrityError):
                reg.verify_artifact_integrity("v002")

    def test_data_quality_endpoint(self, client):
        response = client.get("/api/data-quality")
        assert response.status_code == 200
        data = response.json()
        assert data["dataset_version"] == "v0.3"
        assert data["processed_record_count"] == 999
        assert data["ml_readiness"]["is_ready"] is True
        assert "car_age" in data["features_engineered"]
        assert isinstance(data["missingness_summary"], dict)
        assert isinstance(data["source_distribution"], dict)

    def test_drift_monitoring_endpoint(self, client):
        response = client.get("/api/models/drift")
        assert response.status_code == 200
        data = response.json()
        assert data["active_model_version"] == "v002"
        assert data["status"] in ["healthy", "warning", "insufficient_data"]
        assert data["baseline_sample_size"] > 0
        assert data["current_sample_size"] > 0
        assert "feature_audits" in data
        assert "monitored_features" in data

    def test_metrics_prometheus_endpoint(self, client):
        # Trigger a valuation to increment counters
        client.post("/api/valuation", json={
            "brand": "Hyundai",
            "model": "Creta",
            "year": 2021,
            "km_driven": 35000,
            "fuel_type": "Diesel",
            "transmission": "Manual",
            "city": "Pune"
        })

        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        body = response.text
        assert "autovalue_http_requests_total" in body
        assert "autovalue_valuation_requests_total" in body
        assert "autovalue_active_model_info" in body

    def test_models_registry_endpoint(self, client):
        response = client.get("/api/models")
        assert response.status_code == 200
        data = response.json()
        assert data["active_model_version"] == "v002"
        assert len(data["available_versions"]) >= 2
        assert len(data["registry"]) >= 2
        
        # Verify metadata structure in registry
        v002 = next((m for m in data["registry"] if m["model_version"] == "v002"), None)
        assert v002 is not None
        assert v002["selected_model"] == "XGBoost Regressor"
        assert v002["has_integrity_record"] is True
