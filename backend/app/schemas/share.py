"""
Pydantic contracts for public shareable valuation reports and token management.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ShareTokenResponse(BaseModel):
    share_token: str
    share_url: str
    is_active: bool
    created_at: datetime
    view_count: int


class SharedValuationResponse(BaseModel):
    """
    Public, sanitized valuation report view.
    Explicitly excludes user identifiers, emails, passwords, and sensitive internal telemetry.
    """
    share_token: str
    created_at: datetime
    brand: str
    model: str
    variant: Optional[str] = None
    year: int
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    km_driven: int
    city: str
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
    
    # Detailed components
    payload: Optional[Dict[str, Any]] = None
    disclaimer: str = (
        "This is an empirical machine-learning estimate based on historical asking prices. "
        "It does not constitute a certified appraisal or guaranteed transaction price."
    )

    model_config = ConfigDict(from_attributes=True)
