"""
AutoValue Market Forecasting and Buy/Sell Timing Domain Models (Phase 14).
Defines strongly typed schemas for temporal market aggregation, price momentum,
volatility, depreciation trajectories, statistical forecasting with uncertainty corridors,
evidence validation, and decision-support timing indicators.
"""
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class TrendDirection(str, Enum):
    RISING = "RISING"
    STABLE = "STABLE"
    DECLINING = "DECLINING"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ForecastConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class TimingSignal(str, Enum):
    FAVORABLE = "FAVORABLE"
    NEUTRAL = "NEUTRAL"
    UNFAVORABLE = "UNFAVORABLE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ForecastScenarioType(str, Enum):
    CONSERVATIVE = "CONSERVATIVE"
    BASE = "BASE"
    OPTIMISTIC = "OPTIMISTIC"


class MarketVolatilityLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class DemandSignalLevel(str, Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ForecastRequest(BaseModel):
    """Vehicle specification for market forecasting and timing intelligence."""
    brand: str
    model: str
    variant: Optional[str] = None
    year: int
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    km_driven: Optional[int] = None
    city: Optional[str] = None
    asking_price: Optional[float] = None
    horizon_days: Optional[int] = Field(default=365, description="Primary forecast horizon (30, 90, 180, 365 days)")
    cutoff_date: Optional[str] = Field(default=None, description="Optional ISO cutoff date for backtesting without future leakage")

    model_config = ConfigDict(extra="ignore")


class HistoricalMarketPoint(BaseModel):
    """Aggregated temporal market snapshot for a discrete time window."""
    period_start: str
    period_end: str
    period_label: str
    observation_count: int
    median_price: float
    mean_price: float
    p25_price: float
    p75_price: float
    min_price: float
    max_price: float
    dispersion_cv: float = Field(..., description="Coefficient of variation (std / mean)")
    median_formatted: str


class TrendMetrics(BaseModel):
    """Calculated market movement metrics across a specific historical horizon."""
    period: str = Field(..., description="E.g. '30D', '90D', '180D', '365D'")
    period_days: int
    observation_count: int
    historical_median: Optional[float] = None
    current_median: Optional[float] = None
    absolute_change: Optional[float] = None
    price_change_pct: Optional[float] = None
    annualized_change_pct: Optional[float] = None
    direction: TrendDirection
    description: str


class MarketMomentum(BaseModel):
    """Multi-horizon historical price velocity and overall directional momentum."""
    m30d: TrendMetrics
    m90d: TrendMetrics
    m180d: TrendMetrics
    m365d: TrendMetrics
    overall_direction: TrendDirection
    velocity_summary: str


class MarketVolatility(BaseModel):
    """Market price dispersion metrics calculated from empirical listings."""
    level: MarketVolatilityLevel
    coefficient_of_variation: Optional[float] = None
    interquartile_range: Optional[float] = None
    price_spread: Optional[float] = None
    rolling_std: Optional[float] = None
    explanation: str


class DemandSignal(BaseModel):
    """Observable marketplace proxy for demand intensity (not actual buyer transactions)."""
    level: DemandSignalLevel
    signal_name: str = "market demand proxy"
    listing_count_growth_pct: Optional[float] = None
    listing_density_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    price_consistency_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    basis_explanation: str


class DepreciationTrajectory(BaseModel):
    """Comparison between observed market depreciation, model forecast, and baseline."""
    historical_observed_annual_pct: Optional[float] = None
    forecast_annual_pct: Optional[float] = None
    phase13_baseline_annual_pct: float
    methodology_comparison: str


class MarketPositionComparison(BaseModel):
    """Current vehicle market median compared to historical time horizons and percentile."""
    current_market_median: Optional[float] = None
    current_price_vs_30d_pct: Optional[float] = None
    current_price_vs_90d_pct: Optional[float] = None
    current_price_vs_180d_pct: Optional[float] = None
    current_price_vs_365d_pct: Optional[float] = None
    historical_percentile_position: Optional[float] = Field(None, ge=0.0, le=100.0)
    position_summary: str


class ForecastScenario(BaseModel):
    """Deterministic forecast scenario (Conservative, Base, Optimistic)."""
    scenario_type: ForecastScenarioType
    horizon_days: int
    projected_value: float
    projected_value_formatted: str
    change_from_current_pct: float
    change_from_current_amount: float
    annual_depreciation_rate_pct: float
    lower_bound: float
    upper_bound: float
    lower_bound_formatted: str
    upper_bound_formatted: str


class ForecastPoint(BaseModel):
    """Forecast trajectory point at a specific horizon with uncertainty bounds."""
    horizon_days: int
    horizon_label: str
    base_price: float
    lower_bound: float
    upper_bound: float
    base_formatted: str
    lower_formatted: str
    upper_formatted: str
    change_pct: float
    change_amount: float
    confidence: ForecastConfidenceLevel
    supporting_observations: int
    scenarios: Dict[str, ForecastScenario]


class TimingFactor(BaseModel):
    """Individual evidence-grounded factor influencing buy/sell timing."""
    factor_type: str = Field(..., description="'POSITIVE', 'NEGATIVE', or 'NEUTRAL'")
    title: str
    description: str
    impact_weight: float = Field(..., ge=0.0, le=1.0)


class TimingScore(BaseModel):
    """Decision-support market timing indicator (0-100). Not financial/investment advice."""
    score: Optional[float] = Field(None, ge=0.0, le=100.0)
    signal: TimingSignal
    rating_label: str
    factors: List[TimingFactor]
    positive_factors: List[str]
    negative_factors: List[str]
    methodology_summary: str
    disclaimer: str = "Timing indicators reflect empirical market momentum and observed asking prices. They do not constitute financial advice or guarantees."


class ForecastEvidence(BaseModel):
    """Audit provenance and evidence strength supporting the forecast."""
    observation_count: int
    history_days: int
    earliest_observation_date: Optional[str] = None
    latest_observation_date: Optional[str] = None
    segment_level: str
    segment_hierarchy_used: str
    segment_fallback_applied: bool
    forecast_model_version: str = "temporal_trend_v001"
    forecast_method: str = "bounded_exponential_trend"
    source: str = "AutoValue empirical marketplace dataset"
    data_density_score: float = Field(..., ge=0.0, le=100.0)
    temporal_coverage_score: float = Field(..., ge=0.0, le=100.0)
    dispersion_score: float = Field(..., ge=0.0, le=100.0)
    confidence_reasons: List[str]
    missing_evidence_reasons: List[str] = Field(default_factory=list)


class ForecastAlert(BaseModel):
    """Market timing or forecast movement alert."""
    alert_type: str = Field(..., description="E.g. 'MARKET_TREND_CHANGED', 'BUY_TIMING_CHANGED', 'PRICE_MOMENTUM_CHANGED'")
    title: str
    description: str
    previous_value: Optional[str] = None
    current_value: Optional[str] = None
    severity: str = Field(default="INFO", description="'INFO', 'WARNING', or 'OPPORTUNITY'")
    triggered_at: str


class ForecastResponse(BaseModel):
    """Complete vehicle market forecasting and buy/sell timing intelligence payload."""
    status: str = Field(..., description="'AVAILABLE' or 'INSUFFICIENT_EVIDENCE'")
    brand: str
    model: str
    variant: Optional[str] = None
    year: int
    city: Optional[str] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    current_market_median: Optional[float] = None
    current_market_median_formatted: Optional[str] = None
    trend_summary: str
    overall_trend: TrendDirection
    momentum: MarketMomentum
    volatility: MarketVolatility
    demand_proxy: DemandSignal
    depreciation: DepreciationTrajectory
    market_position: MarketPositionComparison
    forecast_points: List[ForecastPoint]
    scenarios: Dict[str, List[ForecastScenario]]
    buy_timing: TimingScore
    sell_timing: TimingScore
    forecast_confidence: ForecastConfidenceLevel
    forecast_confidence_score: float = Field(..., ge=0.0, le=100.0)
    evidence: ForecastEvidence
    historical_points: List[HistoricalMarketPoint]
    alerts: List[ForecastAlert]
    limitations: List[str]
    disclaimer: str = (
        "Market forecasts and timing scores are analytical indicators derived from historical listing asking prices. "
        "They represent statistical trend estimates, not guaranteed future asset values or investment advice."
    )
    request_id: Optional[str] = None
    latency_ms: Optional[float] = None


class BatchForecastRequest(BaseModel):
    """Batch vehicle forecasting request for up to 10 vehicles."""
    vehicles: List[ForecastRequest] = Field(..., min_length=1, max_length=10)


class BatchForecastResponse(BaseModel):
    """Batch vehicle forecasting response container."""
    items: List[ForecastResponse]
    count: int
    processing_time_ms: float
