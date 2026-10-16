"""
Pydantic contracts for vehicle and valuation comparison (Enhanced for Phase 11).
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ComparisonRequest(BaseModel):
    valuation_ids: Optional[List[str]] = Field(None, max_length=3, description="List of 2 to 3 saved valuation IDs to compare")
    vehicle_ids: Optional[List[str]] = Field(None, max_length=3, description="List of 2 to 3 saved vehicle IDs to compare")


class VehicleComparisonItem(BaseModel):
    id: str
    source_type: str  # "saved_valuation" or "saved_vehicle"
    brand: str
    model: str
    variant: Optional[str] = None
    year: int
    km_driven: int
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    engine_cc: Optional[int] = None
    city: str
    asking_price: Optional[float] = None
    
    # Valuation parameters
    estimated_value: Optional[float] = None
    range_low: Optional[float] = None
    range_high: Optional[float] = None
    market_median: Optional[float] = None
    market_p25: Optional[float] = None
    market_p75: Optional[float] = None
    market_position: Optional[str] = None
    uncertainty_width: Optional[float] = None
    evidence_strength: Optional[str] = None
    model_version: Optional[str] = None
    dataset_version: Optional[str] = None


class EmpiricalDeltaItem(BaseModel):
    metric: str
    description: str
    baseline_vehicle_id: str
    target_vehicle_id: str
    numerical_delta: Optional[float] = None


class ComparisonResponse(BaseModel):
    vehicles: List[VehicleComparisonItem]
    empirical_differences: List[EmpiricalDeltaItem]
    factual_summary: str
