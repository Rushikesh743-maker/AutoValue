"""
Vehicle and Valuation Comparison API Routes (Phase 11).
Provides side-by-side empirical comparison for up to 3 saved vehicles/valuations.
Highlights factual mathematical differences, interval comparisons, and market positions
without subjective winner declarations.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models.user import User
from ...models.saved_valuation import SavedValuation
from ...models.saved_vehicle import SavedVehicle
from ...schemas.comparison import (
    ComparisonRequest,
    VehicleComparisonItem,
    EmpiricalDeltaItem,
    ComparisonResponse
)
from ..deps import get_current_user

router = APIRouter(prefix="/compare", tags=["Comparison"])


@router.post(
    "",
    response_model=ComparisonResponse,
    summary="Compare up to 3 saved vehicles or valuations"
)
def compare_vehicles(
    payload: ComparisonRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Compare 2 to 3 saved vehicles or valuations.
    Computes factual, empirical deltas across price, market median, mileage, age, engine, and uncertainty.
    """
    valuation_ids = payload.valuation_ids or []
    vehicle_ids = payload.vehicle_ids or []

    total_count = len(valuation_ids) + len(vehicle_ids)
    if total_count < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select at least 2 items to compare."
        )
    if total_count > 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comparison is limited to a maximum of 3 items."
        )

    compared_items: List[VehicleComparisonItem] = []

    # Fetch valuations
    if valuation_ids:
        valuations = (
            db.query(SavedValuation)
            .filter(
                SavedValuation.id.in_(valuation_ids),
                SavedValuation.user_id == current_user.id
            )
            .all()
        )
        for v in valuations:
            unc_width = (v.range_high - v.range_low) if (v.range_high is not None and v.range_low is not None) else None
            ev_strength = "HIGH" if (v.comparable_count and v.comparable_count >= 5) else ("MEDIUM" if (v.comparable_count and v.comparable_count >= 2) else "LOW")
            
            m_pos = None
            if v.asking_price is not None and v.asking_price > 0 and v.estimated_value:
                p_diff = v.asking_price - v.estimated_value
                if p_diff > 0:
                    m_pos = f"₹{abs(p_diff):,.0f} above estimated fair value"
                else:
                    m_pos = f"₹{abs(p_diff):,.0f} below estimated fair value"

            compared_items.append(
                VehicleComparisonItem(
                    id=v.id,
                    source_type="saved_valuation",
                    brand=v.brand,
                    model=v.model,
                    variant=v.variant,
                    year=v.year,
                    km_driven=v.km_driven,
                    fuel_type=v.fuel_type,
                    transmission=v.transmission,
                    engine_cc=v.engine_cc,
                    city=v.city,
                    asking_price=v.asking_price,
                    estimated_value=v.estimated_value,
                    range_low=v.range_low,
                    range_high=v.range_high,
                    market_median=v.market_median,
                    market_position=m_pos,
                    uncertainty_width=unc_width,
                    evidence_strength=ev_strength,
                    model_version=v.model_version,
                    dataset_version=v.dataset_version
                )
            )

    # Fetch bookmarked vehicles
    if vehicle_ids:
        vehicles = (
            db.query(SavedVehicle)
            .filter(
                SavedVehicle.id.in_(vehicle_ids),
                SavedVehicle.user_id == current_user.id
            )
            .all()
        )
        for veh in vehicles:
            compared_items.append(
                VehicleComparisonItem(
                    id=veh.id,
                    source_type="saved_vehicle",
                    brand=veh.brand,
                    model=veh.model,
                    variant=veh.variant,
                    year=veh.year,
                    km_driven=veh.km_driven,
                    fuel_type=veh.fuel_type,
                    transmission=veh.transmission,
                    engine_cc=None,
                    city=veh.city,
                    estimated_value=veh.last_estimated_value
                )
            )

    if len(compared_items) < 2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not retrieve the requested items for comparison."
        )

    # Compute empirical differences between items relative to baseline item 0
    deltas: List[EmpiricalDeltaItem] = []
    base = compared_items[0]

    for other in compared_items[1:]:
        # 1. Estimated value delta
        if base.estimated_value is not None and other.estimated_value is not None:
            price_diff = other.estimated_value - base.estimated_value
            if price_diff > 0:
                desc = f"₹{abs(price_diff):,.0f} higher estimated value compared to {base.brand} {base.model}"
            elif price_diff < 0:
                desc = f"₹{abs(price_diff):,.0f} lower estimated value compared to {base.brand} {base.model}"
            else:
                desc = f"Identical estimated valuation to {base.brand} {base.model}"
            
            deltas.append(
                EmpiricalDeltaItem(
                    metric="Estimated Value Difference",
                    description=desc,
                    baseline_vehicle_id=base.id,
                    target_vehicle_id=other.id,
                    numerical_delta=price_diff
                )
            )

        # 2. Market median delta
        if base.market_median is not None and other.market_median is not None:
            med_diff = other.market_median - base.market_median
            desc = f"Observed market median is ₹{abs(med_diff):,.0f} {'higher' if med_diff > 0 else 'lower'} than {base.brand} {base.model}"
            deltas.append(
                EmpiricalDeltaItem(
                    metric="Market Median Delta",
                    description=desc,
                    baseline_vehicle_id=base.id,
                    target_vehicle_id=other.id,
                    numerical_delta=med_diff
                )
            )

        # 3. Asking price delta (if both have asking prices)
        if base.asking_price is not None and other.asking_price is not None:
            ask_diff = other.asking_price - base.asking_price
            desc = f"Asking price is ₹{abs(ask_diff):,.0f} {'higher' if ask_diff > 0 else 'lower'} than {base.brand} {base.model}"
            deltas.append(
                EmpiricalDeltaItem(
                    metric="Asking Price Delta",
                    description=desc,
                    baseline_vehicle_id=base.id,
                    target_vehicle_id=other.id,
                    numerical_delta=ask_diff
                )
            )

        # 4. Mileage delta
        km_diff = other.km_driven - base.km_driven
        if km_diff > 0:
            km_desc = f"{abs(km_diff):,} km more driven than {base.brand} {base.model}"
        elif km_diff < 0:
            km_desc = f"{abs(km_diff):,} km less driven than {base.brand} {base.model}"
        else:
            km_desc = f"Same odometer reading as {base.brand} {base.model}"
        
        deltas.append(
            EmpiricalDeltaItem(
                metric="Odometer Reading Difference",
                description=km_desc,
                baseline_vehicle_id=base.id,
                target_vehicle_id=other.id,
                numerical_delta=float(km_diff)
            )
        )

        # 5. Age delta
        year_diff = other.year - base.year
        if year_diff > 0:
            yr_desc = f"{abs(year_diff)} model year(s) newer than {base.brand} {base.model}"
        elif year_diff < 0:
            yr_desc = f"{abs(year_diff)} model year(s) older than {base.brand} {base.model}"
        else:
            yr_desc = f"Same model year ({base.year}) as {base.brand} {base.model}"
        
        deltas.append(
            EmpiricalDeltaItem(
                metric="Model Year Delta",
                description=yr_desc,
                baseline_vehicle_id=base.id,
                target_vehicle_id=other.id,
                numerical_delta=float(year_diff)
            )
        )

        # 6. Engine CC delta
        if base.engine_cc is not None and other.engine_cc is not None:
            eng_diff = other.engine_cc - base.engine_cc
            if eng_diff != 0:
                eng_desc = f"{abs(eng_diff)} cc {'larger' if eng_diff > 0 else 'smaller'} engine displacement"
                deltas.append(
                    EmpiricalDeltaItem(
                        metric="Engine Displacement Delta",
                        description=eng_desc,
                        baseline_vehicle_id=base.id,
                        target_vehicle_id=other.id,
                        numerical_delta=float(eng_diff)
                    )
                )

        # 7. Evidence availability comparison
        if base.evidence_strength and other.evidence_strength:
            desc = f"Market evidence confidence: {other.brand} ({other.evidence_strength}) vs {base.brand} ({base.evidence_strength})"
            deltas.append(
                EmpiricalDeltaItem(
                    metric="Comparable Evidence Density",
                    description=desc,
                    baseline_vehicle_id=base.id,
                    target_vehicle_id=other.id,
                    numerical_delta=None
                )
            )

    summary_text = (
        f"Empirical comparison across {len(compared_items)} vehicle configurations. "
        "Deltas reflect model-estimated valuation differentials, odometer discrepancies, and model year variations."
    )

    return ComparisonResponse(
        vehicles=compared_items,
        empirical_differences=deltas,
        factual_summary=summary_text
    )
