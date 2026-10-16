"""
Explainability endpoints providing feature importance and SHAP value breakdowns.
"""
from typing import Optional
from fastapi import APIRouter
from ...schemas.responses import UnimplementedResponse

router = APIRouter(prefix="/explain", tags=["Explainability"])


@router.get("/feature-importance", response_model=UnimplementedResponse)
def get_feature_importance(listing_id: Optional[str] = None) -> UnimplementedResponse:
    """
    Returns SHAP value breakdown explaining the factors driving a vehicle's estimated price range.
    Unimplemented in Phase 1: SHAP explainers will be trained and integrated in Phase 6.
    """
    return UnimplementedResponse(
        status="not_implemented",
        phase="Phase 1: Project Foundation",
        message="Model explainability with SHAP value breakdown will be integrated in Phase 6."
    )
