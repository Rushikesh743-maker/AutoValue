import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import time
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.base import Base
from backend.app.db.session import engine


def run_benchmark():
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)

    print("\n" + "=" * 60)
    print("AutoValue Phase 8 Performance Benchmark")
    print("=" * 60)

    # 1. Benchmark Registration
    start = time.perf_counter()
    reg_res = client.post(
        "/api/auth/register",
        json={"email": "perf_test@example.com", "password": "BenchmarkPassword123!", "full_name": "Perf Tester"}
    )
    reg_lat = (time.perf_counter() - start) * 1000
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"1. Registration (bcrypt 12 rounds): {reg_lat:.2f} ms [Status: {reg_res.status_code}]")

    # 2. Benchmark Login
    start = time.perf_counter()
    login_res = client.post(
        "/api/auth/login",
        json={"email": "perf_test@example.com", "password": "BenchmarkPassword123!"}
    )
    login_lat = (time.perf_counter() - start) * 1000
    print(f"2. Login Verification:              {login_lat:.2f} ms [Status: {login_res.status_code}]")

    # 3. Benchmark Current User (/me)
    start = time.perf_counter()
    me_res = client.get("/api/auth/me", headers=headers)
    me_lat = (time.perf_counter() - start) * 1000
    print(f"3. Current User Profile (/me):      {me_lat:.2f} ms [Status: {me_res.status_code}]")

    # 4. Benchmark Save Valuation
    save_payload = {
        "vehicle": {
            "brand": "Hyundai",
            "model": "Creta",
            "variant": "SX",
            "year": 2021,
            "km_driven": 35000,
            "city": "Bengaluru",
            "fuel_type": "Diesel",
            "transmission": "Manual"
        },
        "valuation_result": {
            "model_version": "v002",
            "dataset_version": "v0.3",
            "valuation": {"estimated_value": 1320000.0, "estimated_value_formatted": "₹13.20 Lakh", "range_method": "empirical", "combination_method": "blended"},
            "market": {"median": 1340000.0, "comparable_count": 5},
            "comparables": [],
            "source_analysis": [],
            "explanation": [],
            "transparency_notice": "Empirical model estimate."
        }
    }
    start = time.perf_counter()
    save_res = client.post("/api/valuations", json=save_payload, headers=headers)
    save_lat = (time.perf_counter() - start) * 1000
    val_id = save_res.json()["id"]
    print(f"4. Save Valuation Snapshot:         {save_lat:.2f} ms [Status: {save_res.status_code}]")

    # 5. Benchmark History Query
    start = time.perf_counter()
    hist_res = client.get("/api/valuations?page=1&page_size=10", headers=headers)
    hist_lat = (time.perf_counter() - start) * 1000
    print(f"5. Valuation History Query:         {hist_lat:.2f} ms [Status: {hist_res.status_code}]")

    # 6. Benchmark Single Valuation Detail
    start = time.perf_counter()
    val_detail_res = client.get(f"/api/valuations/{val_id}", headers=headers)
    val_detail_lat = (time.perf_counter() - start) * 1000
    print(f"6. Single Valuation Detail Report:  {val_detail_lat:.2f} ms [Status: {val_detail_res.status_code}]")

    # 7. Benchmark Share Token Generation
    start = time.perf_counter()
    share_res = client.post(f"/api/valuations/{val_id}/share", headers=headers)
    share_lat = (time.perf_counter() - start) * 1000
    share_token = share_res.json()["share_token"]
    print(f"7. Generate Share Token:            {share_lat:.2f} ms [Status: {share_res.status_code}]")

    # 8. Benchmark Public Shared Report Access
    start = time.perf_counter()
    public_res = client.get(f"/api/shared/{share_token}")
    public_lat = (time.perf_counter() - start) * 1000
    print(f"8. Public Shared Report Access:     {public_lat:.2f} ms [Status: {public_res.status_code}]")

    # Clean up test user
    client.delete("/api/auth/me", headers=headers)
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_benchmark()
