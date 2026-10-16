"""
Source management and data collection status endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...models.source import Source
from ...schemas.source import SourceRead, SourceCreate

router = APIRouter(prefix="/sources", tags=["Sources & Provenance"])


@router.get("", response_model=List[SourceRead])
@router.get("/", response_model=List[SourceRead])
def list_sources(db: Session = Depends(get_db)) -> List[SourceRead]:
    """
    Returns registered data collection sources.
    """
    sources = db.query(Source).all()
    return sources


@router.post("", response_model=SourceRead)
@router.post("/", response_model=SourceRead)
def register_source(source_in: SourceCreate, db: Session = Depends(get_db)) -> SourceRead:
    """
    Registers a new data source for collection tracking.
    """
    db_source = Source(
        name=source_in.name,
        base_url=source_in.base_url,
        active=source_in.active
    )
    db.add(db_source)
    db.commit()
    db.refresh(db_source)
    return db_source
