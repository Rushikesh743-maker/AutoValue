"""
AutoValue Vehicle Market Forecasting & Buy/Sell Timing API Routes (Phase 14).
Provides endpoints for:
- GET /api/market/forecast: Query param-based vehicle forecasting and timing
- POST /api/market/forecast: JSON body-based vehicle forecasting
- GET /api/market/forecast/{valuation_id}: Saved valuation forecasting with IDOR & share-token protection
- POST /api/market/forecast/batch: Bounded batch forecasting (max 10 vehicles)
"""
import time
import uuid
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.schemas.forecast import (
    ForecastRequest,
    ForecastResponse,
    BatchForecastRequest,
    BatchForecastResponse
)
from backend.app.services.market_forecast_service import market_forecast_service
from backend.app.services.telemetry import metrics_collector
from backend.app.db.session import get_db
from backend.app.models.saved_valuation import SavedValuation
from backend.app.models.user import User
from backend.app.api.deps import get_current_user_optional

logger = logging.getLogger("autovalue.forecast_api")

router = APIRouter(prefix="/market/forecast", tags=["Vehicle Market Forecasting & Buy/Sell Timing"])


@router.get(
    "",
    response_model=ForecastResponse,
    status_code=status.HTTP_200_OK,
    summary="Vehicle market trend forecast and buy/sell timing intelligence (query params)"
)
def get_vehicle_forecast(
    brand: str = Query(..., description="Vehicle manufacturer brand"),
    model: str = Query(..., description="Vehicle model name"),
    variant: Optional[str] = Query(None, description="Vehicle trim/variant"),
    year: int = Query(2021, ge=1990, le=2030, description="Manufacturing year"),
    fuel_type: Optional[str] = Query(None, description="Fuel type"),
    transmission: Optional[str] = Query(None, description="Transmission type"),
    km_driven: Optional[int] = Query(None, ge=0, description="Odometer reading in km"),
    city: Optional[str] = Query(None, description="Metro city location"),
    asking_price: Optional[float] = Query(None, gt=0, description="Seller asking price in INR"),
    horizon_days: Optional[int] = Query(365, description="Primary forecast horizon (30, 90, 180, 365 days)"),
    cutoff_date: Optional[str] = Query(None, description="Optional ISO cutoff date to prevent future data leakage")
) -> ForecastResponse:
    """
    Computes multi-horizon momentum, market volatility, depreciation trajectories,
    deterministic forecast scenarios, and buy/sell timing indicators.
    """
    start_time = time.time()
    req = ForecastRequest(
        brand=brand,
        model=model,
        variant=variant,
        year=year,
        fuel_type=fuel_type,
        transmission=transmission,
        km_driven=km_driven,
        city=city,
        asking_price=asking_price,
        horizon_days=horizon_days,
        cutoff_date=cutoff_date
    )

    response = market_forecast_service.forecast_vehicle_market(req)
    req_id = str(uuid.uuid4())
    response.request_id = req_id

    duration_ms = (time.time() - start_time) * 1000.0
    response.latency_ms = round(duration_ms, 2)

    # Telemetry
    is_insufficient = response.status == "INSUFFICIENT_EVIDENCE"
    conf_str = response.forecast_confidence.value
    metrics_collector.record_forecast_request(
        insufficient_evidence=is_insufficient,
        confidence=conf_str,
        duration_ms=duration_ms
    )
    metrics_collector.record_timing_request()

    return response


@router.post(
    "",
    response_model=ForecastResponse,
    status_code=status.HTTP_200_OK,
    summary="Vehicle market trend forecast and buy/sell timing intelligence (JSON body)"
)
def post_vehicle_forecast(request: ForecastRequest) -> ForecastResponse:
    """
    Computes market forecasting and timing indicators from JSON request payload.
    """
    start_time = time.time()
    response = market_forecast_service.forecast_vehicle_market(request)
    req_id = str(uuid.uuid4())
    response.request_id = req_id

    duration_ms = (time.time() - start_time) * 1000.0
    response.latency_ms = round(duration_ms, 2)

    # Telemetry
    is_insufficient = response.status == "INSUFFICIENT_EVIDENCE"
    conf_str = response.forecast_confidence.value
    metrics_collector.record_forecast_request(
        insufficient_evidence=is_insufficient,
        confidence=conf_str,
        duration_ms=duration_ms
    )
    metrics_collector.record_timing_request()

    return response


@router.post(
    "/batch",
    response_model=BatchForecastResponse,
    status_code=status.HTTP_200_OK,
    summary="Bounded batch market forecasting (maximum 10 vehicles)"
)
def batch_forecast_vehicles(batch_req: BatchForecastRequest) -> BatchForecastResponse:
    """
    Evaluates market forecasting and buy/sell timing for up to 10 vehicles concurrently.
    Rejects requests exceeding 10 vehicles with HTTP 400.
    """
    start_time = time.time()

    if len(batch_req.vehicles) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch limit exceeded. Maximum 10 vehicles allowed per batch request."
        )

    results: List[ForecastResponse] = []
    for vehicle_req in batch_req.vehicles:
        res = market_forecast_service.forecast_vehicle_market(vehicle_req)
        res.request_id = str(uuid.uuid4())
        results.append(res)

    total_time_ms = (time.time() - start_time) * 1000.0

    return BatchForecastResponse(
        items=results,
        count=len(results),
        processing_time_ms=round(total_time_ms, 2)
    )


@router.get(
    "/{valuation_id}",
    response_model=ForecastResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate market forecast and timing for a saved valuation"
)
def get_saved_valuation_forecast(
    valuation_id: str,
    share_token: Optional[str] = Query(None, description="Optional public report share token"),
    horizon_days: Optional[int] = Query(365, description="Forecast horizon in days"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> ForecastResponse:
    """
    Reconstructs saved valuation snapshot and executes market forecasting & timing analysis.
    Enforces user authorization or valid public share token access.
    """
    start_time = time.time()
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
                detail="Authentication required to view private valuation forecast."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this valuation forecast."
            )

    # Reconstruct forecast request from saved record
    req = ForecastRequest(
        brand=valuation.brand,
        model=valuation.model,
        variant=valuation.variant,
        year=valuation.year,
        fuel_type=valuation.fuel_type,
        transmission=valuation.transmission,
        km_driven=valuation.km_driven,
        city=valuation.city,
        asking_price=valuation.asking_price or valuation.estimated_value,
        horizon_days=horizon_days
    )

    response = market_forecast_service.forecast_vehicle_market(req)
    req_id = str(uuid.uuid4())
    response.request_id = req_id

    duration_ms = (time.time() - start_time) * 1000.0
    response.latency_ms = round(duration_ms, 2)

    # Telemetry
    is_insufficient = response.status == "INSUFFICIENT_EVIDENCE"
    conf_str = response.forecast_confidence.value
    metrics_collector.record_forecast_request(
        insufficient_evidence=is_insufficient,
        confidence=conf_str,
        duration_ms=duration_ms
    )
    metrics_collector.record_timing_request()

    return response
