"""
AutoValue Vehicle Lifecycle & Ownership Decision Intelligence API Routes (Phase 15).
Provides unified lifecycle action recommendations (BUY, KEEP, SELL_NOW, WAIT, REPLACE),
multi-horizon outlooks, what-if scenario simulations, alternative vehicle comparisons,
and bounded batch processing.
"""
import time
import uuid
from typing import Optional, List
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.schemas.lifecycle import (
    LifecycleDecisionRequest,
    LifecycleDecisionResponse,
    LifecycleScenarioRequest,
    LifecycleCompareRequest,
    LifecycleCompareResponse,
    BatchLifecycleRequest,
    BatchLifecycleResponse,
    LifecycleScenarioType,
    DecisionMode
)
from backend.app.services.lifecycle_service import lifecycle_service
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.models.saved_valuation import SavedValuation
from backend.app.api.deps import get_current_user_optional

router = APIRouter(prefix="/lifecycle", tags=["Lifecycle Decision Intelligence"])
logger = logging.getLogger("autovalue.lifecycle_api")


@router.post(
    "/decision",
    response_model=LifecycleDecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate unified vehicle lifecycle recommendation"
)
def post_lifecycle_decision(request: LifecycleDecisionRequest) -> LifecycleDecisionResponse:
    """
    Evaluates vehicle state, ownership economics, market momentum, risk, and replacement
    alternatives to produce a transparent lifecycle recommendation (BUY, KEEP, SELL_NOW, WAIT, REPLACE).
    """
    return lifecycle_service.evaluate_lifecycle(request)


@router.post(
    "/scenario",
    response_model=LifecycleDecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Simulate what-if lifecycle scenario"
)
def post_lifecycle_scenario(request: LifecycleScenarioRequest) -> LifecycleDecisionResponse:
    """
    Simulates what-if parameter variations (annual mileage, waiting time, price shifts)
    and returns the adjusted lifecycle recommendation and sensitivity analysis.
    """
    return lifecycle_service.simulate_scenario(request)


@router.post(
    "/compare",
    response_model=LifecycleCompareResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare lifecycle economics across multiple vehicles (max 5 candidates)"
)
def post_lifecycle_compare(request: LifecycleCompareRequest) -> LifecycleCompareResponse:
    """
    Compares 5-year TCO, resale retention, cost/km, risk, and recommended actions
    between a current vehicle and up to 5 replacement candidates.
    """
    if len(request.replacement_vehicles) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comparison limit exceeded: maximum 5 replacement candidates allowed."
        )
    return lifecycle_service.compare_lifecycle(request)


@router.post(
    "/batch",
    response_model=BatchLifecycleResponse,
    status_code=status.HTTP_200_OK,
    summary="Bounded batch lifecycle evaluations (maximum 10 vehicles)"
)
def post_lifecycle_batch(batch_req: BatchLifecycleRequest) -> BatchLifecycleResponse:
    """
    Evaluates lifecycle recommendations for up to 10 vehicles.
    Rejects batches greater than 10 with HTTP 400 Bad Request.
    """
    if len(batch_req.vehicles) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch limit exceeded: maximum 10 vehicles allowed per batch request."
        )
    return lifecycle_service.batch_lifecycle(batch_req)


@router.get(
    "/{valuation_id}",
    response_model=LifecycleDecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate lifecycle decision for a saved valuation"
)
def get_saved_valuation_lifecycle(
    valuation_id: str,
    share_token: Optional[str] = Query(None, description="Optional public report share token"),
    annual_km: Optional[int] = Query(12000, ge=0, le=200000, description="Annual driving distance in km"),
    horizon_years: Optional[int] = Query(5, ge=1, le=10, description="Evaluation horizon in years"),
    scenario: Optional[LifecycleScenarioType] = Query(LifecycleScenarioType.BASE, description="Scenario assumption"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> LifecycleDecisionResponse:
    """
    Reconstructs saved valuation snapshot and executes lifecycle decision analysis.
    Enforces owner authorization or valid public share token access.
    """
    valuation = db.query(SavedValuation).filter(SavedValuation.id == valuation_id).first()
    if not valuation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Valuation with ID '{valuation_id}' not found."
        )

    # IDOR & Authorization Check
    is_authorized = False
    if current_user and valuation.user_id == current_user.id:
        is_authorized = True
    elif share_token and valuation.share_token and valuation.share_token.is_active:
        if valuation.share_token.token == share_token:
            is_authorized = True

    if not is_authorized:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to view private valuation lifecycle decision."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this valuation lifecycle decision."
            )

    # Reconstruct lifecycle request from saved record
    req = LifecycleDecisionRequest(
        mode=DecisionMode.OWNER if valuation.user_id else DecisionMode.BUY,
        brand=valuation.brand,
        model=valuation.model,
        variant=valuation.variant,
        year=valuation.year,
        fuel_type=valuation.fuel_type,
        transmission=valuation.transmission,
        km_driven=valuation.km_driven,
        city=valuation.city,
        asking_price=valuation.asking_price,
        current_market_value=valuation.estimated_value,
        annual_km=annual_km,
        horizon_years=horizon_years,
        scenario=scenario
    )

    return lifecycle_service.evaluate_lifecycle(req)
