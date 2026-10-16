"""
Garage & Portfolio Intelligence API Routes (Phase 16).
Provides secure endpoints for personal garage asset management, portfolio economic aggregation,
vehicle ranking, sell/keep prioritization, replacement discovery, and what-if scenarios.
All endpoints require JWT authentication and enforce strict IDOR protection.
"""
import time
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models.user import User
from ...models.garage import GarageVehicle
from ...schemas.garage import (
    OwnershipStatus,
    GarageVehicleCreate,
    GarageVehicleUpdate,
    GarageVehicleResponse,
    GarageVehicleSnapshot,
    GarageIntelligenceResponse,
    GarageScenarioRequest,
    GarageScenarioResponse,
    GarageCompareRequest,
    GarageCompareResponse
)
from ...services.garage_intelligence_service import garage_intelligence_service
from ...services.telemetry import metrics_collector
from ..deps import get_current_user

logger = logging.getLogger("autovalue.garage_routes")

router = APIRouter(prefix="/garage", tags=["Garage & Portfolio Intelligence"])


@router.post(
    "",
    response_model=GarageVehicleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a vehicle to personal garage"
)
def add_garage_vehicle(
    payload: GarageVehicleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Creates a new garage asset record for the authenticated user.
    """
    start_t = time.time()
    try:
        veh = garage_intelligence_service.create_vehicle(db, current_user.id, payload)
        metrics_collector.record_garage_request(
            action="ADD_VEHICLE",
            vehicle_count=1,
            duration_ms=(time.time() - start_t) * 1000
        )
        return GarageVehicleResponse.model_validate(veh)
    except Exception as e:
        logger.error(f"Failed to add garage vehicle: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to add vehicle to garage: {str(e)}"
        )


@router.get(
    "",
    response_model=List[GarageVehicleResponse],
    summary="List all personal garage vehicles"
)
def list_garage_vehicles(
    ownership_status: Optional[OwnershipStatus] = Query(None, description="Filter by ownership status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves all garage vehicles owned by the authenticated user.
    """
    start_t = time.time()
    vehicles = garage_intelligence_service.list_vehicles(db, current_user.id, ownership_status)
    metrics_collector.record_garage_request(
        action="LIST_VEHICLES",
        vehicle_count=len(vehicles),
        duration_ms=(time.time() - start_t) * 1000
    )
    return [GarageVehicleResponse.model_validate(v) for v in vehicles]


@router.get(
    "/intelligence",
    response_model=GarageIntelligenceResponse,
    summary="Get unified garage portfolio intelligence"
)
def get_garage_intelligence(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Computes portfolio economic summary, garage efficiency score, rankings,
    sell-first and keep-first priorities, redundancy alerts, and strategic recommendations.
    """
    start_t = time.time()
    resp = garage_intelligence_service.evaluate_garage_intelligence(db, current_user.id)
    metrics_collector.record_garage_request(
        action=resp.recommendation.action.value,
        vehicle_count=resp.summary.total_vehicles,
        duration_ms=(time.time() - start_t) * 1000,
        is_insufficient=(resp.recommendation.action.value == "INSUFFICIENT_EVIDENCE")
    )
    return resp


@router.get(
    "/{vehicle_id}",
    response_model=GarageVehicleResponse,
    summary="Get a specific garage vehicle"
)
def get_garage_vehicle_by_id(
    vehicle_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves a single garage vehicle with IDOR isolation.
    """
    veh = db.query(GarageVehicle).filter(GarageVehicle.id == vehicle_id).first()
    if not veh:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found in garage."
        )

    if veh.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not own this garage vehicle."
        )

    return GarageVehicleResponse.model_validate(veh)


@router.get(
    "/{vehicle_id}/intelligence",
    response_model=GarageVehicleSnapshot,
    summary="Get single garage vehicle economic snapshot"
)
def get_garage_vehicle_intelligence(
    vehicle_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Computes full valuation, TCO, risk, forecast, and lifecycle metrics for one vehicle.
    """
    veh = db.query(GarageVehicle).filter(GarageVehicle.id == vehicle_id).first()
    if not veh:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found in garage."
        )

    if veh.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not own this garage vehicle."
        )

    return garage_intelligence_service.evaluate_vehicle_snapshot(veh)


@router.patch(
    "/{vehicle_id}",
    response_model=GarageVehicleResponse,
    summary="Update garage vehicle metadata"
)
def update_garage_vehicle(
    vehicle_id: str,
    payload: GarageVehicleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates specifications or ownership metadata for an owned garage vehicle.
    """
    veh = db.query(GarageVehicle).filter(GarageVehicle.id == vehicle_id).first()
    if not veh:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found in garage."
        )

    if veh.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not own this garage vehicle."
        )

    updated = garage_intelligence_service.update_vehicle(db, current_user.id, vehicle_id, payload)
    return GarageVehicleResponse.model_validate(updated)


@router.delete(
    "/{vehicle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a vehicle from garage"
)
def delete_garage_vehicle(
    vehicle_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deletes a vehicle record from the user's garage.
    """
    veh = db.query(GarageVehicle).filter(GarageVehicle.id == vehicle_id).first()
    if not veh:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found in garage."
        )

    if veh.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not own this garage vehicle."
        )

    garage_intelligence_service.delete_vehicle(db, current_user.id, vehicle_id)
    return None


@router.post(
    "/scenario",
    response_model=GarageScenarioResponse,
    summary="Simulate what-if modifications on garage portfolio"
)
def simulate_garage_scenario(
    payload: GarageScenarioRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Simulates selling, adding, replacing, or adjusting mileage on garage vehicles.
    Validates ownership of all targeted vehicles. Max 10 actions.
    """
    if len(payload.actions) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 scenario actions supported per simulation."
        )

    # Validate ownership of all referenced vehicle IDs
    target_ids = [a.vehicle_id for a in payload.actions if a.vehicle_id]
    if target_ids:
        owned_count = db.query(GarageVehicle).filter(
            GarageVehicle.user_id == current_user.id,
            GarageVehicle.id.in_(target_ids)
        ).count()
        if owned_count < len(target_ids):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="One or more vehicle IDs do not belong to the authenticated user."
            )

    start_t = time.time()
    resp = garage_intelligence_service.simulate_garage_scenario(db, current_user.id, payload)
    metrics_collector.record_garage_scenario_request()
    return resp


@router.post(
    "/compare",
    response_model=GarageCompareResponse,
    summary="Compare 2 to 10 vehicles from garage"
)
def compare_garage_vehicles(
    payload: GarageCompareRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Renders a comparative matrix and economic ranking across selected garage vehicles.
    """
    if len(payload.vehicle_ids) < 2 or len(payload.vehicle_ids) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comparison requires between 2 and 10 vehicle identifiers."
        )

    # Validate ownership
    owned = db.query(GarageVehicle).filter(
        GarageVehicle.user_id == current_user.id,
        GarageVehicle.id.in_(payload.vehicle_ids)
    ).all()

    if len(owned) < len(payload.vehicle_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="One or more comparison vehicles do not belong to the authenticated user."
        )

    try:
        return garage_intelligence_service.compare_garage_vehicles(db, current_user.id, payload)
    except Exception as e:
        logger.error(f"Garage comparison failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to compare vehicles: {str(e)}"
        )
