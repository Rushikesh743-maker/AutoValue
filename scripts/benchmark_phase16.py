"""
Phase 16 Benchmark Script: Garage & Portfolio Intelligence Engine.
Executes 50 iterations across all key Phase 16 performance dimensions:
1. Garage List (GET /api/garage)
2. Garage Intelligence Engine (GET /api/garage/intelligence)
3. Vehicle Intelligence (GET /api/garage/{id}/intelligence)
4. Replacement Analysis
5. What-If Scenario Simulation (POST /api/garage/scenario)
6. 10-Vehicle Portfolio Comparison (POST /api/garage/compare)

Measures and reports mean, median, p95, min, max latencies in milliseconds.
"""
import time
import os
import sys
import statistics
import uuid
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.db.session import engine, SessionLocal
from backend.app.db.base import Base
from backend.app.models.user import User
from backend.app.models.garage import GarageVehicle
from backend.app.schemas.garage import (
    OwnershipStatus,
    GarageScenarioRequest,
    GarageScenarioVehicleAction,
    GarageScenarioActionType,
    GarageCompareRequest
)
from backend.app.services.garage_intelligence_service import garage_intelligence_service
from backend.app.core.security import create_access_token


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
    print(f"   AutoValue Phase 16: Garage & Portfolio Intelligence Engine Benchmark")
    print(f"   Iterations: {iterations} per benchmark target")
    print(f"================================================================================\n")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    client = TestClient(app)

    try:
        # Create test benchmark user
        test_email = f"benchmark_p16_{uuid.uuid4().hex[:8]}@autovalue.internal"
        user = User(
            email=test_email,
            password_hash="hashed_benchmark_pw",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create token
        token = create_access_token(subject=str(user.id))
        headers = {"Authorization": f"Bearer {token}"}

        # Seed 10 realistic vehicles in the garage
        vehicles_data = [
            ("Hyundai", "Creta", 2021, "Diesel", "Manual", "Bengaluru", 14000, 38000, 1350000.0, "Primary SUV"),
            ("Honda", "City", 2020, "Petrol", "Manual", "Bengaluru", 10000, 32000, 950000.0, "City Commuter"),
            ("Maruti", "Swift", 2019, "Petrol", "Manual", "Bengaluru", 8000, 45000, 620000.0, "Secondary Hatch"),
            ("Tata", "Nexon", 2022, "Diesel", "Automatic", "Bengaluru", 15000, 28000, 1200000.0, "Crossover"),
            ("Mahindra", "XUV700", 2022, "Diesel", "Automatic", "Bengaluru", 18000, 30000, 2100000.0, "Highway SUV"),
            ("Toyota", "Innova", 2018, "Diesel", "Manual", "Bengaluru", 16000, 85000, 1500000.0, "Family MPV"),
            ("Kia", "Seltos", 2021, "Petrol", "Automatic", "Bengaluru", 11000, 34000, 1400000.0, "Compact SUV"),
            ("Skoda", "Octavia", 2019, "Petrol", "Automatic", "Bengaluru", 9000, 42000, 1750000.0, "Executive Sedan"),
            ("Volkswagen", "Polo", 2020, "Petrol", "Manual", "Bengaluru", 12000, 36000, 780000.0, "Hot Hatch"),
            ("MG", "Hector", 2021, "Petrol", "Manual", "Bengaluru", 10000, 31000, 1300000.0, "Family SUV")
        ]

        created_vehicles: List[GarageVehicle] = []
        for brand, model, year, fuel, trans, city, ann_km, odo, price, nick in vehicles_data:
            gv = GarageVehicle(
                user_id=user.id,
                brand=brand,
                model=model,
                year=year,
                fuel_type=fuel,
                transmission=trans,
                city=city,
                annual_km=ann_km,
                current_odometer=odo,
                purchase_price=price,
                nickname=nick,
                ownership_status=OwnershipStatus.OWNED.value
            )
            db.add(gv)
            created_vehicles.append(gv)
        db.commit()
        for gv in created_vehicles:
            db.refresh(gv)

        target_v = created_vehicles[0]
        vehicle_ids = [v.id for v in created_vehicles]

        # 1. Benchmark: Garage List API
        print("1. Benchmarking Garage List (GET /api/garage)...")
        list_latencies: List[float] = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            resp = client.get("/api/garage", headers=headers)
            t1 = time.perf_counter()
            assert resp.status_code == 200
            list_latencies.append((t1 - t0) * 1000.0)

        # 2. Benchmark: Vehicle Intelligence (GET /api/garage/{id}/intelligence)
        print("2. Benchmarking Vehicle Intelligence (GET /api/garage/{id}/intelligence)...")
        veh_intel_latencies: List[float] = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            resp = client.get(f"/api/garage/{target_v.id}/intelligence", headers=headers)
            t1 = time.perf_counter()
            assert resp.status_code == 200
            veh_intel_latencies.append((t1 - t0) * 1000.0)

        # 3. Benchmark: Garage Portfolio Intelligence (GET /api/garage/intelligence)
        print("3. Benchmarking Garage Intelligence (GET /api/garage/intelligence)...")
        garage_intel_latencies: List[float] = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            resp = client.get("/api/garage/intelligence", headers=headers)
            t1 = time.perf_counter()
            assert resp.status_code == 200
            garage_intel_latencies.append((t1 - t0) * 1000.0)

        # 4. Benchmark: Replacement Opportunity Analysis (Service Layer)
        print("4. Benchmarking Replacement Opportunity Analysis (Service Layer)...")
        repl_latencies: List[float] = []
        target_snapshot = garage_intelligence_service.evaluate_vehicle_snapshot(target_v)
        for _ in range(iterations):
            t0 = time.perf_counter()
            _ = garage_intelligence_service._discover_replacement_opportunities([target_snapshot])
            t1 = time.perf_counter()
            repl_latencies.append((t1 - t0) * 1000.0)

        # 5. Benchmark: What-If Scenario Simulation (POST /api/garage/scenario)
        print("5. Benchmarking What-If Scenario Simulation (POST /api/garage/scenario)...")
        sc_payload = {
            "actions": [
                {
                    "vehicle_id": created_vehicles[1].id,
                    "action_type": "SELL"
                },
                {
                    "vehicle_id": created_vehicles[2].id,
                    "action_type": "UPDATE_MILEAGE",
                    "annual_km_override": 18000
                }
            ],
            "ownership_horizon_years": 5
        }
        scenario_latencies: List[float] = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            resp = client.post("/api/garage/scenario", json=sc_payload, headers=headers)
            t1 = time.perf_counter()
            assert resp.status_code == 200
            scenario_latencies.append((t1 - t0) * 1000.0)

        # 6. Benchmark: 10-Vehicle Portfolio Comparison (POST /api/garage/compare)
        print("6. Benchmarking 10-Vehicle Comparison (POST /api/garage/compare)...")
        compare_payload = {"vehicle_ids": vehicle_ids}
        compare_latencies: List[float] = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            resp = client.post("/api/garage/compare", json=compare_payload, headers=headers)
            t1 = time.perf_counter()
            assert resp.status_code == 200
            compare_latencies.append((t1 - t0) * 1000.0)

        # Aggregate Results
        results = {
            "Garage List (API)": compute_metrics(list_latencies),
            "Vehicle Intelligence (API)": compute_metrics(veh_intel_latencies),
            "Garage Intelligence (API, 10 vehicles)": compute_metrics(garage_intel_latencies),
            "Replacement Analysis (Service)": compute_metrics(repl_latencies),
            "What-If Scenario Simulation (API)": compute_metrics(scenario_latencies),
            "10-Vehicle Portfolio Compare (API)": compute_metrics(compare_latencies),
        }

        print("\n================================================================================")
        print("                       PHASE 16 PERFORMANCE BENCHMARK REPORT                    ")
        print("================================================================================")
        print(f"{'Benchmark Target':<42} | {'Mean (ms)':<10} | {'Median':<10} | {'P95 (ms)':<10} | {'Min (ms)':<10} | {'Max (ms)':<10}")
        print("-" * 100)

        targets_spec = {
            "Garage List (API)": 100.0,
            "Vehicle Intelligence (API)": 200.0,
            "Garage Intelligence (API, 10 vehicles)": 500.0,
            "Replacement Analysis (Service)": 200.0,
            "What-If Scenario Simulation (API)": 300.0,
            "10-Vehicle Portfolio Compare (API)": 1000.0,
        }

        all_passed = True
        for name, m in results.items():
            target_p95 = targets_spec.get(name, 500.0)
            status = "PASS" if m["p95"] <= target_p95 else "WARN"
            if status != "PASS":
                all_passed = False
            print(f"{name:<42} | {m['mean']:<10.2f} | {m['median']:<10.2f} | {m['p95']:<10.2f} | {m['min']:<10.2f} | {m['max']:<10.2f} [{status} <= {target_p95}ms]")

        print("================================================================================")
        print(f"Overall Benchmark Status: {'ALL TARGETS PASSED' if all_passed else 'COMPLETED WITH OBSERVATIONS'}")
        print("================================================================================\n")

    finally:
        # Cleanup benchmark data
        try:
            db.query(GarageVehicle).filter(GarageVehicle.user_id == user.id).delete()
            db.query(User).filter(User.id == user.id).delete()
            db.commit()
        except Exception:
            pass
        db.close()


if __name__ == "__main__":
    run_benchmarks(iterations=50)
