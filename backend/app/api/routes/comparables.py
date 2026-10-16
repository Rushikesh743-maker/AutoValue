"""
Comparable vehicle search endpoints.
"""
from typing import Optional
from fastapi import APIRouter
from ...schemas.responses import UnimplementedResponse

router = APIRouter(prefix="/comparables", tags=["Comparables"])


@router.get("", response_model=UnimplementedResponse)
@router.get("/", response_model=UnimplementedResponse)
def get_comparable_listings(
    brand: Optional[str] = None,
    model: Optional[str] = None,
    year: Optional[int] = None,
    city: Optional[str] = None
) -> UnimplementedResponse:
    """
    Finds nearest comparable active listings matching vehicle parameters.
    Unimplemented in Phase 1: Will be connected to the similarity search engine in Phase 7.
    """
    return UnimplementedResponse(
        status="not_implemented",
        phase="Phase 1: Project Foundation",
        message="Comparable vehicle matching engine will be activated in Phase 7 after database population."
    )
