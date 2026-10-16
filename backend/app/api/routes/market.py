"""
Aggregated market trends and vehicle historical intelligence endpoints.
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Query
from backend.app.services.historical_market_service import historical_market_service

router = APIRouter(prefix="/market", tags=["Market Analysis"])


@router.get("/history")
def get_market_history(
    brand: Optional[str] = Query(None, description="Vehicle brand / OEM"),
    model: Optional[str] = Query(None, description="Vehicle model name"),
    city: Optional[str] = Query(None, description="Metro city filter"),
    time_period: str = Query("all", pattern="^(3m|6m|12m|all)$", description="Time period filter: 3m, 6m, 12m, all")
) -> Dict[str, Any]:
    """
    Returns empirical historical asking price aggregations (monthly median, mean, p25, p75)
    and observed market movements across historical collection dates.
    """
    return historical_market_service.get_market_history(
        brand=brand,
        model=model,
        city=city,
        time_period=time_period
    )


@router.get("/timing")
def get_market_timing(
    brand: str = Query(..., description="Vehicle brand / OEM"),
    model: str = Query(..., description="Vehicle model name"),
    city: Optional[str] = Query(None, description="Metro city filter"),
    time_period: str = Query("6m", pattern="^(3m|6m|12m|all)$", description="Time period filter: 3m, 6m, 12m, all")
):
    """
    Returns observed price velocity, trajectory direction (RISING, STABLE, DECLINING),
    and evidence strength from historical market collections.
    """
    from backend.app.services.market_timing_service import market_timing_service
    return market_timing_service.analyze_market_timing(
        brand=brand,
        model=model,
        city=city,
        time_period=time_period
    )

