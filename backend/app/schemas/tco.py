"""
Pydantic contracts for Total Cost of Ownership (TCO) & Resale Intelligence Engine (Phase 13).
Defines strongly-typed schemas for ownership assumptions, purchase price modes,
cost breakdowns, year-by-year projections, scenarios, sensitivity analysis, and multi-vehicle comparison.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from backend.app.schemas.valuation import ValuationRequestSchema


class TCOAssumptions(BaseModel):
    """
    Configurable assumptions for ownership economics.
    """
    annual_km: int = Field(12000, ge=0, le=100000, description="Projected annual mileage in kilometers")
    ownership_years: int = Field(5, ge=1, le=10, description="Planned ownership duration in years (1 to 10)")
    purchase_price_mode: str = Field(
        "FAIR_VALUE",
        description="'FAIR_VALUE', 'ASKING_PRICE', or 'CUSTOM'"
    )
    custom_purchase_price: Optional[float] = Field(None, gt=0, description="Custom purchase price if mode is CUSTOM")
    fuel_price: Optional[float] = Field(None, gt=0, description="Fuel price (INR per L or per kWh for EV)")
    fuel_efficiency: Optional[float] = Field(None, gt=0, description="Fuel economy (km/L, km/kg, or kWh/100km for EV)")
    annual_insurance_rate: float = Field(0.03, ge=0.005, le=0.15, description="Annual insurance percentage of vehicle value")
    custom_annual_insurance: Optional[float] = Field(None, ge=0, description="Fixed annual insurance premium override")
    annual_maintenance: Optional[float] = Field(None, ge=0, description="Estimated annual maintenance and service budget")
    upfront_tax_registration: float = Field(0.0, ge=0, description="One-time upfront registration/transfer fees")
    other_annual_cost: float = Field(0.0, ge=0, description="Other annual recurring expenses (parking, tolls, warranties)")
    scenario: str = Field("BASE", description="'CONSERVATIVE', 'BASE', 'OPTIMISTIC', or 'CUSTOM'")


class TCORequest(BaseModel):
    """
    Request model for TCO calculation on a vehicle configuration.
    """
    vehicle: ValuationRequestSchema
    assumptions: Optional[TCOAssumptions] = None


class TCOPurchaseInfo(BaseModel):
    """
    Purchase price context and mode applied in the TCO model.
    """
    mode: str = Field(..., description="'FAIR_VALUE', 'ASKING_PRICE', or 'CUSTOM'")
    price: float = Field(..., ge=0, description="Effective purchase price in INR")
    source: str = Field(..., description="Descriptive label of purchase price baseline")


class TCOCostBreakdown(BaseModel):
    """
    Comprehensive gross and net ownership economics breakdown.
    """
    purchase_cost: float = Field(..., ge=0)
    fuel_cost: float = Field(..., ge=0)
    insurance_cost: float = Field(..., ge=0)
    maintenance_cost: float = Field(..., ge=0)
    taxes_and_fees: float = Field(default=0.0, ge=0)
    other_costs: float = Field(default=0.0, ge=0)
    gross_cost: float = Field(..., ge=0, description="Total cash expenditure without resale recovery")
    estimated_resale: float = Field(..., ge=0, description="Projected resale value at end of horizon")
    net_tco: float = Field(..., description="Net ownership cost (Gross Expenditure - Resale Recovery)")
    annual_cost: float = Field(..., description="Net ownership cost per year")
    cost_per_km: float = Field(..., description="Net ownership cost per kilometer")
    total_projected_km: int = Field(default=0, ge=0, description="Total projected kilometers across ownership horizon")


class ResaleProjection(BaseModel):
    """
    Future vehicle value projection with uncertainty bounds and empirical confidence.
    """
    estimated_resale_value: float = Field(..., ge=0)
    lower_bound: float = Field(..., ge=0)
    upper_bound: float = Field(..., ge=0)
    confidence: str = Field(..., description="'VERY_LOW', 'LOW', 'MODERATE', 'HIGH', 'VERY_HIGH', or 'INSUFFICIENT_EVIDENCE'")
    projected_retention_pct: float = Field(..., description="Percentage of purchase price retained")
    annual_depreciation_rate: float = Field(..., description="Estimated average annual compound depreciation rate")
    methodology: str = Field(..., description="Explanation of depreciation model and market anchoring")


class YearlyProjectionItem(BaseModel):
    """
    Year-by-year financial progression timeline.
    """
    year: int = Field(..., ge=1, le=10)
    vehicle_age: int = Field(..., ge=0)
    cumulative_km: int = Field(..., ge=0)
    annual_fuel_cost: float = Field(..., ge=0)
    annual_insurance_cost: float = Field(..., ge=0)
    annual_maintenance_cost: float = Field(..., ge=0)
    annual_running_cost: float = Field(..., ge=0)
    cumulative_expenditure: float = Field(..., ge=0)
    projected_resale_value: float = Field(..., ge=0)
    projected_resale_low: float = Field(..., ge=0)
    projected_resale_high: float = Field(..., ge=0)
    net_cost_to_date: float = Field(..., description="Cumulative Outflow - Resale at Year t")
    cost_per_km_to_date: Optional[float] = Field(default=None, description="Net cost per km at Year t")
    resale_value_formatted: Optional[str] = Field(default=None, description="Formatted resale value")
    resale_low_formatted: Optional[str] = Field(default=None, description="Formatted lower resale bound")
    resale_high_formatted: Optional[str] = Field(default=None, description="Formatted upper resale bound")
    cumulative_gross_formatted: Optional[str] = Field(default=None, description="Formatted cumulative gross cash outflow")
    net_cost_to_date_formatted: Optional[str] = Field(default=None, description="Formatted net cost to date")


class TCOSensitivityItem(BaseModel):
    """
    Single-variable sensitivity impact on net TCO.
    """
    variable: str
    change_description: str
    delta_tco: float
    percentage_impact: float
    new_net_tco: float


class ScenarioSummary(BaseModel):
    """
    Scenario comparison metrics.
    """
    name: str
    gross_cost: float
    estimated_resale: float
    net_tco: float
    annual_cost: float
    cost_per_km: float


class TCOResponse(BaseModel):
    """
    Complete Total Cost of Ownership and Resale Intelligence response.
    """
    vehicle: Dict[str, Any]
    purchase: TCOPurchaseInfo
    assumptions: Dict[str, Any]
    assumptions_provenance: Dict[str, str] = Field(
        ...,
        description="Source categorization for every assumption: OBSERVED_MARKET, USER_INPUT, DEFAULT_CONFIG, or DERIVED"
    )
    ownership: TCOCostBreakdown
    resale: ResaleProjection
    yearly_projection: List[YearlyProjectionItem]
    scenarios: Dict[str, ScenarioSummary]
    sensitivity: List[TCOSensitivityItem]
    disclaimer: str = Field(
        default="Ownership costs and projected resale values are statistical estimates based on observable market evidence and stated assumptions. "
                "They do not constitute guaranteed future prices, quotes, or binding financial advice."
    )


class TCOScenarioRequest(BaseModel):
    """
    Request model for running custom or named ownership scenarios.
    """
    vehicle: ValuationRequestSchema
    scenario_name: str = Field("BASE", description="'CONSERVATIVE', 'BASE', 'OPTIMISTIC', or 'CUSTOM'")
    assumptions: Optional[TCOAssumptions] = None


class TCOCompareItem(BaseModel):
    """
    Compact vehicle TCO summary for comparison matrices.
    """
    vehicle_identifier: str
    brand: str
    model: str
    year: int
    fuel_type: str
    purchase_price: float
    gross_cost: float
    estimated_resale: float
    net_tco: float
    annual_cost: float
    cost_per_km: float
    resale_confidence: str


class TCOCompareRequest(BaseModel):
    """
    Batch comparison request for up to 10 vehicles.
    """
    vehicles: List[ValuationRequestSchema]
    shared_assumptions: Optional[TCOAssumptions] = None


class TCOCompareResponse(BaseModel):
    """
    Comparative ownership economics across candidate vehicles.
    """
    total_vehicles: int
    horizon_years: int
    results: List[TCOCompareItem]
    break_even_analysis: Optional[Dict[str, Any]] = None
    disclaimer: str = Field(
        default="Comparison economics reflect stated annual usage and empirical depreciation models. Not guaranteed future resale quotes."
    )
