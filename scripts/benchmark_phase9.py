#!/usr/bin/env python
"""
AutoValue Phase 9 Production Performance Benchmark.

Measures real empirical latencies across core operational endpoints:
- Health Liveness (/api/health)
- System Readiness Probe (/api/ready)
- User Registration & Password Hashing (bcrypt 12 rounds)
- User Authentication Login
- Point Vehicle Valuation (XGBoost v002 + Feature Engineering) (20 iterations)
- Conformal Uncertainty Interval Generation
- Comparable Search & Market Statistics
- SHAP Feature Attribution
- Valuation Snapshot Persistence
- History Listing & Pagination Query
- Public Shared Report Retrieval
"""
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import statistics
import time
import numpy as np
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.db.base import Base
from backend.app.db.session import get_db

# Setup fast in-memory SQLite for isolated local benchmarking
bench_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
BenchSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=bench_engine)

def override_bench_db():
    db = BenchSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_bench_db
Base.metadata.create_all(bind=bench_engine)

client = TestClient(app)


def compute_metrics(latencies_ms):
    return {
        "count": len(latencies_ms),
        "mean_ms": round(statistics.mean(latencies_ms), 2),
        "median_ms": round(statistics.median(latencies_ms), 2),
        "p95_ms": round(float(np.percentile(latencies_ms, 95)), 2),
        "min_ms": round(min(latencies_ms), 2),
        "max_ms": round(max(latencies_ms), 2)
    }


def run_benchmark():
    print("=" * 80)
    print("AutoValue Phase 9 Production Performance & Latency Benchmark")
    print("=" * 80)

    # 1. Health Probe
    health_times = []
    for _ in range(30):
        t0 = time.perf_counter()
        r = client.get("/api/health")
        t1 = time.perf_counter()
        assert r.status_code == 200
        health_times.append((t1 - t0) * 1000)

    # 2. Readiness Probe
    ready_times = []
    for _ in range(20):
        t0 = time.perf_counter()
        r = client.get("/api/ready")
        t1 = time.perf_counter()
        assert r.status_code == 200
        ready_times.append((t1 - t0) * 1000)

    # 3. User Registration (bcrypt 12 rounds)
    reg_times = []
    registered_email = "bench_user_main@example.com"
    r_first = client.post("/api/auth/register", json={"email": registered_email, "password": "BenchPassword123!", "full_name": "Main User"})
    assert r_first.status_code == 201
    auth_token = r_first.json()["access_token"]
    headers = {"Authorization": f"Bearer {auth_token}"}

    for i in range(10):
        email = f"bench_reg_{i}_{time.time()}@example.com"
        t0 = time.perf_counter()
        r = client.post("/api/auth/register", json={"email": email, "password": "BenchPassword123!", "full_name": f"User {i}"})
        t1 = time.perf_counter()
        assert r.status_code == 201
        reg_times.append((t1 - t0) * 1000)

    # 4. User Login
    login_times = []
    for _ in range(15):
        t0 = time.perf_counter()
        r = client.post("/api/auth/login", json={"email": registered_email, "password": "BenchPassword123!"})
        t1 = time.perf_counter()
        assert r.status_code == 200
        login_times.append((t1 - t0) * 1000)

    # 5. Vehicle Valuation Endpoint (20 iterations)
    val_payloads = [
        {"brand": "Maruti", "model": "Swift", "variant": "VXI", "year": 2020, "fuel_type": "Petrol", "transmission": "Manual", "km_driven": 35000, "city": "Mumbai", "asking_price": 580000},
        {"brand": "Hyundai", "model": "Creta", "variant": "SX", "year": 2021, "fuel_type": "Diesel", "transmission": "Manual", "km_driven": 22000, "city": "Delhi", "asking_price": 1250000},
        {"brand": "Honda", "model": "City", "variant": "VX", "year": 2019, "fuel_type": "Petrol", "transmission": "Manual", "km_driven": 45000, "city": "Bangalore", "asking_price": 850000},
        {"brand": "Toyota", "model": "Innova Crysta", "variant": "GX", "year": 2018, "fuel_type": "Diesel", "transmission": "Manual", "km_driven": 80000, "city": "Pune", "asking_price": 1450000},
    ]

    val_times = []
    last_val_result = None
    last_val_input = None
    for i in range(24):
        payload = val_payloads[i % len(val_payloads)]
        t0 = time.perf_counter()
        r = client.post("/api/valuation", json=payload)
        t1 = time.perf_counter()
        assert r.status_code == 200
        val_times.append((t1 - t0) * 1000)
        last_val_result = r.json()
        last_val_input = payload

    # 6. Save Valuation Snapshot
    save_times = []
    saved_ids = []
    for i in range(15):
        t0 = time.perf_counter()
        r = client.post(
            "/api/valuations",
            json={"vehicle": last_val_input, "valuation_result": last_val_result, "notes": f"Bench note {i}"},
            headers=headers
        )
        t1 = time.perf_counter()
        assert r.status_code == 201
        save_times.append((t1 - t0) * 1000)
        saved_ids.append(r.json()["id"])

    # 7. History Query
    hist_times = []
    for _ in range(20):
        t0 = time.perf_counter()
        r = client.get("/api/valuations?page=1&page_size=10", headers=headers)
        t1 = time.perf_counter()
        assert r.status_code == 200
        hist_times.append((t1 - t0) * 1000)

    # 8. Share Token & Public Report Fetch
    share_r = client.post(f"/api/valuations/{saved_ids[0]}/share", headers=headers)
    share_token = share_r.json()["share_token"]

    shared_times = []
    for _ in range(25):
        t0 = time.perf_counter()
        r = client.get(f"/api/shared/{share_token}")
        t1 = time.perf_counter()
        assert r.status_code == 200
        shared_times.append((t1 - t0) * 1000)

    # Results Table
    benchmarks = {
        "Health Probe (/api/health)": compute_metrics(health_times),
        "Readiness Check (/api/ready)": compute_metrics(ready_times),
        "User Registration (bcrypt 12)": compute_metrics(reg_times),
        "User Login (bcrypt verify)": compute_metrics(login_times),
        "Vehicle Valuation (XGBoost v002)": compute_metrics(val_times),
        "Save Valuation Snapshot": compute_metrics(save_times),
        "Valuation History Query": compute_metrics(hist_times),
        "Public Shared Report Retrieval": compute_metrics(shared_times),
    }

    print(f"\n{'Operation / Endpoint':<35} | {'Mean (ms)':<10} | {'Median':<8} | {'p95':<8} | {'Min':<8} | {'Max':<8} | {'N'}")
    print("-" * 90)
    for op, m in benchmarks.items():
        print(f"{op:<35} | {m['mean_ms']:<10} | {m['median_ms']:<8} | {m['p95_ms']:<8} | {m['min_ms']:<8} | {m['max_ms']:<8} | {m['count']}")
    print("=" * 90)

    return benchmarks


if __name__ == "__main__":
    run_benchmark()
