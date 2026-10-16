"""
AutoValue Vehicle Risk & Trust Intelligence API Routes (Phase 12).
Provides endpoints for:
- POST /api/risk: Single vehicle risk analysis
- GET /api/risk/{valuation_id}: Saved valuation risk analysis with IDOR protection
- POST /api/risk/batch: Bounded batch risk evaluation for comparison and shortlists
"""
import time
import uuid
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.schemas.valuation import ValuationRequestSchema
from backend.app.schemas.risk import (
    RiskAnalysisResponse,
    BatchRiskRequest,
    BatchRiskResponse
)
from backend.app.services.valuation_service import valuation_service
from backend.app.services.risk_service import risk_service
from backend.app.services.telemetry import metrics_collector
from backend.app.db.session import get_db
from backend.app.models.saved_valuation import SavedValuation
from backend.app.models.user import User
from backend.app.api.deps import get_current_user, get_current_user_optional

logger = logging.getLogger("autovalue.risk_api")

router = APIRouter(prefix="/risk", tags=["Vehicle Risk & Trust Intelligence"])


@router.post(
    "",
    response_model=RiskAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate observable market, pricing, usage, and evidence risk"
)
def evaluate_vehicle_risk(request: ValuationRequestSchema) -> RiskAnalysisResponse:
    """
    Computes deterministic observable risk across 9 transparent dimensions:
    1. Price Anomaly Risk (20%)
    2. Mileage & Usage Risk (15%)
    3. Vehicle Age Risk (10%)
    4. Market Liquidity Risk (15%)
    5. Data Quality Risk (10%)
    6. Market Evidence Risk (10%)
    7. Valuation Uncertainty Risk (10%)
    8. Price Dispersion Risk (5%)
    9. Source Concentration Risk (5%)

    Includes explicit physical condition disclaimer for unverified mechanical factors.
    """
    start_time = time.time()
    req_dict = request.model_dump()

    # 1. Execute valuation pipeline (reusing singleton active model)
    val_response = valuation_service.evaluate_valuation(request, include_shap=False)

    # 2. Execute risk evaluation
    risk_response = risk_service.evaluate_risk(req_dict, val_response)

    duration_ms = (time.time() - start_time) * 1000.0

    # Telemetry
    is_insufficient = risk_response.risk_level == "INSUFFICIENT_EVIDENCE"
    metrics_collector.record_risk_request(insufficient_evidence=is_insufficient, duration_ms=duration_ms)

    return risk_response


@router.get(
    "/{valuation_id}",
    response_model=RiskAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate risk for a saved vehicle valuation"
)
def evaluate_saved_valuation_risk(
    valuation_id: str,
    share_token: Optional[str] = Query(None, description="Optional public report share token"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> RiskAnalysisResponse:
    """
    Retrieves a saved valuation snapshot and executes risk intelligence evaluation.
    Enforces user ownership or valid public share token access.
    """
    valuation = db.query(SavedValuation).filter(SavedValuation.id == valuation_id).first()
    if not valuation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Valuation with ID '{valuation_id}' not found."
        )

    # Access control: User is owner OR valid share token provided
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
                detail="Authentication required to view private valuation risk analysis."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this valuation risk analysis."
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

    val_response = valuation_service.evaluate_valuation(val_req, include_shap=False)
    risk_response = risk_service.evaluate_risk(val_req.model_dump(), val_response)

    return risk_response


@router.post(
    "/batch",
    response_model=BatchRiskResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch evaluate risk across multiple candidate vehicles"
)
def evaluate_batch_risk(request: BatchRiskRequest) -> BatchRiskResponse:
    """
    Executes bounded batch risk evaluation across multiple vehicle configurations (max 10).
    Ideal for shortlist screening and comparison matrix integration.
    """
    start_time = time.time()
    batch_response = risk_service.evaluate_batch(request.vehicles)
    duration_ms = (time.time() - start_time) * 1000.0

    metrics_collector.record_risk_request(duration_ms=duration_ms)
    return batch_response
