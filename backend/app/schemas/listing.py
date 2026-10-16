from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ListingBase(BaseModel):
    listing_id: str
    source: str
    listing_url: Optional[str] = None
    brand: str
    model: str
    variant: Optional[str] = None
    year: int
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    km_driven: Optional[int] = None
    engine_cc: Optional[int] = None
    mileage: Optional[float] = None
    owner_count: Optional[int] = None
    city: Optional[str] = None
    state: Optional[str] = None
    seller_type: Optional[str] = None
    listed_price: float
    date_collected: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ListingCreate(ListingBase):
    pass


class ListingRead(ListingBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

