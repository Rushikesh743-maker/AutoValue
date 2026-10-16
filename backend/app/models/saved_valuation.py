"""
SavedValuation ORM model representing immutable snapshots of completed vehicle valuations.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, ForeignKey, Index
)
from sqlalchemy.orm import relationship

from ..db.base import Base


class SavedValuation(Base):
    __tablename__ = "saved_valuations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    request_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    # Vehicle snapshot
    brand = Column(String(64), index=True, nullable=False)
    model = Column(String(64), index=True, nullable=False)
    variant = Column(String(128), nullable=True)
    year = Column(Integer, nullable=False)
    fuel_type = Column(String(32), nullable=True)
    transmission = Column(String(32), nullable=True)
    km_driven = Column(Integer, nullable=False)
    city = Column(String(64), nullable=False)
    engine_cc = Column(Integer, nullable=True)
    mileage = Column(Float, nullable=True)
    owner_count = Column(Integer, nullable=True)
    seller_type = Column(String(64), nullable=True)
    asking_price = Column(Float, nullable=True)

    # Valuation snapshot (immutable calculation result)
    estimated_value = Column(Float, nullable=False)
    range_low = Column(Float, nullable=True)
    range_high = Column(Float, nullable=True)
    model_interval_low = Column(Float, nullable=True)
    model_interval_high = Column(Float, nullable=True)
    market_median = Column(Float, nullable=True)
    comparable_count = Column(Integer, nullable=False, default=0)
    model_version = Column(String(32), nullable=False)
    dataset_version = Column(String(32), nullable=False)

    # Rich snapshot payload preserving SHAP values, comparables, and market positions
    payload_json = Column(Text, nullable=True)
    notes = Column(String(512), nullable=True)

    # Relationships
    user = relationship("User", back_populates="saved_valuations")
    share_token = relationship("ShareToken", back_populates="valuation", uselist=False, cascade="all, delete-orphan", passive_deletes=True)

    __table_args__ = (
        Index("ix_saved_valuations_user_created", "user_id", "created_at"),
        Index("ix_saved_valuations_brand_model", "brand", "model"),
    )
