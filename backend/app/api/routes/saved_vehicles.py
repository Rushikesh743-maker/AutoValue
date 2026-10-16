"""
Saved Vehicles / Bookmarks API Routes.
Allows users to save, list, and delete bookmarked vehicle configurations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ...db.session import get_db
from ...models.user import User
from ...models.saved_vehicle import SavedVehicle
from ...schemas.saved_vehicle import (
    SavedVehicleCreateRequest,
    SavedVehicleResponse,
    SavedVehicleListResponse
)
from ..deps import get_current_user

router = APIRouter(prefix="/saved-vehicles", tags=["Saved Vehicles"])


@router.get(
    "",
    response_model=SavedVehicleListResponse,
    summary="List user's bookmarked vehicle configurations"
)
def get_saved_vehicles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve all bookmarked vehicles belonging to the current user.
    """
    vehicles = (
        db.query(SavedVehicle)
        .filter(SavedVehicle.user_id == current_user.id)
        .order_by(SavedVehicle.created_at.desc())
        .all()
    )
    items = [SavedVehicleResponse.model_validate(v) for v in vehicles]
    return SavedVehicleListResponse(
        items=items,
        total=len(items)
    )


@router.post(
    "",
    response_model=SavedVehicleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bookmark a vehicle configuration"
)
def bookmark_vehicle(
    payload: SavedVehicleCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Bookmark a vehicle configuration. Prevents duplicate bookmarks.
    """
    # Check for existing identical vehicle bookmark with NULL-safe matching
    variant_val = payload.variant.strip() if payload.variant else None
    fuel_val = payload.fuel_type.strip() if payload.fuel_type else None
    trans_val = payload.transmission.strip() if payload.transmission else None

    query = (
        db.query(SavedVehicle)
        .filter(
            SavedVehicle.user_id == current_user.id,
            SavedVehicle.brand == payload.brand.strip(),
            SavedVehicle.model == payload.model.strip(),
            SavedVehicle.year == payload.year,
            SavedVehicle.km_driven == payload.km_driven,
            SavedVehicle.city == payload.city.strip()
        )
    )
    if variant_val is not None:
        query = query.filter(SavedVehicle.variant == variant_val)
    else:
        query = query.filter(SavedVehicle.variant.is_(None))

    if fuel_val is not None:
        query = query.filter(SavedVehicle.fuel_type == fuel_val)
    else:
        query = query.filter(SavedVehicle.fuel_type.is_(None))

    if trans_val is not None:
        query = query.filter(SavedVehicle.transmission == trans_val)
    else:
        query = query.filter(SavedVehicle.transmission.is_(None))

    existing = query.first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This vehicle configuration is already bookmarked."
        )

    saved_veh = SavedVehicle(
        user_id=current_user.id,
        brand=payload.brand.strip(),
        model=payload.model.strip(),
        variant=payload.variant.strip() if payload.variant else None,
        year=payload.year,
        fuel_type=payload.fuel_type,
        transmission=payload.transmission,
        km_driven=payload.km_driven,
        city=payload.city.strip(),
        notes=payload.notes
    )

    try:
        db.add(saved_veh)
        db.commit()
        db.refresh(saved_veh)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This vehicle configuration is already bookmarked."
        )

    return SavedVehicleResponse.model_validate(saved_veh)


@router.delete(
    "/{saved_vehicle_id}",
    summary="Delete a bookmarked vehicle"
)
def delete_saved_vehicle(
    saved_vehicle_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a bookmarked vehicle. Verifies ownership.
    """
    vehicle = db.query(SavedVehicle).filter(SavedVehicle.id == saved_vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved vehicle not found."
        )

    if vehicle.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You cannot delete bookmarks you do not own."
        )

    db.delete(vehicle)
    db.commit()
    return {"message": "Saved vehicle bookmark removed successfully."}
