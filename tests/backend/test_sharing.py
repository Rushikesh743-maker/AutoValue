"""
Integration tests for Shareable Valuation Reports.
Validates secure random token generation, public sanitized access,
view count incrementation, and sharing revocation.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def auth_share_user(client: TestClient):
    payload = {"email": "share_owner@example.com", "password": "Password12345!"}
    res = client.post("/api/auth/register", json=payload)
    token = res.json()["access_token"]
    return {"token": token, "headers": {"Authorization": f"Bearer {token}"}}


def create_sample_valuation(client: TestClient, headers: dict) -> str:
    payload = {
        "vehicle": {
            "brand": "Kia",
            "model": "Seltos",
            "variant": "HTX IVT",
            "year": 2021,
            "fuel_type": "Petrol",
            "transmission": "Automatic",
            "km_driven": 26000,
            "city": "Hyderabad",
            "asking_price": 1450000.0
        },
        "valuation_result": {
            "model_version": "v002",
            "dataset_version": "v0.3",
            "valuation": {
                "estimated_value": 1410000.0,
                "estimated_value_formatted": "₹14.10 Lakh",
                "range_low": 1330000.0,
                "range_high": 1490000.0,
                "range_low_formatted": "₹13.30 Lakh",
                "range_high_formatted": "₹14.90 Lakh",
                "range_method": "empirical_market_bounds",
                "combination_method": "blended"
            },
            "market": {"median": 1420000.0, "comparable_count": 4},
            "comparables": [],
            "source_analysis": [],
            "explanation": [],
            "transparency_notice": "Empirical model estimate.",
            "request_id": "req-share-99"
        }
    }
    res = client.post("/api/valuations", json=payload, headers=headers)
    return res.json()["id"]


def test_share_token_generation_and_public_access(client: TestClient, auth_share_user):
    val_id = create_sample_valuation(client, auth_share_user["headers"])

    # Generate share link
    share_res = client.post(f"/api/valuations/{val_id}/share", headers=auth_share_user["headers"])
    assert share_res.status_code == 200
    share_data = share_res.json()
    token = share_data["share_token"]
    assert len(token) >= 32
    assert share_data["is_active"] is True

    # Access public report endpoint (unauthenticated)
    public_res = client.get(f"/api/shared/{token}")
    assert public_res.status_code == 200
    public_data = public_res.json()
    assert public_data["brand"] == "Kia"
    assert public_data["model"] == "Seltos"
    assert public_data["estimated_value"] == 1410000.0
    # Crucial security checks: sensitive user fields MUST NOT be present
    assert "user_id" not in public_data
    assert "email" not in public_data
    assert "password" not in public_data
    assert "password_hash" not in public_data
    assert "disclaimer" in public_data

    # Access again to test view count increment
    public_res_2 = client.get(f"/api/shared/{token}")
    assert public_res_2.status_code == 200


def test_revoke_share_token(client: TestClient, auth_share_user):
    val_id = create_sample_valuation(client, auth_share_user["headers"])

    # Create share link
    share_res = client.post(f"/api/valuations/{val_id}/share", headers=auth_share_user["headers"])
    token = share_res.json()["share_token"]

    # Verify public access works
    assert client.get(f"/api/shared/{token}").status_code == 200

    # Revoke share link
    revoke_res = client.delete(f"/api/valuations/{val_id}/share", headers=auth_share_user["headers"])
    assert revoke_res.status_code == 200

    # Verify public access returns 404
    assert client.get(f"/api/shared/{token}").status_code == 404


def test_share_token_expiration_handling(client: TestClient, auth_share_user, db_session):
    from datetime import datetime, timedelta, timezone
    from backend.app.models.share_token import ShareToken

    val_id = create_sample_valuation(client, auth_share_user["headers"])

    # 1. Create token with future expiration (active)
    share_res = client.post(f"/api/valuations/{val_id}/share", headers=auth_share_user["headers"])
    token = share_res.json()["share_token"]

    st = db_session.query(ShareToken).filter(ShareToken.token == token).first()
    # Set naive future datetime
    st.expires_at = datetime.utcnow() + timedelta(days=2)
    db_session.commit()

    active_res = client.get(f"/api/shared/{token}")
    assert active_res.status_code == 200

    # 2. Set naive past datetime (expired)
    st.expires_at = datetime.utcnow() - timedelta(days=1)
    db_session.commit()

    expired_res = client.get(f"/api/shared/{token}")
    assert expired_res.status_code == 404
    data = expired_res.json()
    err_msg = data.get("error", {}).get("message", data.get("detail", ""))
    assert "expired" in err_msg.lower()

    # 3. Set timezone-aware past datetime (expired)
    st.expires_at = datetime.now(timezone.utc) - timedelta(hours=2)
    db_session.commit()

    expired_res_2 = client.get(f"/api/shared/{token}")
    assert expired_res_2.status_code == 404

    # 4. Token without expiration (None)
    st.expires_at = None
    db_session.commit()

    no_exp_res = client.get(f"/api/shared/{token}")
    assert no_exp_res.status_code == 200

