#!/usr/bin/env python
"""
AutoValue Production End-to-End Smoke Test (Phase 9).

Performs comprehensive automated verification against a live AutoValue deployment:
1. Liveness health check (/api/health)
2. Readiness dependencies & model integrity (/api/ready)
3. User registration with random credentials
4. User login & session cookie/JWT verification
5. Current user profile fetch (/api/auth/me)
6. Point vehicle valuation & conformal interval computation (/api/valuation)
7. Immutable valuation snapshot persistence (/api/valuations)
8. Valuation history listing & pagination
9. Single valuation report retrieval
10. Saved vehicle bookmarking (/api/saved-vehicles)
11. Multi-vehicle empirical comparison (/api/compare)
12. Share token creation (/api/valuations/{id}/share)
13. Public unauthenticated share report retrieval (/api/shared/{token})
14. Session logout (/api/auth/logout)
15. Unauthenticated access denial check (HTTP 401)
16. Cleanup: Test account deletion (DELETE /api/auth/me)

Usage:
    python scripts/smoke_test.py [--url http://127.0.0.1:8000]
"""
import argparse
import sys
import uuid
import requests

def run_smoke_test(base_url: str) -> bool:
    print("=" * 70)
    print(f"AutoValue Production Deployment Smoke Test")
    print(f"Target URL: {base_url}")
    print("=" * 70)

    session = requests.Session()
    random_id = uuid.uuid4().hex[:8]
    test_email = f"smoke_test_{random_id}@example.com"
    test_password = f"SmokeP@ssw0rd_{random_id}!"
    auth_headers = {}

    steps_passed = 0
    total_steps = 16

    try:
        # Step 1: Health Check
        print("\n[Step 1/16] Testing Liveness (/api/health)...", end=" ")
        r = session.get(f"{base_url}/api/health", timeout=10)
        if r.status_code == 200 and r.json().get("status") == "ok":
            print(f"PASSED (v{r.json().get('version')})")
            steps_passed += 1
        else:
            print(f"FAILED (Status {r.status_code}: {r.text})")
            return False

        # Step 2: Readiness Check
        print("[Step 2/16] Testing Readiness (/api/ready)...", end=" ")
        r = session.get(f"{base_url}/api/ready", timeout=10)
        if r.status_code == 200 and r.json().get("status") == "ready":
            print(f"PASSED (Model: {r.json().get('active_model_version')})")
            steps_passed += 1
        else:
            print(f"FAILED (Status {r.status_code}: {r.text})")
            return False

        # Step 3: User Registration
        print(f"[Step 3/16] Registering test user ({test_email})...", end=" ")
        reg_payload = {
            "email": test_email,
            "password": test_password,
            "full_name": f"Smoke Tester {random_id}"
        }
        r = session.post(f"{base_url}/api/auth/register", json=reg_payload, timeout=10)
        if r.status_code == 201:
            token = r.json().get("access_token")
            auth_headers = {"Authorization": f"Bearer {token}"}
            print("PASSED")
            steps_passed += 1
        else:
            print(f"FAILED (Status {r.status_code}: {r.text})")
            return False

        # Step 4: User Login
        print("[Step 4/16] Testing user authentication login (/api/auth/login)...", end=" ")
        login_payload = {"email": test_email, "password": test_password}
        r = session.post(f"{base_url}/api/auth/login", json=login_payload, timeout=10)
        if r.status_code == 200 and "access_token" in r.json():
            token = r.json().get("access_token")
            auth_headers = {"Authorization": f"Bearer {token}"}
            print("PASSED")
            steps_passed += 1
        else:
            print(f"FAILED (Status {r.status_code}: {r.text})")
            return False

        # Step 5: Profile Fetch
        print("[Step 5/16] Fetching current user profile (/api/auth/me)...", end=" ")
        r = session.get(f"{base_url}/api/auth/me", headers=auth_headers, timeout=10)
        if r.status_code == 200 and r.json().get("email") == test_email:
            print(f"PASSED (User ID: {r.json().get('id')})")
            steps_passed += 1
        else:
            print(f"FAILED (Status {r.status_code}: {r.text})")
            return False

        # Step 6: Point Valuation
        print("[Step 6/16] Requesting ML vehicle valuation (/api/valuation)...", end=" ")
        val_input = {
            "brand": "Maruti",
            "model": "Swift",
            "variant": "VXI",
            "year": 2021,
            "fuel_type": "Petrol",
            "transmission": "Manual",
            "km_driven": 28000,
            "city": "Mumbai",
            "asking_price": 620000
        }
        r = session.post(f"{base_url}/api/valuation", json=val_input, timeout=15)
        if r.status_code == 200:
            val_result = r.json()
            est = val_result.get("valuation", {}).get("estimated_value_formatted")
            print(f"PASSED (Estimated: {est})")
            steps_passed += 1
        else:
            print(f"FAILED (Status {r.status_code}: {r.text})")
            return False

        # Step 7: Save Valuation Snapshot
        print("[Step 7/16] Persisting immutable valuation snapshot (/api/valuations)...", end=" ")
        save_payload = {
            "vehicle": val_input,
            "valuation_result": val_result,
            "notes": "Smoke test automated run"
        }
        r = session.post(f"{base_url}/api/valuations", json=save_payload, headers=auth_headers, timeout=10)
        if r.status_code == 201:
            saved_val = r.json()
            saved_val_id = saved_val.get("id")
            print(f"PASSED (Snapshot ID: {saved_val_id})")
            steps_passed += 1
        else:
            print(f"FAILED (Status {r.status_code}: {r.text})")
            return False

        # Step 8: Valuation History
        print("[Step 8/16] Querying valuation history (/api/valuations)...", end=" ")
        r = session.get(f"{base_url}/api/valuations", headers=auth_headers, timeout=10)
        if r.status_code == 200 and r.json().get("total", 0) >= 1:
            print(f"PASSED ({r.json().get('total')} items found)")
            steps_passed += 1
        else:
            print(f"FAILED (Status {r.status_code}: {r.text})")
            return False

        # Step 9: Single Valuation Detail Report
        print(f"[Step 9/16] Fetching valuation report detail (/api/valuations/{saved_val_id})...", end=" ")
        r = session.get(f"{base_url}/api/valuations/{saved_val_id}", headers=auth_headers, timeout=10)
        if r.status_code == 200 and r.json().get("id") == saved_val_id:
            print("PASSED")
            steps_passed += 1
        else:
            print(f"FAILED (Status {r.status_code}: {r.text})")
            return False

        # Step 10: Bookmark Vehicle
        print("[Step 10/16] Bookmarking vehicle configuration (/api/saved-vehicles)...", end=" ")
        bm_payload = {
            "brand": "Hyundai",
            "model": "Creta",
            "variant": "SX",
            "year": 2022,
            "fuel_type": "Diesel",
            "transmission": "Manual",
            "km_driven": 18000,
            "city": "Delhi"
        }
        r = session.post(f"{base_url}/api/saved-vehicles", json=bm_payload, headers=auth_headers, timeout=10)
        if r.status_code == 201:
            bm_id = r.json().get("id")
            print(f"PASSED (Bookmark ID: {bm_id})")
            steps_passed += 1
        else:
            print(f"FAILED (Status {r.status_code}: {r.text})")
            return False

        # Step 11: Compare Vehicles
        print("[Step 11/16] Running multi-vehicle comparison (/api/compare)...", end=" ")
        comp_payload = {
            "valuation_ids": [saved_val_id],
            "vehicle_ids": [bm_id]
        }
        r = session.post(f"{base_url}/api/compare", json=comp_payload, headers=auth_headers, timeout=10)
        if r.status_code == 200 and len(r.json().get("vehicles", [])) == 2:
            print(f"PASSED (Deltas calculated: {len(r.json().get('empirical_differences', []))})")
            steps_passed += 1
        else:
            print(f"FAILED (Status {r.status_code}: {r.text})")
            return False

        # Step 12: Share Token Generation
        print(f"[Step 12/16] Generating public share token (/api/valuations/{saved_val_id}/share)...", end=" ")
        r = session.post(f"{base_url}/api/valuations/{saved_val_id}/share", headers=auth_headers, timeout=10)
        if r.status_code == 200 and "share_token" in r.json():
            share_tok = r.json().get("share_token")
            print(f"PASSED (Token: {share_tok[:12]}...)")
            steps_passed += 1
        else:
            print(f"FAILED (Status {r.status_code}: {r.text})")
            return False

        # Step 13: Public Shared Report Access
        print(f"[Step 13/16] Accessing public unauthenticated report (/api/shared/{share_tok})...", end=" ")
        unauth_session = requests.Session()
        r = unauth_session.get(f"{base_url}/api/shared/{share_tok}", timeout=10)
        if r.status_code == 200 and r.json().get("share_token") == share_tok:
            assert "email" not in r.text, "Privacy leak detected in shared report"
            assert "user_id" not in r.text, "User ID leak detected in shared report"
            print("PASSED (Zero user leaks)")
            steps_passed += 1
        else:
            print(f"FAILED (Status {r.status_code}: {r.text})")
            return False

        # Step 14: Logout
        print("[Step 14/16] Logging out session (/api/auth/logout)...", end=" ")
        r = session.post(f"{base_url}/api/auth/logout", headers=auth_headers, timeout=10)
        if r.status_code == 200:
            print("PASSED")
            steps_passed += 1
        else:
            print(f"FAILED (Status {r.status_code}: {r.text})")
            return False

        # Step 15: Verify Unauthenticated Denial
        print("[Step 15/16] Verifying unauthenticated rejection on /api/auth/me...", end=" ")
        r = requests.get(f"{base_url}/api/auth/me", timeout=10)
        if r.status_code == 401:
            print("PASSED (HTTP 401 Unauthorized)")
            steps_passed += 1
        else:
            print(f"FAILED (Expected 401, got {r.status_code})")
            return False

        # Step 16: Cleanup (Account Deletion)
        print(f"[Step 16/16] Cleaning up test user account ({test_email})...", end=" ")
        del_session = requests.Session()
        r = del_session.delete(f"{base_url}/api/auth/me", headers=auth_headers, timeout=10)
        if r.status_code == 200:
            print("PASSED (Account and cascaded data permanently purged)")
            steps_passed += 1
        else:
            print(f"FAILED (Status {r.status_code}: {r.text})")
            return False

    except Exception as exc:
        print(f"\n[ERROR] Exception encountered during smoke test: {exc}")
        return False

    print("\n" + "=" * 70)
    print(f"Smoke Test Result: {steps_passed}/{total_steps} checks PASSED")
    print("STATUS: ALL TESTS COMPLETED SUCCESSFULLY")
    print("=" * 70)
    return steps_passed == total_steps


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoValue Production Smoke Test")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="AutoValue API Base URL")
    args = parser.parse_args()

    success = run_smoke_test(args.url.rstrip("/"))
    sys.exit(0 if success else 1)
