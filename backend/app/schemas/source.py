from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class SourceBase(BaseModel):
    name: str
    base_url: str
    active: bool = True


class SourceCreate(SourceBase):
    pass


class SourceRead(SourceBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CollectionRunRead(BaseModel):
    id: int
    source_id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    records_collected: int
    records_valid: int
    records_rejected: int
    status: str

    model_config = ConfigDict(from_attributes=True)

