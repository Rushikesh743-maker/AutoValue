"""
AutoValue Phase 13 Latency Benchmark Suite.
Benchmarks:
1. POST /api/tco (50 iterations)
2. POST /api/tco/scenario (50 iterations)
3. POST /api/tco/compare (50 iterations)
4. Pure TCOService.calculate_tco execution (50 iterations)
"""
import os
import sys
import time
import statistics
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.schemas.valuation import ValuationRequestSchema
from backend.app.services.valuation_service import valuation_service
from backend.app.services.tco_service import tco_service

client = TestClient(app)

ITERATIONS = 50


def benchmark_pure_tco_service():
    req = ValuationRequestSchema(
        brand="Hyundai",
        model="Creta",
        year=2021,
        km_driven=35000,
        fuel_type="Diesel",
        transmission="Manual",
        city="Mumbai",
        asking_price=1250000.0
    )
    val_resp = valuation_service.evaluate_valuation(req, include_shap=False)
    v_dict = req.model_dump()

    latencies = []
    for _ in range(ITERATIONS):
        t0 = time.perf_counter()
        _ = tco_service.calculate_tco(v_dict, val_resp)
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)

    return latencies


def benchmark_post_tco_endpoint():
    payload = {
        "vehicle": {
            "brand": "Hyundai",
            "model": "Creta",
            "year": 2021,
            "km_driven": 35000,
            "fuel_type": "Diesel",
            "transmission": "Manual",
            "city": "Mumbai",
            "asking_price": 1250000.0
        },
        "assumptions": {
            "ownership_years": 5,
            "annual_km": 12000
        }
    }

    latencies = []
    for _ in range(ITERATIONS):
        t0 = time.perf_counter()
        resp = client.post("/api/tco", json=payload)
        t1 = time.perf_counter()
        assert resp.status_code == 200
        latencies.append((t1 - t0) * 1000.0)

    return latencies


def benchmark_post_scenario_endpoint():
    payload = {
        "vehicle": {
            "brand": "Tata",
            "model": "Nexon",
            "year": 2022,
            "km_driven": 25000,
            "fuel_type": "Petrol",
            "transmission": "Manual",
            "city": "Pune"
        },
        "scenario_name": "BASE",
        "assumptions": {
            "ownership_years": 3,
            "annual_km": 15000
        }
    }

    latencies = []
    for _ in range(ITERATIONS):
        t0 = time.perf_counter()
        resp = client.post("/api/tco/scenario", json=payload)
        t1 = time.perf_counter()
        assert resp.status_code == 200
        latencies.append((t1 - t0) * 1000.0)

    return latencies


def benchmark_post_compare_endpoint():
    payload = {
        "vehicles": [
            {
                "brand": "Hyundai",
                "model": "Creta",
                "year": 2021,
                "km_driven": 35000,
                "fuel_type": "Petrol",
                "transmission": "Manual",
                "city": "Mumbai"
            },
            {
                "brand": "Tata",
                "model": "Nexon",
                "year": 2022,
                "km_driven": 20000,
                "fuel_type": "Electric",
                "transmission": "Manual",
                "city": "Mumbai"
            }
        ]
    }

    latencies = []
    for _ in range(ITERATIONS):
        t0 = time.perf_counter()
        resp = client.post("/api/tco/compare", json=payload)
        t1 = time.perf_counter()
        assert resp.status_code == 200
        latencies.append((t1 - t0) * 1000.0)

    return latencies


def print_stats(name: str, latencies: list):
    mean = statistics.mean(latencies)
    median = statistics.median(latencies)
    p95 = np.percentile(latencies, 95)
    min_lat = min(latencies)
    max_lat = max(latencies)

    print(f"\n=======================================================")
    print(f" Benchmark: {name} (N = {len(latencies)})")
    print(f"=======================================================")
    print(f"  Mean:    {mean:.2f} ms")
    print(f"  Median:  {median:.2f} ms")
    print(f"  P95:     {p95:.2f} ms")
    print(f"  Min:     {min_lat:.2f} ms")
    print(f"  Max:     {max_lat:.2f} ms")
    print(f"  Target:  P95 < 150ms -> {'PASSED' if p95 < 150 else 'FAILED'}")


if __name__ == "__main__":
    print("Initializing AutoValue Phase 13 Benchmarking Suite...")
    # Warmup
    _ = client.get("/api/health")

    stats_pure = benchmark_pure_tco_service()
    print_stats("Pure TCOService.calculate_tco", stats_pure)

    stats_post = benchmark_post_tco_endpoint()
    print_stats("POST /api/tco", stats_post)

    stats_scenario = benchmark_post_scenario_endpoint()
    print_stats("POST /api/tco/scenario", stats_scenario)

    stats_compare = benchmark_post_compare_endpoint()
    print_stats("POST /api/tco/compare", stats_compare)
