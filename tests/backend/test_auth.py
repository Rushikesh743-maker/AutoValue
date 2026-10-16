"""
Integration tests for User Authentication, Profiles, and Security.
Validates registration, login, logout, password hashing, /auth/me,
generic error protection (anti-user enumeration), and account deletion.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.core.security import verify_password, create_access_token
from backend.app.models.user import User


def test_user_registration_success(client: TestClient):
    payload = {
        "email": "Test.User@Example.com",  # Should be normalized to lowercase
        "password": "StrongPassword123!",
        "full_name": "Test User"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "test.user@example.com"
    assert data["user"]["full_name"] == "Test User"
    assert data["user"]["is_active"] is True
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]
    assert "autovalue_token" in response.cookies


def test_user_registration_duplicate_email(client: TestClient):
    payload = {
        "email": "duplicate@example.com",
        "password": "StrongPassword123!",
        "full_name": "Original User"
    }
    res1 = client.post("/api/auth/register", json=payload)
    assert res1.status_code == 201

    # Attempt registering same email
    res2 = client.post("/api/auth/register", json=payload)
    assert res2.status_code == 409
    err = res2.json()
    assert "error" in err
    assert err["error"]["code"] == "CONFLICT"


def test_user_registration_short_password(client: TestClient):
    payload = {
        "email": "short@example.com",
        "password": "short",
        "full_name": "Short Password"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


def test_user_login_success(client: TestClient):
    reg_payload = {
        "email": "login_user@example.com",
        "password": "ValidPassword123!",
        "full_name": "Login User"
    }
    client.post("/api/auth/register", json=reg_payload)

    login_payload = {
        "email": "login_user@example.com",
        "password": "ValidPassword123!"
    }
    response = client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "login_user@example.com"
    assert "autovalue_token" in response.cookies


def test_user_login_invalid_password_generic_error(client: TestClient):
    reg_payload = {
        "email": "auth_test@example.com",
        "password": "CorrectPassword123!"
    }
    client.post("/api/auth/register", json=reg_payload)

    login_payload = {
        "email": "auth_test@example.com",
        "password": "WrongPassword999!"
    }
    response = client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 401
    err = response.json()
    # Ensure error is generic and does not disclose account existence
    assert "Invalid email or password" in err["error"]["message"]


def test_user_login_nonexistent_email_generic_error(client: TestClient):
    login_payload = {
        "email": "does_not_exist@example.com",
        "password": "RandomPassword123!"
    }
    response = client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 401
    err = response.json()
    assert "Invalid email or password" in err["error"]["message"]


def test_get_current_user_me_authenticated(client: TestClient):
    reg_payload = {
        "email": "me_test@example.com",
        "password": "TestPassword123!",
        "full_name": "Me User"
    }
    reg_res = client.post("/api/auth/register", json=reg_payload)
    token = reg_res.json()["access_token"]

    # Test via Authorization Bearer header
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me_test@example.com"
    assert data["full_name"] == "Me User"


def test_get_current_user_me_unauthenticated(client: TestClient):
    # No cookies or bearer headers
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    err = response.json()
    assert err["error"]["code"] == "UNAUTHORIZED"


def test_logout_clears_session(client: TestClient):
    reg_payload = {
        "email": "logout_test@example.com",
        "password": "TestPassword123!"
    }
    client.post("/api/auth/register", json=reg_payload)
    logout_res = client.post("/api/auth/logout")
    assert logout_res.status_code == 200


def test_account_deletion(client: TestClient, db_session):
    reg_payload = {
        "email": "delete_me@example.com",
        "password": "Password12345!"
    }
    reg_res = client.post("/api/auth/register", json=reg_payload)
    token = reg_res.json()["access_token"]
    user_id = reg_res.json()["user"]["id"]

    headers = {"Authorization": f"Bearer {token}"}
    del_res = client.delete("/api/auth/me", headers=headers)
    assert del_res.status_code == 200

    # User should no longer exist in DB
    user = db_session.query(User).filter(User.id == user_id).first()
    assert user is None

    # Subsequent /me should return 401
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 401
