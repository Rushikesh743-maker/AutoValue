from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, Text, Index
)
from ..db.base import Base


class CarListing(Base):
    __tablename__ = "car_listings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    listing_id = Column(String(128), index=True, nullable=False, doc="Source-specific listing identifier")
    source = Column(String(64), index=True, nullable=False, doc="Source marketplace name")
    listing_url = Column(String(1024), nullable=True, doc="URL of the vehicle listing")
    
    brand = Column(String(64), index=True, nullable=False)
    model = Column(String(64), index=True, nullable=False)
    variant = Column(String(128), nullable=True)
    year = Column(Integer, index=True, nullable=False)
    
    fuel_type = Column(String(32), nullable=True)
    transmission = Column(String(32), nullable=True)
    km_driven = Column(Integer, nullable=True)
    engine_cc = Column(Integer, nullable=True)
    mileage = Column(Float, nullable=True)
    owner_count = Column(Integer, nullable=True)
    
    city = Column(String(64), index=True, nullable=True)
    state = Column(String(64), nullable=True)
    seller_type = Column(String(64), nullable=True)
    
    listed_price = Column(Float, nullable=False, doc="Observed asking price in INR (NOT verified market transaction value)")
    date_collected = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Provenance & Duplicate Candidate Detection
    is_duplicate_candidate = Column(Boolean, default=False, nullable=False, index=True)
    duplicate_similarity = Column(Float, nullable=True)
    duplicate_of_id = Column(Integer, nullable=True)
    duplicate_notes = Column(String(512), nullable=True)
    raw_payload = Column(Text, nullable=True, doc="Preserved original JSON payload string from source")

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))



    __table_args__ = (
        Index("ix_listings_brand_model_year", "brand", "model", "year"),
        Index("ix_listings_brand_model_city", "brand", "model", "city"),
        Index("ix_listings_brand_model_date", "brand", "model", "date_collected"),
        Index("ix_listings_source_listing_id", "source", "listing_id"),
    )
