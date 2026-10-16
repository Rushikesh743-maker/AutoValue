"""
AutoValue Decision Intelligence API Routes (Phase 11).
Coordinates Smart Deal Analysis, Negotiation Intelligence, Value-For-Money Scoring,
Data Confidence Evaluation, What-If Simulator, and Alternative Vehicle Discovery.
"""
import time
import uuid
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.schemas.intelligence import (
    DealAnalysis,
    NegotiationAnalysis,
    ValueScore,
    DataConfidence,
    ScenarioRequest,
    ScenarioResponse,
    AlternativeVehicleQuery,
    AlternativeVehicleResponse,
    MarketTiming,
    DecisionIntelligenceResponse
)
from backend.app.schemas.valuation import ValuationRequestSchema
from backend.app.services.valuation_service import valuation_service
from backend.app.services.deal_analysis_service import deal_analysis_service
from backend.app.services.negotiation_service import negotiation_service
from backend.app.services.value_score_service import value_score_service
from backend.app.services.data_confidence_service import data_confidence_service
from backend.app.services.scenario_service import scenario_service
from backend.app.services.alternative_vehicle_service import alternative_vehicle_service
from backend.app.services.market_timing_service import market_timing_service
from backend.app.services.market_forecast_service import market_forecast_service
from backend.app.services.risk_service import risk_service
from backend.app.services.tco_service import tco_service
from backend.app.services.telemetry import metrics_collector
from backend.app.core.exceptions import AutoValueException, ModelNotFoundError
from backend.app.schemas.forecast import ForecastRequest

logger = logging.getLogger("autovalue.intelligence_api")

router = APIRouter(tags=["Intelligence"])


@router.post(
    "/intelligence",
    response_model=DecisionIntelligenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute comprehensive decision intelligence for a vehicle"
)
def compute_decision_intelligence(request: ValuationRequestSchema) -> DecisionIntelligenceResponse:
    """
    Unified decision intelligence endpoint delivering:
    1. ML valuation & conformal uncertainty interval
    2. Market statistics & comparable listings
    3. Smart deal analysis & classification
    4. Evidence-supported negotiation targets & talking points
    5. Transparent Value-for-Money score breakdown
    6. Data confidence score & physical condition disclaimers
    7. Observed market timing & trajectory
    8. SHAP feature attributions
    9. Vehicle risk intelligence (Phase 12)
    10. TCO and resale projections (Phase 13)
    11. Market forecasting and buy/sell timing intelligence (Phase 14)
    """
    start_time = time.time()
    request_id = f"intel-{uuid.uuid4().hex[:8]}"

    if not valuation_service.is_model_ready:
        raise ModelNotFoundError(
            valuation_service.model_version,
            "Valuation model is currently unavailable or initializing."
        )

    # 1. Execute Core Valuation Pipeline
    val_response = valuation_service.evaluate_valuation(request)
    est_val = val_response.valuation.estimated_value
    m_interval = val_response.valuation.model_interval
    interval_low = m_interval.interval_low if m_interval else None
    interval_high = m_interval.interval_high if m_interval else None

    market_stats = val_response.market
    comparables = val_response.comparables or []

    # 2. Run Deal Analysis
    deal_res = deal_analysis_service.evaluate_deal(
        asking_price=request.asking_price,
        estimated_value=est_val,
        interval_low=interval_low,
        interval_high=interval_high,
        market_median=market_stats.median,
        market_p25=market_stats.p25,
        market_p75=market_stats.p75,
        comparables=[c.model_dump() for c in comparables]
    )

    # 3. Run Negotiation Intelligence
    negotiation_res = negotiation_service.analyze_negotiation(
        asking_price=request.asking_price,
        estimated_value=est_val,
        model_interval_low=interval_low,
        model_interval_high=interval_high,
        market_median=market_stats.median,
        market_p25=market_stats.p25,
        market_p75=market_stats.p75,
        comparable_count=len(comparables)
    )

    # 4. Run Value-for-Money Score
    value_res = value_score_service.calculate_value_score(
        year=request.year,
        km_driven=request.km_driven,
        estimated_value=est_val,
        asking_price=request.asking_price,
        market_median=market_stats.median,
        comparable_count=len(comparables)
    )

    # 5. Run Data Confidence & Limitations Layer
    confidence_res = data_confidence_service.evaluate_confidence(
        vehicle_data=request.model_dump(),
        comparable_count=len(comparables),
        estimated_value=est_val,
        interval_low=interval_low,
        interval_high=interval_high
    )

    # 6. Run Market Timing
    timing_res = market_timing_service.analyze_market_timing(
        brand=request.brand,
        model=request.model,
        city=request.city
    )

    # 7. Run Vehicle Risk & Trust Intelligence (Phase 12)
    risk_res = risk_service.evaluate_risk(request.model_dump(), val_response)

    # 8. Run Total Cost of Ownership & Resale Intelligence (Phase 13)
    try:
        tco_res = tco_service.calculate_tco(request.model_dump(), val_response)
        tco_dict = tco_res.model_dump()
    except Exception as e:
        logger.warning(f"Error computing TCO in decision intelligence: {e}")
        tco_dict = None

    # 9. Run Market Forecasting & Buy/Sell Timing (Phase 14)
    try:
        fc_req = ForecastRequest(
            brand=request.brand,
            model=request.model,
            variant=request.variant,
            year=request.year,
            fuel_type=request.fuel_type,
            transmission=request.transmission,
            km_driven=request.km_driven,
            city=request.city,
            asking_price=request.asking_price or est_val,
            horizon_days=365
        )
        fc_res = market_forecast_service.forecast_vehicle_market(fc_req)
        forecast_dict = fc_res.model_dump()
    except Exception as e:
        logger.warning(f"Error computing Forecast in decision intelligence: {e}")
        forecast_dict = None

    duration_ms = (time.time() - start_time) * 1000.0

    # Record telemetry
    metrics_collector.record_deal_analysis(deal_res.classification)
    metrics_collector.record_intelligence_latency(duration_ms)

    return DecisionIntelligenceResponse(
        request_id=request_id,
        vehicle=request.model_dump(),
        valuation=val_response.valuation,
        market_statistics=market_stats,
        deal_analysis=deal_res,
        negotiation=negotiation_res,
        value_score=value_res,
        confidence=confidence_res,
        market_timing=timing_res,
        shap_explanations=val_response.explanation,
        comparables=comparables,
        risk=risk_res.model_dump(),
        tco=tco_dict,
        forecast=forecast_dict
    )


@router.post(
    "/scenario",
    response_model=ScenarioResponse,
    status_code=status.HTTP_200_OK,
    summary="Interactive 'What If?' Vehicle Scenario Simulator"
)
def simulate_vehicle_scenario(payload: ScenarioRequest) -> ScenarioResponse:
    """
    Evaluates the marginal effect of mileage, manufacturing year, location,
    or powertrain modifications using the active XGBoost model.
    """
    start_time = time.time()
    res = scenario_service.simulate_scenario(payload)
    metrics_collector.record_scenario_request()
    return res


@router.post(
    "/alternatives",
    response_model=AlternativeVehicleResponse,
    status_code=status.HTTP_200_OK,
    summary="Discover evidence-supported alternative vehicles within budget"
)
def discover_alternatives(query: AlternativeVehicleQuery) -> AlternativeVehicleResponse:
    """
    Discovers closest alternative vehicle listings supported by empirical dataset.
    """
    start_time = time.time()
    res = alternative_vehicle_service.find_alternatives(query)
    metrics_collector.record_alternative_search()
    return res
