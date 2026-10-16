"""
SavedVehicle ORM model representing bookmarked vehicle configurations.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Index, UniqueConstraint
)

from sqlalchemy.orm import relationship

from ..db.base import Base


class SavedVehicle(Base):
    __tablename__ = "saved_vehicles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)

    brand = Column(String(64), nullable=False)
    model = Column(String(64), nullable=False)
    variant = Column(String(128), nullable=True)
    year = Column(Integer, nullable=False)
    fuel_type = Column(String(32), nullable=True)
    transmission = Column(String(32), nullable=True)
    km_driven = Column(Integer, nullable=False)
    city = Column(String(64), nullable=False)
    notes = Column(String(256), nullable=True)
    watch_status = Column(String(32), nullable=True, default="watching", index=True)
    last_checked_at = Column(DateTime, nullable=True)
    last_estimated_value = Column(Float, nullable=True)
    previous_estimated_value = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    user = relationship("User", back_populates="saved_vehicles")

    __table_args__ = (
        UniqueConstraint(
            "user_id", "brand", "model", "variant", "year", "fuel_type", "transmission", "km_driven", "city",
            name="uq_user_saved_vehicle_fingerprint"
        ),
        Index("ix_saved_vehicles_user_created", "user_id", "created_at"),
    )
