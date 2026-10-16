"""
GarageVehicle ORM model representing personalized vehicle ownership and portfolio assets (Phase 16).
Supports owned, considering, sold, and tracked vehicles with economic profiles and usage parameters.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship

from ..db.base import Base


class GarageVehicle(Base):
    __tablename__ = "garage_vehicles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    valuation_id = Column(String(36), ForeignKey("saved_valuations.id", ondelete="SET NULL"), index=True, nullable=True)

    # Vehicle Specifications
    brand = Column(String(64), nullable=False)
    model = Column(String(64), nullable=False)
    variant = Column(String(128), nullable=True)
    year = Column(Integer, nullable=False)
    fuel_type = Column(String(32), nullable=True, default="Petrol")
    transmission = Column(String(32), nullable=True, default="Manual")
    city = Column(String(64), nullable=True, default="Bengaluru")
    nickname = Column(String(64), nullable=True)

    # Ownership & Economic Metadata
    ownership_status = Column(String(32), nullable=False, default="OWNED", index=True)  # OWNED, CONSIDERING, SOLD, WATCHING
    purchase_price = Column(Float, nullable=True)
    purchase_date = Column(DateTime, nullable=True)
    current_odometer = Column(Integer, nullable=True, default=35000)
    annual_km = Column(Integer, nullable=True, default=12000)
    ownership_purpose = Column(String(64), nullable=True)  # Daily Commute, Family / Weekend, Highway Cruiser, Secondary Utility
    notes = Column(String(512), nullable=True)

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="garage_vehicles")
    valuation = relationship("SavedValuation", foreign_keys=[valuation_id])

    __table_args__ = (
        Index("ix_garage_vehicles_user_status", "user_id", "ownership_status"),
        Index("ix_garage_vehicles_user_created", "user_id", "created_at"),
    )
