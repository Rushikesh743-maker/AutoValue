"""
Pydantic contracts for bookmarked/saved vehicles.
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class SavedVehicleCreateRequest(BaseModel):
    brand: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    variant: Optional[str] = Field(None)
    year: int = Field(..., ge=1990, le=2030)
    fuel_type: Optional[str] = Field(None)
    transmission: Optional[str] = Field(None)
    km_driven: int = Field(..., ge=0, le=1000000)
    city: str = Field(..., min_length=1)
    notes: Optional[str] = Field(None, max_length=256)


class SavedVehicleResponse(BaseModel):
    id: str
    brand: str
    model: str
    variant: Optional[str] = None
    year: int
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    km_driven: int
    city: str
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SavedVehicleListResponse(BaseModel):
    items: List[SavedVehicleResponse]
    total: int
