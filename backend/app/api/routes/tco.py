"""
AutoValue Total Cost of Ownership (TCO) & Resale Intelligence API Routes (Phase 13).
Provides endpoints for:
- POST /api/tco: Calculate ownership economics and resale projections
- GET /api/tco/{valuation_id}: Recompute/retrieve TCO for saved valuation with IDOR protection
- POST /api/tco/scenario: Run non-destructive ownership scenario analysis
- POST /api/tco/compare: Multi-vehicle TCO comparison matrix (max 10)
"""
import time
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.schemas.valuation import ValuationRequestSchema
from backend.app.schemas.tco import (
    TCOAssumptions,
    TCORequest,
    TCOResponse,
    TCOScenarioRequest,
    TCOCompareRequest,
    TCOCompareResponse
)
from backend.app.services.valuation_service import valuation_service
from backend.app.services.tco_service import tco_service
from backend.app.services.telemetry import metrics_collector
from backend.app.db.session import get_db
from backend.app.models.saved_valuation import SavedValuation
from backend.app.models.user import User
from backend.app.api.deps import get_current_user_optional

logger = logging.getLogger("autovalue.tco_api")

router = APIRouter(prefix="/tco", tags=["Total Cost of Ownership & Resale Intelligence"])


@router.post(
    "",
    response_model=TCOResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate vehicle total cost of ownership and resale projections"
)
def calculate_vehicle_tco(request: TCORequest) -> TCOResponse:
    """
    Computes multi-year ownership economics, market-anchored depreciation,
    fuel/energy expenditure, insurance, maintenance, scenario forecasts, and sensitivity analysis.
    """
    start_time = time.time()
    try:
        val_response = valuation_service.evaluate_valuation(request.vehicle, include_shap=False)
        tco_response = tco_service.calculate_tco(
            vehicle_data=request.vehicle.model_dump(),
            valuation_resp=val_response,
            assumptions=request.assumptions
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Error calculating TCO: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate ownership economics: {str(e)}"
        )

    duration_ms = (time.time() - start_time) * 1000.0
    is_insufficient = tco_response.resale.confidence == "INSUFFICIENT_EVIDENCE"
    metrics_collector.record_tco_request(insufficient_evidence=is_insufficient, duration_ms=duration_ms)

    return tco_response


@router.get(
    "/{valuation_id}",
    response_model=TCOResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate TCO for a saved vehicle valuation"
)
def get_saved_valuation_tco(
    valuation_id: str,
    share_token: Optional[str] = Query(None, description="Optional public report share token"),
    annual_km: Optional[int] = Query(None, ge=0, le=100000),
    ownership_years: Optional[int] = Query(None, ge=1, le=10),
    purchase_price_mode: Optional[str] = Query(None),
    custom_purchase_price: Optional[float] = Query(None, gt=0),
    fuel_price: Optional[float] = Query(None, gt=0),
    fuel_efficiency: Optional[float] = Query(None, gt=0),
    annual_insurance_rate: Optional[float] = Query(None, ge=0.005, le=0.15),
    annual_maintenance: Optional[float] = Query(None, ge=0),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> TCOResponse:
    """
    Reconstructs saved valuation snapshot and executes TCO analysis.
    Enforces owner authorization or valid public share token access.
    """
    valuation = db.query(SavedValuation).filter(SavedValuation.id == valuation_id).first()
    if not valuation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Valuation with ID '{valuation_id}' not found."
        )

    # Authorization Check
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
                detail="Authentication required to view private valuation ownership economics."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this valuation ownership economics."
            )

    # Reconstruct valuation request
    val_req = ValuationRequestSchema(
        brand=valuation.brand,
        model=valuation.model,
        variant=valuation.variant,
        year=valuation.year,
        fuel_type=valuation.fuel_type or "Petrol",
        transmission=valuation.transmission or "Manual",
        km_driven=valuation.km_driven,
        city=valuation.city,
        engine_cc=valuation.engine_cc,
        mileage=valuation.mileage,
        owner_count=valuation.owner_count or 1,
        seller_type=valuation.seller_type or "Individual",
        asking_price=valuation.asking_price
    )

    # Build assumptions overrides
    assumptions = TCOAssumptions(
        annual_km=annual_km if annual_km is not None else 12000,
        ownership_years=ownership_years if ownership_years is not None else 5,
        purchase_price_mode=purchase_price_mode or "FAIR_VALUE",
        custom_purchase_price=custom_purchase_price,
        fuel_price=fuel_price,
        fuel_efficiency=fuel_efficiency,
        annual_insurance_rate=annual_insurance_rate if annual_insurance_rate is not None else 0.03,
        annual_maintenance=annual_maintenance
    )

    start_time = time.time()
    val_response = valuation_service.evaluate_valuation(val_req, include_shap=False)
    tco_response = tco_service.calculate_tco(val_req.model_dump(), val_response, assumptions)
    duration_ms = (time.time() - start_time) * 1000.0

    metrics_collector.record_tco_request(duration_ms=duration_ms)
    return tco_response


@router.post(
    "/scenario",
    response_model=TCOResponse,
    status_code=status.HTTP_200_OK,
    summary="Run non-destructive ownership scenario analysis"
)
def evaluate_tco_scenario(request: TCOScenarioRequest) -> TCOResponse:
    """
    Executes non-destructive scenario analysis (Conservative, Base, Optimistic, or Custom).
    """
    start_time = time.time()
    assumptions = request.assumptions or TCOAssumptions()
    assumptions.scenario = request.scenario_name.upper()

    try:
        val_response = valuation_service.evaluate_valuation(request.vehicle, include_shap=False)
        tco_response = tco_service.calculate_tco(request.vehicle.model_dump(), val_response, assumptions)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve)
        )

    duration_ms = (time.time() - start_time) * 1000.0
    metrics_collector.record_tco_request(duration_ms=duration_ms)
    return tco_response


@router.post(
    "/compare",
    response_model=TCOCompareResponse,
    status_code=status.HTTP_200_OK,
    summary="Multi-vehicle ownership economics comparison (max 10)"
)
def compare_vehicle_tco(request: TCOCompareRequest) -> TCOCompareResponse:
    """
    Evaluates comparative Total Cost of Ownership across up to 10 candidate vehicles.
    Computes break-even ownership crossover when exactly 2 vehicles are compared.
    """
    if not request.vehicles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one vehicle configuration is required for TCO comparison."
        )
    if len(request.vehicles) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TCO comparison is bounded to a maximum of 10 vehicles."
        )

    start_time = time.time()
    try:
        compare_response = tco_service.compare_tco(
            vehicles=request.vehicles,
            shared_assumptions=request.shared_assumptions
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve)
        )

    duration_ms = (time.time() - start_time) * 1000.0
    metrics_collector.record_tco_request(duration_ms=duration_ms)
    return compare_response
