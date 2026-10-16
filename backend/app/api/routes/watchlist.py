"""
AutoValue Personal Valuation Watchlist API Routes (Phase 11).
Enables users to monitor valuation trajectories, refresh estimates against active models,
and track selling or buying interest states without fabricating fake history.
"""
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.models.saved_vehicle import SavedVehicle
from backend.app.schemas.intelligence import WatchlistItem, WatchlistStatusUpdate
from backend.app.schemas.valuation import ValuationRequestSchema
from backend.app.services.valuation_service import valuation_service
from backend.app.services.telemetry import metrics_collector
from ..deps import get_current_user

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])


@router.get(
    "",
    response_model=List[WatchlistItem],
    summary="Get current user's tracked vehicle watchlist"
)
def get_user_watchlist(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[WatchlistItem]:
    """
    Returns all vehicles bookmarked by the user with their tracking status and valuation history.
    """
    vehicles = (
        db.query(SavedVehicle)
        .filter(SavedVehicle.user_id == current_user.id)
        .order_by(SavedVehicle.created_at.desc())
        .all()
    )

    items: List[WatchlistItem] = []
    for v in vehicles:
        val_change = None
        pct_change = None
        if v.last_estimated_value is not None and v.previous_estimated_value is not None:
            val_change = round(v.last_estimated_value - v.previous_estimated_value, 2)
            if v.previous_estimated_value > 0:
                pct_change = round((val_change / v.previous_estimated_value) * 100.0, 2)

        items.append(
            WatchlistItem(
                id=v.id,
                user_id=v.user_id,
                brand=v.brand,
                model=v.model,
                variant=v.variant,
                year=v.year,
                fuel_type=v.fuel_type,
                transmission=v.transmission,
                km_driven=v.km_driven,
                city=v.city,
                notes=v.notes,
                watch_status=v.watch_status or "watching",
                last_checked_at=v.last_checked_at.isoformat() if v.last_checked_at else None,
                last_estimated_value=v.last_estimated_value,
                previous_estimated_value=v.previous_estimated_value,
                value_change=val_change,
                value_change_percentage=pct_change,
                market_median=None,
                created_at=v.created_at.isoformat()
            )
        )

    return items


@router.post(
    "/{vehicle_id}/refresh",
    response_model=WatchlistItem,
    summary="Refresh valuation estimate for a watchlist vehicle using the active model"
)
def refresh_watchlist_vehicle_valuation(
    vehicle_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> WatchlistItem:
    """
    Re-computes vehicle fair market value using the active ML model,
    recording the change from previous valuation.
    """
    vehicle = (
        db.query(SavedVehicle)
        .filter(SavedVehicle.id == vehicle_id, SavedVehicle.user_id == current_user.id)
        .first()
    )
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist vehicle not found or access unauthorized."
        )

    req = ValuationRequestSchema(
        brand=vehicle.brand,
        model=vehicle.model,
        variant=vehicle.variant,
        year=vehicle.year,
        fuel_type=vehicle.fuel_type or "Petrol",
        transmission=vehicle.transmission or "Manual",
        km_driven=vehicle.km_driven,
        city=vehicle.city
    )

    val_res = valuation_service.evaluate_valuation(req, include_shap=False)
    new_estimate = val_res.valuation.estimated_value
    market_median = val_res.market.median


    # Update state: previous estimate becomes the old last_estimated_value
    if vehicle.last_estimated_value is not None:
        vehicle.previous_estimated_value = vehicle.last_estimated_value

    vehicle.last_estimated_value = new_estimate
    vehicle.last_checked_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(vehicle)

    metrics_collector.record_watchlist_refresh()

    val_change = None
    pct_change = None
    if vehicle.last_estimated_value is not None and vehicle.previous_estimated_value is not None:
        val_change = round(vehicle.last_estimated_value - vehicle.previous_estimated_value, 2)
        if vehicle.previous_estimated_value > 0:
            pct_change = round((val_change / vehicle.previous_estimated_value) * 100.0, 2)

    return WatchlistItem(
        id=vehicle.id,
        user_id=vehicle.user_id,
        brand=vehicle.brand,
        model=vehicle.model,
        variant=vehicle.variant,
        year=vehicle.year,
        fuel_type=vehicle.fuel_type,
        transmission=vehicle.transmission,
        km_driven=vehicle.km_driven,
        city=vehicle.city,
        notes=vehicle.notes,
        watch_status=vehicle.watch_status or "watching",
        last_checked_at=vehicle.last_checked_at.isoformat() if vehicle.last_checked_at else None,
        last_estimated_value=vehicle.last_estimated_value,
        previous_estimated_value=vehicle.previous_estimated_value,
        value_change=val_change,
        value_change_percentage=pct_change,
        market_median=market_median,
        created_at=vehicle.created_at.isoformat()
    )


@router.patch(
    "/{vehicle_id}/status",
    response_model=WatchlistItem,
    summary="Update vehicle tracking intent status"
)
def update_watchlist_status(
    vehicle_id: str,
    payload: WatchlistStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> WatchlistItem:
    """
    Updates watch status ('watching', 'interested_selling', 'interested_buying').
    """
    vehicle = (
        db.query(SavedVehicle)
        .filter(SavedVehicle.id == vehicle_id, SavedVehicle.user_id == current_user.id)
        .first()
    )
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist vehicle not found or access unauthorized."
        )

    vehicle.watch_status = payload.watch_status
    db.commit()
    db.refresh(vehicle)

    val_change = None
    pct_change = None
    if vehicle.last_estimated_value is not None and vehicle.previous_estimated_value is not None:
        val_change = round(vehicle.last_estimated_value - vehicle.previous_estimated_value, 2)
        if vehicle.previous_estimated_value > 0:
            pct_change = round((val_change / vehicle.previous_estimated_value) * 100.0, 2)

    return WatchlistItem(
        id=vehicle.id,
        user_id=vehicle.user_id,
        brand=vehicle.brand,
        model=vehicle.model,
        variant=vehicle.variant,
        year=vehicle.year,
        fuel_type=vehicle.fuel_type,
        transmission=vehicle.transmission,
        km_driven=vehicle.km_driven,
        city=vehicle.city,
        notes=vehicle.notes,
        watch_status=vehicle.watch_status,
        last_checked_at=vehicle.last_checked_at.isoformat() if vehicle.last_checked_at else None,
        last_estimated_value=vehicle.last_estimated_value,
        previous_estimated_value=vehicle.previous_estimated_value,
        value_change=val_change,
        value_change_percentage=pct_change,
        market_median=None,
        created_at=vehicle.created_at.isoformat()
    )
