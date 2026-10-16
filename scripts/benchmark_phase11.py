"""
Benchmark script for Phase 11 Decision Intelligence endpoints and services.
Measures real latencies for:
- Intelligence pipeline (deal analysis, negotiation, value score, data confidence)
- Scenario prediction (XGBoost counterfactual simulation)
- Alternative vehicle discovery
- Market timing analysis
- Watchlist database operations
"""
import time
import statistics
import sys
import os

# Add root directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.schemas.valuation import ValuationRequestSchema
from backend.app.services.valuation_service import valuation_service
from backend.app.services.deal_analysis_service import deal_analysis_service
from backend.app.services.negotiation_service import negotiation_service
from backend.app.services.value_score_service import value_score_service
from backend.app.services.data_confidence_service import data_confidence_service
from backend.app.services.scenario_service import scenario_service
from backend.app.services.alternative_vehicle_service import alternative_vehicle_service
from backend.app.services.market_timing_service import market_timing_service
from backend.app.schemas.intelligence import ScenarioRequest, AlternativeVehicleQuery

def run_benchmarks():
    print("==================================================")
    print("AUTOVALUE PHASE 11 PERFORMANCE BENCHMARKS")
    print("==================================================")

    # 1. Warm-up
    val_req = ValuationRequestSchema(
        brand="Hyundai",
        model="Creta",
        variant="SX",
        year=2021,
        fuel_type="Petrol",
        transmission="Manual",
        km_driven=35000,
        city="Mumbai",
        owner_count=1,
        asking_price=1250000.0
    )
    val_resp = valuation_service.evaluate_valuation(val_req)

    # 2. Benchmark Scenario Engine (Target: < 100ms)
    scenario_req = ScenarioRequest(
        base_vehicle=val_req,
        changes={"km_driven": 60000, "year": 2020}
    )
    scenario_latencies = []
    for _ in range(50):
        t0 = time.perf_counter()
        _ = scenario_service.simulate_scenario(scenario_req)
        scenario_latencies.append((time.perf_counter() - t0) * 1000)

    # 3. Benchmark Alternative Vehicle Discovery (Target: < 300ms)
    alt_filter = AlternativeVehicleQuery(
        target_budget=1250000.0,
        fuel_type="Petrol",
        city="Mumbai",
        limit=5
    )
    alt_latencies = []
    for _ in range(50):
        t0 = time.perf_counter()
        _ = alternative_vehicle_service.find_alternatives(alt_filter)
        alt_latencies.append((time.perf_counter() - t0) * 1000)

    # 4. Benchmark Market Timing Engine
    timing_latencies = []
    for _ in range(50):
        t0 = time.perf_counter()
        _ = market_timing_service.analyze_market_timing("Hyundai", "Creta", "Mumbai")
        timing_latencies.append((time.perf_counter() - t0) * 1000)

    # 5. Benchmark Combined Intelligence Services Pipeline (Target: < 500ms)
    est_val = val_resp.valuation.estimated_value
    m_interval = val_resp.valuation.model_interval
    interval_low = m_interval.interval_low if m_interval else None
    interval_high = m_interval.interval_high if m_interval else None
    market_stats = val_resp.market
    comparables = val_resp.comparables or []

    intel_latencies = []
    for _ in range(50):
        t0 = time.perf_counter()
        deal = deal_analysis_service.evaluate_deal(
            asking_price=val_req.asking_price,
            estimated_value=est_val,
            interval_low=interval_low,
            interval_high=interval_high,
            market_median=market_stats.median,
            market_p25=market_stats.p25,
            market_p75=market_stats.p75,
            comparables=[c.model_dump() for c in comparables]
        )
        nego = negotiation_service.analyze_negotiation(
            asking_price=val_req.asking_price,
            estimated_value=est_val,
            model_interval_low=interval_low,
            model_interval_high=interval_high,
            market_median=market_stats.median,
            market_p25=market_stats.p25,
            market_p75=market_stats.p75,
            comparable_count=len(comparables)
        )
        vscore = value_score_service.calculate_value_score(
            year=val_req.year,
            km_driven=val_req.km_driven,
            estimated_value=est_val,
            asking_price=val_req.asking_price,
            market_median=market_stats.median,
            comparable_count=len(comparables)
        )
        conf = data_confidence_service.evaluate_confidence(
            vehicle_data=val_req.model_dump(),
            comparable_count=len(comparables),
            estimated_value=est_val,
            interval_low=interval_low,
            interval_high=interval_high
        )
        timing = market_timing_service.analyze_market_timing(
            brand=val_req.brand,
            model=val_req.model,
            city=val_req.city
        )
        intel_latencies.append((time.perf_counter() - t0) * 1000)

    print("\nBENCHMARK RESULTS (50 iterations each):")
    print(f"1. Scenario Engine Simulation:")
    print(f"   - Mean: {statistics.mean(scenario_latencies):.2f} ms | P95: {statistics.quantiles(scenario_latencies, n=20)[18]:.2f} ms | Target: < 100 ms")

    print(f"2. Alternative Vehicle Discovery:")
    print(f"   - Mean: {statistics.mean(alt_latencies):.2f} ms | P95: {statistics.quantiles(alt_latencies, n=20)[18]:.2f} ms | Target: < 300 ms")

    print(f"3. Market Timing Engine:")
    print(f"   - Mean: {statistics.mean(timing_latencies):.2f} ms | P95: {statistics.quantiles(timing_latencies, n=20)[18]:.2f} ms | Target: < 100 ms")

    print(f"4. Core Intelligence Suite (Deal + Nego + ValueScore + Confidence):")
    print(f"   - Mean: {statistics.mean(intel_latencies):.2f} ms | P95: {statistics.quantiles(intel_latencies, n=20)[18]:.2f} ms | Target: < 500 ms")

    print("==================================================")

if __name__ == "__main__":
    run_benchmarks()
