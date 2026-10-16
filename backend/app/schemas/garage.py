"""
Pydantic contracts for Garage & Portfolio Intelligence Engine (Phase 16).
Provides strongly typed schemas for garage vehicle CRUD, portfolio economic aggregation,
sell-first and keep-first rankings, replacement opportunities, garage efficiency scoring,
redundancy analysis, scenario simulations, and multi-vehicle garage comparisons.
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class OwnershipStatus(str, Enum):
    OWNED = "OWNED"
    CONSIDERING = "CONSIDERING"
    SOLD = "SOLD"
    WATCHING = "WATCHING"


class UtilizationClass(str, Enum):
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class PortfolioAction(str, Enum):
    KEEP_GARAGE = "KEEP_GARAGE"
    SELL_VEHICLE = "SELL_VEHICLE"
    REPLACE_VEHICLE = "REPLACE_VEHICLE"
    CONSOLIDATE = "CONSOLIDATE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class PortfolioConfidence(str, Enum):
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class GarageScenarioActionType(str, Enum):
    SELL = "SELL"
    KEEP = "KEEP"
    REPLACE = "REPLACE"
    ADD = "ADD"
    UPDATE_MILEAGE = "UPDATE_MILEAGE"


class GarageVehicleCreate(BaseModel):
    brand: str = Field(..., description="Vehicle brand name (e.g., Hyundai, Honda)")
    model: str = Field(..., description="Vehicle model name (e.g., Creta, City)")
    variant: Optional[str] = Field(default=None, description="Trim or variant name")
    year: int = Field(..., ge=1990, le=2030, description="Manufacturing year")
    fuel_type: Optional[str] = Field(default="Petrol", description="Fuel type: Petrol, Diesel, CNG, Electric, Hybrid")
    transmission: Optional[str] = Field(default="Manual", description="Transmission: Manual or Automatic")
    city: Optional[str] = Field(default="Bengaluru", description="Geographic location / metro market")
    nickname: Optional[str] = Field(default=None, description="Custom vehicle nickname")
    ownership_status: Optional[OwnershipStatus] = Field(default=OwnershipStatus.OWNED, description="Ownership state")
    purchase_price: Optional[float] = Field(default=None, ge=0, description="Acquisition purchase price in INR")
    purchase_date: Optional[datetime] = Field(default=None, description="Acquisition date")
    current_odometer: Optional[int] = Field(default=35000, ge=0, description="Current odometer reading in km")
    annual_km: Optional[int] = Field(default=12000, ge=0, le=200000, description="Projected annual mileage in km")
    ownership_purpose: Optional[str] = Field(default=None, description="Primary purpose: Daily Commute, Family / Weekend, Highway Cruiser, Secondary Utility")
    notes: Optional[str] = Field(default=None, max_length=512, description="Custom user notes")
    valuation_id: Optional[str] = Field(default=None, description="Linked SavedValuation identifier if available")

    model_config = ConfigDict(extra="ignore")


class GarageVehicleUpdate(BaseModel):
    brand: Optional[str] = None
    model: Optional[str] = None
    variant: Optional[str] = None
    year: Optional[int] = Field(default=None, ge=1990, le=2030)
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    city: Optional[str] = None
    nickname: Optional[str] = None
    ownership_status: Optional[OwnershipStatus] = None
    purchase_price: Optional[float] = Field(default=None, ge=0)
    purchase_date: Optional[datetime] = None
    current_odometer: Optional[int] = Field(default=None, ge=0)
    annual_km: Optional[int] = Field(default=None, ge=0, le=200000)
    ownership_purpose: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=512)
    valuation_id: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class GarageVehicleResponse(BaseModel):
    id: str
    user_id: str
    valuation_id: Optional[str] = None
    brand: str
    model: str
    variant: Optional[str] = None
    year: int
    fuel_type: Optional[str] = "Petrol"
    transmission: Optional[str] = "Manual"
    city: Optional[str] = "Bengaluru"
    nickname: Optional[str] = None
    ownership_status: OwnershipStatus
    purchase_price: Optional[float] = None
    purchase_date: Optional[datetime] = None
    current_odometer: Optional[int] = 35000
    annual_km: Optional[int] = 12000
    ownership_purpose: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class GarageVehicleSnapshot(BaseModel):
    vehicle: GarageVehicleResponse
    current_estimated_value: Optional[float] = None
    current_estimated_value_formatted: str
    market_median: Optional[float] = None
    five_year_tco: Optional[float] = None
    five_year_tco_formatted: str
    annual_ownership_cost: Optional[float] = None
    annual_ownership_cost_formatted: str
    cost_per_km: Optional[float] = None
    cost_per_km_formatted: str
    projected_resale_5y: Optional[float] = None
    projected_resale_formatted: str
    five_year_depreciation: Optional[float] = None
    five_year_depreciation_formatted: str
    annual_depreciation_rate: Optional[float] = None
    risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_level: str
    market_trend: str
    momentum_90d: float
    buy_timing_score: float
    sell_timing_score: float
    lifecycle_action: str
    lifecycle_score: float
    confidence: str
    utilization_class: UtilizationClass


class GarageSummary(BaseModel):
    total_vehicles: int
    owned_vehicles: int
    owned_vehicles_count: Optional[int] = None
    considering_vehicles: int
    watching_vehicles: int
    sold_vehicles: int
    total_current_value: float
    total_current_value_formatted: str
    total_annual_cost: float
    total_annual_cost_formatted: str
    total_5y_tco: float
    total_5y_tco_formatted: str
    total_projected_5y_resale: float
    total_projected_5y_resale_formatted: str
    average_cost_per_km: float
    average_cost_per_km_formatted: str
    weighted_average_risk: float
    weighted_market_momentum: float
    overall_market_direction: str
    risk_level_label: Optional[str] = None
    excluded_vehicles_count: int = 0
    excluded_vehicle_reasons: List[str] = Field(default_factory=list)


class GarageEfficiencyCategory(BaseModel):
    category_name: str
    score: float = Field(..., ge=0.0, le=100.0)
    weight: float = Field(..., ge=0.0, le=1.0)
    contribution: float = Field(..., ge=0.0, le=100.0)
    reasoning: str


class GarageEfficiencyScore(BaseModel):
    overall_score: float = Field(..., ge=0.0, le=100.0)
    categories: List[GarageEfficiencyCategory]
    summary_reasoning: str
    rating_label: Optional[str] = None


class VehicleRankingItem(BaseModel):
    vehicle_id: str
    vehicle_label: str
    metric_value: float
    metric_formatted: str
    rank: int


class VehicleRankings(BaseModel):
    most_expensive_annual: List[VehicleRankingItem]
    highest_5y_tco: List[VehicleRankingItem]
    highest_cost_per_km: List[VehicleRankingItem]
    highest_depreciation: List[VehicleRankingItem]
    highest_risk: List[VehicleRankingItem]


class SellFirstItem(BaseModel):
    vehicle_id: str
    vehicle_label: str
    vehicle_display_name: Optional[str] = None
    sell_priority_score: float = Field(..., ge=0.0, le=100.0)
    current_value: Optional[float] = None
    current_value_formatted: str
    sell_timing_score: float
    depreciation_rate: Optional[float] = None
    projected_resale_decline_pct: Optional[float] = None
    annual_cost: Optional[float] = None
    annual_cost_formatted: str
    annual_ownership_cost_formatted: Optional[str] = None
    factors: List[str] = Field(default_factory=list)
    reasons: Optional[List[str]] = None
    recommendation: str


class KeepFirstItem(BaseModel):
    vehicle_id: str
    vehicle_label: str
    vehicle_display_name: Optional[str] = None
    keep_priority_score: float = Field(..., ge=0.0, le=100.0)
    five_year_tco: Optional[float] = None
    five_year_tco_formatted: str
    risk_score: float
    risk_level: Optional[str] = None
    market_trend: str
    cost_per_km: Optional[float] = None
    cost_per_km_formatted: str
    factors: List[str] = Field(default_factory=list)
    reasons: Optional[List[str]] = None


class ReplacementOpportunityItem(BaseModel):
    current_vehicle_id: str
    current_vehicle_label: str
    current_vehicle_name: Optional[str] = None
    candidate_brand: str
    candidate_model: str
    candidate_year: int
    candidate_replacement_name: Optional[str] = None
    candidate_replacement_brand: Optional[str] = None
    candidate_replacement_model: Optional[str] = None
    estimated_purchase_diff: float
    purchase_difference_formatted: Optional[str] = None
    tco_savings_5y: float
    tco_savings_5y_formatted: str
    tco_difference_formatted: Optional[str] = None
    resale_advantage: float
    resale_difference_formatted: Optional[str] = None
    risk_difference: float
    break_even_months: Optional[float] = None
    replacement_score: float = Field(..., ge=0.0, le=100.0)
    replacement_opportunity_score: Optional[float] = None
    recommendation_reason: str
    recommendation_rationale: Optional[str] = None


class VehicleRedundancyItem(BaseModel):
    vehicle_a_id: str
    vehicle_a_label: str
    vehicle_a_name: Optional[str] = None
    vehicle_b_id: str
    vehicle_b_label: str
    vehicle_b_name: Optional[str] = None
    redundancy_level: str  # HIGH, MODERATE, LOW, NONE, INSUFFICIENT_EVIDENCE
    overlap_reasons: List[str] = Field(default_factory=list)
    overlap_factors: Optional[List[str]] = None
    potential_annual_savings: float
    potential_annual_savings_formatted: str
    recommendation: Optional[str] = None


class GarageRecommendation(BaseModel):
    action: PortfolioAction
    confidence: PortfolioConfidence
    confidence_score: float = Field(..., ge=0.0, le=100.0)
    reasons: List[str] = Field(default_factory=list)
    economic_impact_summary: str
    headline: Optional[str] = None
    primary_reasons: Optional[List[str]] = None
    caution_factors: Optional[List[str]] = None
    suggested_next_steps: Optional[List[str]] = None
    portfolio_action_score: Optional[float] = None


class GarageIntelligenceResponse(BaseModel):
    summary: GarageSummary
    efficiency: GarageEfficiencyScore
    efficiency_score: Optional[GarageEfficiencyScore] = None
    recommendation: GarageRecommendation
    sell_first_ranking: List[SellFirstItem]
    keep_first_ranking: List[KeepFirstItem]
    replacement_opportunities: List[ReplacementOpportunityItem]
    redundancies: List[VehicleRedundancyItem]
    redundancy_analysis: Optional[List[VehicleRedundancyItem]] = None
    rankings: VehicleRankings
    vehicle_rankings: Optional[VehicleRankings] = None
    vehicle_snapshots: List[GarageVehicleSnapshot]
    snapshots: Optional[List[GarageVehicleSnapshot]] = None
    limitations: List[str] = Field(default_factory=list)
    provenance: Dict[str, str] = Field(default_factory=dict)
    disclaimer: Optional[str] = None


class GarageScenarioVehicleAction(BaseModel):
    vehicle_id: Optional[str] = Field(default=None, description="Target garage vehicle ID for SELL, KEEP, REPLACE, UPDATE_MILEAGE")
    action_type: GarageScenarioActionType
    replacement_vehicle: Optional[GarageVehicleCreate] = Field(default=None, description="New vehicle specs if action is REPLACE or ADD")
    annual_km_override: Optional[int] = Field(default=None, ge=0, le=200000, description="New annual driving mileage if updating")


class GarageScenarioRequest(BaseModel):
    actions: List[GarageScenarioVehicleAction] = Field(..., max_length=10, description="List of portfolio transformation actions (max 10)")


class GarageScenarioResponse(BaseModel):
    baseline_summary: GarageSummary
    scenario_summary: GarageSummary
    delta_annual_cost: float
    delta_annual_cost_formatted: str
    delta_5y_tco: float
    delta_5y_tco_formatted: str
    delta_efficiency_score: float
    break_even_months: Optional[float] = None
    executive_summary: str
    scenario_vehicles: List[GarageVehicleSnapshot]


class GarageCompareRequest(BaseModel):
    vehicle_ids: List[str] = Field(..., min_length=2, max_length=10, description="List of garage vehicle IDs to compare (2-10)")


class GarageCompareResponse(BaseModel):
    total_vehicles: int
    vehicles: List[GarageVehicleSnapshot]
    economic_rankings: Dict[str, List[str]]
    best_keep_vehicle_id: Optional[str] = None
    best_sell_vehicle_id: Optional[str] = None
    summary: str
