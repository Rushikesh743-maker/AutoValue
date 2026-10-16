"""
ShareToken ORM model representing public, revocable share links for saved valuation reports.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship

from ..db.base import Base


class ShareToken(Base):
    __tablename__ = "share_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    valuation_id = Column(String(36), ForeignKey("saved_valuations.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=True)
    view_count = Column(Integer, default=0, nullable=False)

    # Relationships
    valuation = relationship("SavedValuation", back_populates="share_token")

    __table_args__ = (
        Index("ix_share_tokens_token_active", "token", "is_active"),
    )
