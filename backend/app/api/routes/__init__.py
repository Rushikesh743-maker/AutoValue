"""API routes registration module."""
from fastapi import APIRouter
from .health import router as health_router
from .valuation import router as valuation_router
from .comparables import router as comparables_router
from .market import router as market_router
from .explain import router as explain_router
from .sources import router as sources_router
from .models import router as models_router
from .data_quality import router as data_quality_router
from .auth import router as auth_router
from .valuations import router as valuations_router
from .saved_vehicles import router as saved_vehicles_router
from .shared import router as shared_router
from .comparison import router as comparison_router
from .intelligence import router as intelligence_router
from .watchlist import router as watchlist_router
from .risk import router as risk_router
from .tco import router as tco_router
from .forecast import router as forecast_router
from .lifecycle import router as lifecycle_router
from .garage import router as garage_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(valuation_router)
api_router.include_router(intelligence_router)
api_router.include_router(lifecycle_router)
api_router.include_router(garage_router)
api_router.include_router(risk_router)
api_router.include_router(tco_router)
api_router.include_router(forecast_router)
api_router.include_router(watchlist_router)
api_router.include_router(comparables_router)
api_router.include_router(market_router)
api_router.include_router(explain_router)
api_router.include_router(sources_router)
api_router.include_router(models_router)
api_router.include_router(data_quality_router)
api_router.include_router(auth_router)
api_router.include_router(valuations_router)
api_router.include_router(saved_vehicles_router)
api_router.include_router(shared_router)
api_router.include_router(comparison_router)

__all__ = ["api_router"]

