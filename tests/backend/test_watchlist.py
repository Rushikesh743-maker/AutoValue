"""
Tests for AutoValue Personal Valuation Watchlist API (Phase 11).
Validates authentication enforcement, IDOR isolation, valuation refresh,
and watch status updates.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.core.security import hash_password, create_access_token
from backend.app.models.user import User
from backend.app.models.saved_vehicle import SavedVehicle


def test_watchlist_requires_auth(client: TestClient):
    """Unauthenticated GET /api/watchlist returns 401."""
    resp = client.get("/api/watchlist")
    assert resp.status_code == 401


def test_watchlist_crud_and_refresh_flow(client: TestClient, db_session):
    """Full watchlist lifecycle: create bookmark, view watchlist, refresh estimate, update status."""
    # 1. Create User
    user = User(
        email="watchlist_user@example.com",
        password_hash=hash_password("Password123!"),
        is_active=True
    )
    db_session.add(user)
    db_session.commit()

    token = create_access_token(subject=user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Add saved vehicle
    veh = SavedVehicle(
        user_id=user.id,
        brand="Hyundai",
        model="Creta",
        year=2021,
        km_driven=25000,
        fuel_type="Diesel",
        transmission="Manual",
        city="Mumbai",
        watch_status="watching"
    )
    db_session.add(veh)
    db_session.commit()

    # 3. GET /api/watchlist
    list_resp = client.get("/api/watchlist", headers=headers)
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) == 1
    assert items[0]["id"] == veh.id
    assert items[0]["watch_status"] == "watching"

    # 4. POST /api/watchlist/{id}/refresh
    ref_resp = client.post(f"/api/watchlist/{veh.id}/refresh", headers=headers)
    assert ref_resp.status_code == 200
    ref_data = ref_resp.json()
    assert ref_data["last_estimated_value"] is not None
    assert ref_data["last_estimated_value"] > 0
    assert ref_data["last_checked_at"] is not None

    # Refresh second time to verify previous_estimated_value tracking
    first_est = ref_data["last_estimated_value"]
    ref_resp2 = client.post(f"/api/watchlist/{veh.id}/refresh", headers=headers)
    assert ref_resp2.status_code == 200
    ref_data2 = ref_resp2.json()
    assert ref_data2["previous_estimated_value"] == first_est

    # 5. PATCH /api/watchlist/{id}/status
    patch_resp = client.patch(
        f"/api/watchlist/{veh.id}/status",
        headers=headers,
        json={"watch_status": "interested_selling"}
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["watch_status"] == "interested_selling"


def test_watchlist_idor_protection(client: TestClient, db_session):
    """User A cannot refresh or modify User B's watchlist vehicle."""
    user_a = User(email="watch_a@example.com", password_hash=hash_password("Pass123!"), is_active=True)
    user_b = User(email="watch_b@example.com", password_hash=hash_password("Pass123!"), is_active=True)
    db_session.add_all([user_a, user_b])
    db_session.commit()

    veh_b = SavedVehicle(
        user_id=user_b.id,
        brand="Honda",
        model="City",
        year=2020,
        km_driven=30000,
        city="Pune"
    )
    db_session.add(veh_b)
    db_session.commit()

    token_a = create_access_token(subject=user_a.id)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # User A attempts to refresh User B's vehicle
    ref_resp = client.post(f"/api/watchlist/{veh_b.id}/refresh", headers=headers_a)
    assert ref_resp.status_code == 404

    # User A attempts to change status of User B's vehicle
    status_resp = client.patch(
        f"/api/watchlist/{veh_b.id}/status",
        headers=headers_a,
        json={"watch_status": "interested_buying"}
    )
    assert status_resp.status_code == 404
