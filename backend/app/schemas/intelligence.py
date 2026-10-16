"""
AutoValue Decision Intelligence Pydantic Schemas (Phase 11).
Defines strongly typed contracts for Smart Deal Analysis, Negotiation Intelligence,
Value-For-Money Scoring, Data Confidence & Disclaimers, What-If Simulator,
Alternative Vehicle Discovery, Market Timing, and Valuation Watchlists.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from .valuation import (
    ValuationRequestSchema,
    ValuationDetails,
    MarketStatistics,
    ComparableCarItem,
    SHAPExplanationItem
)


class DealAnalysis(BaseModel):
    """
    Evidence-grounded deal classification and mathematical gap metrics.
    """
    asking_price: Optional[float] = None
    estimated_value: float
    market_median: Optional[float] = None
    market_range: Optional[Dict[str, Optional[float]]] = None
    asking_price_vs_ml: Optional[float] = None
    asking_price_vs_market_median: Optional[float] = None
    asking_price_vs_p25: Optional[float] = None
    asking_price_vs_p75: Optional[float] = None
    percentage_difference_from_ml: Optional[float] = None
    percentage_difference_from_market_median: Optional[float] = None
    comparable_support_score: float = Field(..., ge=0.0, le=1.0)
    evidence_strength: str = Field(..., description="'HIGH', 'MEDIUM', 'LOW', or 'INSUFFICIENT'")
    price_position: str = Field(
        ...,
        description="'BELOW_P25', 'BETWEEN_P25_AND_MEDIAN', 'BETWEEN_MEDIAN_AND_P75', 'ABOVE_P75', or 'UNSPECIFIED'"
    )
    classification: str = Field(
        ...,
        description="'SIGNIFICANTLY_BELOW_MARKET', 'BELOW_MARKET', 'FAIRLY_PRICED', 'ABOVE_MARKET', 'SIGNIFICANTLY_ABOVE_MARKET', or 'INSUFFICIENT_EVIDENCE'"
    )
    explanation: str
    thresholds_used: Dict[str, Any]


class NegotiationAnalysis(BaseModel):
    """
    Evidence-supported negotiation targets and talking points.
    """
    observed_market_median: Optional[float] = None
    observed_market_p25: Optional[float] = None
    observed_market_p75: Optional[float] = None
    model_estimate: float
    model_interval_low: Optional[float] = None
    model_interval_high: Optional[float] = None
    asking_price: Optional[float] = None
    negotiation_gap: Optional[float] = None
    evidence_supported_target: float
    conservative_target: float
    aggressive_target: float
    negotiation_range_formatted: str
    buyer_leverage: str
    talking_points: List[str]
    disclaimer: str


class ValueScore(BaseModel):
    """
    Transparent, formulaic Value-for-Money breakdown.
    """
    price_value_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    mileage_value_score: float = Field(..., ge=0.0, le=100.0)
    age_value_score: float = Field(..., ge=0.0, le=100.0)
    market_support_score: float = Field(..., ge=0.0, le=100.0)
    evidence_confidence: str
    overall_value_score: float = Field(..., ge=0.0, le=100.0)
    rating_label: str
    score_breakdown: Dict[str, Any]
    disclaimer: str


class DataConfidence(BaseModel):
    """
    Statistical confidence indicators and physical condition limitation warnings.
    """
    market_confidence: str
    data_completeness: float = Field(..., ge=0.0, le=1.0)
    comparable_quality: str
    model_confidence: str
    condition_unknown_warning: bool = True
    unverified_factors: List[str]
    disclaimer_text: str


class ScenarioRequest(BaseModel):
    """
    Simulation request against a base vehicle configuration.
    """
    base_vehicle: ValuationRequestSchema
    changes: Dict[str, Any] = Field(..., description="Dict of modified fields (e.g. {'km_driven': 60000})")


class ScenarioResponse(BaseModel):
    """
    Quantified outcome of running active model inference on modified parameters.
    """
    base_estimate: float
    scenario_estimate: float
    estimated_change: float
    percentage_change: float
    changed_features: List[str]
    explanation: List[str]
    simulation_note: str


class AlternativeVehicleQuery(BaseModel):
    """
    Search parameters for finding evidence-supported vehicle alternatives.
    """
    target_budget: Optional[float] = Field(None, gt=0)
    budget_min: Optional[float] = Field(None, ge=0)
    budget_max: Optional[float] = Field(None, gt=0)
    brand: Optional[str] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    city: Optional[str] = None
    min_year: Optional[int] = Field(None, ge=1990, le=2030)
    max_km: Optional[int] = Field(None, ge=0)
    limit: int = Field(6, ge=1, le=20)


class AlternativeVehicleItem(BaseModel):
    """
    An alternative vehicle listing candidate with transparent ranking metrics.
    """
    listing_id: str
    brand: str
    model: str
    variant: Optional[str] = None
    year: int
    km_driven: int
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    city: Optional[str] = None
    listed_price: float
    listed_price_formatted: str
    estimated_value: Optional[float] = None
    price_proximity_score: float
    age_score: float
    mileage_score: float
    overall_match_score: float
    match_reasons: List[str]


class AlternativeVehicleResponse(BaseModel):
    """
    Results list of closest evidence-supported vehicle alternatives.
    """
    query: Dict[str, Any]
    count: int
    results: List[AlternativeVehicleItem]
    ranking_methodology: str
    disclaimer: str


class MarketTiming(BaseModel):
    """
    Observed historical trajectory and momentum intelligence.
    """
    brand: str
    model: str
    city: Optional[str] = None
    recent_median: Optional[float] = None
    previous_median: Optional[float] = None
    percentage_movement: Optional[float] = None
    direction: str = Field(..., description="'RISING', 'STABLE', 'DECLINING', or 'INSUFFICIENT_DATA'")
    observation_count: int
    evidence_strength: str
    summary: str
    disclaimer: str


class WatchlistItem(BaseModel):
    """
    User vehicle bookmark with valuation tracking and status.
    """
    id: str
    user_id: str
    brand: str
    model: str
    variant: Optional[str] = None
    year: int
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    km_driven: int
    city: str
    notes: Optional[str] = None
    watch_status: Optional[str] = "watching"
    last_checked_at: Optional[str] = None
    last_estimated_value: Optional[float] = None
    previous_estimated_value: Optional[float] = None
    value_change: Optional[float] = None
    value_change_percentage: Optional[float] = None
    market_median: Optional[float] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class WatchlistStatusUpdate(BaseModel):
    """
    Update request for watch_status field.
    """
    watch_status: str = Field(..., pattern="^(watching|interested_selling|interested_buying)$")


class DecisionIntelligenceResponse(BaseModel):
    """
    Complete composite decision intelligence packet for a vehicle.
    """
    request_id: str
    vehicle: Dict[str, Any]
    valuation: ValuationDetails
    market_statistics: MarketStatistics
    deal_analysis: DealAnalysis
    negotiation: NegotiationAnalysis
    value_score: ValueScore
    confidence: DataConfidence
    market_timing: MarketTiming
    shap_explanations: List[SHAPExplanationItem]
    comparables: List[ComparableCarItem]
    risk: Optional[Dict[str, Any]] = None
    tco: Optional[Dict[str, Any]] = None
    forecast: Optional[Dict[str, Any]] = None
