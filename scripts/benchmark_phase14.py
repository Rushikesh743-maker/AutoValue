#!/usr/bin/env python
"""
AutoValue Phase 14 Market Forecasting & Buy/Sell Timing Performance Benchmark.

Empirically benchmarks execution latencies across 50 iterations:
1. Pure Forecast Computation (< 50ms target)
2. Buy/Sell Timing Engine Calculation (< 5ms target)
3. Historical Market Aggregation & Bucketing (< 25ms target)
4. API Forecast Endpoint (GET /api/market/forecast) (< 200ms target)
5. Bounded Batch Forecasting (10 vehicles) (< 500ms target)

Reports: mean, median, p95, min, max latencies and target compliance.
"""
import sys
import os
import time
import statistics
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import numpy as np
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.schemas.forecast import (
    ForecastRequest,
    BatchForecastRequest,
    TrendDirection,
    ForecastConfidenceLevel,
    MarketVolatilityLevel
)
from backend.app.services.market_forecast_service import market_forecast_service
from backend.app.services.timing_service import timing_service

# Setup isolated in-memory SQLite for test benchmarking
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


def run_phase14_benchmark(iterations: int = 50):
    print("=" * 80)
    print(f" AutoValue Phase 14 Market Forecasting Performance Benchmark ({iterations} iterations)")
    print("=" * 80)

    sample_vehicle = ForecastRequest(
        brand="Hyundai",
        model="Creta",
        variant="1.5 CRDi SX",
        year=2021,
        fuel_type="Diesel",
        transmission="Manual",
        km_driven=38000,
        city="Bengaluru",
        asking_price=1250000.0,
        horizon_days=365
    )

    batch_10_vehicles = [
        {"brand": "Hyundai", "model": "Creta", "year": 2021, "city": "Bengaluru"},
        {"brand": "Honda", "model": "City", "year": 2020, "city": "Mumbai"},
        {"brand": "Maruti Suzuki", "model": "Swift", "year": 2019, "city": "Delhi Ncr"},
        {"brand": "Tata", "model": "Nexon", "year": 2022, "city": "Pune"},
        {"brand": "Toyota", "model": "Innova Crysta", "year": 2018, "city": "Hyderabad"},
        {"brand": "Mahindra", "model": "XUV700", "year": 2022, "city": "Bengaluru"},
        {"brand": "Kia", "model": "Seltos", "year": 2020, "city": "Mumbai"},
        {"brand": "Volkswagen", "model": "Polo", "year": 2021, "city": "Delhi Ncr"},
        {"brand": "Hyundai", "model": "Venue", "year": 2021, "city": "Bengaluru"},
        {"brand": "Tata", "model": "Harrier", "year": 2020, "city": "Pune"}
    ]

    # Warmup
    print("Warming up runtime caches...")
    for _ in range(5):
        market_forecast_service.forecast_vehicle_market(sample_vehicle)
        client.get("/api/market/forecast?brand=Hyundai&model=Creta&year=2021&city=Bengaluru")

    # 1. Pure Forecast Computation
    print("1. Benchmarking Pure Forecast Engine...")
    pure_forecast_latencies = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        market_forecast_service.forecast_vehicle_market(sample_vehicle)
        t1 = time.perf_counter()
        pure_forecast_latencies.append((t1 - t0) * 1000.0)

    # 2. Timing Engine Calculation
    print("2. Benchmarking Buy/Sell Timing Engine...")
    timing_latencies = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        timing_service.compute_buy_timing(
            current_median=1200000.0,
            asking_price=1150000.0,
            m90d_pct=2.1,
            m180d_pct=3.4,
            overall_trend=TrendDirection.RISING,
            volatility_level=MarketVolatilityLevel.LOW,
            annual_depreciation_pct=7.5,
            confidence_level=ForecastConfidenceLevel.HIGH,
            confidence_score=78.0,
            historical_percentile=60.0
        )
        timing_service.compute_sell_timing(
            current_median=1200000.0,
            asking_price=1150000.0,
            m90d_pct=2.1,
            m180d_pct=3.4,
            overall_trend=TrendDirection.RISING,
            volatility_level=MarketVolatilityLevel.LOW,
            annual_depreciation_pct=7.5,
            confidence_level=ForecastConfidenceLevel.HIGH,
            confidence_score=78.0,
            historical_percentile=60.0
        )
        t1 = time.perf_counter()
        timing_latencies.append((t1 - t0) * 1000.0)

    # 3. Temporal Bucketing & Historical Aggregation
    print("3. Benchmarking Historical Market Aggregation...")
    hist_agg_latencies = []
    df_raw = market_forecast_service._df
    for _ in range(iterations):
        t0 = time.perf_counter()
        market_forecast_service._aggregate_temporal_buckets(df_raw)
        t1 = time.perf_counter()
        hist_agg_latencies.append((t1 - t0) * 1000.0)

    # 4. API Forecast Endpoint (GET)
    print("4. Benchmarking API Forecast Endpoint (GET)...")
    api_get_latencies = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        res = client.get("/api/market/forecast?brand=Hyundai&model=Creta&year=2021&city=Bengaluru&asking_price=1250000")
        assert res.status_code == 200
        t1 = time.perf_counter()
        api_get_latencies.append((t1 - t0) * 1000.0)

    # 5. Batch Forecast (10 Vehicles)
    print("5. Benchmarking Batch Forecast Endpoint (POST 10 vehicles)...")
    batch_latencies = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        res = client.post("/api/market/forecast/batch", json={"vehicles": batch_10_vehicles})
        assert res.status_code == 200
        t1 = time.perf_counter()
        batch_latencies.append((t1 - t0) * 1000.0)

    # Compile Summary
    benchmarks = {
        "Pure Forecast Engine": (compute_metrics(pure_forecast_latencies), "< 50 ms", 50.0),
        "Buy/Sell Timing Engine": (compute_metrics(timing_latencies), "< 5 ms", 5.0),
        "Historical Market Aggregation": (compute_metrics(hist_agg_latencies), "< 25 ms", 25.0),
        "API Forecast (GET Endpoint)": (compute_metrics(api_get_latencies), "< 200 ms", 200.0),
        "Batch Forecast (10 Vehicles)": (compute_metrics(batch_latencies), "< 500 ms", 500.0)
    }

    print("\n" + "=" * 90)
    print(f"{'Operation / Component':<32} | {'Mean (ms)':<9} | {'Median':<8} | {'P95 (ms)':<8} | {'Min/Max':<12} | {'Target':<9} | {'Status'}")
    print("-" * 90)

    all_passed = True
    for name, (m, target_str, target_val) in benchmarks.items():
        status = "PASS" if m["mean_ms"] <= target_val else "WARN"
        if status != "PASS":
            all_passed = False
        min_max_str = f"{m['min_ms']}/{m['max_ms']}"
        print(f"{name:<32} | {m['mean_ms']:<9.2f} | {m['median_ms']:<8.2f} | {m['p95_ms']:<8.2f} | {min_max_str:<12} | {target_str:<9} | {status}")

    print("=" * 90)
    if all_passed:
        print(">> ALL PHASE 14 PERFORMANCE TARGETS MET SUCCESSFULLY <<")
    else:
        print(">> BENCHMARK COMPLETED WITH WARNINGS <<")
    print("=" * 90 + "\n")


if __name__ == "__main__":
    run_phase14_benchmark(50)
