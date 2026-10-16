"""
AutoValue Vehicle Lifecycle & Ownership Decision Intelligence Domain Models (Phase 15).
Defines strongly typed schemas for unified vehicle lifecycle recommendations, multi-category
decision scoring, decision confidence, factor attribution, multi-horizon outlooks,
scenarios, replacement candidate ranking, break-even economics, and sensitivity analysis.
"""
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class LifecycleAction(str, Enum):
    BUY = "BUY"
    KEEP = "KEEP"
    SELL_NOW = "SELL_NOW"
    WAIT = "WAIT"
    REPLACE = "REPLACE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class DecisionConfidence(str, Enum):
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class FactorDirection(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


class LifecycleScenarioType(str, Enum):
    CONSERVATIVE = "CONSERVATIVE"
    BASE = "BASE"
    OPTIMISTIC = "OPTIMISTIC"


class DataIntegrityType(str, Enum):
    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    USER_DEFINED = "USER_DEFINED"
    DEFAULT_ASSUMPTION = "DEFAULT_ASSUMPTION"
    FORECAST = "FORECAST"


class DecisionMode(str, Enum):
    BUY = "BUY"
    OWNER = "OWNER"


class LifecycleDecisionRequest(BaseModel):
    """
    Unified input for lifecycle decision intelligence.
    Supports prospective buyers (Mode A) and current vehicle owners (Mode B).
    """
    mode: Optional[DecisionMode] = Field(
        default=None,
        description="Explicit decision mode: BUY or OWNER. Auto-detected if omitted."
    )
    brand: Optional[str] = Field(default=None, description="Vehicle brand name (e.g., Hyundai, Honda)")
    model: Optional[str] = Field(default=None, description="Vehicle model name (e.g., Creta, City)")
    variant: Optional[str] = Field(default=None, description="Trim or variant name")
    year: Optional[int] = Field(default=None, description="Manufacturing year")
    fuel_type: Optional[str] = Field(default="Petrol", description="Fuel type: Petrol, Diesel, CNG, Electric, Hybrid")
    transmission: Optional[str] = Field(default="Manual", description="Transmission: Manual or Automatic")
    km_driven: Optional[int] = Field(default=35000, ge=0, description="Current odometer reading in kilometers")
    city: Optional[str] = Field(default="Bengaluru", description="Geographic location / metro market")
    
    # Prospective Buyer Inputs (Mode A)
    asking_price: Optional[float] = Field(default=None, ge=0, description="Seller asking price in INR")
    
    # Current Owner Inputs (Mode B)
    current_market_value: Optional[float] = Field(default=None, ge=0, description="Estimated or user-specified current vehicle value in INR")
    purchase_price: Optional[float] = Field(default=None, ge=0, description="User's original purchase price in INR if known")
    ownership_years: Optional[int] = Field(default=None, ge=0, le=30, description="Number of years already owned")
    annual_km: Optional[int] = Field(default=12000, ge=0, le=200000, description="Annual driving distance in kilometers")
    
    # Evaluation Horizon and Overrides
    horizon_years: Optional[int] = Field(default=5, ge=1, le=10, description="Primary evaluation horizon in years (1, 3, or 5)")
    scenario: Optional[LifecycleScenarioType] = Field(default=LifecycleScenarioType.BASE, description="Economic/Market scenario assumption")
    fuel_price_override: Optional[float] = Field(default=None, ge=0, description="Custom fuel price in INR per unit")
    include_alternatives: Optional[bool] = Field(default=True, description="Whether to discover and evaluate replacement candidates")

    model_config = ConfigDict(extra="ignore")


class DecisionFactor(BaseModel):
    """
    Transparent explanatory factor attributing positive or negative influence to the recommendation.
    Every factor originates from an empirical metric.
    """
    category: str = Field(..., description="E.g., Market Position, Ownership Economics, Timing, Risk")
    factor_text: str = Field(..., description="Human-readable explanation of the factor")
    direction: FactorDirection = Field(..., description="POSITIVE, NEGATIVE, or NEUTRAL")
    metric_name: str = Field(..., description="Exact internal metric key")
    metric_value: Optional[Any] = Field(default=None, description="Empirical value of the metric")
    impact_weight: float = Field(..., ge=0.0, le=1.0, description="Relative influence on the category score")
    source_type: DataIntegrityType = Field(..., description="OBSERVED, DERIVED, USER_DEFINED, DEFAULT_ASSUMPTION, or FORECAST")


class DecisionCategoryScore(BaseModel):
    """
    Detailed breakdown of a single weighted decision pillar.
    """
    category_name: str = Field(..., description="Category label")
    score: float = Field(..., ge=0.0, le=100.0, description="Category raw score (0-100)")
    weight: float = Field(..., ge=0.0, le=1.0, description="Configured category weight fraction (e.g., 0.20)")
    contribution: float = Field(..., ge=0.0, le=100.0, description="Weighted contribution to overall score")
    reasoning: str = Field(..., description="Summary explanation of category score")


class DecisionScore(BaseModel):
    """
    Transparent multi-pillar decision score structure.
    """
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Aggregated decision score (0-100)")
    category_breakdown: List[DecisionCategoryScore] = Field(..., description="Breakdown of all 6 decision categories")
    decision_margin: float = Field(..., description="Score margin between winning action and next-best action")
    winning_action: LifecycleAction = Field(..., description="Best supported lifecycle action")
    secondary_action: Optional[LifecycleAction] = Field(default=None, description="Next-best alternate action")
    action_scores: Dict[str, float] = Field(default_factory=dict, description="Calculated scores for all evaluated actions")


class LifecycleHorizonOutlook(BaseModel):
    """
    Multi-year financial and depreciation projection for a specific horizon.
    """
    horizon_years: int = Field(..., description="Horizon in years (1, 3, or 5)")
    projected_resale_value: float = Field(..., description="Expected market value at horizon end in INR")
    projected_resale_formatted: str = Field(..., description="Formatted resale value")
    cumulative_depreciation: float = Field(..., description="Total depreciation loss over horizon in INR")
    cumulative_depreciation_formatted: str = Field(..., description="Formatted depreciation loss")
    cumulative_ownership_cost: float = Field(..., description="Fuel, maintenance, insurance, financing in INR")
    cumulative_ownership_formatted: str = Field(..., description="Formatted ownership cost")
    total_cost_of_ownership: float = Field(..., description="TCO = Depreciation + Operating Costs in INR")
    total_cost_of_ownership_formatted: str = Field(..., description="Formatted TCO")
    cost_per_km: float = Field(..., description="Effective cost per kilometer driven")
    cost_per_km_formatted: str = Field(..., description="Formatted cost per km")
    replacement_advantage: Optional[float] = Field(default=None, description="Advantage score vs average replacement candidate")


class ReplacementCandidate(BaseModel):
    """
    Evidence-supported alternative vehicle evaluated as a replacement.
    """
    id: str = Field(..., description="Unique vehicle listing / candidate identifier")
    brand: str = Field(..., description="Brand")
    model: str = Field(..., description="Model")
    variant: Optional[str] = Field(default=None, description="Variant")
    year: int = Field(..., description="Manufacturing year")
    fuel_type: Optional[str] = Field(default=None, description="Fuel type")
    transmission: Optional[str] = Field(default=None, description="Transmission")
    estimated_purchase_price: float = Field(..., description="Estimated acquisition price in INR")
    estimated_purchase_price_formatted: str = Field(..., description="Formatted purchase price")
    fair_value: float = Field(..., description="Estimated fair market value in INR")
    five_year_tco: float = Field(..., description="5-year projected total cost of ownership in INR")
    five_year_tco_formatted: str = Field(..., description="Formatted 5Y TCO")
    cost_per_km: float = Field(..., description="5-year cost per kilometer driven")
    projected_resale: float = Field(..., description="5-year projected resale value in INR")
    projected_resale_formatted: str = Field(..., description="Formatted resale value")
    risk_level: str = Field(..., description="LOW, MODERATE, or HIGH risk")
    risk_score: float = Field(..., description="Risk score 0-100")
    buy_timing_score: float = Field(..., description="Buy timing score 0-100")
    forecast_direction: str = Field(..., description="RISING, STABLE, or DECLINING")
    tco_savings_5y: float = Field(..., description="5-year TCO savings compared to current vehicle in INR (positive is savings)")
    tco_savings_5y_formatted: str = Field(..., description="Formatted 5Y savings")
    resale_advantage: float = Field(..., description="Difference in projected resale value in INR")
    replacement_advantage_score: float = Field(..., ge=0.0, le=100.0, description="Overall replacement advantage score (0-100)")
    break_even_months: Optional[float] = Field(default=None, description="Months of ownership to recover acquisition cost differential")
    recommendation_reason: str = Field(..., description="Specific economic rationale for or against this alternative")


class LifecycleScenario(BaseModel):
    """
    Lifecycle outcome under a specific market/economic scenario.
    """
    scenario_type: LifecycleScenarioType = Field(..., description="CONSERVATIVE, BASE, or OPTIMISTIC")
    action: LifecycleAction = Field(..., description="Recommended action under this scenario")
    decision_score: float = Field(..., ge=0.0, le=100.0, description="Decision score under this scenario")
    five_year_tco: float = Field(..., description="5-year TCO in INR under scenario")
    five_year_tco_formatted: str = Field(..., description="Formatted TCO")
    projected_resale: float = Field(..., description="5-year resale value in INR under scenario")
    projected_resale_formatted: str = Field(..., description="Formatted resale value")
    key_assumption: str = Field(..., description="Key driving assumption of this scenario")


class DecisionSensitivity(BaseModel):
    """
    Boundary condition showing what parameter change would trigger a recommendation pivot.
    """
    variable_name: str = Field(..., description="Input variable being tested (e.g. Purchase Price, Annual Mileage)")
    current_value: Any = Field(..., description="Current value or baseline")
    threshold_value: Any = Field(..., description="Value at which the recommendation changes")
    action_before: LifecycleAction = Field(..., description="Action with current value")
    action_after: LifecycleAction = Field(..., description="Action if threshold is crossed")
    sensitivity_description: str = Field(..., description="Plain-language description of the sensitivity")


class LifecycleDecisionResponse(BaseModel):
    """
    Complete, authoritative decision intelligence response for a vehicle lifecycle query.
    """
    decision_version: str = Field(default="lifecycle_v001", description="Engine schema/rules version")
    timestamp: str = Field(..., description="ISO 8601 generation timestamp")
    mode: str = Field(..., description="Evaluation mode: BUY or OWNER")
    vehicle_summary: Dict[str, Any] = Field(..., description="Vehicle specifications and baseline metrics")
    recommended_action: LifecycleAction = Field(..., description="Primary recommended action")
    decision_score: DecisionScore = Field(..., description="Multi-category transparent score breakdown")
    confidence: DecisionConfidence = Field(..., description="Confidence level: HIGH, MODERATE, LOW, or INSUFFICIENT_EVIDENCE")
    confidence_score: float = Field(..., ge=0.0, le=100.0, description="Numerical confidence metric (0-100)")
    confidence_reasons: List[str] = Field(default_factory=list, description="Specific empirical factors determining confidence")
    alternative_actions: List[Dict[str, Any]] = Field(default_factory=list, description="Ranked list of other considered actions with scores")
    positive_factors: List[DecisionFactor] = Field(default_factory=list, description="Factors supporting the primary recommendation")
    negative_factors: List[DecisionFactor] = Field(default_factory=list, description="Risk factors or headwinds")
    economic_reasoning: str = Field(..., description="Financial / TCO / depreciation assessment")
    market_reasoning: str = Field(..., description="Market momentum / liquidity / pricing position assessment")
    ownership_reasoning: str = Field(..., description="Vehicle age / operating cost / usage outlook")
    risk_considerations: List[str] = Field(default_factory=list, description="Identified vehicle, market, and liquidity risks")
    forecast_considerations: List[str] = Field(default_factory=list, description="Future price trajectories and momentum considerations")
    resale_considerations: List[str] = Field(default_factory=list, description="Projected residual retention and depreciation windows")
    tco_considerations: List[str] = Field(default_factory=list, description="Operating cost breakdown and efficiency observations")
    horizon_outlooks: List[LifecycleHorizonOutlook] = Field(default_factory=list, description="1Y, 3Y, 5Y financial and residual outlooks")
    scenarios: List[LifecycleScenario] = Field(default_factory=list, description="Conservative, Base, and Optimistic scenario sensitivity")
    replacement_candidates: List[ReplacementCandidate] = Field(default_factory=list, description="Ranked alternative replacement options")
    best_replacement_candidate: Optional[ReplacementCandidate] = Field(default=None, description="Top-ranked replacement alternative if any")
    decision_sensitivities: List[DecisionSensitivity] = Field(default_factory=list, description="Critical pivot thresholds for key variables")
    missing_data: List[str] = Field(default_factory=list, description="List of missing empirical evidence if any")
    assumptions: List[str] = Field(default_factory=list, description="Explicit default and model assumptions")
    limitations: List[str] = Field(default_factory=list, description="System boundaries and disclaimer notices")
    audit_trail: Dict[str, Any] = Field(default_factory=dict, description="Audit trace for deterministic verification")


class LifecycleScenarioRequest(BaseModel):
    """
    Simulation request to test what-if parameter changes on lifecycle recommendations.
    """
    base_request: LifecycleDecisionRequest = Field(..., description="Base vehicle request")
    annual_km_override: Optional[int] = Field(default=None, ge=0, le=200000, description="What-if annual mileage")
    wait_months: Optional[int] = Field(default=0, ge=0, le=36, description="What-if wait duration in months")
    purchase_price_override: Optional[float] = Field(default=None, ge=0, description="What-if purchase/asking price")
    market_shift_pct: Optional[float] = Field(default=0.0, ge=-50.0, le=50.0, description="What-if market price percentage shift")
    replacement_candidate_id: Optional[str] = Field(default=None, description="Alternative vehicle ID to simulate replacement against")


class LifecycleCompareRequest(BaseModel):
    """
    Request to compare lifecycle economics of current vehicle vs up to 5 replacement candidates.
    """
    current_vehicle: LifecycleDecisionRequest = Field(..., description="Current or primary vehicle")
    replacement_vehicles: List[LifecycleDecisionRequest] = Field(..., min_length=1, max_length=5, description="Up to 5 comparison candidates")


class LifecycleCompareItem(BaseModel):
    """
    Individual vehicle record in multi-vehicle lifecycle comparison.
    """
    vehicle_label: str
    brand: str
    model: str
    year: int
    fuel_type: Optional[str]
    purchase_price: Optional[float]
    purchase_price_formatted: str
    fair_value: float
    fair_value_formatted: str
    five_year_tco: float
    five_year_tco_formatted: str
    cost_per_km: float
    cost_per_km_formatted: str
    projected_resale: float
    projected_resale_formatted: str
    risk_score: float
    risk_level: str
    buy_timing_score: float
    sell_timing_score: float
    market_forecast: str
    replacement_advantage: Optional[float] = None
    lifecycle_action: LifecycleAction
    decision_score: float


class LifecycleCompareResponse(BaseModel):
    """
    Comparison matrix of lifecycle economics across multiple vehicles.
    """
    items: List[LifecycleCompareItem] = Field(..., description="Comparison items")
    best_overall_vehicle: str = Field(..., description="Vehicle with best overall lifecycle score")
    comparison_matrix: Dict[str, Any] = Field(default_factory=dict, description="Aggregated comparison summary")
    summary_reasoning: str = Field(..., description="Executive comparative analysis")


class BatchLifecycleRequest(BaseModel):
    """
    Batch request for lifecycle decisions (bounded to max 10 vehicles).
    """
    vehicles: List[LifecycleDecisionRequest] = Field(..., min_length=1, max_length=10, description="List of 1-10 vehicle requests")


class BatchLifecycleResponse(BaseModel):
    """
    Batch response for multiple vehicle lifecycle decisions.
    """
    total_vehicles: int
    results: List[LifecycleDecisionResponse]
