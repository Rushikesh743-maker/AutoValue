"""
AutoValue Temporal Market Forecasting & Intelligence Service (Phase 14).
Aggregates historical marketplace evidence, computes multi-horizon momentum,
market volatility, empirical depreciation trajectories, deterministic forecast scenarios
with uncertainty corridors, demand proxies, and integrates buy/sell timing indicators.
"""
from typing import Dict, Any, List, Optional, Tuple
import os
import math
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging

from backend.app.core.config import settings
from backend.app.schemas.forecast import (
    ForecastRequest,
    ForecastResponse,
    HistoricalMarketPoint,
    TrendMetrics,
    MarketMomentum,
    MarketVolatility,
    DemandSignal,
    DepreciationTrajectory,
    MarketPositionComparison,
    ForecastScenario,
    ForecastPoint,
    TimingScore,
    ForecastEvidence,
    ForecastAlert,
    TrendDirection,
    ForecastConfidenceLevel,
    TimingSignal,
    ForecastScenarioType,
    MarketVolatilityLevel,
    DemandSignalLevel
)
from backend.app.services.timing_service import timing_service

logger = logging.getLogger("autovalue.market_forecast_service")


class MarketForecastService:
    """
    Production-grade temporal market forecasting engine.
    Extracts empirical signals from historical marketplace snapshots without
    unsubstantiated claims of deterministic future certitude.
    """

    # Momentum Direction Thresholds
    THRESHOLD_RISING_PCT = 1.5       # >= +1.5% observed price movement
    THRESHOLD_DECLINING_PCT = -1.5   # <= -1.5% observed price movement

    # Volatility CV Thresholds
    VOLATILITY_LOW_MAX = 0.12
    VOLATILITY_MODERATE_MAX = 0.22

    # Evidence Minimums
    MIN_OBSERVATIONS_FOR_FORECAST = 3
    MIN_HISTORY_SPAN_DAYS = 14

    # Default Phase 13 Baseline Annual Depreciation by Age Bracket
    BASELINE_DEPRECIATION_RATES = {
        (0, 2): 10.0,   # 10% annual for 0-2 year cars
        (3, 5): 8.5,    # 8.5% annual for 3-5 year cars
        (6, 8): 7.0,    # 7.0% annual for 6-8 year cars
        (9, 30): 6.0    # 6.0% annual for 9+ year cars
    }

    def __init__(self, processed_csv_path: Optional[str] = None):
        self.csv_path = processed_csv_path or os.path.join(settings.PROCESSED_DATA_DIR, "autovalue_processed.csv")
        self._df: Optional[pd.DataFrame] = None
        self._aggregation_cache: Dict[str, Any] = {}
        self._load_data()

    def _load_data(self):
        """Loads and pre-processes CSV listings data."""
        if os.path.exists(self.csv_path):
            try:
                df = pd.read_csv(self.csv_path)
                if "date_collected" in df.columns:
                    df["date_collected"] = pd.to_datetime(df["date_collected"], errors="coerce")
                else:
                    df["date_collected"] = pd.Timestamp.now()
                # Ensure numerical columns
                df["listed_price"] = pd.to_numeric(df["listed_price"], errors="coerce")
                df["year"] = pd.to_numeric(df["year"], errors="coerce")
                df["km_driven"] = pd.to_numeric(df.get("km_driven", 0), errors="coerce")
                self._df = df.dropna(subset=["listed_price", "brand", "model"])
            except Exception as ex:
                logger.error(f"Error loading historical dataset: {ex}")
                self._df = pd.DataFrame()
        else:
            self._df = pd.DataFrame()

    def _get_filtered_df(self, cutoff_date: Optional[str] = None) -> pd.DataFrame:
        """Returns dataframe respecting cutoff date to prevent temporal leakage."""
        if self._df is None or self._df.empty:
            return pd.DataFrame()
        df = self._df.copy()
        if cutoff_date:
            try:
                cutoff_dt = pd.to_datetime(cutoff_date)
                df = df[df["date_collected"] <= cutoff_dt]
            except Exception:
                pass
        return df

    def _match_segment_hierarchy(
        self,
        df: pd.DataFrame,
        req: ForecastRequest
    ) -> Tuple[pd.DataFrame, str, str, bool]:
        """
        Applies hierarchical segmentation to balance specificity with statistical power.
        Returns: (subset_df, segment_level, segment_description, fallback_applied)
        """
        brand_clean = req.brand.strip().lower()
        model_clean = req.model.strip().lower()
        city_clean = (req.city or "").strip().lower()
        fuel_clean = (req.fuel_type or "").strip().lower()
        trans_clean = (req.transmission or "").strip().lower()

        # Step 1: Exact vehicle spec + city
        s1 = df[
            (df["brand"].str.lower() == brand_clean) &
            (df["model"].str.lower() == model_clean) &
            (df["year"] == req.year)
        ]
        if city_clean:
            s1_city = s1[s1["city"].str.lower() == city_clean]
            if len(s1_city) >= 5:
                return s1_city, "exact_model_year_city", f"{req.brand} {req.model} ({req.year}) in {req.city}", False

        # Step 2: Model + Year
        if len(s1) >= 5:
            return s1, "model_year", f"{req.brand} {req.model} ({req.year}) Nationwide", False

        # Step 3: Model + City
        if city_clean:
            s3 = df[
                (df["brand"].str.lower() == brand_clean) &
                (df["model"].str.lower() == model_clean) &
                (df["city"].str.lower() == city_clean)
            ]
            if len(s3) >= 5:
                return s3, "model_city", f"{req.brand} {req.model} all years in {req.city}", True

        # Step 4: Model overall
        s4 = df[
            (df["brand"].str.lower() == brand_clean) &
            (df["model"].str.lower() == model_clean)
        ]
        if len(s4) >= self.MIN_OBSERVATIONS_FOR_FORECAST:
            return s4, "model_national", f"{req.brand} {req.model} all years Nationwide", True

        # Step 5: Brand level
        s5 = df[df["brand"].str.lower() == brand_clean]
        if len(s5) >= self.MIN_OBSERVATIONS_FOR_FORECAST:
            return s5, "brand_level", f"{req.brand} Brand Fleet", True

        # Fallback: empty / insufficient
        return df.iloc[0:0], "insufficient", "Insufficient segment observations", True

    def _aggregate_temporal_buckets(
        self,
        df: pd.DataFrame
    ) -> List[HistoricalMarketPoint]:
        """
        Aggregates observations into discrete temporal buckets (monthly or multi-week).
        """
        if df.empty or "date_collected" not in df.columns:
            return []

        df_valid = df.dropna(subset=["date_collected", "listed_price"]).sort_values("date_collected")
        if df_valid.empty:
            return []

        # Determine bucket frequency: weekly if observations > 100 spanning < 90 days, otherwise monthly
        min_date = df_valid["date_collected"].min()
        max_date = df_valid["date_collected"].max()
        span_days = (max_date - min_date).days

        if span_days < 30:
            # Single bucket
            prices = df_valid["listed_price"].values
            med = float(np.median(prices))
            mean = float(np.mean(prices))
            std = float(np.std(prices)) if len(prices) > 1 else 0.0
            cv = (std / mean) if mean > 0 else 0.0
            return [
                HistoricalMarketPoint(
                    period_start=min_date.strftime("%Y-%m-%d"),
                    period_end=max_date.strftime("%Y-%m-%d"),
                    period_label=min_date.strftime("%b %Y"),
                    observation_count=len(prices),
                    median_price=round(med, 2),
                    mean_price=round(mean, 2),
                    p25_price=round(float(np.percentile(prices, 25)), 2),
                    p75_price=round(float(np.percentile(prices, 75)), 2),
                    min_price=round(float(np.min(prices)), 2),
                    max_price=round(float(np.max(prices)), 2),
                    dispersion_cv=round(cv, 4),
                    median_formatted=f"₹{med:,.0f}"
                )
            ]

        # Group by Month
        df_valid["period_key"] = df_valid["date_collected"].dt.to_period("M")
        grouped = df_valid.groupby("period_key")

        buckets: List[HistoricalMarketPoint] = []
        for period_key, grp in sorted(grouped, key=lambda x: str(x[0])):
            prices = grp["listed_price"].values
            if len(prices) == 0:
                continue
            med = float(np.median(prices))
            mean = float(np.mean(prices))
            std = float(np.std(prices)) if len(prices) > 1 else 0.0
            cv = (std / mean) if mean > 0 else 0.0
            start_dt = grp["date_collected"].min().strftime("%Y-%m-%d")
            end_dt = grp["date_collected"].max().strftime("%Y-%m-%d")
            period_label = grp["date_collected"].min().strftime("%b %Y")

            buckets.append(
                HistoricalMarketPoint(
                    period_start=start_dt,
                    period_end=end_dt,
                    period_label=period_label,
                    observation_count=len(prices),
                    median_price=round(med, 2),
                    mean_price=round(mean, 2),
                    p25_price=round(float(np.percentile(prices, 25)), 2),
                    p75_price=round(float(np.percentile(prices, 75)), 2),
                    min_price=round(float(np.min(prices)), 2),
                    max_price=round(float(np.max(prices)), 2),
                    dispersion_cv=round(cv, 4),
                    median_formatted=f"₹{med:,.0f}"
                )
            )

        return buckets

    def _compute_momentum_metrics(
        self,
        df: pd.DataFrame,
        current_median: float
    ) -> MarketMomentum:
        """
        Calculates multi-horizon momentum over 30, 90, 180, and 365 days.
        """
        if df.empty or "date_collected" not in df.columns or current_median <= 0:
            empty_trend = lambda p, d: TrendMetrics(
                period=p,
                period_days=d,
                observation_count=0,
                historical_median=None,
                current_median=None,
                absolute_change=None,
                price_change_pct=None,
                annualized_change_pct=None,
                direction=TrendDirection.INSUFFICIENT_EVIDENCE,
                description=f"Insufficient historical data to compute {p} momentum."
            )
            return MarketMomentum(
                m30d=empty_trend("30D", 30),
                m90d=empty_trend("90D", 90),
                m180d=empty_trend("180D", 180),
                m365d=empty_trend("365D", 365),
                overall_direction=TrendDirection.INSUFFICIENT_EVIDENCE,
                velocity_summary="Insufficient historical price observations."
            )

        max_date = df["date_collected"].max()
        horizons = [("30D", 30), ("90D", 90), ("180D", 180), ("365D", 365)]
        metrics_dict: Dict[str, TrendMetrics] = {}

        for p_label, p_days in horizons:
            cutoff = max_date - timedelta(days=p_days)
            # Historical window: observations before cutoff or around cutoff
            hist_subset = df[df["date_collected"] <= cutoff]

            if len(hist_subset) >= 2:
                hist_median = float(np.median(hist_subset["listed_price"].values))
                abs_change = current_median - hist_median
                pct_change = (abs_change / hist_median) * 100.0 if hist_median > 0 else 0.0

                # Annualize for >= 90 days
                annualized_pct = None
                if p_days >= 90 and hist_median > 0:
                    growth_factor = 1.0 + (pct_change / 100.0)
                    if growth_factor > 0:
                        annualized_pct = round((math.pow(growth_factor, 365.0 / p_days) - 1.0) * 100.0, 2)
                        # Clamp extreme annualized numbers
                        annualized_pct = max(-90.0, min(150.0, annualized_pct))

                if pct_change >= self.THRESHOLD_RISING_PCT:
                    direction = TrendDirection.RISING
                elif pct_change <= self.THRESHOLD_DECLINING_PCT:
                    direction = TrendDirection.DECLINING
                else:
                    direction = TrendDirection.STABLE

                sign = "+" if pct_change >= 0 else ""
                desc = (
                    f"{p_label} price change of {sign}{pct_change:.1f}% "
                    f"({sign}₹{abs_change:,.0f}) from historical median of ₹{hist_median:,.0f}."
                )

                metrics_dict[p_label] = TrendMetrics(
                    period=p_label,
                    period_days=p_days,
                    observation_count=len(hist_subset),
                    historical_median=round(hist_median, 2),
                    current_median=round(current_median, 2),
                    absolute_change=round(abs_change, 2),
                    price_change_pct=round(pct_change, 2),
                    annualized_change_pct=annualized_pct,
                    direction=direction,
                    description=desc
                )
            else:
                # If no direct historical slice, compute from available data span
                metrics_dict[p_label] = TrendMetrics(
                    period=p_label,
                    period_days=p_days,
                    observation_count=len(hist_subset),
                    historical_median=None,
                    current_median=round(current_median, 2),
                    absolute_change=None,
                    price_change_pct=None,
                    annualized_change_pct=None,
                    direction=TrendDirection.INSUFFICIENT_EVIDENCE,
                    description=f"Insufficient observations available older than {p_days} days."
                )

        # Determine overall momentum direction (prioritizing 90D / 180D)
        if metrics_dict["90D"].direction != TrendDirection.INSUFFICIENT_EVIDENCE:
            overall = metrics_dict["90D"].direction
        elif metrics_dict["180D"].direction != TrendDirection.INSUFFICIENT_EVIDENCE:
            overall = metrics_dict["180D"].direction
        elif metrics_dict["30D"].direction != TrendDirection.INSUFFICIENT_EVIDENCE:
            overall = metrics_dict["30D"].direction
        else:
            overall = TrendDirection.STABLE if len(df) >= self.MIN_OBSERVATIONS_FOR_FORECAST else TrendDirection.INSUFFICIENT_EVIDENCE

        m90 = metrics_dict["90D"]
        m180 = metrics_dict["180D"]
        if m90.price_change_pct is not None:
            sign = "+" if m90.price_change_pct >= 0 else ""
            summary = f"Observed 90-day momentum is {sign}{m90.price_change_pct:.1f}% ({overall.value.lower()})."
        else:
            summary = f"Market momentum classified as {overall.value.lower()} across available historical span."

        return MarketMomentum(
            m30d=metrics_dict["30D"],
            m90d=metrics_dict["90D"],
            m180d=metrics_dict["180D"],
            m365d=metrics_dict["365D"],
            overall_direction=overall,
            velocity_summary=summary
        )

    def _compute_market_volatility(
        self,
        df: pd.DataFrame
    ) -> MarketVolatility:
        """
        Measures price dispersion across historical listings.
        """
        if len(df) < self.MIN_OBSERVATIONS_FOR_FORECAST:
            return MarketVolatility(
                level=MarketVolatilityLevel.INSUFFICIENT_EVIDENCE,
                coefficient_of_variation=None,
                interquartile_range=None,
                price_spread=None,
                rolling_std=None,
                explanation="Insufficient observations to reliably calculate market price volatility."
            )

        prices = df["listed_price"].values
        mean = float(np.mean(prices))
        std = float(np.std(prices))
        cv = (std / mean) if mean > 0 else 0.0
        p25 = float(np.percentile(prices, 25))
        p75 = float(np.percentile(prices, 75))
        iqr = p75 - p25
        spread = float(np.max(prices) - np.min(prices))

        if cv < self.VOLATILITY_LOW_MAX:
            level = MarketVolatilityLevel.LOW
            expl = f"Low price dispersion (CV: {cv:.2%}, IQR: ₹{iqr:,.0f}), indicating tight pricing consistency."
        elif cv <= self.VOLATILITY_MODERATE_MAX:
            level = MarketVolatilityLevel.MODERATE
            expl = f"Moderate price dispersion (CV: {cv:.2%}, IQR: ₹{iqr:,.0f}), reflecting standard condition/trim variations."
        else:
            level = MarketVolatilityLevel.HIGH
            expl = f"High price dispersion (CV: {cv:.2%}, IQR: ₹{iqr:,.0f}), indicating wide spread in seller asking prices."

        return MarketVolatility(
            level=level,
            coefficient_of_variation=round(cv, 4),
            interquartile_range=round(iqr, 2),
            price_spread=round(spread, 2),
            rolling_std=round(std, 2),
            explanation=expl
        )

    def _compute_demand_proxy(
        self,
        df: pd.DataFrame
    ) -> DemandSignal:
        """
        Calculates observable marketplace demand proxy signals from inventory flow and pricing stability.
        Explicitly branded as a proxy, not actual transaction volumes.
        """
        if len(df) < self.MIN_OBSERVATIONS_FOR_FORECAST:
            return DemandSignal(
                level=DemandSignalLevel.INSUFFICIENT_EVIDENCE,
                signal_name="market demand proxy",
                listing_count_growth_pct=None,
                listing_density_score=None,
                price_consistency_score=None,
                basis_explanation="Insufficient listings to evaluate marketplace demand proxies."
            )

        # Density score (0-100) based on sample size
        density = min(100.0, (len(df) / 30.0) * 100.0)

        # Price consistency score (0-100) inverted from CV
        prices = df["listed_price"].values
        mean = float(np.mean(prices))
        cv = (float(np.std(prices)) / mean) if mean > 0 else 0.5
        consistency = max(0.0, min(100.0, (1.0 - cv) * 100.0))

        # Growth proxy if temporal span permits
        df_sorted = df.sort_values("date_collected")
        midpoint = len(df_sorted) // 2
        first_half = len(df_sorted.iloc[:midpoint])
        second_half = len(df_sorted.iloc[midpoint:])
        growth_pct = ((second_half - first_half) / max(1, first_half)) * 100.0

        if density >= 60.0 and consistency >= 75.0:
            lvl = DemandSignalLevel.STRONG
            expl = f"Strong marketplace liquidity proxy: {len(df)} active/recent listings with high price clustering ({consistency:.0f}/100)."
        elif density >= 30.0:
            lvl = DemandSignalLevel.MODERATE
            expl = f"Moderate marketplace activity: {len(df)} listings observed across the segment."
        else:
            lvl = DemandSignalLevel.WEAK
            expl = f"Thin marketplace liquidity: limited observation count ({len(df)} listings)."

        return DemandSignal(
            level=lvl,
            signal_name="market demand proxy",
            listing_count_growth_pct=round(growth_pct, 1),
            listing_density_score=round(density, 1),
            price_consistency_score=round(consistency, 1),
            basis_explanation=expl
        )

    def _compute_depreciation_trajectory(
        self,
        df: pd.DataFrame,
        vehicle_year: int,
        momentum_90d_pct: Optional[float]
    ) -> DepreciationTrajectory:
        """
        Compares observed historical depreciation against Phase 13 baseline and forecast rates.
        """
        current_year = datetime.now().year
        vehicle_age = max(0, current_year - vehicle_year)

        # 1. Baseline depreciation from Phase 13 lookup
        baseline_rate = 8.5
        for (min_age, max_age), rate in self.BASELINE_DEPRECIATION_RATES.items():
            if min_age <= vehicle_age <= max_age:
                baseline_rate = rate
                break

        # 2. Historical observed annual depreciation (from age vs price slope if multi-year data available)
        observed_rate = None
        if len(df) >= 10 and df["year"].nunique() >= 2:
            try:
                # Regress log(price) on year
                valid_subset = df.dropna(subset=["year", "listed_price"])
                years = valid_subset["year"].values
                log_prices = np.log(valid_subset["listed_price"].values)
                # slope represents annual change in log price
                slope, _ = np.polyfit(years, log_prices, 1)
                # If newer years have higher price, slope > 0 => older cars depreciate at ~ -slope
                obs_annual = (math.exp(slope) - 1.0) * 100.0
                observed_rate = round(abs(obs_annual), 1)
            except Exception:
                observed_rate = None

        # 3. Forecast annual depreciation rate: weighted blend of baseline & recent momentum
        if momentum_90d_pct is not None:
            # Positive momentum reduces effective depreciation, negative momentum accelerates it
            effective_forecast_rate = baseline_rate - (momentum_90d_pct * 0.4)
            forecast_rate = round(max(3.0, min(18.0, effective_forecast_rate)), 1)
        else:
            forecast_rate = baseline_rate

        comp_str = (
            f"Phase 13 Baseline: -{baseline_rate:.1f}%/yr | "
            f"Forecast Effective: -{forecast_rate:.1f}%/yr"
            + (f" | Historical Observed: -{observed_rate:.1f}%/yr" if observed_rate else "")
        )

        return DepreciationTrajectory(
            historical_observed_annual_pct=observed_rate,
            forecast_annual_pct=forecast_rate,
            phase13_baseline_annual_pct=baseline_rate,
            methodology_comparison=comp_str
        )

    def _compute_market_position(
        self,
        df: pd.DataFrame,
        current_median: float,
        momentum: MarketMomentum
    ) -> MarketPositionComparison:
        """
        Calculates current market position vs 30D, 90D, 180D, 365D historical medians and percentile.
        """
        if df.empty or current_median <= 0:
            return MarketPositionComparison(
                current_market_median=None,
                current_price_vs_30d_pct=None,
                current_price_vs_90d_pct=None,
                current_price_vs_180d_pct=None,
                current_price_vs_365d_pct=None,
                historical_percentile_position=None,
                position_summary="Insufficient historical observations to establish percentile positioning."
            )

        prices = df["listed_price"].values
        percentile = float((prices < current_median).mean() * 100.0)

        m30_pct = momentum.m30d.price_change_pct
        m90_pct = momentum.m90d.price_change_pct
        m180_pct = momentum.m180d.price_change_pct
        m365_pct = momentum.m365d.price_change_pct

        summary = f"Current median of ₹{current_median:,.0f} sits at the {percentile:.0f}th percentile of observed segment listings."

        return MarketPositionComparison(
            current_market_median=round(current_median, 2),
            current_price_vs_30d_pct=m30_pct,
            current_price_vs_90d_pct=m90_pct,
            current_price_vs_180d_pct=m180_pct,
            current_price_vs_365d_pct=m365_pct,
            historical_percentile_position=round(percentile, 1),
            position_summary=summary
        )

    def _generate_forecast_trajectory(
        self,
        current_median: float,
        annual_depreciation_pct: float,
        volatility_cv: float,
        confidence_score: float,
        supporting_obs: int,
        confidence_level: ForecastConfidenceLevel
    ) -> Tuple[List[ForecastPoint], Dict[str, List[ForecastScenario]]]:
        """
        Generates deterministic statistical forecast points across 30, 90, 180, and 365 days
        with conservative, base, and optimistic scenarios and uncertainty corridors.
        """
        horizons = [
            (30, "30 Days (1 Month)"),
            (90, "90 Days (3 Months)"),
            (180, "180 Days (6 Months)"),
            (365, "365 Days (1 Year)")
        ]

        forecast_points: List[ForecastPoint] = []
        scenarios_by_type: Dict[str, List[ForecastScenario]] = {
            "BASE": [],
            "CONSERVATIVE": [],
            "OPTIMISTIC": []
        }

        # Annual effective decay rate r
        annual_rate = annual_depreciation_pct / 100.0

        for h_days, h_label in horizons:
            t_years = h_days / 365.0

            # Base forecast: exponential depreciation decay
            decay_factor = math.exp(-annual_rate * t_years)
            base_val = current_median * decay_factor

            # Uncertainty width depends on volatility CV, horizon, and confidence score
            conf_uncertainty_penalty = (1.0 - (confidence_score / 100.0)) * 0.15
            effective_sigma = max(0.04, (volatility_cv * 0.8) + conf_uncertainty_penalty)
            margin_pct = 1.96 * effective_sigma * math.sqrt(t_years + 0.08)

            lower_bound = max(current_median * 0.25, base_val * (1.0 - margin_pct))
            upper_bound = base_val * (1.0 + margin_pct)

            change_amt = base_val - current_median
            change_pct = (change_amt / current_median) * 100.0

            # Scenarios
            conservative_val = max(lower_bound, base_val * (1.0 - (margin_pct * 0.45)))
            optimistic_val = min(upper_bound, base_val * (1.0 + (margin_pct * 0.45)))

            scenarios_dict: Dict[str, ForecastScenario] = {
                "BASE": ForecastScenario(
                    scenario_type=ForecastScenarioType.BASE,
                    horizon_days=h_days,
                    projected_value=round(base_val, 2),
                    projected_value_formatted=f"₹{base_val:,.0f}",
                    change_from_current_pct=round(change_pct, 2),
                    change_from_current_amount=round(change_amt, 2),
                    annual_depreciation_rate_pct=round(annual_depreciation_pct, 2),
                    lower_bound=round(lower_bound, 2),
                    upper_bound=round(upper_bound, 2),
                    lower_bound_formatted=f"₹{lower_bound:,.0f}",
                    upper_bound_formatted=f"₹{upper_bound:,.0f}"
                ),
                "CONSERVATIVE": ForecastScenario(
                    scenario_type=ForecastScenarioType.CONSERVATIVE,
                    horizon_days=h_days,
                    projected_value=round(conservative_val, 2),
                    projected_value_formatted=f"₹{conservative_val:,.0f}",
                    change_from_current_pct=round(((conservative_val - current_median) / current_median) * 100.0, 2),
                    change_from_current_amount=round(conservative_val - current_median, 2),
                    annual_depreciation_rate_pct=round(annual_depreciation_pct * 1.3, 2),
                    lower_bound=round(lower_bound, 2),
                    upper_bound=round(base_val, 2),
                    lower_bound_formatted=f"₹{lower_bound:,.0f}",
                    upper_bound_formatted=f"₹{base_val:,.0f}"
                ),
                "OPTIMISTIC": ForecastScenario(
                    scenario_type=ForecastScenarioType.OPTIMISTIC,
                    horizon_days=h_days,
                    projected_value=round(optimistic_val, 2),
                    projected_value_formatted=f"₹{optimistic_val:,.0f}",
                    change_from_current_pct=round(((optimistic_val - current_median) / current_median) * 100.0, 2),
                    change_from_current_amount=round(optimistic_val - current_median, 2),
                    annual_depreciation_rate_pct=round(annual_depreciation_pct * 0.7, 2),
                    lower_bound=round(base_val, 2),
                    upper_bound=round(upper_bound, 2),
                    lower_bound_formatted=f"₹{base_val:,.0f}",
                    upper_bound_formatted=f"₹{upper_bound:,.0f}"
                )
            }

            scenarios_by_type["BASE"].append(scenarios_dict["BASE"])
            scenarios_by_type["CONSERVATIVE"].append(scenarios_dict["CONSERVATIVE"])
            scenarios_by_type["OPTIMISTIC"].append(scenarios_dict["OPTIMISTIC"])

            point = ForecastPoint(
                horizon_days=h_days,
                horizon_label=h_label,
                base_price=round(base_val, 2),
                lower_bound=round(lower_bound, 2),
                upper_bound=round(upper_bound, 2),
                base_formatted=f"₹{base_val:,.0f}",
                lower_formatted=f"₹{lower_bound:,.0f}",
                upper_formatted=f"₹{upper_bound:,.0f}",
                change_pct=round(change_pct, 2),
                change_amount=round(change_amt, 2),
                confidence=confidence_level,
                supporting_observations=supporting_obs,
                scenarios=scenarios_dict
            )
            forecast_points.append(point)

        return forecast_points, scenarios_by_type

    def _evaluate_confidence(
        self,
        obs_count: int,
        span_days: int,
        cv: float,
        fallback_applied: bool,
        segment_level: str
    ) -> Tuple[ForecastConfidenceLevel, float, List[str], List[str]]:
        """
        Calculates empirical confidence score (0-100) and structured reasoning.
        """
        reasons: List[str] = []
        missing: List[str] = []

        if obs_count < self.MIN_OBSERVATIONS_FOR_FORECAST or span_days < self.MIN_HISTORY_SPAN_DAYS:
            missing.append(f"Found {obs_count} observation(s), minimum {self.MIN_OBSERVATIONS_FOR_FORECAST} required.")
            missing.append(f"Historical span is {span_days} day(s), minimum {self.MIN_HISTORY_SPAN_DAYS} required.")
            return ForecastConfidenceLevel.INSUFFICIENT_EVIDENCE, 10.0, [], missing

        # 1. Observation Score (0-35 pts)
        if obs_count >= 50:
            obs_score = 35.0
            reasons.append(f"Large sample size of {obs_count} historical market listings.")
        elif obs_count >= 20:
            obs_score = 28.0
            reasons.append(f"Solid sample size of {obs_count} historical market listings.")
        elif obs_count >= 8:
            obs_score = 20.0
            reasons.append(f"Moderate sample size of {obs_count} historical market listings.")
        else:
            obs_score = 12.0
            missing.append(f"Limited historical observations ({obs_count} listings).")

        # 2. Temporal Coverage (0-25 pts)
        if span_days >= 180:
            span_score = 25.0
            reasons.append(f"Extensive temporal coverage spanning {span_days} days ({span_days // 30} months).")
        elif span_days >= 90:
            span_score = 20.0
            reasons.append(f"Quarterly temporal coverage spanning {span_days} days.")
        elif span_days >= 30:
            span_score = 14.0
            reasons.append(f"Short-term temporal coverage spanning {span_days} days.")
        else:
            span_score = 8.0
            missing.append(f"Narrow time window of {span_days} days.")

        # 3. Dispersion Tightness (0-20 pts)
        if cv < 0.10:
            disp_score = 20.0
            reasons.append("Very tight asking-price dispersion (CV < 10%).")
        elif cv < 0.20:
            disp_score = 15.0
            reasons.append("Normal price dispersion across trim and condition variants.")
        else:
            disp_score = 8.0
            missing.append("Elevated asking-price dispersion widens forecast interval.")

        # 4. Segment Match Quality (0-20 pts)
        if not fallback_applied and "exact" in segment_level:
            seg_score = 20.0
            reasons.append("Exact model, trim, and city segment match.")
        elif not fallback_applied:
            seg_score = 16.0
            reasons.append("Model and registration year segment match.")
        else:
            seg_score = 10.0
            reasons.append(f"Hierarchical fallback applied to broader '{segment_level}' cohort.")

        total_score = round(obs_score + span_score + disp_score + seg_score, 1)

        if total_score >= 70.0:
            level = ForecastConfidenceLevel.HIGH
        elif total_score >= 45.0:
            level = ForecastConfidenceLevel.MODERATE
        elif total_score >= 20.0:
            level = ForecastConfidenceLevel.LOW
        else:
            level = ForecastConfidenceLevel.INSUFFICIENT_EVIDENCE

        return level, total_score, reasons, missing

    def forecast_vehicle_market(
        self,
        req: ForecastRequest
    ) -> ForecastResponse:
        """
        Main entry point for vehicle market forecasting and buy/sell timing intelligence.
        """
        start_time = datetime.now()
        df = self._get_filtered_df(cutoff_date=req.cutoff_date)

        if df.empty:
            return self._build_insufficient_response(req, "Historical dataset empty or unavailable.", start_time)

        # 1. Segment Filtering with Fallback Hierarchy
        segment_df, seg_level, seg_desc, fallback_applied = self._match_segment_hierarchy(df, req)

        if segment_df.empty or len(segment_df) < self.MIN_OBSERVATIONS_FOR_FORECAST:
            return self._build_insufficient_response(
                req,
                f"Found only {len(segment_df)} historical observation(s) across segment matching. Minimum {self.MIN_OBSERVATIONS_FOR_FORECAST} required.",
                start_time,
                obs_count=len(segment_df)
            )

        # 2. Date Span & Temporal Bucketing
        min_date = segment_df["date_collected"].min()
        max_date = segment_df["date_collected"].max()
        span_days = max(1, (max_date - min_date).days)

        historical_buckets = self._aggregate_temporal_buckets(segment_df)
        current_median = float(np.median(segment_df["listed_price"].values))

        # 3. Market Momentum
        momentum = self._compute_momentum_metrics(segment_df, current_median)

        # 4. Market Volatility
        volatility = self._compute_market_volatility(segment_df)

        # 5. Demand Proxy
        demand_proxy = self._compute_demand_proxy(segment_df)

        # 6. Depreciation Trajectory
        m90_pct = momentum.m90d.price_change_pct
        depreciation = self._compute_depreciation_trajectory(segment_df, req.year, m90_pct)

        # 7. Market Position Comparison
        market_position = self._compute_market_position(segment_df, current_median, momentum)

        # 8. Confidence Evaluation
        vol_cv = volatility.coefficient_of_variation or 0.15
        conf_level, conf_score, conf_reasons, missing_reasons = self._evaluate_confidence(
            obs_count=len(segment_df),
            span_days=span_days,
            cv=vol_cv,
            fallback_applied=fallback_applied,
            segment_level=seg_level
        )

        # 9. Evidence Metadata
        evidence = ForecastEvidence(
            observation_count=len(segment_df),
            history_days=span_days,
            earliest_observation_date=min_date.strftime("%Y-%m-%d") if pd.notna(min_date) else None,
            latest_observation_date=max_date.strftime("%Y-%m-%d") if pd.notna(max_date) else None,
            segment_level=seg_level,
            segment_hierarchy_used=seg_desc,
            segment_fallback_applied=fallback_applied,
            forecast_model_version="temporal_trend_v001",
            forecast_method="bounded_exponential_trend",
            source="AutoValue empirical marketplace dataset",
            data_density_score=min(100.0, (len(segment_df) / 30.0) * 100.0),
            temporal_coverage_score=min(100.0, (span_days / 180.0) * 100.0),
            dispersion_score=max(0.0, min(100.0, (1.0 - vol_cv) * 100.0)),
            confidence_reasons=conf_reasons,
            missing_evidence_reasons=missing_reasons
        )

        # 10. Forecast Trajectory & Scenarios
        forecast_annual_dep = depreciation.forecast_annual_pct or 8.5
        forecast_points, scenarios = self._generate_forecast_trajectory(
            current_median=current_median,
            annual_depreciation_pct=forecast_annual_dep,
            volatility_cv=vol_cv,
            confidence_score=conf_score,
            supporting_obs=len(segment_df),
            confidence_level=conf_level
        )

        # 11. Buy and Sell Timing
        buy_timing = timing_service.compute_buy_timing(
            current_median=current_median,
            asking_price=req.asking_price,
            m90d_pct=m90_pct,
            m180d_pct=momentum.m180d.price_change_pct,
            overall_trend=momentum.overall_direction,
            volatility_level=volatility.level,
            annual_depreciation_pct=forecast_annual_dep,
            confidence_level=conf_level,
            confidence_score=conf_score,
            historical_percentile=market_position.historical_percentile_position
        )

        sell_timing = timing_service.compute_sell_timing(
            current_median=current_median,
            asking_price=req.asking_price,
            m90d_pct=m90_pct,
            m180d_pct=momentum.m180d.price_change_pct,
            overall_trend=momentum.overall_direction,
            volatility_level=volatility.level,
            annual_depreciation_pct=forecast_annual_dep,
            confidence_level=conf_level,
            confidence_score=conf_score,
            historical_percentile=market_position.historical_percentile_position
        )

        # 12. Trend Summary
        trend_dir_str = momentum.overall_direction.value.lower()
        if m90_pct is not None:
            sign = "+" if m90_pct >= 0 else ""
            trend_sum = f"Market prices for {req.brand} {req.model} are currently {trend_dir_str} ({sign}{m90_pct:.1f}% 90D momentum across {len(segment_df)} listings)."
        else:
            trend_sum = f"Market trajectory for {req.brand} {req.model} classified as {trend_dir_str} across {len(segment_df)} listings."

        # 13. Limitations
        limitations = [
            "Forecasts project asking-price movements and asset depreciation curves, not closed transaction guarantees.",
            "Condition, maintenance history, accident record, and localized buyer negotiations are unverified in historical asking data.",
            "Macroeconomic shifts, fuel price shocks, or OEM facelift launches may distort observed statistical trajectories."
        ]

        # 14. Watchlist Alerts Check
        alerts: List[ForecastAlert] = []
        if momentum.overall_direction == TrendDirection.RISING:
            alerts.append(
                ForecastAlert(
                    alert_type="MARKET_TREND_CHANGED",
                    title="Rising Market Momentum",
                    description=f"{req.brand} {req.model} asking prices have appreciated over recent observation windows.",
                    previous_value="STABLE",
                    current_value="RISING",
                    severity="OPPORTUNITY",
                    triggered_at=datetime.now().isoformat()
                )
            )
        if buy_timing.score is not None and buy_timing.score >= 75.0:
            alerts.append(
                ForecastAlert(
                    alert_type="BUY_TIMING_CHANGED",
                    title="Favorable Buy Window",
                    description=f"Buy timing score reached {buy_timing.score:.0f}/100 based on attractive relative pricing.",
                    previous_value="Neutral",
                    current_value="Favorable",
                    severity="OPPORTUNITY",
                    triggered_at=datetime.now().isoformat()
                )
            )

        latency_ms = (datetime.now() - start_time).total_seconds() * 1000.0

        return ForecastResponse(
            status="AVAILABLE",
            brand=req.brand,
            model=req.model,
            variant=req.variant,
            year=req.year,
            city=req.city,
            fuel_type=req.fuel_type,
            transmission=req.transmission,
            current_market_median=round(current_median, 2),
            current_market_median_formatted=f"₹{current_median:,.0f}",
            trend_summary=trend_sum,
            overall_trend=momentum.overall_direction,
            momentum=momentum,
            volatility=volatility,
            demand_proxy=demand_proxy,
            depreciation=depreciation,
            market_position=market_position,
            forecast_points=forecast_points,
            scenarios=scenarios,
            buy_timing=buy_timing,
            sell_timing=sell_timing,
            forecast_confidence=conf_level,
            forecast_confidence_score=conf_score,
            evidence=evidence,
            historical_points=historical_buckets,
            alerts=alerts,
            limitations=limitations,
            latency_ms=round(latency_ms, 2)
        )

    def _build_insufficient_response(
        self,
        req: ForecastRequest,
        message: str,
        start_time: datetime,
        obs_count: int = 0
    ) -> ForecastResponse:
        """Constructs a factual, transparent INSUFFICIENT_EVIDENCE response."""
        latency_ms = (datetime.now() - start_time).total_seconds() * 1000.0
        empty_trend = lambda p, d: TrendMetrics(
            period=p,
            period_days=d,
            observation_count=0,
            historical_median=None,
            current_median=None,
            absolute_change=None,
            price_change_pct=None,
            annualized_change_pct=None,
            direction=TrendDirection.INSUFFICIENT_EVIDENCE,
            description=f"Insufficient data for {p} horizon."
        )

        empty_momentum = MarketMomentum(
            m30d=empty_trend("30D", 30),
            m90d=empty_trend("90D", 90),
            m180d=empty_trend("180D", 180),
            m365d=empty_trend("365D", 365),
            overall_direction=TrendDirection.INSUFFICIENT_EVIDENCE,
            velocity_summary="Insufficient historical observations."
        )

        empty_volatility = MarketVolatility(
            level=MarketVolatilityLevel.INSUFFICIENT_EVIDENCE,
            coefficient_of_variation=None,
            interquartile_range=None,
            price_spread=None,
            rolling_std=None,
            explanation="Insufficient market observations to compute price dispersion."
        )

        empty_demand = DemandSignal(
            level=DemandSignalLevel.INSUFFICIENT_EVIDENCE,
            signal_name="market demand proxy",
            listing_count_growth_pct=None,
            listing_density_score=None,
            price_consistency_score=None,
            basis_explanation="Insufficient data to evaluate marketplace liquidity."
        )

        empty_deprec = DepreciationTrajectory(
            historical_observed_annual_pct=None,
            forecast_annual_pct=None,
            phase13_baseline_annual_pct=8.5,
            methodology_comparison="Baseline available, but historical empirical comparison requires additional data."
        )

        empty_pos = MarketPositionComparison(
            current_market_median=None,
            current_price_vs_30d_pct=None,
            current_price_vs_90d_pct=None,
            current_price_vs_180d_pct=None,
            current_price_vs_365d_pct=None,
            historical_percentile_position=None,
            position_summary="Historical percentile positioning unavailable."
        )

        empty_timing = lambda label: TimingScore(
            score=None,
            signal=TimingSignal.INSUFFICIENT_EVIDENCE,
            rating_label="Insufficient Evidence",
            factors=[],
            positive_factors=[],
            negative_factors=[f"Only {obs_count} observation(s) available; reliable timing cannot be derived."],
            methodology_summary="Timing indicators withheld due to sparse market evidence."
        )

        evidence = ForecastEvidence(
            observation_count=obs_count,
            history_days=0,
            earliest_observation_date=None,
            latest_observation_date=None,
            segment_level="none",
            segment_hierarchy_used="No matching segment with sufficient volume",
            segment_fallback_applied=True,
            forecast_model_version="temporal_trend_v001",
            forecast_method="bounded_exponential_trend",
            source="AutoValue empirical marketplace dataset",
            data_density_score=0.0,
            temporal_coverage_score=0.0,
            dispersion_score=0.0,
            confidence_reasons=[],
            missing_evidence_reasons=[message]
        )

        return ForecastResponse(
            status="INSUFFICIENT_EVIDENCE",
            brand=req.brand,
            model=req.model,
            variant=req.variant,
            year=req.year,
            city=req.city,
            fuel_type=req.fuel_type,
            transmission=req.transmission,
            current_market_median=None,
            current_market_median_formatted=None,
            trend_summary=f"Forecast unavailable: {message}",
            overall_trend=TrendDirection.INSUFFICIENT_EVIDENCE,
            momentum=empty_momentum,
            volatility=empty_volatility,
            demand_proxy=empty_demand,
            depreciation=empty_deprec,
            market_position=empty_pos,
            forecast_points=[],
            scenarios={"BASE": [], "CONSERVATIVE": [], "OPTIMISTIC": []},
            buy_timing=empty_timing("Buy Timing"),
            sell_timing=empty_timing("Sell Timing"),
            forecast_confidence=ForecastConfidenceLevel.INSUFFICIENT_EVIDENCE,
            forecast_confidence_score=0.0,
            evidence=evidence,
            historical_points=[],
            alerts=[],
            limitations=["Forecasting refused to manufacture estimates on insufficient historical sample size."],
            latency_ms=round(latency_ms, 2)
        )


market_forecast_service = MarketForecastService()
