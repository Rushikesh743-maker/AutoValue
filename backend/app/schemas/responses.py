"""
General API response envelopes and placeholder schemas.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "autovalue-api"


class UnimplementedResponse(BaseModel):
    status: str = "not_implemented"
    phase: str = "Phase 1: Project Foundation"
    message: str


class ValuationRequest(BaseModel):
    brand: str
    model: str
    variant: Optional[str] = None
    year: int
    km_driven: int
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    city: Optional[str] = None
    owner_count: Optional[int] = 1
