"""
Public Shareable Valuation Reports API Route.
Exposes sanitized, read-only valuation reports via unguessable share tokens.
"""
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models.share_token import ShareToken
from ...schemas.share import SharedValuationResponse

router = APIRouter(prefix="/shared", tags=["Public Sharing"])


@router.get(
    "/{token}",
    response_model=SharedValuationResponse,
    summary="Get public read-only valuation report by share token"
)
def get_shared_report(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve sanitized, read-only valuation snapshot using public share token.
    Increments report view counter.
    Does not expose sensitive user identifiers or telemetry.
    """
    share = db.query(ShareToken).filter(ShareToken.token == token, ShareToken.is_active == True).first()
    if not share or not share.valuation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shared valuation report not found or link has been revoked."
        )

    # Check expiration if configured
    if share.expires_at:
        exp = share.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shared valuation link has expired."
            )

    # Increment view counter
    share.view_count += 1
    db.commit()

    v = share.valuation
    raw_payload = None
    if v.payload_json:
        try:
            raw_payload = json.loads(v.payload_json)
        except Exception:
            raw_payload = None

    return SharedValuationResponse(
        share_token=share.token,
        created_at=v.created_at,
        brand=v.brand,
        model=v.model,
        variant=v.variant,
        year=v.year,
        fuel_type=v.fuel_type,
        transmission=v.transmission,
        km_driven=v.km_driven,
        city=v.city,
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
        payload=raw_payload
    )
