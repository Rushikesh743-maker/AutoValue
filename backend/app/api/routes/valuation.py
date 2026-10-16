"""
Valuation estimation API endpoints.
Connects input requests to the valuation service, comparable engine, and SHAP explainer.
"""
from fastapi import APIRouter, status, HTTPException, Depends
from ...schemas.valuation import ValuationRequestSchema, ValuationResponse
from ...services.valuation_service import valuation_service

from ...core.exceptions import AutoValueException, ModelNotFoundError

router = APIRouter(prefix="/valuation", tags=["Valuation"])


@router.post("", response_model=ValuationResponse, status_code=status.HTTP_200_OK)
@router.post("/", response_model=ValuationResponse, status_code=status.HTTP_200_OK)
def calculate_valuation(request: ValuationRequestSchema) -> ValuationResponse:
    """
    Computes vehicle fair market value estimate using trained regression artifacts,
    finds nearest active comparable listings, calculates empirical price ranges,
    and returns SHAP feature-level price explanations.
    """
    if not valuation_service.is_model_ready:
        raise ModelNotFoundError(
            valuation_service.model_version,
            "Valuation model is currently unavailable or initializing. Please ensure model training has been completed."
        )

    try:
        response = valuation_service.evaluate_valuation(request)
        return response
    except AutoValueException:
        raise
    except HTTPException:
        raise
    except Exception:
        raise AutoValueException("Valuation computation failed.", code="INTERNAL_SERVER_ERROR", status_code=500)


