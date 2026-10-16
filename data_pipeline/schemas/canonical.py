"""
Canonical schema definitions for used car listings across all data sources.
Serves as the contract between collectors, cleaners, normalizers, and the database.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


class RawCarListing(BaseModel):
    """
    Represents raw, unstructured listing data extracted directly from a source
    before cleaning and normalization.
    """
    raw_id: Optional[str] = Field(None, description="Raw source-specific identifier")
    source: str = Field(..., description="Identifier of the source platform")
    source_url: Optional[str] = Field(None, description="URL where listing was located")
    raw_title: Optional[str] = Field(None, description="Full raw title text of the listing")
    raw_price: Optional[str] = Field(None, description="Raw price string e.g. '₹ 12.5 Lakh'")
    raw_km: Optional[str] = Field(None, description="Raw km string e.g. '45,000 km'")
    raw_year: Optional[str] = Field(None, description="Raw year string e.g. '2019'")
    raw_fuel: Optional[str] = Field(None, description="Raw fuel type e.g. 'Diesel'")
    raw_transmission: Optional[str] = Field(None, description="Raw transmission string e.g. 'Automatic'")
    raw_location: Optional[str] = Field(None, description="Raw location string e.g. 'Bangalore, Karnataka'")
    raw_seller: Optional[str] = Field(None, description="Raw seller type or name e.g. 'Dealer' / 'Individual'")
    raw_specs: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional unparsed key-value specs")
    date_collected: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when record was captured")


class CanonicalCarListing(BaseModel):
    """
    The canonical standardized used-car listing representation.
    All data cleaners and normalizers must produce records adhering to this schema.
    """
    listing_id: str = Field(..., description="Unique source-scoped or global listing identifier")
    source: str = Field(..., description="Source platform name e.g. 'spinny', 'cars24', 'carwale'")
    listing_url: Optional[str] = Field(None, description="URL of the vehicle listing where legitimately available")
    
    brand: str = Field(..., min_length=1, description="Standardized brand/make name (e.g. 'Hyundai', 'Honda')")
    model: str = Field(..., min_length=1, description="Standardized model name (e.g. 'Creta', 'City')")
    variant: Optional[str] = Field(None, description="Standardized trim/variant (e.g. '1.5 CRDi SX', 'V CVT')")
    year: int = Field(..., ge=1990, le=2030, description="Manufacturing / registration year")
    
    fuel_type: Optional[str] = Field(None, description="Standardized fuel type: 'Petrol', 'Diesel', 'CNG', 'Electric', 'Hybrid', 'LPG'")
    transmission: Optional[str] = Field(None, description="Standardized transmission: 'Manual', 'Automatic'")
    km_driven: Optional[int] = Field(None, ge=0, le=1000000, description="Odometer reading in kilometers")
    engine_cc: Optional[int] = Field(None, ge=500, le=10000, description="Engine displacement in cubic centimeters")
    mileage: Optional[float] = Field(None, ge=0.0, le=100.0, description="Fuel efficiency in kmpl or km/kg")
    owner_count: Optional[int] = Field(None, ge=1, le=10, description="Number of previous owners")
    
    city: Optional[str] = Field(None, description="Standardized city name")
    state: Optional[str] = Field(None, description="Standardized state name")
    seller_type: Optional[str] = Field(None, description="Seller classification: 'Individual', 'Dealer', 'Certified Dealer'")
    
    listed_price: float = Field(..., gt=0, description="Observed asking / listing price in INR. (Asking price, NOT transaction price)")
    date_collected: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when the listing was observed")

    @field_validator("listed_price")
    @classmethod
    def validate_price_bounds(cls, v: float) -> float:
        if v < 10000:
            raise ValueError("listed_price must be at least ₹10,000")
        if v > 100000000: # 10 Crore upper bound for sanity
            raise ValueError("listed_price exceeds realistic upper bound ₹10 Cr")
        return round(v, 2)

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "listing_id": "cars24-delhi-109482",
                "source": "cars24",
                "listing_url": "https://example.com/listing/109482",
                "brand": "Hyundai",
                "model": "Creta",
                "variant": "1.5 CRDi SX (O)",
                "year": 2021,
                "fuel_type": "Diesel",
                "transmission": "Automatic",
                "km_driven": 35000,
                "engine_cc": 1493,
                "mileage": 18.5,
                "owner_count": 1,
                "city": "New Delhi",
                "state": "Delhi",
                "seller_type": "Certified Dealer",
                "listed_price": 1450000.0,
                "date_collected": "2024-01-15T10:30:00"
            }
        }
    )

