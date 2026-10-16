"""
Saved Valuation History and Snapshot Management API Routes.
Provides saving, listing, detail viewing, deleting, and share management for valuation snapshots.
"""
import json
import math
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...core.security import generate_share_token
from ...models.user import User
from ...models.saved_valuation import SavedValuation
from ...models.share_token import ShareToken
from ...schemas.saved_valuation import (
    SaveValuationRequest,
    SavedValuationSummary,
    SavedValuationDetail,
    ValuationHistoryResponse
)
from ...schemas.share import ShareTokenResponse
from ..deps import get_current_user

router = APIRouter(prefix="/valuations", tags=["Valuations & History"])


def map_saved_valuation_summary(v: SavedValuation) -> SavedValuationSummary:
    """Helper to convert ORM SavedValuation into summary schema with share metadata."""
    is_shared = False
    share_token_val = None
    if v.share_token and v.share_token.is_active:
        is_shared = True
        share_token_val = v.share_token.token

    return SavedValuationSummary(
        id=v.id,
        request_id=v.request_id,
        created_at=v.created_at,
        brand=v.brand,
        model=v.model,
        variant=v.variant,
        year=v.year,
        fuel_type=v.fuel_type,
        transmission=v.transmission,
        km_driven=v.km_driven,
        city=v.city,
        engine_cc=v.engine_cc,
        mileage=v.mileage,
        owner_count=v.owner_count,
        seller_type=v.seller_type,
        asking_price=v.asking_price,
        estimated_value=v.estimated_value,
        range_low=v.range_low,
        range_high=v.range_high,
        model_interval_low=v.model_interval_low,
        model_interval_high=v.model_interval_high,
        market_median=v.market_median,
        comparable_count=v.comparable_count,
        model_version=v.model_version,
        dataset_version=v.dataset_version,
        notes=v.notes,
        is_shared=is_shared,
        share_token=share_token_val
    )


@router.get(
    "",
    response_model=ValuationHistoryResponse,
    summary="Get user's valuation history with pagination"
)
def get_user_valuation_history(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Items per page"),
    brand: Optional[str] = Query(None, description="Optional brand filter"),
    model: Optional[str] = Query(None, description="Optional model filter"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve authenticated user's saved valuations with deterministic sorting (created_at DESC).
    Users can only access their own valuations.
    """
    query = db.query(SavedValuation).filter(SavedValuation.user_id == current_user.id)

    if brand:
        query = query.filter(SavedValuation.brand.ilike(f"%{brand.strip()}%"))
    if model:
        query = query.filter(SavedValuation.model.ilike(f"%{model.strip()}%"))

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    records = (
        query.order_by(SavedValuation.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [map_saved_valuation_summary(v) for v in records]
    return ValuationHistoryResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.post(
    "",
    response_model=SavedValuationSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Save a completed valuation result snapshot"
)
@router.post(
    "/save",
    response_model=SavedValuationSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Save a completed valuation result snapshot (alias)"
)
def save_valuation_snapshot(
    payload: SaveValuationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Save an immutable valuation snapshot for the authenticated user.
    Preserves all calculated outputs, SHAP explanations, and comparables without recomputation.
    """
    veh = payload.vehicle
    res = payload.valuation_result

    # Extract interval bounds if available
    interval_low = None
    interval_high = None
    if res.valuation.model_interval:
        interval_low = res.valuation.model_interval.interval_low
        interval_high = res.valuation.model_interval.interval_high

    # Serialize complete payload dict
    payload_dict = res.model_dump()

    saved = SavedValuation(
        user_id=current_user.id,
        request_id=res.request_id,
        brand=veh.brand,
        model=veh.model,
        variant=veh.variant,
        year=veh.year,
        fuel_type=veh.fuel_type,
        transmission=veh.transmission,
        km_driven=veh.km_driven,
        city=veh.city,
        engine_cc=veh.engine_cc,
        mileage=veh.mileage,
        owner_count=veh.owner_count,
        seller_type=veh.seller_type,
        asking_price=veh.asking_price,
        estimated_value=res.valuation.estimated_value,
        range_low=res.valuation.range_low,
        range_high=res.valuation.range_high,
        model_interval_low=interval_low,
        model_interval_high=interval_high,
        market_median=res.market.median if res.market else None,
        comparable_count=len(res.comparables),
        model_version=res.model_version,
        dataset_version=res.dataset_version,
        payload_json=json.dumps(payload_dict),
        notes=payload.notes
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)

    return map_saved_valuation_summary(saved)


@router.get(
    "/{valuation_id}",
    response_model=SavedValuationDetail,
    summary="Get single saved valuation detail by ID"
)
def get_saved_valuation_by_id(
    valuation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve full saved valuation report. Enforces strict user ownership to prevent IDOR.
    """
    valuation = db.query(SavedValuation).filter(SavedValuation.id == valuation_id).first()
    if not valuation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Valuation record not found."
        )

    if valuation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not have permission to view this valuation."
        )

    summary = map_saved_valuation_summary(valuation)
    raw_payload = None
    if valuation.payload_json:
        try:
            raw_payload = json.loads(valuation.payload_json)
        except Exception:
            raw_payload = None

    return SavedValuationDetail(
        **summary.model_dump(),
        payload=raw_payload
    )


@router.delete(
    "/{valuation_id}",
    summary="Delete a saved valuation"
)
def delete_saved_valuation(
    valuation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a saved valuation owned by current user.
    """
    valuation = db.query(SavedValuation).filter(SavedValuation.id == valuation_id).first()
    if not valuation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Valuation record not found."
        )

    if valuation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not have permission to delete this valuation."
        )

    db.delete(valuation)
    db.commit()
    return {"message": "Valuation record deleted successfully."}


@router.post(
    "/{valuation_id}/share",
    response_model=ShareTokenResponse,
    summary="Generate or enable a public share link for a valuation report"
)
def share_valuation_report(
    valuation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a non-guessable, cryptographically secure share token for a valuation.
    """
    valuation = db.query(SavedValuation).filter(SavedValuation.id == valuation_id).first()
    if not valuation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Valuation record not found."
        )

    if valuation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You cannot share valuations you do not own."
        )

    share = db.query(ShareToken).filter(ShareToken.valuation_id == valuation_id).first()
    if share:
        share.is_active = True
        db.commit()
        db.refresh(share)
    else:
        token = generate_share_token(32)
        share = ShareToken(
            valuation_id=valuation_id,
            token=token,
            is_active=True
        )
        db.add(share)
        db.commit()
        db.refresh(share)

    return ShareTokenResponse(
        share_token=share.token,
        share_url=f"/shared/{share.token}",
        is_active=share.is_active,
        created_at=share.created_at,
        view_count=share.view_count
    )


@router.delete(
    "/{valuation_id}/share",
    summary="Revoke public share link for a valuation"
)
def revoke_valuation_share(
    valuation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Revoke public sharing for a valuation report.
    """
    valuation = db.query(SavedValuation).filter(SavedValuation.id == valuation_id).first()
    if not valuation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Valuation record not found."
        )

    if valuation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You cannot modify sharing for valuations you do not own."
        )

    share = db.query(ShareToken).filter(ShareToken.valuation_id == valuation_id).first()
    if share:
        share.is_active = False
        db.commit()

    return {"message": "Public sharing link has been revoked."}
