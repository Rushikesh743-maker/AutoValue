"""
Pydantic contracts for valuation request, comparable vehicles, market intelligence,
prediction uncertainty, and SHAP explainability.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ValuationRequestSchema(BaseModel):
    """
    Input schema for requesting a vehicle valuation.
    """
    brand: str = Field(..., min_length=1, description="Vehicle manufacturer make (e.g. 'Hyundai', 'Honda')")
    model: str = Field(..., min_length=1, description="Vehicle model name (e.g. 'Creta', 'City')")
    variant: Optional[str] = Field(None, description="Trim or variant designation (e.g. 'SX', 'V CVT')")
    year: int = Field(..., ge=1990, le=2030, description="Manufacturing / registration year")
    fuel_type: str = Field(..., min_length=1, description="Fuel type: 'Petrol', 'Diesel', 'CNG', 'Electric', 'Hybrid'")
    transmission: str = Field(..., min_length=1, description="Transmission: 'Manual' or 'Automatic'")
    km_driven: int = Field(..., ge=0, le=1000000, description="Odometer reading in kilometers")
    city: str = Field(..., min_length=1, description="City location of the vehicle")

    # Optional enrichment attributes
    engine_cc: Optional[int] = Field(None, ge=500, le=10000, description="Engine displacement in cc")
    mileage: Optional[float] = Field(None, ge=0.0, le=100.0, description="Fuel efficiency in kmpl")
    owner_count: Optional[int] = Field(1, ge=1, le=10, description="Number of previous owners")
    seller_type: Optional[str] = Field("Individual", description="Seller type: 'Individual', 'Dealer', 'Certified Dealer'")
    asking_price: Optional[float] = Field(None, gt=0, description="Optional user asking price in INR for market position evaluation")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "brand": "Hyundai",
                "model": "Creta",
                "variant": "1.5 CRDi SX",
                "year": 2021,
                "fuel_type": "Diesel",
                "transmission": "Manual",
                "km_driven": 38000,
                "city": "Bengaluru",
                "asking_price": 1350000.0
            }
        }
    )


class ModelInterval(BaseModel):
    interval_low: float
    interval_high: float
    interval_low_formatted: str
    interval_high_formatted: str
    confidence_level: float
    method: str


class ValuationDetails(BaseModel):
    estimated_value: float
    estimated_value_formatted: str
    range_low: Optional[float] = None
    range_high: Optional[float] = None
    range_low_formatted: Optional[str] = None
    range_high_formatted: Optional[str] = None
    range_method: str
    combination_method: str
    model_interval: Optional[ModelInterval] = None


class MarketStatistics(BaseModel):
    median: Optional[float] = None
    mean: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    p25: Optional[float] = None
    p75: Optional[float] = None
    comparable_count: int
    price_dispersion_std: Optional[float] = None


class ComparableCarItem(BaseModel):
    listing_id: str
    brand: str
    model: str
    variant: Optional[str] = None
    year: int
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    km_driven: Optional[int] = None
    city: Optional[str] = None
    state: Optional[str] = None
    listed_price: float
    listed_price_formatted: str
    source: str
    similarity_score: float
    similarity_percentage: str
    date_collected: Optional[str] = None


class SourceAnalysisItem(BaseModel):
    source: str
    listing_count: int
    median_price: float
    mean_price: float
    min_price: float
    max_price: float


class SHAPExplanationItem(BaseModel):
    feature: str
    impact_inr: float
    direction: str  # "increases_price" or "decreases_price"
    human_readable_text: str


class MarketPosition(BaseModel):
    asking_price: float
    position: str  # "Below observed comparable range", "Within observed comparable range", "Above observed comparable range"
    difference_from_median: float
    percentage_difference_from_median: float


class ModelEvidence(BaseModel):
    selected_model: str
    dataset_records: int
    test_mae: Optional[float] = None
    test_r2: Optional[float] = None
    evaluation_strategy: str


class ValuationResponse(BaseModel):
    model_version: str
    dataset_version: str
    valuation: ValuationDetails
    market: MarketStatistics
    model_evidence: Optional[ModelEvidence] = None
    comparables: List[ComparableCarItem]
    source_analysis: List[SourceAnalysisItem]
    explanation: List[SHAPExplanationItem]
    market_position: Optional[MarketPosition] = None
    transparency_notice: str
    request_id: Optional[str] = None
    latency_ms: Optional[float] = None
