import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import time
import numpy as np
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.schemas.valuation import ValuationRequestSchema
from backend.app.services.risk_service import risk_service
from backend.app.services.valuation_service import valuation_service

def benchmark_phase12(iterations: int = 50):
    client = TestClient(app)
    payload = {
        "brand": "Hyundai",
        "model": "Creta",
        "variant": "1.5 CRDi SX",
        "year": 2021,
        "km_driven": 38000,
        "fuel_type": "Diesel",
        "transmission": "Manual",
        "city": "Pune",
        "asking_price": 1150000.0
    }
    val_req = ValuationRequestSchema(**payload)
    val_resp = valuation_service.evaluate_valuation(val_req, include_shap=False)
    
    # 1. Benchmark Risk Intelligence Core Engine (Target: P95 < 100ms)
    service_latencies_ms = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        _ = risk_service.evaluate_risk(val_req, val_resp)
        t1 = time.perf_counter()
        service_latencies_ms.append((t1 - t0) * 1000.0)
    
    # 2. Warmup & Benchmark End-to-End Endpoint
    for _ in range(3):
        client.post("/api/risk", json=payload)
        
    endpoint_latencies_ms = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        resp = client.post("/api/risk", json=payload)
        t1 = time.perf_counter()
        assert resp.status_code == 200, f"Benchmark request failed: {resp.status_code}"
        endpoint_latencies_ms.append((t1 - t0) * 1000.0)
        
    srv_lat = np.array(service_latencies_ms)
    ep_lat = np.array(endpoint_latencies_ms)
    
    mean_srv = float(np.mean(srv_lat))
    med_srv = float(np.median(srv_lat))
    p95_srv = float(np.percentile(srv_lat, 95))
    min_srv = float(np.min(srv_lat))
    max_srv = float(np.max(srv_lat))
    
    print("=" * 65)
    print("AUTOVALUE PHASE 12 PERFORMANCE BENCHMARKS (N = 50)")
    print("=" * 65)
    print("1. VEHICLE RISK & TRUST INTELLIGENCE ENGINE (Pure Risk Evaluation):")
    print(f"   Mean Latency:   {mean_srv:.3f} ms")
    print(f"   Median Latency: {med_srv:.3f} ms")
    print(f"   P95 Latency:    {p95_srv:.3f} ms")
    print(f"   Min Latency:    {min_srv:.3f} ms")
    print(f"   Max Latency:    {max_srv:.3f} ms")
    print("-" * 65)
    print("2. END-TO-END HTTP API (POST /api/risk including XGBoost & Comparables):")
    print(f"   Mean Latency:   {float(np.mean(ep_lat)):.2f} ms")
    print(f"   Median Latency: {float(np.median(ep_lat)):.2f} ms")
    print(f"   P95 Latency:    {float(np.percentile(ep_lat, 95)):.2f} ms")
    print(f"   Min Latency:    {float(np.min(ep_lat)):.2f} ms")
    print(f"   Max Latency:    {float(np.max(ep_lat)):.2f} ms")
    print("=" * 65)
    
    assert p95_srv < 100.0, f"Risk Engine P95 target failed: {p95_srv:.2f} ms >= 100 ms"
    print("PERFORMANCE TARGET VERIFICATION (P95 < 100ms): PASSED")
    print("=" * 65)
    
    return {
        "iterations": iterations,
        "service_p95_ms": p95_srv,
        "service_mean_ms": mean_srv,
        "service_median_ms": med_srv,
        "service_min_ms": min_srv,
        "service_max_ms": max_srv,
        "endpoint_p95_ms": float(np.percentile(ep_lat, 95)),
        "endpoint_mean_ms": float(np.mean(ep_lat)),
        "endpoint_median_ms": float(np.median(ep_lat))
    }

if __name__ == "__main__":
    benchmark_phase12(50)
