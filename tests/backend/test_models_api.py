"""
Integration tests for GET /api/models endpoint and version registry.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


class TestModelsAPI:
    def test_get_models_endpoint(self):
        response = client.get("/api/models")
        assert response.status_code == 200
        data = response.json()

        assert "active_model_version" in data
        assert data["active_model_version"] in ["v001", "v002"]
        assert "dataset_version" in data
        assert "metrics" in data
        assert "available_versions" in data
        assert len(data["available_versions"]) > 0
