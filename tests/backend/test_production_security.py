"""
AutoValue Production Security & Resilience Regression Test Suite (Phase 9).

Covers all Phase 9 security audit requirements:
- Invalid JWT returns 401
- Expired JWT returns 401
- Inactive account cannot authenticate (403 on login, 401 on bearer)
- Unauthorized valuation history access returns 401
- IDOR attempts across valuations and bookmarks prevented
- Oversized requests rejected (413 Payload Too Large)
- Rate-limit enforcement (429 Rate Limit Exceeded)
- Invalid model version rejected with structured 503
- Invalid model checksum triggers integrity failure
- Unsafe CORS wildcard rejected in production mode
- Invalid input payloads return structured 422 errors
- Missing required production configuration fails fast
- Sensitive information leakage (passwords, tracebacks) prevented in all responses
"""
import os
import json
import tempfile
import pytest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.core.config import Settings, settings
from backend.app.core.security import (
    hash_password,
    create_access_token,
    generate_share_token,
    get_jwt_secret
)
from backend.app.core.middleware import rate_limiter
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.models.saved_valuation import SavedValuation
from backend.app.models.saved_vehicle import SavedVehicle
from backend.app.models.garage import GarageVehicle
from backend.app.services.model_registry import (
    ModelRegistry,
    ModelIntegrityError,
    ModelNotFoundError
)

# Use standard test session fixture
@pytest.fixture
def db(db_session):
    return db_session



# 1. Invalid JWT
def test_jwt_invalid_token_returns_401(client):
    """Ensure malformed, tampered, or forged JWTs return HTTP 401."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid.jwt.token.here"}
    )
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "Authentication required" in data["error"]["message"]


# 2. Expired JWT
def test_jwt_expired_token_returns_401(client, db):
    """Ensure expired JWT tokens are rejected with 401."""
    user = User(
        email="expired_user@example.com",
        password_hash=hash_password("ValidPassword123!"),
        is_active=True
    )
    db.add(user)
    db.commit()

    expired_token = create_access_token(
        subject=user.id,
        expires_delta=timedelta(seconds=-60)
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


# 3. Inactive Account
def test_inactive_user_cannot_authenticate(client, db):
    """Ensure deactivated accounts are rejected on login and token access."""
    user = User(
        email="inactive@example.com",
        password_hash=hash_password("Password123!"),
        is_active=False
    )
    db.add(user)
    db.commit()

    login_resp = client.post(
        "/api/auth/login",
        json={"email": "inactive@example.com", "password": "Password123!"}
    )
    assert login_resp.status_code == 403
    assert "deactivated" in login_resp.json()["error"]["message"]

    token = create_access_token(subject=user.id)
    me_resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_resp.status_code == 401


# 4. Unauthorized Valuation Access
def test_unauthorized_valuation_access_returns_401(client):
    """Ensure unauthenticated access to valuations history is blocked."""
    resp = client.get("/api/valuations")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


# 5. IDOR on Saved Valuations
def test_idor_protection_saved_valuation(client, db):
    """Ensure User A cannot view or delete User B's saved valuation."""
    user_a = User(email="user_a@example.com", password_hash=hash_password("Pass12345!"), is_active=True)
    user_b = User(email="user_b@example.com", password_hash=hash_password("Pass12345!"), is_active=True)
    db.add_all([user_a, user_b])
    db.commit()

    val_b = SavedValuation(
        user_id=user_b.id,
        brand="Hyundai",
        model="Creta",
        year=2021,
        km_driven=25000,
        city="Mumbai",
        estimated_value=1250000,
        comparable_count=5,
        model_version="v002",
        dataset_version="v0.3"
    )
    db.add(val_b)
    db.commit()

    token_a = create_access_token(subject=user_a.id)

    # User A tries to GET User B's valuation
    resp = client.get(
        f"/api/valuations/{val_b.id}",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert resp.status_code in [403, 404]

    # User A tries to DELETE User B's valuation
    del_resp = client.delete(
        f"/api/valuations/{val_b.id}",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert del_resp.status_code in [403, 404]


# 6. IDOR on Saved Vehicles
def test_idor_protection_saved_vehicle(client, db):
    """Ensure User A cannot delete User B's bookmarked vehicle."""
    user_a = User(email="usera_veh@example.com", password_hash=hash_password("Pass12345!"), is_active=True)
    user_b = User(email="userb_veh@example.com", password_hash=hash_password("Pass12345!"), is_active=True)
    db.add_all([user_a, user_b])
    db.commit()

    veh_b = SavedVehicle(
        user_id=user_b.id,
        brand="Maruti",
        model="Swift",
        year=2020,
        km_driven=30000,
        city="Pune"
    )
    db.add(veh_b)
    db.commit()

    token_a = create_access_token(subject=user_a.id)

    del_resp = client.delete(
        f"/api/saved-vehicles/{veh_b.id}",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert del_resp.status_code in [403, 404]


# 7. Oversized Request Payload
def test_oversized_request_rejected(client):
    """Ensure payloads exceeding max body size are rejected with HTTP 413."""
    with patch.object(settings, "MAX_REQUEST_BODY_BYTES", 64):
        large_payload = {
            "brand": "Hyundai",
            "model": "Creta Super Extended Model Name That Easily Exceeds Sixty Four Bytes Limit",
            "year": 2021,
            "km_driven": 25000,
            "city": "Mumbai"
        }
        response = client.post("/api/valuation", json=large_payload)
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"


# 8. Rate Limit Enforcement
def test_rate_limiting_enforcement(client):
    """Ensure repeated requests exceeding rate limit are throttled with HTTP 429."""
    rate_limiter.reset()
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
        r1 = client.post("/api/valuation", json=payload)
        assert r1.status_code == 200

        r2 = client.post("/api/valuation", json=payload)
        assert r2.status_code == 200

        r3 = client.post("/api/valuation", json=payload)
        assert r3.status_code == 429
        data = r3.json()
        assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert "Retry-After" in r3.headers
    rate_limiter.reset()


# 9. Invalid Model Version
def test_invalid_model_version_rejected():
    """Ensure nonexistent model versions raise ModelNotFoundError."""
    registry = ModelRegistry()
    with pytest.raises(ModelNotFoundError):
        registry.load_model_bundle("nonexistent_v999")


# 10. Invalid Model Checksum Verification
def test_invalid_model_checksum_rejection():
    """Ensure corrupted artifact checksums trigger ModelIntegrityError."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        model_path = os.path.join(tmp_dir, "model_vtest.joblib")
        prep_path = os.path.join(tmp_dir, "preprocessor_vtest.joblib")
        meta_path = os.path.join(tmp_dir, "metadata_vtest.json")

        with open(model_path, "wb") as f:
            f.write(b"fake_model_data")
        with open(prep_path, "wb") as f:
            f.write(b"fake_prep_data")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "selected_model": "TestModel",
                "dataset_version": "v0.3",
                "artifact_integrity": {
                    "model_sha256": "expected_different_sha256_hash_here",
                    "preprocessor_sha256": "expected_prep_sha256"
                }
            }, f)

        registry = ModelRegistry(models_dir=tmp_dir)
        with pytest.raises(ModelIntegrityError):
            registry.verify_artifact_integrity("vtest")


# 11. Unsafe CORS Configuration Rejection in Production
def test_unsafe_cors_rejected_in_production():
    """Ensure production settings reject wildcard '*' CORS origins."""
    with pytest.raises(ValueError, match="CORS"):
        Settings(
            ENVIRONMENT="production",
            AUTH_SECRET="strong-prod-auth-secret-1234567890",
            SECRET_KEY="strong-prod-secret-1234567890",
            DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/db",
            COOKIE_SECURE=True,
            BACKEND_CORS_ORIGINS=["*"]
        )


# 12. Invalid Input Payload Validation
def test_invalid_input_payload_structured_error(client):
    """Ensure invalid payload fields return structured 422 responses with details."""
    payload = {
        "brand": "Hyundai",
        "model": "Creta",
        "year": 1850,  # Impossible year
        "km_driven": -20000,  # Negative km
        "city": "Pune"
    }
    response = client.post("/api/valuation", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in data["error"]
    assert len(data["error"]["details"]) > 0


# 13. Production Environment Missing Configuration Validation
def test_production_environment_settings_validation():
    """Verify that Settings strictly enforces all production security rules."""
    # Weak AUTH_SECRET
    with pytest.raises(ValueError, match="AUTH_SECRET"):
        Settings(
            ENVIRONMENT="production",
            AUTH_SECRET="autovalue-dev-secret-key-do-not-use-in-prod-xyz-987654321",
            SECRET_KEY="some-key",
            DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/db",
            COOKIE_SECURE=True,
            BACKEND_CORS_ORIGINS=["https://autovalue.com"]
        )

    # SQLite URL in production
    with pytest.raises(ValueError, match="PostgreSQL"):
        Settings(
            ENVIRONMENT="production",
            AUTH_SECRET="strong-prod-auth-secret-1234567890",
            SECRET_KEY="strong-prod-secret-1234567890",
            DATABASE_URL="sqlite:///prod.db",
            COOKIE_SECURE=True,
            BACKEND_CORS_ORIGINS=["https://autovalue.com"]
        )

    # Insecure cookies in production
    with pytest.raises(ValueError, match="COOKIE_SECURE"):
        Settings(
            ENVIRONMENT="production",
            AUTH_SECRET="strong-prod-auth-secret-1234567890",
            SECRET_KEY="strong-prod-secret-1234567890",
            DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/db",
            COOKIE_SECURE=False,
            BACKEND_CORS_ORIGINS=["https://autovalue.com"]
        )


# 14. Sensitive Information Leakage Prevention
def test_password_hash_never_exposed_in_responses(client, db):
    """Ensure password hashes never leak in registration, login, or profile payloads."""
    reg_resp = client.post(
        "/api/auth/register",
        json={"email": "leaktest@example.com", "password": "SecurePassword123!", "full_name": "Test Security"}
    )
    assert reg_resp.status_code == 201
    resp_text = reg_resp.text
    assert "password_hash" not in resp_text
    assert "SecurePassword123!" not in resp_text

    token = reg_resp.json()["access_token"]
    me_resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_resp.status_code == 200
    assert "password_hash" not in me_resp.text


def test_no_sensitive_info_leaked_on_unhandled_error(client):
    """Ensure unhandled server exceptions return generic error without tracebacks."""
    with patch("backend.app.api.routes.valuation.valuation_service.evaluate_valuation", side_effect=RuntimeError("Secret DB password in exception")):
        payload = {
            "brand": "Hyundai",
            "model": "Creta",
            "year": 2021,
            "km_driven": 25000,
            "fuel_type": "Diesel",
            "transmission": "Manual",
            "city": "Mumbai"
        }
        response = client.post("/api/valuation", json=payload)
        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert "Secret DB password" not in response.text
        assert "Traceback" not in response.text
        assert "request_id" in data["error"]


# 15. Task 1: JWT Signing-Secret Safety in Production
def test_jwt_signing_secret_safety_production():
    """Ensure missing or default secrets raise fast errors in production."""
    with pytest.raises(ValueError, match="AUTH_SECRET or SECRET_KEY"):
        Settings(
            ENVIRONMENT="production",
            AUTH_SECRET="short-secret",
            DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/db",
            COOKIE_SECURE=True,
            BACKEND_CORS_ORIGINS=["https://autovalue.com"]
        )

    # Valid secret in production works
    prod_settings = Settings(
        ENVIRONMENT="production",
        AUTH_SECRET="a" * 32,
        DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/db",
        COOKIE_SECURE=True,
        BACKEND_CORS_ORIGINS=["https://autovalue.com"]
    )
    assert prod_settings.AUTH_SECRET == "a" * 32

    # In production, get_jwt_secret fails if secret is default
    with patch.object(settings, "ENVIRONMENT", "production"):
        with patch.object(settings, "AUTH_SECRET", "autovalue-dev-secret-key-do-not-use-in-prod-xyz-987654321"):
            with patch.object(settings, "SECRET_KEY", None):
                with pytest.raises(ValueError, match="JWT signing secret"):
                    get_jwt_secret()


# 16. Task 2: No PII Leakage in Auth Logs
def test_auth_logs_no_pii_leakage(client):
    """Verify registration, login, and deletion logs do not contain raw email PII."""
    import backend.app.api.routes.auth as auth_route

    logged_messages = []
    def capture_log(msg):
        logged_messages.append(str(msg))

    with patch.object(auth_route.logger, "info", side_effect=capture_log):
        reg_payload = {
            "email": "pii_test_user@example.com",
            "password": "Password123!",
            "full_name": "PII Security User"
        }
        reg_res = client.post("/api/auth/register", json=reg_payload)
        assert reg_res.status_code == 201

        token = reg_res.json()["access_token"]
        user_id = reg_res.json()["user"]["id"]

        # Login
        login_res = client.post("/api/auth/login", json={"email": reg_payload["email"], "password": reg_payload["password"]})
        assert login_res.status_code == 200

        # Account Deletion
        del_res = client.delete("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert del_res.status_code == 200

        # Check captured logs for absence of email address and presence of user_id
        all_logs = " ".join(logged_messages)
        assert "pii_test_user@example.com" not in all_logs
        assert f"user_id={user_id}" in all_logs
        assert "Password123!" not in all_logs
        assert len(logged_messages) == 3


# 17. Task 3: Comprehensive Multi-Resource IDOR Protection Matrix
def test_comprehensive_idor_protection_across_resources(client, db):
    """Test User A attempting to access or modify User B's resources across all endpoints."""
    user_a = User(email="idor_a@example.com", password_hash=hash_password("Pass123!"), is_active=True)
    user_b = User(email="idor_b@example.com", password_hash=hash_password("Pass123!"), is_active=True)
    db.add_all([user_a, user_b])
    db.commit()

    token_a = create_access_token(subject=user_a.id)

    # 1. User B's Saved Valuation
    val_b = SavedValuation(
        user_id=user_b.id,
        brand="Honda",
        model="City",
        year=2021,
        km_driven=20000,
        city="Bengaluru",
        estimated_value=1100000.0,
        model_version="v002",
        dataset_version="v0.3"
    )
    db.add(val_b)

    # 2. User B's Saved Vehicle
    veh_b = SavedVehicle(
        user_id=user_b.id,
        brand="Tata",
        model="Nexon",
        year=2022,
        km_driven=15000,
        city="Mumbai"
    )
    db.add(veh_b)

    # 3. User B's Garage Vehicle
    gar_b = GarageVehicle(
        user_id=user_b.id,
        brand="Hyundai",
        model="Venue",
        year=2020,
        fuel_type="Petrol",
        annual_km=12000,
        ownership_status="OWNED"
    )
    db.add(gar_b)
    db.commit()

    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Valuations IDOR
    assert client.get(f"/api/valuations/{val_b.id}", headers=headers_a).status_code in [403, 404]
    assert client.delete(f"/api/valuations/{val_b.id}", headers=headers_a).status_code in [403, 404]
    assert client.post(f"/api/valuations/{val_b.id}/share", headers=headers_a).status_code in [403, 404]
    assert client.delete(f"/api/valuations/{val_b.id}/share", headers=headers_a).status_code in [403, 404]

    # Lifecycle for private valuation IDOR
    assert client.get(f"/api/lifecycle/{val_b.id}", headers=headers_a).status_code in [403, 404]

    # Saved Vehicle IDOR
    assert client.delete(f"/api/saved-vehicles/{veh_b.id}", headers=headers_a).status_code in [403, 404]

    # Watchlist IDOR
    assert client.post(f"/api/watchlist/{veh_b.id}/refresh", headers=headers_a).status_code in [403, 404]
    assert client.patch(f"/api/watchlist/{veh_b.id}/status", json={"watch_status": "interested_selling"}, headers=headers_a).status_code in [403, 404]

    # Garage IDOR
    assert client.get(f"/api/garage/{gar_b.id}", headers=headers_a).status_code in [403, 404]
    assert client.get(f"/api/garage/{gar_b.id}/intelligence", headers=headers_a).status_code in [403, 404]
    assert client.patch(f"/api/garage/{gar_b.id}", json={"nickname": "Hacked"}, headers=headers_a).status_code in [403, 404]
    assert client.delete(f"/api/garage/{gar_b.id}", headers=headers_a).status_code in [403, 404]

    # Garage Scenario IDOR with User B's vehicle
    scenario_payload = {"actions": [{"vehicle_id": gar_b.id, "action_type": "SELL"}]}
    assert client.post("/api/garage/scenario", json=scenario_payload, headers=headers_a).status_code in [403, 404]

    # Garage Compare IDOR with User B's vehicle
    compare_payload = {"vehicle_ids": [gar_b.id, "some_other_id"]}
    assert client.post("/api/garage/compare", json=compare_payload, headers=headers_a).status_code in [403, 404]

    # Non-existent resource ID returns 404
    assert client.get("/api/valuations/nonexistent_12345", headers=headers_a).status_code == 404
    assert client.get("/api/garage/nonexistent_12345", headers=headers_a).status_code == 404
    assert client.get("/api/shared/nonexistent_share_token_12345").status_code == 404


# 18. Task 4: AUTO_CREATE_TABLES safety
def test_auto_create_tables_rejected_in_production():
    """Ensure production environment rejects AUTO_CREATE_TABLES=True."""
    with pytest.raises(ValueError, match="AUTO_CREATE_TABLES"):
        Settings(
            ENVIRONMENT="production",
            AUTO_CREATE_TABLES=True,
            AUTH_SECRET="a" * 32,
            DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/db",
            COOKIE_SECURE=True,
            BACKEND_CORS_ORIGINS=["https://autovalue.com"]
        )

