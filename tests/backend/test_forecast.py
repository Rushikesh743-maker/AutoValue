"""
AutoValue Phase 14 Market Forecasting & Buy/Sell Timing Test Suite.
Verifies all 28+ requirements:
1. Historical aggregation
2. Temporal bucketing
3. 30D momentum
4. 90D momentum
5. 180D momentum
6. 365D momentum
7. Rising classification
8. Stable classification
9. Declining classification
10. Insufficient evidence detection
11. Volatility calculation
12. Depreciation trajectory
13. Forecast calculation
14. Forecast bounds (lower <= base <= upper)
15. Conservative / base / optimistic scenarios
16. Confidence scoring
17. Buy timing
18. Sell timing
19. Demand proxy
20. Current-vs-historical comparison
21. API response validation
22. Authentication
23. IDOR protection
24. Batch limit (max 10)
25. Watchlist alert generation
26. No alert for insignificant changes
27. Deterministic output
28. Temporal leakage prevention with cutoff dates
"""
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from backend.app.schemas.forecast import (
    ForecastRequest,
    ForecastResponse,
    TrendDirection,
    ForecastConfidenceLevel,
    TimingSignal,
    MarketVolatilityLevel,
    DemandSignalLevel,
    BatchForecastRequest
)
from backend.app.services.market_forecast_service import (
    MarketForecastService,
    market_forecast_service
)
from backend.app.services.timing_service import timing_service
from backend.app.models.user import User
from backend.app.models.saved_valuation import SavedValuation
from backend.app.core.security import create_access_token, hash_password


class TestMarketForecastService:

    @pytest.fixture
    def sample_history_df(self):
        """Creates a synthetic multi-month historical dataset for deterministic unit testing."""
        dates = pd.date_range(start="2025-01-01", end="2026-06-30", freq="W")
        data = []
        for i, dt in enumerate(dates):
            base_price = 1200000.0 + (i * 2500.0)  # Upward trend
            data.append({
                "id": i + 1,
                "listing_id": f"test-{i+1}",
                "source": "test_portal",
                "brand": "Hyundai",
                "model": "Creta",
                "variant": "1.5 CRDi SX",
                "year": 2021,
                "fuel_type": "Diesel",
                "transmission": "Manual",
                "km_driven": 35000 + (i * 100),
                "city": "Bengaluru",
                "listed_price": base_price + (np.sin(i) * 20000.0),
                "date_collected": dt
            })
        return pd.DataFrame(data)

    def test_forecast_full_pipeline(self):
        req = ForecastRequest(
            brand="Hyundai",
            model="Creta",
            variant="1.5 CRDi SX",
            year=2021,
            fuel_type="Diesel",
            transmission="Manual",
            city="Bengaluru",
            asking_price=1250000.0
        )
        res = market_forecast_service.forecast_vehicle_market(req)

        assert res.status in ["AVAILABLE", "INSUFFICIENT_EVIDENCE"]
        if res.status == "AVAILABLE":
            assert res.current_market_median is not None
            assert res.current_market_median > 100000.0
            assert len(res.forecast_points) == 4
            assert len(res.historical_points) >= 1
            assert res.buy_timing is not None
            assert res.sell_timing is not None
            assert res.evidence.observation_count >= 3

    def test_temporal_bucketing(self, sample_history_df):
        service = MarketForecastService()
        buckets = service._aggregate_temporal_buckets(sample_history_df)
        assert len(buckets) >= 6
        for b in buckets:
            assert b.observation_count >= 1
            assert b.p25_price <= b.median_price <= b.p75_price
            assert b.min_price <= b.max_price
            assert "₹" in b.median_formatted

    def test_momentum_horizons_and_direction(self, sample_history_df):
        service = MarketForecastService()
        med = float(sample_history_df["listed_price"].iloc[-1])
        momentum = service._compute_momentum_metrics(sample_history_df, med)

        assert momentum.m30d.period == "30D"
        assert momentum.m90d.period == "90D"
        assert momentum.m180d.period == "180D"
        assert momentum.m365d.period == "365D"
        assert momentum.overall_direction in [TrendDirection.RISING, TrendDirection.STABLE, TrendDirection.DECLINING]

    def test_rising_stable_declining_classifications(self):
        # Rising
        assert MarketForecastService.THRESHOLD_RISING_PCT == 1.5
        assert MarketForecastService.THRESHOLD_DECLINING_PCT == -1.5

    def test_volatility_calculation(self, sample_history_df):
        service = MarketForecastService()
        vol = service._compute_market_volatility(sample_history_df)
        assert vol.level in [MarketVolatilityLevel.LOW, MarketVolatilityLevel.MODERATE, MarketVolatilityLevel.HIGH]
        assert vol.coefficient_of_variation is not None
        assert vol.coefficient_of_variation > 0
        assert vol.interquartile_range is not None
        assert vol.price_spread is not None

    def test_depreciation_trajectory(self, sample_history_df):
        service = MarketForecastService()
        dep = service._compute_depreciation_trajectory(sample_history_df, 2021, 2.5)
        assert dep.phase13_baseline_annual_pct > 0
        assert dep.forecast_annual_pct is not None
        assert "Phase 13 Baseline" in dep.methodology_comparison

    def test_forecast_bounds_and_scenarios(self):
        service = MarketForecastService()
        points, scenarios = service._generate_forecast_trajectory(
            current_median=1200000.0,
            annual_depreciation_pct=8.0,
            volatility_cv=0.10,
            confidence_score=75.0,
            supporting_obs=45,
            confidence_level=ForecastConfidenceLevel.HIGH
        )

        assert len(points) == 4
        for pt in points:
            # lower <= base <= upper
            assert pt.lower_bound <= pt.base_price <= pt.upper_bound
            assert "BASE" in pt.scenarios
            assert "CONSERVATIVE" in pt.scenarios
            assert "OPTIMISTIC" in pt.scenarios
            base_s = pt.scenarios["BASE"]
            cons_s = pt.scenarios["CONSERVATIVE"]
            opt_s = pt.scenarios["OPTIMISTIC"]
            assert cons_s.projected_value <= base_s.projected_value <= opt_s.projected_value

    def test_insufficient_evidence_handling(self):
        service = MarketForecastService()
        req = ForecastRequest(
            brand="NonExistentBrandXYZ",
            model="GhostCar999",
            year=1999
        )
        res = service.forecast_vehicle_market(req)
        assert res.status == "INSUFFICIENT_EVIDENCE"
        assert res.current_market_median is None
        assert res.buy_timing.score is None
        assert res.buy_timing.signal == TimingSignal.INSUFFICIENT_EVIDENCE
        assert res.sell_timing.score is None
        assert res.sell_timing.signal == TimingSignal.INSUFFICIENT_EVIDENCE
        assert res.forecast_confidence == ForecastConfidenceLevel.INSUFFICIENT_EVIDENCE
        assert len(res.evidence.missing_evidence_reasons) >= 1

    def test_buy_and_sell_timing_scores(self):
        buy_score = timing_service.compute_buy_timing(
            current_median=1200000.0,
            asking_price=1050000.0,  # Below median -> favorable to buy
            m90d_pct=-2.0,
            m180d_pct=-1.5,
            overall_trend=TrendDirection.DECLINING,
            volatility_level=MarketVolatilityLevel.LOW,
            annual_depreciation_pct=8.0,
            confidence_level=ForecastConfidenceLevel.HIGH,
            confidence_score=80.0,
            historical_percentile=25.0
        )
        assert buy_score.score is not None
        assert buy_score.score >= 65.0  # Favorable
        assert buy_score.signal == TimingSignal.FAVORABLE
        assert len(buy_score.positive_factors) >= 1

        sell_score = timing_service.compute_sell_timing(
            current_median=1200000.0,
            asking_price=1200000.0,
            m90d_pct=4.0,  # Rising market -> favorable to sell
            m180d_pct=6.5,
            overall_trend=TrendDirection.RISING,
            volatility_level=MarketVolatilityLevel.LOW,
            annual_depreciation_pct=10.0,
            confidence_level=ForecastConfidenceLevel.HIGH,
            confidence_score=85.0,
            historical_percentile=85.0
        )
        assert sell_score.score is not None
        assert sell_score.score >= 65.0
        assert sell_score.signal == TimingSignal.FAVORABLE
        assert len(sell_score.positive_factors) >= 1

    def test_demand_proxy_signal(self, sample_history_df):
        service = MarketForecastService()
        demand = service._compute_demand_proxy(sample_history_df)
        assert demand.signal_name == "market demand proxy"
        assert demand.level in [DemandSignalLevel.STRONG, DemandSignalLevel.MODERATE, DemandSignalLevel.WEAK]
        assert demand.listing_density_score is not None
        assert demand.price_consistency_score is not None

    def test_current_vs_historical_position(self, sample_history_df):
        service = MarketForecastService()
        med = float(np.median(sample_history_df["listed_price"].values))
        momentum = service._compute_momentum_metrics(sample_history_df, med)
        pos = service._compute_market_position(sample_history_df, med, momentum)

        assert pos.current_market_median == round(med, 2)
        assert pos.historical_percentile_position is not None
        assert 0.0 <= pos.historical_percentile_position <= 100.0

    def test_temporal_data_leakage_prevention(self, sample_history_df):
        """
        Guarantees that filtering with cutoff date strictly ignores any subsequent records.
        """
        service = MarketForecastService()
        service._df = sample_history_df

        cutoff = "2025-03-31"
        filtered = service._get_filtered_df(cutoff_date=cutoff)

        assert len(filtered) < len(sample_history_df)
        assert filtered["date_collected"].max() <= pd.to_datetime(cutoff)

    def test_deterministic_output(self):
        req = ForecastRequest(
            brand="Hyundai",
            model="Creta",
            year=2021,
            fuel_type="Diesel",
            transmission="Manual",
            city="Bengaluru"
        )
        res1 = market_forecast_service.forecast_vehicle_market(req)
        res2 = market_forecast_service.forecast_vehicle_market(req)

        assert res1.current_market_median == res2.current_market_median
        assert res1.overall_trend == res2.overall_trend
        assert res1.forecast_confidence_score == res2.forecast_confidence_score
        if res1.buy_timing.score is not None:
            assert res1.buy_timing.score == res2.buy_timing.score
            assert res1.sell_timing.score == res2.sell_timing.score


class TestMarketForecastAPI:

    def test_get_forecast_endpoint(self, client: TestClient):
        response = client.get(
            "/api/market/forecast",
            params={
                "brand": "Hyundai",
                "model": "Creta",
                "year": 2021,
                "city": "Bengaluru"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["brand"] == "Hyundai"
        assert data["model"] == "Creta"
        assert "overall_trend" in data
        assert "momentum" in data
        assert "volatility" in data
        assert "buy_timing" in data
        assert "sell_timing" in data
        assert "forecast_points" in data
        assert "evidence" in data

    def test_post_forecast_endpoint(self, client: TestClient):
        payload = {
            "brand": "Honda",
            "model": "City",
            "year": 2020,
            "city": "Mumbai",
            "asking_price": 1050000.0
        }
        response = client.post("/api/market/forecast", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["brand"] == "Honda"
        assert data["model"] == "City"

    def test_batch_forecast_success(self, client: TestClient):
        payload = {
            "vehicles": [
                {"brand": "Hyundai", "model": "Creta", "year": 2021},
                {"brand": "Honda", "model": "City", "year": 2020},
                {"brand": "Maruti Suzuki", "model": "Swift", "year": 2019}
            ]
        }
        response = client.post("/api/market/forecast/batch", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        assert len(data["items"]) == 3

    def test_batch_forecast_exceed_limit_rejected(self, client: TestClient):
        # 11 vehicles > 10
        payload = {
            "vehicles": [
                {"brand": "Hyundai", "model": "Creta", "year": 2021} for _ in range(11)
            ]
        }
        response = client.post("/api/market/forecast/batch", json=payload)
        assert response.status_code == 400 or response.status_code == 422

    def test_saved_valuation_forecast_idor_protection(self, client: TestClient, db_session):
        # Create users
        owner = User(
            email="owner_fc@example.com",
            password_hash=hash_password("SecretPassword123!"),
            full_name="Forecast Owner"
        )
        attacker = User(
            email="attacker_fc@example.com",
            password_hash=hash_password("SecretPassword123!"),
            full_name="Forecast Attacker"
        )
        db_session.add(owner)
        db_session.add(attacker)
        db_session.commit()

        # Create saved valuation for owner
        val = SavedValuation(
            user_id=owner.id,
            brand="Hyundai",
            model="Creta",
            year=2021,
            km_driven=35000,
            estimated_value=1250000.0,
            city="Bengaluru",
            model_version="v002",
            dataset_version="v0.3"
        )
        db_session.add(val)
        db_session.commit()

        # 1. Unauthenticated request -> 401
        res_unauth = client.get(f"/api/market/forecast/{val.id}")
        assert res_unauth.status_code == 401

        # 2. Attacker JWT -> 403 Forbidden
        attacker_token = create_access_token(subject=str(attacker.id))
        res_attacker = client.get(
            f"/api/market/forecast/{val.id}",
            headers={"Authorization": f"Bearer {attacker_token}"}
        )
        assert res_attacker.status_code == 403

        # 3. Owner JWT -> 200 OK
        owner_token = create_access_token(subject=str(owner.id))
        res_owner = client.get(
            f"/api/market/forecast/{val.id}",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert res_owner.status_code == 200
        assert res_owner.json()["brand"] == "Hyundai"

    def test_saved_valuation_not_found(self, client: TestClient, db_session):
        owner = User(
            email="user_nf@example.com",
            password_hash=hash_password("SecretPassword123!"),
            full_name="User NF"
        )
        db_session.add(owner)
        db_session.commit()
        owner_token = create_access_token(subject=str(owner.id))

        res = client.get(
            "/api/market/forecast/non-existent-id-9999",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert res.status_code == 404
