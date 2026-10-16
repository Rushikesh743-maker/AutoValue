"""
User ORM model representing registered system accounts.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Index
from sqlalchemy.orm import relationship

from ..db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(128), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login_at = Column(DateTime, nullable=True)

    # Relationships
    saved_valuations = relationship("SavedValuation", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    saved_vehicles = relationship("SavedVehicle", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    garage_vehicles = relationship("GarageVehicle", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
