"""
Pydantic contracts for saving, retrieving, and listing valuation snapshots.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from .valuation import ValuationRequestSchema, ValuationResponse


class SaveValuationRequest(BaseModel):
    """
    Request payload to save a valuation snapshot.
    Can accept either the raw request + response payload or individual parameters.
    """
    vehicle: ValuationRequestSchema
    valuation_result: ValuationResponse
    notes: Optional[str] = Field(None, max_length=512, description="Optional user notes")


class SavedValuationSummary(BaseModel):
    id: str
    request_id: Optional[str] = None
    created_at: datetime
    brand: str
    model: str
    variant: Optional[str] = None
    year: int
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    km_driven: int
    city: str
    engine_cc: Optional[int] = None
    mileage: Optional[float] = None
    owner_count: Optional[int] = None
    seller_type: Optional[str] = None
    asking_price: Optional[float] = None

    estimated_value: float
    range_low: Optional[float] = None
    range_high: Optional[float] = None
    model_interval_low: Optional[float] = None
    model_interval_high: Optional[float] = None
    market_median: Optional[float] = None
    comparable_count: int
    model_version: str
    dataset_version: str
    notes: Optional[str] = None
    is_shared: bool = False
    share_token: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SavedValuationDetail(SavedValuationSummary):
    payload: Optional[Dict[str, Any]] = None


class ValuationHistoryResponse(BaseModel):
    items: List[SavedValuationSummary]
    total: int
    page: int
    page_size: int
    total_pages: int
