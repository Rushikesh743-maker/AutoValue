"""
Phase 15 Benchmark Script: Vehicle Lifecycle & Ownership Decision Intelligence.
Executes 50 iterations across all key Phase 15 performance dimensions:
1. Pure lifecycle decision
2. Scenario simulation
3. Replacement comparison
4. API decision (FastAPI TestClient)
5. Batch 10 vehicles

Measures and reports mean, median, p95, min, max latencies in milliseconds.
"""
import time
import os
import sys
import statistics
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.schemas.lifecycle import (
    LifecycleDecisionRequest,
    LifecycleScenarioRequest,
    LifecycleCompareRequest,
    DecisionMode
)
from backend.app.services.lifecycle_service import lifecycle_service


def compute_metrics(latencies_ms: List[float]) -> Dict[str, float]:
    sorted_l = sorted(latencies_ms)
    p95_idx = int(len(sorted_l) * 0.95)
    return {
        "mean": round(statistics.mean(sorted_l), 2),
        "median": round(statistics.median(sorted_l), 2),
        "p95": round(sorted_l[min(p95_idx, len(sorted_l) - 1)], 2),
        "min": round(min(sorted_l), 2),
        "max": round(max(sorted_l), 2),
        "count": len(sorted_l)
    }


def run_benchmarks(iterations: int = 50):
    print(f"================================================================================")
    print(f"   AutoValue Phase 15: Lifecycle Decision Intelligence Engine Benchmark")
    print(f"   Iterations: {iterations} per benchmark target")
    print(f"================================================================================\n")

    client = TestClient(app)

    base_buy_req = LifecycleDecisionRequest(
        mode=DecisionMode.BUY,
        brand="Hyundai",
        model="Creta",
        variant="SX",
        year=2021,
        fuel_type="Diesel",
        transmission="Manual",
        km_driven=35000,
        city="Bengaluru",
        asking_price=1150000.0,
        include_alternatives=True
    )

    base_owner_req = LifecycleDecisionRequest(
        mode=DecisionMode.OWNER,
        brand="Hyundai",
        model="Creta",
        variant="SX",
        year=2021,
        fuel_type="Diesel",
        transmission="Manual",
        km_driven=40000,
        city="Bengaluru",
        current_market_value=1200000.0,
        annual_km=14000,
        include_alternatives=True
    )

    # 1. Benchmark: Pure Lifecycle Decision (Service Layer)
    print("1. Benchmarking Pure Lifecycle Decision (Service Layer)...")
    pure_latencies: List[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        _ = lifecycle_service.evaluate_lifecycle(base_buy_req)
        t1 = time.perf_counter()
        pure_latencies.append((t1 - t0) * 1000.0)

    # 2. Benchmark: Scenario Simulation
    print("2. Benchmarking Scenario Simulation (What-If)...")
    scenario_req = LifecycleScenarioRequest(
        base_request=base_owner_req,
        annual_km_override=20000,
        market_shift_pct=-5.0,
        wait_months=6
    )
    scenario_latencies: List[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        _ = lifecycle_service.simulate_scenario(scenario_req)
        t1 = time.perf_counter()
        scenario_latencies.append((t1 - t0) * 1000.0)

    # 3. Benchmark: Multi-Vehicle Replacement Comparison (5 candidates)
    print("3. Benchmarking Replacement Comparison (5 candidates)...")
    candidates = [
        LifecycleDecisionRequest(brand="Kia", model="Seltos", year=2021, km_driven=32000, city="Bengaluru"),
        LifecycleDecisionRequest(brand="Tata", model="Harrier", year=2020, km_driven=45000, city="Bengaluru"),
        LifecycleDecisionRequest(brand="MG", model="Hector", year=2021, km_driven=28000, city="Bengaluru"),
        LifecycleDecisionRequest(brand="Mahindra", model="XUV700", year=2022, km_driven=22000, city="Bengaluru"),
        LifecycleDecisionRequest(brand="Maruti Suzuki", model="Grand Vitara", year=2022, km_driven=18000, city="Bengaluru"),
    ]
    compare_req = LifecycleCompareRequest(
        current_vehicle=base_owner_req,
        replacement_vehicles=candidates
    )
    compare_latencies: List[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        _ = lifecycle_service.compare_lifecycle(compare_req)
        t1 = time.perf_counter()
        compare_latencies.append((t1 - t0) * 1000.0)

    # 4. Benchmark: API Decision (HTTP POST endpoint)
    print("4. Benchmarking API Decision (POST /api/lifecycle/decision)...")
    api_latencies: List[float] = []
    payload = base_buy_req.model_dump()
    for _ in range(iterations):
        t0 = time.perf_counter()
        resp = client.post("/api/lifecycle/decision", json=payload)
        t1 = time.perf_counter()
        assert resp.status_code == 200
        api_latencies.append((t1 - t0) * 1000.0)

    # 5. Benchmark: Batch 10 Vehicles
    print("5. Benchmarking Batch 10 Vehicles (POST /api/lifecycle/batch)...")
    batch_items = [
        LifecycleDecisionRequest(
            brand="Hyundai",
            model="Creta",
            year=2018 + (i % 5),
            km_driven=25000 + (i * 5000),
            city="Bengaluru",
            asking_price=900000.0 + (i * 50000)
        ).model_dump()
        for i in range(10)
    ]
    batch_latencies: List[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        resp = client.post("/api/lifecycle/batch", json={"vehicles": batch_items})
        t1 = time.perf_counter()
        assert resp.status_code == 200
        batch_latencies.append((t1 - t0) * 1000.0)

    # Output Report
    results = {
        "Pure Lifecycle Decision (Target <100ms)": compute_metrics(pure_latencies),
        "Scenario Simulation (Target <200ms)": compute_metrics(scenario_latencies),
        "Replacement Comparison (5 Candidates)": compute_metrics(compare_latencies),
        "API Decision (Target <300ms)": compute_metrics(api_latencies),
        "Batch 10 Vehicles (Target <1000ms)": compute_metrics(batch_latencies),
    }

    print("\n" + "=" * 80)
    print(f"{'BENCHMARK TARGET':<40} | {'MEAN':<8} | {'MEDIAN':<8} | {'P95':<8} | {'MIN':<8} | {'MAX':<8}")
    print("-" * 80)
    for name, m in results.items():
        print(f"{name:<40} | {m['mean']:>6.1f}ms | {m['median']:>6.1f}ms | {m['p95']:>6.1f}ms | {m['min']:>6.1f}ms | {m['max']:>6.1f}ms")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_benchmarks(50)
