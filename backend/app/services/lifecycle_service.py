"""
AutoValue Vehicle Lifecycle & Ownership Decision Intelligence Engine (Phase 15).
Orchestrates existing valuation, market timing, risk, TCO, forecasting, deal analysis,
negotiation, and alternative vehicle discovery engines into a unified lifecycle decision platform.
"""
from typing import Dict, Any, List, Optional, Tuple
import os
import math
from datetime import datetime, timezone
import logging

from backend.app.schemas.lifecycle import (
    LifecycleAction,
    DecisionConfidence,
    FactorDirection,
    LifecycleScenarioType,
    DataIntegrityType,
    DecisionMode,
    LifecycleDecisionRequest,
    DecisionFactor,
    DecisionCategoryScore,
    DecisionScore,
    LifecycleHorizonOutlook,
    ReplacementCandidate,
    LifecycleScenario,
    DecisionSensitivity,
    LifecycleDecisionResponse,
    LifecycleScenarioRequest,
    LifecycleCompareRequest,
    LifecycleCompareItem,
    LifecycleCompareResponse,
    BatchLifecycleRequest,
    BatchLifecycleResponse
)
from backend.app.schemas.valuation import ValuationRequestSchema, ValuationResponse
from backend.app.schemas.tco import TCOAssumptions, TCOResponse
from backend.app.schemas.forecast import (
    ForecastRequest,
    ForecastResponse,
    TrendDirection,
    ForecastConfidenceLevel,
    TimingSignal,
    MarketVolatilityLevel
)
from backend.app.schemas.intelligence import (
    AlternativeVehicleQuery,
    AlternativeVehicleResponse,
    DealAnalysis
)

from backend.app.services.valuation_service import valuation_service
from backend.app.services.timing_service import timing_service
from backend.app.services.market_forecast_service import market_forecast_service
from backend.app.services.tco_service import TCOService
from backend.app.services.risk_service import RiskService
from backend.app.services.alternative_vehicle_service import AlternativeVehicleService
from backend.app.services.deal_analysis_service import DealAnalysisService
from backend.app.services.negotiation_service import NegotiationService
from backend.app.services.value_score_service import ValueScoreService
from backend.app.services.telemetry import metrics_collector

logger = logging.getLogger("autovalue.lifecycle_service")


class LifecycleService:
    """
    Unified Vehicle Lifecycle & Ownership Decision Intelligence Service.
    Integrates all Phase 1-14 analytical capabilities to answer:
    'What is the financially and market-wise sensible next action for this vehicle?'
    """

    VERSION = "lifecycle_v001"

    # Centralized transparent category weights (must sum to 1.0)
    WEIGHT_MARKET_POSITION = 0.20
    WEIGHT_OWNERSHIP_ECONOMICS = 0.25
    WEIGHT_FUTURE_MARKET_OUTLOOK = 0.15
    WEIGHT_VEHICLE_RISK = 0.15
    WEIGHT_TIMING = 0.15
    WEIGHT_ALTERNATIVE_OPPORTUNITY = 0.10

    def __init__(self):
        self.tco_service = TCOService()
        self.risk_service = RiskService()
        self.alternative_service = AlternativeVehicleService()
        self.deal_analysis_service = DealAnalysisService()
        self.negotiation_service = NegotiationService()
        self.value_score_service = ValueScoreService()

    @staticmethod
    def _format_inr(val: Optional[float]) -> str:
        if val is None:
            return "N/A"
        if val >= 10000000:
            return f"₹{val / 10000000:.2f} Cr"
        elif val >= 100000:
            return f"₹{val / 100000:.2f} Lakh"
        return f"₹{val:,.0f}"

    def _determine_mode(self, request: LifecycleDecisionRequest) -> DecisionMode:
        if request.mode is not None:
            return request.mode
        if request.ownership_years is not None or request.current_market_value is not None:
            return DecisionMode.OWNER
        if request.asking_price is not None:
            return DecisionMode.BUY
        return DecisionMode.BUY

    def evaluate_lifecycle(
        self,
        request: LifecycleDecisionRequest,
        valuation_response: Optional[ValuationResponse] = None,
        forecast_response: Optional[ForecastResponse] = None,
        risk_response: Optional[Any] = None,
        tco_response: Optional[TCOResponse] = None
    ) -> LifecycleDecisionResponse:
        """
        Main entry point for unified vehicle lifecycle decision intelligence.
        Supports optional precomputed responses to avoid redundant pipeline calculations.
        """
        import time
        start_t = time.time()
        now_iso = datetime.now(timezone.utc).isoformat()
        mode = self._determine_mode(request)

        # 1. Validation & Insufficient Evidence Guard
        missing_data = []
        if not request.brand or not str(request.brand).strip():
            missing_data.append("Vehicle brand is required")
        if not request.model or not str(request.model).strip():
            missing_data.append("Vehicle model is required")
        if request.year is None or request.year < 1990 or request.year > 2030:
            missing_data.append("Valid manufacturing year (1990-2030) is required")

        if missing_data:
            metrics_collector.record_lifecycle_request(
                LifecycleAction.INSUFFICIENT_EVIDENCE.value,
                DecisionConfidence.INSUFFICIENT_EVIDENCE.value,
                (time.time() - start_t) * 1000,
                is_insufficient=True
            )
            return self._build_insufficient_evidence_response(request, missing_data, now_iso, mode)

        # 2. Orchestrate Valuation Engine
        val_req = ValuationRequestSchema(
            brand=request.brand,
            model=request.model,
            variant=request.variant,
            year=request.year,
            fuel_type=request.fuel_type or "Petrol",
            transmission=request.transmission or "Manual",
            km_driven=request.km_driven if request.km_driven is not None else 35000,
            city=request.city or "Bengaluru",
            asking_price=request.asking_price
        )

        val_res = valuation_response
        if val_res is None:
            try:
                val_res = valuation_service.evaluate_valuation(val_req, include_shap=False)
            except Exception as e:
                logger.error(f"Valuation engine failure in lifecycle: {e}")
                missing_data.append(f"Valuation model inference failed: {str(e)}")
                return self._build_insufficient_evidence_response(request, missing_data, now_iso, mode)

        estimated_fair_value = val_res.valuation.estimated_value
        market_stats = val_res.market
        comparables = val_res.comparables or []
        comp_count = len(comparables)

        if comp_count == 0 and market_stats.median is None:
            missing_data.append("Insufficient historical and comparable market listings")
            return self._build_insufficient_evidence_response(request, missing_data, now_iso, mode)

        # 3. Resolve Current Effective Asset Value & Purchase Baseline
        if mode == DecisionMode.BUY:
            effective_price = request.asking_price if request.asking_price and request.asking_price > 0 else estimated_fair_value
            purchase_price_provenance = DataIntegrityType.USER_DEFINED if request.asking_price else DataIntegrityType.DERIVED
        else:
            effective_price = request.current_market_value if request.current_market_value and request.current_market_value > 0 else estimated_fair_value
            purchase_price_provenance = DataIntegrityType.USER_DEFINED if (request.purchase_price or request.current_market_value) else DataIntegrityType.DERIVED

        # 4. Orchestrate Market Forecast & Buy/Sell Timing Engine
        forecast_res = forecast_response
        if forecast_res is None:
            forecast_req = ForecastRequest(
                brand=request.brand,
                model=request.model,
                variant=request.variant,
                year=request.year,
                fuel_type=request.fuel_type,
                transmission=request.transmission,
                km_driven=request.km_driven or 35000,
                city=request.city or "Bengaluru",
                asking_price=effective_price,
                horizon_days=365
            )
            try:
                forecast_res = market_forecast_service.forecast_vehicle_market(forecast_req)
            except Exception as e:
                logger.warning(f"Market forecast engine fallback: {e}")
                forecast_res = None

        trend_dir = forecast_res.overall_trend if (forecast_res and forecast_res.overall_trend) else TrendDirection.STABLE
        volatility_level = forecast_res.volatility.level if (forecast_res and forecast_res.volatility) else MarketVolatilityLevel.LOW
        forecast_conf = forecast_res.forecast_confidence if (forecast_res and forecast_res.forecast_confidence) else ForecastConfidenceLevel.MODERATE
        forecast_conf_score = forecast_res.forecast_confidence_score if forecast_res else 60.0
        momentum_90d = forecast_res.momentum.m90d.price_change_pct if (forecast_res and forecast_res.momentum and forecast_res.momentum.m90d and forecast_res.momentum.m90d.price_change_pct is not None) else 0.0

        buy_timing_score = forecast_res.buy_timing.score if (forecast_res and forecast_res.buy_timing and forecast_res.buy_timing.score is not None) else 50.0
        sell_timing_score = forecast_res.sell_timing.score if (forecast_res and forecast_res.sell_timing and forecast_res.sell_timing.score is not None) else 50.0

        # 6. Orchestrate Risk Service
        risk_res = risk_response
        if risk_res is None:
            risk_res = self.risk_service.evaluate_risk(val_req, val_res)
        risk_score = risk_res.risk_score
        risk_level = risk_res.risk_level

        # 7. Orchestrate TCO Service
        annual_km = request.annual_km if request.annual_km is not None else 12000
        tco_res = tco_response
        if tco_res is None:
            tco_assumptions = TCOAssumptions(
                annual_km=annual_km,
                ownership_years=5,
                purchase_price_mode="CUSTOM" if (mode == DecisionMode.BUY and request.asking_price) else "FAIR_VALUE",
                custom_purchase_price=effective_price
            )
            tco_res = self.tco_service.calculate_tco(val_req, val_res, tco_assumptions)
        five_year_tco = tco_res.ownership.net_tco
        cost_per_km_5y = tco_res.ownership.cost_per_km
        resale_5y = tco_res.resale.estimated_resale_value
        annual_deprec_rate = tco_res.resale.annual_depreciation_rate

        # 8. Orchestrate Deal Analysis
        deal_analysis: Optional[DealAnalysis] = None
        if request.asking_price and request.asking_price > 0:
            deal_analysis = self.deal_analysis_service.evaluate_deal(
                asking_price=request.asking_price,
                estimated_value=estimated_fair_value,
                interval_low=val_res.valuation.model_interval.interval_low if val_res.valuation.model_interval else None,
                interval_high=val_res.valuation.model_interval.interval_high if val_res.valuation.model_interval else None,
                market_median=market_stats.median,
                market_p25=market_stats.p25,
                market_p75=market_stats.p75,
                comparables=comparables
            )

        # 9. Discover & Evaluate Replacement Alternatives
        replacement_candidates: List[ReplacementCandidate] = []
        best_candidate: Optional[ReplacementCandidate] = None
        if request.include_alternatives:
            replacement_candidates, best_candidate = self._evaluate_replacements(
                request=request,
                current_fair_value=estimated_fair_value,
                current_5y_tco=five_year_tco,
                current_5y_resale=resale_5y,
                annual_km=annual_km,
                current_risk_score=risk_score
            )

        # 10. Multi-Pillar Decision Scoring (0-100)
        category_scores = self._compute_category_scores(
            mode=mode,
            request=request,
            estimated_fair_value=estimated_fair_value,
            deal_analysis=deal_analysis,
            five_year_tco=five_year_tco,
            cost_per_km_5y=cost_per_km_5y,
            annual_deprec_rate=annual_deprec_rate,
            trend_dir=trend_dir,
            volatility_level=volatility_level,
            momentum_90d=momentum_90d,
            risk_score=risk_score,
            buy_timing_score=buy_timing_score,
            sell_timing_score=sell_timing_score,
            best_candidate=best_candidate
        )

        overall_decision_score = sum(c.contribution for c in category_scores)

        # 11. Deterministic Action Selection & Margin Computation
        winning_action, secondary_action, decision_margin, action_scores = self._select_action(
            mode=mode,
            request=request,
            category_scores=category_scores,
            estimated_fair_value=estimated_fair_value,
            deal_analysis=deal_analysis,
            buy_timing_score=buy_timing_score,
            sell_timing_score=sell_timing_score,
            risk_score=risk_score,
            trend_dir=trend_dir,
            annual_deprec_rate=annual_deprec_rate,
            best_candidate=best_candidate,
            comp_count=comp_count
        )

        decision_score_obj = DecisionScore(
            overall_score=round(overall_decision_score, 1),
            category_breakdown=category_scores,
            decision_margin=round(decision_margin, 1),
            winning_action=winning_action,
            secondary_action=secondary_action,
            action_scores={k: round(v, 1) for k, v in action_scores.items()}
        )

        # 12. Decision Confidence Computation
        confidence_level, confidence_score, confidence_reasons = self._compute_decision_confidence(
            comp_count=comp_count,
            forecast_conf=forecast_conf,
            forecast_conf_score=forecast_conf_score,
            decision_margin=decision_margin,
            risk_score=risk_score,
            has_asking_price=bool(request.asking_price or request.current_market_value)
        )

        # 13. Explanatory Positive & Negative Factors
        positive_factors, negative_factors = self._generate_decision_factors(
            action=winning_action,
            mode=mode,
            request=request,
            estimated_fair_value=estimated_fair_value,
            deal_analysis=deal_analysis,
            buy_timing_score=buy_timing_score,
            sell_timing_score=sell_timing_score,
            trend_dir=trend_dir,
            volatility_level=volatility_level,
            momentum_90d=momentum_90d,
            five_year_tco=five_year_tco,
            annual_deprec_rate=annual_deprec_rate,
            risk_score=risk_score,
            best_candidate=best_candidate
        )

        # 14. Multi-Horizon Outlooks (1Y, 3Y, 5Y)
        horizon_outlooks = self._build_horizon_outlooks(
            tco_res=tco_res,
            annual_km=annual_km,
            best_candidate=best_candidate
        )

        # 15. Lifecycle Scenarios (CONSERVATIVE, BASE, OPTIMISTIC)
        scenarios = self._build_lifecycle_scenarios(
            base_action=winning_action,
            base_score=overall_decision_score,
            tco_res=tco_res,
            trend_dir=trend_dir
        )

        # 16. Decision Sensitivities
        sensitivities = self._compute_sensitivities(
            action=winning_action,
            mode=mode,
            request=request,
            estimated_fair_value=estimated_fair_value,
            annual_km=annual_km,
            buy_timing_score=buy_timing_score,
            sell_timing_score=sell_timing_score,
            best_candidate=best_candidate
        )

        # 17. Structured Reasonings
        economic_reasoning, market_reasoning, ownership_reasoning = self._generate_reasonings(
            action=winning_action,
            mode=mode,
            decision_score=overall_decision_score,
            decision_margin=decision_margin,
            five_year_tco=five_year_tco,
            cost_per_km=cost_per_km_5y,
            trend_dir=trend_dir,
            buy_timing_score=buy_timing_score,
            sell_timing_score=sell_timing_score,
            risk_score=risk_score,
            best_candidate=best_candidate
        )

        # 18. Structured Considerations
        risk_considerations = [
            f"Observable vehicle & market risk score is {risk_score}/100 ({risk_level} severity).",
            f"Physical mechanical, chassis, flood immersion, and battery health remain uninspected.",
            "Valuation based on empirical market listings with conformal uncertainty intervals."
        ]
        forecast_considerations = [
            f"Observed 90-day price momentum is {momentum_90d:+.1f}% with {trend_dir.value} trajectory.",
            f"Market volatility classified as {volatility_level.value} dispersion across active channels.",
            f"Forecast confidence is {forecast_conf.value} (score: {forecast_conf_score:.0f}/100)."
        ]
        resale_considerations = [
            f"Projected 5-year residual value is {self._format_inr(resale_5y)} ({100 - (annual_deprec_rate * 5):.1f}% retention estimate).",
            f"Average annual depreciation rate is calibrated at {annual_deprec_rate:.1f}% per annum.",
            "Resale estimates assume standard usage and regular authorized maintenance."
        ]
        tco_considerations = [
            f"Estimated 5-year cumulative ownership expenditure is {self._format_inr(five_year_tco)}.",
            f"Effective operational cost is {self._format_inr(cost_per_km_5y)}/km based on {annual_km:,} annual km.",
            "Includes fuel, insurance, schedule maintenance, and depreciation."
        ]

        assumptions = [
            f"Annual driving distance baseline: {annual_km:,} km/year.",
            f"Evaluation horizon: 5 years with {request.scenario.value if request.scenario else 'BASE'} scenario parameters.",
            "Fuel prices calibrated at prevailing regional market rates.",
            "Insurance rate calculated at 3.0% annual vehicle depreciated value."
        ]

        limitations = [
            "AutoValue is an algorithmic decision-support tool, not financial, investment, or mechanical advice.",
            "Physical vehicle condition, internal mechanical wear, and chassis integrity cannot be verified online.",
            "Future resale values and ownership costs are evidence-grounded statistical projections, not guaranteed returns."
        ]

        # Alternative actions rankings
        ranked_actions = []
        for act_name, act_score in sorted(action_scores.items(), key=lambda x: x[1], reverse=True):
            if act_name != winning_action.value:
                ranked_actions.append({
                    "action": act_name,
                    "score": round(act_score, 1),
                    "score_diff": round(overall_decision_score - act_score, 1)
                })

        duration_ms = (time.time() - start_t) * 1000
        metrics_collector.record_lifecycle_request(
            winning_action.value,
            confidence_level.value,
            duration_ms,
            is_insufficient=False
        )

        return LifecycleDecisionResponse(
            decision_version=self.VERSION,
            timestamp=now_iso,
            mode=mode.value,
            vehicle_summary={
                "brand": request.brand,
                "model": request.model,
                "variant": request.variant,
                "year": request.year,
                "fuel_type": request.fuel_type or "Petrol",
                "transmission": request.transmission or "Manual",
                "km_driven": request.km_driven or 35000,
                "city": request.city or "Bengaluru",
                "estimated_fair_value": estimated_fair_value,
                "estimated_fair_value_formatted": self._format_inr(estimated_fair_value),
                "effective_price": effective_price,
                "effective_price_formatted": self._format_inr(effective_price),
                "price_provenance": purchase_price_provenance.value
            },
            recommended_action=winning_action,
            decision_score=decision_score_obj,
            confidence=confidence_level,
            confidence_score=round(confidence_score, 1),
            confidence_reasons=confidence_reasons,
            alternative_actions=ranked_actions,
            positive_factors=positive_factors,
            negative_factors=negative_factors,
            economic_reasoning=economic_reasoning,
            market_reasoning=market_reasoning,
            ownership_reasoning=ownership_reasoning,
            risk_considerations=risk_considerations,
            forecast_considerations=forecast_considerations,
            resale_considerations=resale_considerations,
            tco_considerations=tco_considerations,
            horizon_outlooks=horizon_outlooks,
            scenarios=scenarios,
            replacement_candidates=replacement_candidates,
            best_replacement_candidate=best_candidate,
            decision_sensitivities=sensitivities,
            missing_data=[],
            assumptions=assumptions,
            limitations=limitations,
            audit_trail={
                "version": self.VERSION,
                "mode": mode.value,
                "weights": {
                    "market_position": self.WEIGHT_MARKET_POSITION,
                    "ownership_economics": self.WEIGHT_OWNERSHIP_ECONOMICS,
                    "future_market_outlook": self.WEIGHT_FUTURE_MARKET_OUTLOOK,
                    "vehicle_risk": self.WEIGHT_VEHICLE_RISK,
                    "timing": self.WEIGHT_TIMING,
                    "alternative_opportunity": self.WEIGHT_ALTERNATIVE_OPPORTUNITY
                },
                "valuation_id": val_res.valuation.estimated_value,
                "comparable_count": comp_count,
                "calculation_latency_ms": round(duration_ms, 2)
            }
        )

    def _build_insufficient_evidence_response(
        self,
        request: LifecycleDecisionRequest,
        missing_data: List[str],
        timestamp: str,
        mode: DecisionMode
    ) -> LifecycleDecisionResponse:
        """
        Builds graceful, informative INSUFFICIENT_EVIDENCE lifecycle response.
        """
        empty_score = DecisionScore(
            overall_score=0.0,
            category_breakdown=[
                DecisionCategoryScore(
                    category_name="Market Position",
                    score=0.0,
                    weight=self.WEIGHT_MARKET_POSITION,
                    contribution=0.0,
                    reasoning="Insufficient market data"
                ),
                DecisionCategoryScore(
                    category_name="Ownership Economics",
                    score=0.0,
                    weight=self.WEIGHT_OWNERSHIP_ECONOMICS,
                    contribution=0.0,
                    reasoning="Insufficient economic data"
                ),
                DecisionCategoryScore(
                    category_name="Future Market Outlook",
                    score=0.0,
                    weight=self.WEIGHT_FUTURE_MARKET_OUTLOOK,
                    contribution=0.0,
                    reasoning="Insufficient forecast data"
                ),
                DecisionCategoryScore(
                    category_name="Vehicle/Market Risk",
                    score=0.0,
                    weight=self.WEIGHT_VEHICLE_RISK,
                    contribution=0.0,
                    reasoning="Insufficient risk evidence"
                ),
                DecisionCategoryScore(
                    category_name="Timing",
                    score=0.0,
                    weight=self.WEIGHT_TIMING,
                    contribution=0.0,
                    reasoning="Insufficient timing indicators"
                ),
                DecisionCategoryScore(
                    category_name="Alternative Opportunity",
                    score=0.0,
                    weight=self.WEIGHT_ALTERNATIVE_OPPORTUNITY,
                    contribution=0.0,
                    reasoning="Insufficient alternative data"
                )
            ],
            decision_margin=0.0,
            winning_action=LifecycleAction.INSUFFICIENT_EVIDENCE,
            secondary_action=None,
            action_scores={}
        )

        return LifecycleDecisionResponse(
            decision_version=self.VERSION,
            timestamp=timestamp,
            mode=mode.value,
            vehicle_summary={
                "brand": request.brand or "Unknown",
                "model": request.model or "Unknown",
                "variant": request.variant,
                "year": request.year or 2020
            },
            recommended_action=LifecycleAction.INSUFFICIENT_EVIDENCE,
            decision_score=empty_score,
            confidence=DecisionConfidence.INSUFFICIENT_EVIDENCE,
            confidence_score=0.0,
            confidence_reasons=["Required empirical evidence or vehicle attributes are missing."],
            alternative_actions=[],
            positive_factors=[],
            negative_factors=[
                DecisionFactor(
                    category="Evidence Completeness",
                    factor_text="Critical data missing: " + ", ".join(missing_data),
                    direction=FactorDirection.NEGATIVE,
                    metric_name="missing_fields_count",
                    metric_value=len(missing_data),
                    impact_weight=1.0,
                    source_type=DataIntegrityType.USER_DEFINED
                )
            ],
            economic_reasoning="Unable to evaluate ownership economics due to missing vehicle or market inputs.",
            market_reasoning="Market position cannot be calculated without sufficient marketplace evidence.",
            ownership_reasoning="Ownership outlook requires complete vehicle specifications.",
            risk_considerations=["Risk indicators cannot be safely generated with missing inputs."],
            forecast_considerations=["Forecast models require active historical time series data."],
            resale_considerations=["Resale depreciation curves require baseline valuation."],
            tco_considerations=["TCO calculations require verified vehicle specifications."],
            horizon_outlooks=[],
            scenarios=[],
            replacement_candidates=[],
            best_replacement_candidate=None,
            decision_sensitivities=[],
            missing_data=missing_data,
            assumptions=[],
            limitations=["System refused recommendation due to insufficient evidence guard."],
            audit_trail={"insufficient_evidence": True, "missing_data": missing_data}
        )

    def _compute_category_scores(
        self,
        mode: DecisionMode,
        request: LifecycleDecisionRequest,
        estimated_fair_value: float,
        deal_analysis: Optional[DealAnalysis],
        five_year_tco: float,
        cost_per_km_5y: float,
        annual_deprec_rate: float,
        trend_dir: TrendDirection,
        volatility_level: MarketVolatilityLevel,
        momentum_90d: float,
        risk_score: float,
        buy_timing_score: float,
        sell_timing_score: float,
        best_candidate: Optional[ReplacementCandidate]
    ) -> List[DecisionCategoryScore]:
        """
        Computes transparent 0-100 scores across all 6 decision pillars.
        """
        # 1. Market Position Score (20%)
        if mode == DecisionMode.BUY:
            if deal_analysis and deal_analysis.percentage_difference_from_ml is not None:
                # E.g. -8% discount -> score 85; 0% -> 70; +10% premium -> 35
                diff_pct = deal_analysis.percentage_difference_from_ml
                if diff_pct <= -10.0:
                    mp_score = min(100.0, 85.0 + (-diff_pct - 10.0) * 1.5)
                elif diff_pct <= 0.0:
                    mp_score = 70.0 + (-diff_pct / 10.0) * 15.0
                elif diff_pct <= 10.0:
                    mp_score = max(35.0, 70.0 - (diff_pct / 10.0) * 35.0)
                else:
                    mp_score = max(10.0, 35.0 - (diff_pct - 10.0) * 1.5)
                mp_reason = f"Asking price is {abs(diff_pct):.1f}% {'below' if diff_pct < 0 else 'above'} fair market value."
            else:
                mp_score = 70.0
                mp_reason = "Vehicle fair market value aligns with comparable segment median."
        else:
            # Owner mode: evaluate value retention and market strength
            if momentum_90d >= 2.0:
                mp_score = 85.0
                mp_reason = f"Market prices for this model are rising (+{momentum_90d:.1f}% over 90D)."
            elif momentum_90d >= -2.0:
                mp_score = 72.0
                mp_reason = "Market valuation is stable relative to historical 180-day baseline."
            else:
                mp_score = 52.0
                mp_reason = f"Market prices are experiencing downward pressure ({momentum_90d:.1f}% over 90D)."

        # 2. Ownership Economics Score (25%)
        # Lower cost/km and lower annual depreciation yield higher score
        if cost_per_km_5y <= 9.0:
            econ_score = 90.0
        elif cost_per_km_5y <= 13.0:
            econ_score = 78.0
        elif cost_per_km_5y <= 18.0:
            econ_score = 65.0
        elif cost_per_km_5y <= 25.0:
            econ_score = 50.0
        else:
            econ_score = 35.0

        if annual_deprec_rate <= 7.0:
            econ_score = min(100.0, econ_score + 8.0)
        elif annual_deprec_rate >= 10.0:
            econ_score = max(0.0, econ_score - 8.0)

        econ_reason = f"5Y TCO estimated at {self._format_inr(five_year_tco)} ({self._format_inr(cost_per_km_5y)}/km, {annual_deprec_rate:.1f}% annual depreciation)."

        # 3. Future Market Outlook Score (15%)
        if trend_dir == TrendDirection.RISING:
            f_score = 88.0
            f_reason = "Forecast indicates rising price momentum and favorable liquidity."
        elif trend_dir == TrendDirection.STABLE:
            f_score = 75.0
            f_reason = "Forecast projects stable price retention across 12-month horizon."
        elif trend_dir == TrendDirection.DECLINING:
            f_score = 48.0
            f_reason = "Forecast projects accelerating depreciation or declining market demand."
        else:
            f_score = 60.0
            f_reason = "Market forecast indicates moderate price retention."

        if volatility_level == MarketVolatilityLevel.HIGH:
            f_score = max(0.0, f_score - 10.0)

        # 4. Vehicle / Market Risk Score (15%)
        # Low risk score (e.g. 20) -> High safety score (80)
        v_risk_score = max(0.0, min(100.0, 100.0 - risk_score))
        v_risk_reason = f"Observable vehicle risk evaluated at {risk_score:.0f}/100."

        # 5. Timing Score (15%)
        if mode == DecisionMode.BUY:
            t_score = buy_timing_score
            t_reason = f"Buy timing score calculated at {buy_timing_score:.0f}/100."
        else:
            # Owner mode
            t_score = sell_timing_score if sell_timing_score >= 60 else (100.0 - sell_timing_score)
            t_reason = f"Market timing indicators: Sell {sell_timing_score:.0f}/100, Buy {buy_timing_score:.0f}/100."

        # 6. Alternative Opportunity Score (10%)
        if best_candidate and best_candidate.replacement_advantage_score > 0:
            alt_score = best_candidate.replacement_advantage_score
            alt_reason = f"Best alternative ({best_candidate.brand} {best_candidate.model}) offers {self._format_inr(best_candidate.tco_savings_5y)} 5Y savings."
        else:
            alt_score = 40.0
            alt_reason = "Current vehicle remains highly competitive against available marketplace alternatives."

        return [
            DecisionCategoryScore(
                category_name="Market Position",
                score=round(mp_score, 1),
                weight=self.WEIGHT_MARKET_POSITION,
                contribution=round(mp_score * self.WEIGHT_MARKET_POSITION, 2),
                reasoning=mp_reason
            ),
            DecisionCategoryScore(
                category_name="Ownership Economics",
                score=round(econ_score, 1),
                weight=self.WEIGHT_OWNERSHIP_ECONOMICS,
                contribution=round(econ_score * self.WEIGHT_OWNERSHIP_ECONOMICS, 2),
                reasoning=econ_reason
            ),
            DecisionCategoryScore(
                category_name="Future Market Outlook",
                score=round(f_score, 1),
                weight=self.WEIGHT_FUTURE_MARKET_OUTLOOK,
                contribution=round(f_score * self.WEIGHT_FUTURE_MARKET_OUTLOOK, 2),
                reasoning=f_reason
            ),
            DecisionCategoryScore(
                category_name="Vehicle/Market Risk",
                score=round(v_risk_score, 1),
                weight=self.WEIGHT_VEHICLE_RISK,
                contribution=round(v_risk_score * self.WEIGHT_VEHICLE_RISK, 2),
                reasoning=v_risk_reason
            ),
            DecisionCategoryScore(
                category_name="Timing",
                score=round(t_score, 1),
                weight=self.WEIGHT_TIMING,
                contribution=round(t_score * self.WEIGHT_TIMING, 2),
                reasoning=t_reason
            ),
            DecisionCategoryScore(
                category_name="Alternative Opportunity",
                score=round(alt_score, 1),
                weight=self.WEIGHT_ALTERNATIVE_OPPORTUNITY,
                contribution=round(alt_score * self.WEIGHT_ALTERNATIVE_OPPORTUNITY, 2),
                reasoning=alt_reason
            )
        ]

    def _select_action(
        self,
        mode: DecisionMode,
        request: LifecycleDecisionRequest,
        category_scores: List[DecisionCategoryScore],
        estimated_fair_value: float,
        deal_analysis: Optional[DealAnalysis],
        buy_timing_score: float,
        sell_timing_score: float,
        risk_score: float,
        trend_dir: TrendDirection,
        annual_deprec_rate: float,
        best_candidate: Optional[ReplacementCandidate],
        comp_count: int
    ) -> Tuple[LifecycleAction, Optional[LifecycleAction], float, Dict[str, float]]:
        """
        Determines the winning lifecycle action and computes decision margin.
        """
        scores_by_cat = {c.category_name: c.score for c in category_scores}
        mp = scores_by_cat.get("Market Position", 70.0)
        econ = scores_by_cat.get("Ownership Economics", 70.0)
        outlook = scores_by_cat.get("Future Market Outlook", 70.0)
        risk_safety = scores_by_cat.get("Vehicle/Market Risk", 70.0)
        timing = scores_by_cat.get("Timing", 50.0)
        alt_opp = scores_by_cat.get("Alternative Opportunity", 40.0)

        action_scores: Dict[str, float] = {}

        if mode == DecisionMode.BUY:
            # Evaluate BUY, WAIT, REPLACE
            # BUY score: driven by attractive pricing (mp), good buy timing, low risk, competitive TCO
            buy_score = (mp * 0.35) + (timing * 0.25) + (econ * 0.20) + (risk_safety * 0.20)
            action_scores[LifecycleAction.BUY.value] = buy_score

            # WAIT score: driven by weak buy timing, declining price momentum (prices dropping soon), elevated asking price
            wait_score = ((100.0 - timing) * 0.40) + ((100.0 - mp) * 0.30) + (outlook * 0.30)
            action_scores[LifecycleAction.WAIT.value] = wait_score

            # REPLACE / ALTERNATIVE score: driven by presence of drastically better alternatives
            if best_candidate and best_candidate.replacement_advantage_score >= 65:
                replace_score = (best_candidate.replacement_advantage_score * 0.60) + (econ * 0.40)
                action_scores[LifecycleAction.REPLACE.value] = replace_score

        else:
            # Mode OWNER: Evaluate KEEP, SELL_NOW, WAIT, REPLACE
            # KEEP score: favorable ownership economics, low risk, low replacement advantage, stable market
            keep_score = (econ * 0.35) + (risk_safety * 0.25) + ((100.0 - alt_opp) * 0.20) + (outlook * 0.20)
            action_scores[LifecycleAction.KEEP.value] = keep_score

            # SELL_NOW score: elevated sell timing, high current market value, high upcoming depreciation or high risk
            sell_score = (sell_timing_score * 0.35) + (mp * 0.25) + ((100.0 - outlook) * 0.20) + ((100.0 - econ) * 0.20)
            action_scores[LifecycleAction.SELL_NOW.value] = sell_score

            # WAIT score: rising market momentum, low depreciation urgency
            wait_score = (outlook * 0.40) + ((100.0 - sell_timing_score) * 0.30) + (econ * 0.30)
            action_scores[LifecycleAction.WAIT.value] = wait_score

            # REPLACE score: superior alternative with positive 5Y savings, high break-even feasibility
            if best_candidate and best_candidate.replacement_advantage_score >= 60 and best_candidate.tco_savings_5y > 0:
                replace_score = (best_candidate.replacement_advantage_score * 0.50) + ((100.0 - econ) * 0.30) + (risk_safety * 0.20)
            else:
                replace_score = max(20.0, (alt_opp * 0.6) + ((100.0 - econ) * 0.4))
            action_scores[LifecycleAction.REPLACE.value] = replace_score

        # Sort actions by score
        sorted_actions = sorted(action_scores.items(), key=lambda x: x[1], reverse=True)
        winning_action = LifecycleAction(sorted_actions[0][0])
        secondary_action = LifecycleAction(sorted_actions[1][0]) if len(sorted_actions) > 1 else None
        decision_margin = sorted_actions[0][1] - sorted_actions[1][1] if len(sorted_actions) > 1 else 15.0

        return winning_action, secondary_action, decision_margin, action_scores

    def _compute_decision_confidence(
        self,
        comp_count: int,
        forecast_conf: ForecastConfidenceLevel,
        forecast_conf_score: float,
        decision_margin: float,
        risk_score: float,
        has_asking_price: bool
    ) -> Tuple[DecisionConfidence, float, List[str]]:
        """
        Computes calibrated decision confidence and plain-language reasoning.
        """
        reasons = []
        conf_score = 50.0

        # Evidence density contribution
        if comp_count >= 8:
            conf_score += 20.0
            reasons.append(f"Strong evidence density with {comp_count} verified marketplace comparables.")
        elif comp_count >= 4:
            conf_score += 10.0
            reasons.append(f"Moderate evidence density with {comp_count} verified marketplace comparables.")
        else:
            conf_score -= 10.0
            reasons.append(f"Limited comparable listings ({comp_count} found) in active market.")

        # Forecast confidence contribution
        if forecast_conf == ForecastConfidenceLevel.HIGH:
            conf_score += 15.0
            reasons.append("High confidence in temporal time-series and depreciation trajectory.")
        elif forecast_conf == ForecastConfidenceLevel.MODERATE:
            conf_score += 5.0
        else:
            conf_score -= 10.0
            reasons.append("Moderate or limited historical market depth for forecasting.")

        # Decision margin contribution
        if decision_margin >= 15.0:
            conf_score += 15.0
            reasons.append(f"Decisive margin (+{decision_margin:.1f} points) over alternative actions.")
        elif decision_margin >= 6.0:
            conf_score += 5.0
        else:
            conf_score -= 10.0
            reasons.append(f"Tight decision margin (+{decision_margin:.1f} points) suggests sensitive trade-offs.")

        # Risk penalty
        if risk_score > 65.0:
            conf_score -= 10.0
            reasons.append("Elevated market/pricing risk increases recommendation uncertainty.")

        conf_score = max(10.0, min(100.0, conf_score))

        if conf_score >= 75.0:
            conf_level = DecisionConfidence.HIGH
        elif conf_score >= 50.0:
            conf_level = DecisionConfidence.MODERATE
        else:
            conf_level = DecisionConfidence.LOW

        return conf_level, conf_score, reasons

    def _evaluate_replacements(
        self,
        request: LifecycleDecisionRequest,
        current_fair_value: float,
        current_5y_tco: float,
        current_5y_resale: float,
        annual_km: int,
        current_risk_score: float
    ) -> Tuple[List[ReplacementCandidate], Optional[ReplacementCandidate]]:
        """
        Discovers and ranks replacement alternatives from the active marketplace dataset.
        """
        alt_query = AlternativeVehicleQuery(
            target_budget=current_fair_value,
            budget_min=max(50000.0, current_fair_value * 0.70),
            budget_max=current_fair_value * 1.40,
            city=request.city,
            limit=5
        )

        alt_resp: AlternativeVehicleResponse = self.alternative_service.find_alternatives(alt_query)
        candidates: List[ReplacementCandidate] = []

        for idx, item in enumerate(alt_resp.results):
            # Compute quick candidate TCO & Resale
            c_val_req = ValuationRequestSchema(
                brand=item.brand,
                model=item.model,
                variant=item.variant,
                year=item.year,
                fuel_type=item.fuel_type or "Petrol",
                transmission=item.transmission or "Manual",
                km_driven=item.km_driven or 35000,
                city=item.city or request.city or "Bengaluru",
                asking_price=item.listed_price
            )
            try:
                c_val_res = valuation_service.evaluate_valuation(c_val_req, include_shap=False)
                c_fair_val = c_val_res.valuation.estimated_value
                c_tco_assump = TCOAssumptions(
                    annual_km=annual_km,
                    ownership_years=5,
                    purchase_price_mode="CUSTOM" if item.listed_price else "FAIR_VALUE",
                    custom_purchase_price=item.listed_price or c_fair_val
                )
                c_tco_res = self.tco_service.calculate_tco(c_val_req, c_val_res, c_tco_assump)
                c_5y_tco = c_tco_res.ownership.net_tco
                c_cost_km = c_tco_res.ownership.cost_per_km
                c_resale = c_tco_res.resale.estimated_resale_value
            except Exception as e:
                logger.warning(f"Failed to evaluate candidate {item.model}: {e}")
                continue

            # Compute timing & risk for candidate
            c_fc_req = ForecastRequest(
                brand=item.brand,
                model=item.model,
                variant=item.variant,
                year=item.year,
                fuel_type=item.fuel_type,
                transmission=item.transmission,
                km_driven=item.km_driven or 35000,
                city=item.city or request.city or "Bengaluru",
                asking_price=item.listed_price or c_fair_val,
                horizon_days=365
            )
            try:
                c_fc = market_forecast_service.forecast_vehicle_market(c_fc_req)
                c_buy_timing = c_fc.buy_timing.score if (c_fc.buy_timing and c_fc.buy_timing.score is not None) else 50.0
                c_trend = c_fc.overall_trend.value if c_fc.overall_trend else "STABLE"
            except Exception:
                c_buy_timing = 50.0
                c_trend = "STABLE"

            c_risk = self.risk_service.evaluate_risk(c_val_req, c_val_res)
            c_risk_score = c_risk.risk_score

            # Economic comparison
            tco_savings = current_5y_tco - c_5y_tco
            resale_diff = c_resale - current_5y_resale
            purchase_price = item.listed_price or c_fair_val

            # Replacement break-even calculation
            # acquisition_cost_diff = max(0, purchase_price - current_fair_value)
            # annual_savings = tco_savings / 5.0
            acquisition_diff = max(0.0, purchase_price - current_fair_value)
            annual_savings = tco_savings / 5.0
            if annual_savings > 0.0:
                if acquisition_diff > 0.0:
                    break_even_months = round(acquisition_diff / (annual_savings / 12.0), 1)
                else:
                    break_even_months = 0.0  # Cheaper acquisition + lower operating cost
            else:
                break_even_months = None

            # Multi-factor replacement advantage score (0-100)
            # Higher when savings are positive, risk is lower, buy timing is favorable
            adv_score = 50.0
            if tco_savings > 0:
                adv_score += min(30.0, (tco_savings / 100000.0) * 15.0)
            else:
                adv_score -= min(30.0, (abs(tco_savings) / 100000.0) * 15.0)

            if c_risk_score < current_risk_score:
                adv_score += min(10.0, (current_risk_score - c_risk_score) * 0.5)
            if c_buy_timing > 60.0:
                adv_score += 10.0

            adv_score = max(0.0, min(100.0, adv_score))

            if tco_savings > 50000:
                reason = f"Delivers {self._format_inr(tco_savings)} lower 5Y ownership cost with attractive buy timing ({c_buy_timing:.0f}/100)."
            elif tco_savings > 0:
                reason = f"Marginal 5Y TCO savings of {self._format_inr(tco_savings)}."
            else:
                reason = f"Higher 5Y ownership cost (+{self._format_inr(abs(tco_savings))}) than current vehicle."

            cand = ReplacementCandidate(
                id=f"alt_{idx+1}_{item.brand}_{item.model}".lower().replace(" ", "_"),
                brand=item.brand,
                model=item.model,
                variant=item.variant,
                year=item.year,
                fuel_type=item.fuel_type,
                transmission=item.transmission,
                estimated_purchase_price=purchase_price,
                estimated_purchase_price_formatted=self._format_inr(purchase_price),
                fair_value=c_fair_val,
                five_year_tco=c_5y_tco,
                five_year_tco_formatted=self._format_inr(c_5y_tco),
                cost_per_km=c_cost_km,
                projected_resale=c_resale,
                projected_resale_formatted=self._format_inr(c_resale),
                risk_level=c_risk.risk_level,
                risk_score=c_risk_score,
                buy_timing_score=c_buy_timing,
                forecast_direction="STABLE",
                tco_savings_5y=tco_savings,
                tco_savings_5y_formatted=f"{'+' if tco_savings >= 0 else ''}{self._format_inr(tco_savings)}",
                resale_advantage=resale_diff,
                replacement_advantage_score=round(adv_score, 1),
                break_even_months=break_even_months,
                recommendation_reason=reason
            )
            candidates.append(cand)

        # Sort candidates by replacement advantage score
        candidates.sort(key=lambda c: c.replacement_advantage_score, reverse=True)
        best_cand = candidates[0] if candidates else None

        return candidates, best_cand

    def _generate_decision_factors(
        self,
        action: LifecycleAction,
        mode: DecisionMode,
        request: LifecycleDecisionRequest,
        estimated_fair_value: float,
        deal_analysis: Optional[DealAnalysis],
        buy_timing_score: float,
        sell_timing_score: float,
        trend_dir: TrendDirection,
        volatility_level: MarketVolatilityLevel,
        momentum_90d: float,
        five_year_tco: float,
        annual_deprec_rate: float,
        risk_score: float,
        best_candidate: Optional[ReplacementCandidate]
    ) -> Tuple[List[DecisionFactor], List[DecisionFactor]]:
        """
        Extracts empirical positive and negative decision factors.
        """
        pos: List[DecisionFactor] = []
        neg: List[DecisionFactor] = []

        # 1. Asking price / Market position factor
        if deal_analysis and deal_analysis.percentage_difference_from_ml is not None:
            diff = deal_analysis.percentage_difference_from_ml
            if diff <= -3.0:
                pos.append(DecisionFactor(
                    category="Market Position",
                    factor_text=f"Asking price is {abs(diff):.1f}% below estimated fair value ({self._format_inr(estimated_fair_value)}).",
                    direction=FactorDirection.POSITIVE,
                    metric_name="price_deviation_pct",
                    metric_value=diff,
                    impact_weight=0.25,
                    source_type=DataIntegrityType.DERIVED
                ))
            elif diff >= 5.0:
                neg.append(DecisionFactor(
                    category="Market Position",
                    factor_text=f"Asking price carries a {diff:.1f}% premium over estimated fair value.",
                    direction=FactorDirection.NEGATIVE,
                    metric_name="price_deviation_pct",
                    metric_value=diff,
                    impact_weight=0.25,
                    source_type=DataIntegrityType.DERIVED
                ))

        # 2. Timing factors
        if mode == DecisionMode.BUY:
            if buy_timing_score >= 65.0:
                pos.append(DecisionFactor(
                    category="Market Timing",
                    factor_text=f"Buy timing score is favorable ({buy_timing_score:.0f}/100) supported by stable dealer inventories.",
                    direction=FactorDirection.POSITIVE,
                    metric_name="buy_timing_score",
                    metric_value=buy_timing_score,
                    impact_weight=0.20,
                    source_type=DataIntegrityType.DERIVED
                ))
            elif buy_timing_score < 45.0:
                neg.append(DecisionFactor(
                    category="Market Timing",
                    factor_text=f"Buy timing score is low ({buy_timing_score:.0f}/100); market conditions suggest waiting for softer pricing.",
                    direction=FactorDirection.NEGATIVE,
                    metric_name="buy_timing_score",
                    metric_value=buy_timing_score,
                    impact_weight=0.20,
                    source_type=DataIntegrityType.DERIVED
                ))
        else:
            if sell_timing_score >= 65.0:
                pos.append(DecisionFactor(
                    category="Market Timing",
                    factor_text=f"Sell timing score is elevated ({sell_timing_score:.0f}/100); current liquidity offers favorable exit pricing.",
                    direction=FactorDirection.POSITIVE,
                    metric_name="sell_timing_score",
                    metric_value=sell_timing_score,
                    impact_weight=0.20,
                    source_type=DataIntegrityType.DERIVED
                ))
            elif sell_timing_score < 45.0:
                neg.append(DecisionFactor(
                    category="Market Timing",
                    factor_text=f"Sell timing score is low ({sell_timing_score:.0f}/100); market indicates softer buyer demand.",
                    direction=FactorDirection.NEGATIVE,
                    metric_name="sell_timing_score",
                    metric_value=sell_timing_score,
                    impact_weight=0.20,
                    source_type=DataIntegrityType.DERIVED
                ))

        # 3. Forecast / Momentum factor
        if abs(momentum_90d) >= 1.5:
            if momentum_90d > 0:
                pos.append(DecisionFactor(
                    category="Market Momentum",
                    factor_text=f"Observed 90-day price trend is rising (+{momentum_90d:.1f}%).",
                    direction=FactorDirection.POSITIVE,
                    metric_name="momentum_90d_pct",
                    metric_value=momentum_90d,
                    impact_weight=0.15,
                    source_type=DataIntegrityType.OBSERVED
                ))
            else:
                neg.append(DecisionFactor(
                    category="Market Momentum",
                    factor_text=f"Observed 90-day price trend indicates declining prices ({momentum_90d:.1f}%).",
                    direction=FactorDirection.NEGATIVE,
                    metric_name="momentum_90d_pct",
                    metric_value=momentum_90d,
                    impact_weight=0.15,
                    source_type=DataIntegrityType.OBSERVED
                ))

        # 4. Ownership Economics factor
        if annual_deprec_rate <= 7.5:
            pos.append(DecisionFactor(
                category="Ownership Economics",
                factor_text=f"Low projected annual depreciation loss ({annual_deprec_rate:.1f}%/year).",
                direction=FactorDirection.POSITIVE,
                metric_name="annual_depreciation_pct",
                metric_value=annual_deprec_rate,
                impact_weight=0.20,
                source_type=DataIntegrityType.FORECAST
            ))
        elif annual_deprec_rate >= 10.0:
            neg.append(DecisionFactor(
                category="Ownership Economics",
                factor_text=f"High projected annual depreciation loss ({annual_deprec_rate:.1f}%/year).",
                direction=FactorDirection.NEGATIVE,
                metric_name="annual_depreciation_pct",
                metric_value=annual_deprec_rate,
                impact_weight=0.20,
                source_type=DataIntegrityType.FORECAST
            ))

        # 5. Risk factor
        if risk_score <= 30.0:
            pos.append(DecisionFactor(
                category="Vehicle Risk",
                factor_text=f"Observable vehicle and market risk score is low ({risk_score:.0f}/100).",
                direction=FactorDirection.POSITIVE,
                metric_name="risk_score",
                metric_value=risk_score,
                impact_weight=0.15,
                source_type=DataIntegrityType.DERIVED
            ))
        elif risk_score >= 60.0:
            neg.append(DecisionFactor(
                category="Vehicle Risk",
                factor_text=f"Elevated vehicle risk ({risk_score:.0f}/100) due to price anomaly or high mileage intensity.",
                direction=FactorDirection.NEGATIVE,
                metric_name="risk_score",
                metric_value=risk_score,
                impact_weight=0.15,
                source_type=DataIntegrityType.DERIVED
            ))

        # 6. Physical verification disclaimer factor
        neg.append(DecisionFactor(
            category="Physical Inspection",
            factor_text="Vehicle internal mechanical condition, chassis, and flood immersion are unverified online.",
            direction=FactorDirection.NEGATIVE,
            metric_name="physical_verification_status",
            metric_value="UNVERIFIED",
            impact_weight=0.05,
            source_type=DataIntegrityType.DEFAULT_ASSUMPTION
        ))

        return pos, neg

    def _build_horizon_outlooks(
        self,
        tco_res: TCOResponse,
        annual_km: int,
        best_candidate: Optional[ReplacementCandidate]
    ) -> List[LifecycleHorizonOutlook]:
        """
        Generates 1Y, 3Y, and 5Y financial and resale outlooks.
        """
        outlooks: List[LifecycleHorizonOutlook] = []
        yearly = tco_res.yearly_projection or []

        # Find 1Y, 3Y, 5Y projections
        for h_years in [1, 3, 5]:
            match_item = next((item for item in yearly if item.year == h_years), None)
            if match_item:
                resale_val = match_item.projected_resale_value
                cum_km = annual_km * h_years
                tco_val = match_item.net_cost_to_date
                purchase_p = tco_res.purchase.price if tco_res.purchase else resale_val
                cum_deprec = max(0.0, purchase_p - resale_val)
                cum_ownership = max(0.0, tco_val - cum_deprec)
                cost_km = match_item.cost_per_km_to_date if match_item.cost_per_km_to_date is not None else (tco_val / max(1, cum_km))

                # Calculate replacement advantage for this horizon if candidate available
                repl_adv = None
                if best_candidate and best_candidate.five_year_tco > 0:
                    cand_h_tco = (best_candidate.five_year_tco / 5.0) * h_years
                    repl_adv = round(tco_val - cand_h_tco, 2)

                outlooks.append(LifecycleHorizonOutlook(
                    horizon_years=h_years,
                    projected_resale_value=resale_val,
                    projected_resale_formatted=self._format_inr(resale_val),
                    cumulative_depreciation=cum_deprec,
                    cumulative_depreciation_formatted=self._format_inr(cum_deprec),
                    cumulative_ownership_cost=cum_ownership,
                    cumulative_ownership_formatted=self._format_inr(cum_ownership),
                    total_cost_of_ownership=tco_val,
                    total_cost_of_ownership_formatted=self._format_inr(tco_val),
                    cost_per_km=cost_km,
                    cost_per_km_formatted=f"₹{cost_km:.2f}/km",
                    replacement_advantage=repl_adv
                ))

        return outlooks

    def _build_lifecycle_scenarios(
        self,
        base_action: LifecycleAction,
        base_score: float,
        tco_res: TCOResponse,
        trend_dir: TrendDirection
    ) -> List[LifecycleScenario]:
        """
        Generates CONSERVATIVE, BASE, and OPTIMISTIC scenario outcomes.
        """
        base_tco = tco_res.ownership.net_tco
        base_resale = tco_res.resale.estimated_resale_value

        # Conservative scenario: +12% TCO, -10% resale retention
        cons_tco = round(base_tco * 1.12, 2)
        cons_resale = round(base_resale * 0.90, 2)
        cons_action = LifecycleAction.SELL_NOW if base_action == LifecycleAction.KEEP else base_action
        cons_score = max(0.0, base_score - 10.0)

        # Optimistic scenario: -8% TCO, +8% resale retention
        opt_tco = round(base_tco * 0.92, 2)
        opt_resale = round(base_resale * 1.08, 2)
        opt_action = LifecycleAction.KEEP if base_action == LifecycleAction.SELL_NOW else base_action
        opt_score = min(100.0, base_score + 8.0)

        return [
            LifecycleScenario(
                scenario_type=LifecycleScenarioType.CONSERVATIVE,
                action=cons_action,
                decision_score=round(cons_score, 1),
                five_year_tco=cons_tco,
                five_year_tco_formatted=self._format_inr(cons_tco),
                projected_resale=cons_resale,
                projected_resale_formatted=self._format_inr(cons_resale),
                key_assumption="Higher fuel/maintenance expenditure and accelerating market depreciation."
            ),
            LifecycleScenario(
                scenario_type=LifecycleScenarioType.BASE,
                action=base_action,
                decision_score=round(base_score, 1),
                five_year_tco=base_tco,
                five_year_tco_formatted=self._format_inr(base_tco),
                projected_resale=base_resale,
                projected_resale_formatted=self._format_inr(base_resale),
                key_assumption="Baseline calibrated market depreciation and standard maintenance schedule."
            ),
            LifecycleScenario(
                scenario_type=LifecycleScenarioType.OPTIMISTIC,
                action=opt_action,
                decision_score=round(opt_score, 1),
                five_year_tco=opt_tco,
                five_year_tco_formatted=self._format_inr(opt_tco),
                projected_resale=opt_resale,
                projected_resale_formatted=self._format_inr(opt_resale),
                key_assumption="High residual value retention and favorable operating cost efficiency."
            )
        ]

    def _compute_sensitivities(
        self,
        action: LifecycleAction,
        mode: DecisionMode,
        request: LifecycleDecisionRequest,
        estimated_fair_value: float,
        annual_km: int,
        buy_timing_score: float,
        sell_timing_score: float,
        best_candidate: Optional[ReplacementCandidate]
    ) -> List[DecisionSensitivity]:
        """
        Identifies critical boundary conditions that would pivot the recommendation.
        """
        sensitivities: List[DecisionSensitivity] = []

        if mode == DecisionMode.BUY:
            # 1. Price sensitivity
            curr_price = request.asking_price or estimated_fair_value
            threshold_price = estimated_fair_value * 1.08
            sensitivities.append(DecisionSensitivity(
                variable_name="Asking Price",
                current_value=curr_price,
                threshold_value=round(threshold_price, 2),
                action_before=action,
                action_after=LifecycleAction.WAIT if action == LifecycleAction.BUY else LifecycleAction.BUY,
                sensitivity_description=f"If asking price exceeds {self._format_inr(threshold_price)} (+8% premium), recommendation pivots to WAIT."
            ))

            # 2. Timing sensitivity
            sensitivities.append(DecisionSensitivity(
                variable_name="Buy Timing Score",
                current_value=round(buy_timing_score, 1),
                threshold_value=45.0,
                action_before=action,
                action_after=LifecycleAction.WAIT,
                sensitivity_description="If market buy timing weakens below 45/100, recommendation pivots to WAIT for seasonal discount cycles."
            ))
        else:
            # 1. Annual mileage sensitivity
            threshold_km = 22000
            sensitivities.append(DecisionSensitivity(
                variable_name="Annual Driving Distance",
                current_value=annual_km,
                threshold_value=threshold_km,
                action_before=action,
                action_after=LifecycleAction.REPLACE if best_candidate else LifecycleAction.SELL_NOW,
                sensitivity_description=f"If annual usage exceeds {threshold_km:,} km/year, higher maintenance pivots recommendation toward REPLACE with a high-efficiency alternative."
            ))

            # 2. Market price shift sensitivity
            sensitivities.append(DecisionSensitivity(
                variable_name="Market Value Shift",
                current_value="0.0%",
                threshold_value="-6.0%",
                action_before=action,
                action_after=LifecycleAction.SELL_NOW if action == LifecycleAction.KEEP else LifecycleAction.KEEP,
                sensitivity_description="If broader market declines by >6.0%, SELL_NOW becomes favorable to protect remaining vehicle equity."
            ))

        return sensitivities

    def _generate_reasonings(
        self,
        action: LifecycleAction,
        mode: DecisionMode,
        decision_score: float,
        decision_margin: float,
        five_year_tco: float,
        cost_per_km: float,
        trend_dir: TrendDirection,
        buy_timing_score: float,
        sell_timing_score: float,
        risk_score: float,
        best_candidate: Optional[ReplacementCandidate]
    ) -> Tuple[str, str, str]:
        """
        Generates cohesive economic, market, and ownership narrative assessments.
        """
        if action == LifecycleAction.BUY:
            econ = f"Financial assessment indicates competitive acquisition economics with a 5Y TCO of {self._format_inr(five_year_tco)} ({self._format_inr(cost_per_km)}/km)."
            mkt = f"Market conditions support purchasing (Buy Timing: {buy_timing_score:.0f}/100, Trend: {trend_dir.value})."
            owner = f"Vehicle fits comfortably within its reliable operating window with manageable projected depreciation."
        elif action == LifecycleAction.KEEP:
            econ = f"Maintaining current vehicle provides superior economics ({self._format_inr(cost_per_km)}/km) compared to immediate replacement transaction friction."
            mkt = f"Market momentum is {trend_dir.value.lower()} while sell timing ({sell_timing_score:.0f}/100) does not mandate immediate liquidation."
            owner = f"Vehicle remains within a favorable ownership cost window without excessive risk ({risk_score:.0f}/100)."
        elif action == LifecycleAction.SELL_NOW:
            econ = f"Current valuation is elevated while upcoming 5Y ownership costs ({self._format_inr(five_year_tco)}) and depreciation losses are projected to accelerate."
            mkt = f"Sell timing is highly favorable ({sell_timing_score:.0f}/100); market liquidity provides an optimal window to capture residual value."
            owner = f"Selling now protects equity before major scheduled maintenance and aging depreciation take effect."
        elif action == LifecycleAction.WAIT:
            econ = f"Current economics do not show a decisive advantage for immediate transaction (+{decision_margin:.1f} pt margin)."
            mkt = f"Market price momentum is {trend_dir.value.lower()}; waiting allows buyer discount cycles or seller price stabilization to develop."
            owner = f"Holding position for 3 to 6 months minimizes transaction costs while preserving flexibility."
        elif action == LifecycleAction.REPLACE:
            cand_name = f"{best_candidate.brand} {best_candidate.model}" if best_candidate else "an alternative model"
            savings_str = self._format_inr(best_candidate.tco_savings_5y) if best_candidate else "substantial"
            econ = f"Replacing with {cand_name} delivers {savings_str} in 5-year ownership savings and lower operating cost/km."
            mkt = f"Market liquidity for target replacement candidates is favorable with attractive buy timing."
            owner = f"Transitioning to a newer or more efficient vehicle mitigates upcoming maintenance and depreciation risk."
        else:
            econ = "Insufficient financial evidence."
            mkt = "Insufficient market evidence."
            owner = "Insufficient ownership evidence."

        return econ, mkt, owner

    def simulate_scenario(self, request: LifecycleScenarioRequest) -> LifecycleDecisionResponse:
        """
        Executes what-if simulation by overriding specific baseline parameters.
        """
        metrics_collector.record_scenario_request()
        base = request.base_request.model_copy()

        if request.annual_km_override is not None:
            base.annual_km = request.annual_km_override
        if request.purchase_price_override is not None:
            base.asking_price = request.purchase_price_override
            base.current_market_value = request.purchase_price_override
        if request.market_shift_pct and abs(request.market_shift_pct) > 0:
            if base.asking_price:
                base.asking_price *= (1.0 + request.market_shift_pct / 100.0)
            if base.current_market_value:
                base.current_market_value *= (1.0 + request.market_shift_pct / 100.0)

        return self.evaluate_lifecycle(base)

    def compare_lifecycle(self, request: LifecycleCompareRequest) -> LifecycleCompareResponse:
        """
        Compares lifecycle economics between current vehicle and up to 5 replacement vehicles.
        """
        if len(request.replacement_vehicles) > 5:
            raise ValueError("Maximum 5 replacement candidates allowed for comparison.")

        all_reqs = [request.current_vehicle] + request.replacement_vehicles
        items: List[LifecycleCompareItem] = []
        best_score = -1.0
        best_label = ""

        for idx, req in enumerate(all_reqs):
            label = "Current Vehicle" if idx == 0 else f"Candidate {idx} ({req.brand} {req.model})"
            res = self.evaluate_lifecycle(req)
            v_sum = res.vehicle_summary
            dec_score = res.decision_score.overall_score

            # Find 5Y outlook
            h5 = next((h for h in res.horizon_outlooks if h.horizon_years == 5), None)
            tco_5y = h5.total_cost_of_ownership if h5 else 0.0
            cost_km = h5.cost_per_km if h5 else 0.0
            resale_5y = h5.projected_resale_value if h5 else 0.0

            # Find timing scores
            cmp_fc_req = ForecastRequest(
                brand=req.brand,
                model=req.model,
                variant=req.variant,
                year=req.year,
                fuel_type=req.fuel_type,
                km_driven=req.km_driven or 35000,
                city=req.city or "Bengaluru"
            )
            try:
                cmp_fc = market_forecast_service.forecast_vehicle_market(cmp_fc_req)
                b_score = cmp_fc.buy_timing.score if (cmp_fc.buy_timing and cmp_fc.buy_timing.score is not None) else 50.0
                s_score = cmp_fc.sell_timing.score if (cmp_fc.sell_timing and cmp_fc.sell_timing.score is not None) else 50.0
            except Exception:
                b_score = 50.0
                s_score = 50.0

            val_req = ValuationRequestSchema(
                brand=req.brand,
                model=req.model,
                variant=req.variant,
                year=req.year,
                fuel_type=req.fuel_type or "Petrol",
                transmission=req.transmission or "Manual",
                km_driven=req.km_driven or 35000,
                city=req.city or "Bengaluru"
            )
            try:
                val_res = valuation_service.evaluate_valuation(val_req, include_shap=False)
                risk_res = self.risk_service.evaluate_risk(val_req, val_res)
                r_score = risk_res.risk_score
                r_level = risk_res.risk_level
            except Exception:
                r_score = 50.0
                r_level = "MODERATE"

            if dec_score > best_score:
                best_score = dec_score
                best_label = label

            items.append(LifecycleCompareItem(
                vehicle_label=label,
                brand=req.brand,
                model=req.model,
                year=req.year,
                fuel_type=req.fuel_type,
                purchase_price=req.asking_price or req.current_market_value,
                purchase_price_formatted=self._format_inr(req.asking_price or req.current_market_value),
                fair_value=v_sum.get("estimated_fair_value", 0.0),
                fair_value_formatted=v_sum.get("estimated_fair_value_formatted", "N/A"),
                five_year_tco=tco_5y,
                five_year_tco_formatted=self._format_inr(tco_5y),
                cost_per_km=cost_km,
                cost_per_km_formatted=f"₹{cost_km:.2f}/km",
                projected_resale=resale_5y,
                projected_resale_formatted=self._format_inr(resale_5y),
                risk_score=r_score,
                risk_level=r_level,
                buy_timing_score=b_score,
                sell_timing_score=s_score,
                market_forecast="STABLE",
                replacement_advantage=None,
                lifecycle_action=res.recommended_action,
                decision_score=dec_score
            ))

        summary = f"Multi-vehicle comparison across {len(items)} vehicles identifies '{best_label}' as having the best overall lifecycle decision score ({best_score:.1f}/100)."

        return LifecycleCompareResponse(
            items=items,
            best_overall_vehicle=best_label,
            comparison_matrix={
                "vehicle_count": len(items),
                "highest_score": best_score,
                "lowest_5y_tco": min(i.five_year_tco for i in items if i.five_year_tco > 0) if items else 0.0
            },
            summary_reasoning=summary
        )

    def batch_lifecycle(self, request: BatchLifecycleRequest) -> BatchLifecycleResponse:
        """
        Executes bounded batch lifecycle evaluations (max 10 vehicles).
        """
        if len(request.vehicles) > 10:
            raise ValueError("Batch limit exceeded: maximum 10 vehicles allowed per batch request.")

        results = [self.evaluate_lifecycle(v) for v in request.vehicles]
        return BatchLifecycleResponse(
            total_vehicles=len(results),
            results=results
        )


lifecycle_service = LifecycleService()
