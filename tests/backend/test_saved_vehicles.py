"""
Integration tests for Saved Vehicles / Bookmarks.
Validates vehicle bookmarking, duplicate bookmark prevention,
listing, deletion, and ownership enforcement.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def auth_user_1(client: TestClient):
    payload = {"email": "bookmark_user1@example.com", "password": "Password12345!"}
    res = client.post("/api/auth/register", json=payload)
    token = res.json()["access_token"]
    return {"token": token, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture
def auth_user_2(client: TestClient):
    payload = {"email": "bookmark_user2@example.com", "password": "Password12345!"}
    res = client.post("/api/auth/register", json=payload)
    token = res.json()["access_token"]
    return {"token": token, "headers": {"Authorization": f"Bearer {token}"}}


def test_save_vehicle_success_and_list(client: TestClient, auth_user_1):
    payload = {
        "brand": "Honda",
        "model": "City",
        "variant": "ZX CVT",
        "year": 2020,
        "fuel_type": "Petrol",
        "transmission": "Automatic",
        "km_driven": 28000,
        "city": "Mumbai",
        "notes": "Shortlisted candidate"
    }
    create_res = client.post("/api/saved-vehicles", json=payload, headers=auth_user_1["headers"])
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["brand"] == "Honda"
    assert created_data["model"] == "City"
    assert created_data["notes"] == "Shortlisted candidate"

    # List bookmarks
    list_res = client.get("/api/saved-vehicles", headers=auth_user_1["headers"])
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] == 1
    assert list_data["items"][0]["id"] == created_data["id"]


def test_save_vehicle_duplicate_prevented(client: TestClient, auth_user_1):
    payload = {
        "brand": "Maruti Suzuki",
        "model": "Swift",
        "variant": "ZXI",
        "year": 2019,
        "fuel_type": "Petrol",
        "transmission": "Manual",
        "km_driven": 45000,
        "city": "Pune"
    }
    # First save
    res1 = client.post("/api/saved-vehicles", json=payload, headers=auth_user_1["headers"])
    assert res1.status_code == 201

    # Duplicate save
    res2 = client.post("/api/saved-vehicles", json=payload, headers=auth_user_1["headers"])
    assert res2.status_code == 409
    err = res2.json()
    assert "already bookmarked" in err["error"]["message"].lower()


def test_saved_vehicle_deletion_and_idor_protection(client: TestClient, auth_user_1, auth_user_2):
    payload = {
        "brand": "Tata",
        "model": "Nexon",
        "variant": "XZ Plus",
        "year": 2022,
        "fuel_type": "Diesel",
        "transmission": "Manual",
        "km_driven": 22000,
        "city": "Delhi"
    }
    res = client.post("/api/saved-vehicles", json=payload, headers=auth_user_1["headers"])
    veh_id = res.json()["id"]

    # User 2 attempts to delete User 1's saved vehicle
    del_res_2 = client.delete(f"/api/saved-vehicles/{veh_id}", headers=auth_user_2["headers"])
    assert del_res_2.status_code in [403, 404]

    # User 1 deletes own saved vehicle
    del_res_1 = client.delete(f"/api/saved-vehicles/{veh_id}", headers=auth_user_1["headers"])
    assert del_res_1.status_code == 200

    # Ensure list is empty
    list_res = client.get("/api/saved-vehicles", headers=auth_user_1["headers"])
    assert list_res.json()["total"] == 0


def test_save_vehicle_unauthenticated(client: TestClient):
    payload = {
        "brand": "Hyundai",
        "model": "Creta",
        "year": 2021,
        "km_driven": 35000,
        "city": "Bengaluru"
    }
    # Attempting to save without auth returns 401
    post_res = client.post("/api/saved-vehicles", json=payload)
    assert post_res.status_code == 401

    # Attempting to list without auth returns 401
    get_res = client.get("/api/saved-vehicles")
    assert get_res.status_code == 401


def test_save_vehicle_duplicate_with_null_fields(client: TestClient, auth_user_2):
    payload = {
        "brand": "Toyota",
        "model": "Innova Crysta",
        "variant": None,
        "year": 2020,
        "fuel_type": None,
        "transmission": None,
        "km_driven": 60000,
        "city": "Chennai"
    }
    # First save with None fields
    res1 = client.post("/api/saved-vehicles", json=payload, headers=auth_user_2["headers"])
    assert res1.status_code == 201

    # Duplicate save with same None fields
    res2 = client.post("/api/saved-vehicles", json=payload, headers=auth_user_2["headers"])
    assert res2.status_code == 409
    err = res2.json()
    assert "already bookmarked" in err["error"]["message"].lower()


def test_save_vehicle_validation_failure(client: TestClient, auth_user_1):
    # Negative km_driven
    res_neg = client.post(
        "/api/saved-vehicles",
        json={"brand": "Kia", "model": "Seltos", "year": 2022, "km_driven": -500, "city": "Pune"},
        headers=auth_user_1["headers"]
    )
    assert res_neg.status_code == 422

    # Missing model
    res_no_model = client.post(
        "/api/saved-vehicles",
        json={"brand": "Kia", "year": 2022, "km_driven": 20000, "city": "Pune"},
        headers=auth_user_1["headers"]
    )
    assert res_no_model.status_code == 422


def test_cors_preflight_options(client: TestClient):
    # Preflight from localhost:5173
    res_local = client.options(
        "/api/saved-vehicles",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type"
        }
    )
    assert res_local.status_code == 200
    assert res_local.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "POST" in res_local.headers.get("access-control-allow-methods", "")

    # Preflight from 127.0.0.1:5173
    res_ip = client.options(
        "/api/saved-vehicles",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type"
        }
    )
    assert res_ip.status_code == 200
    assert res_ip.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"

    # Preflight with PATCH method
    res_patch = client.options(
        "/api/garage/test-id",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "Authorization,Content-Type"
        }
    )
    assert res_patch.status_code == 200
    assert "PATCH" in res_patch.headers.get("access-control-allow-methods", "")


def test_auth_me_anonymous_vs_authenticated(client: TestClient):
    # 1. Anonymous visitor without token returns 401
    anon_res = client.get("/api/auth/me")
    assert anon_res.status_code == 401

    # 2. Invalid or expired token returns 401
    invalid_res = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid_or_expired_token"})
    assert invalid_res.status_code == 401

    # 3. Authenticated user returns 200 with proper profile
    reg_res = client.post("/api/auth/register", json={"email": "auth_me_user@example.com", "password": "Password123!"})
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]

    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "auth_me_user@example.com"

