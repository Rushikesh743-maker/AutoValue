"""
AutoValue Garage & Portfolio Intelligence Service (Phase 16).
Extends single-vehicle intelligence into portfolio-level economic synthesis,
multi-vehicle aggregation, sell-first/keep-first rankings, redundancy detection,
garage efficiency scoring, and what-if consolidation/replacement scenarios.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.models.garage import GarageVehicle
from backend.app.schemas.garage import (
    OwnershipStatus,
    UtilizationClass,
    PortfolioAction,
    PortfolioConfidence,
    GarageVehicleCreate,
    GarageVehicleUpdate,
    GarageVehicleResponse,
    GarageVehicleSnapshot,
    GarageSummary,
    GarageEfficiencyCategory,
    GarageEfficiencyScore,
    VehicleRankingItem,
    VehicleRankings,
    SellFirstItem,
    KeepFirstItem,
    ReplacementOpportunityItem,
    VehicleRedundancyItem,
    GarageRecommendation,
    GarageIntelligenceResponse,
    GarageScenarioRequest,
    GarageScenarioResponse,
    GarageScenarioActionType,
    GarageCompareRequest,
    GarageCompareResponse
)
from backend.app.schemas.valuation import ValuationRequestSchema, ValuationResponse
from backend.app.schemas.tco import TCOAssumptions, TCOResponse
from backend.app.schemas.forecast import ForecastRequest, ForecastResponse, TrendDirection
from backend.app.schemas.lifecycle import LifecycleDecisionRequest, LifecycleAction, DecisionMode
from backend.app.schemas.intelligence import AlternativeVehicleQuery, AlternativeVehicleResponse

from backend.app.services.valuation_service import valuation_service
from backend.app.services.tco_service import TCOService
from backend.app.services.risk_service import RiskService
from backend.app.services.market_forecast_service import market_forecast_service
from backend.app.services.lifecycle_service import lifecycle_service
from backend.app.services.alternative_vehicle_service import AlternativeVehicleService

logger = logging.getLogger("autovalue.garage_intelligence_service")


class GarageIntelligenceService:
    """
    Unified engine for personal vehicle garage management and portfolio-level economic intelligence.
    """
    VERSION = "garage_v001"

    # Centralized Garage Efficiency Weights (sum = 1.0)
    WEIGHT_ECONOMICS = 0.30
    WEIGHT_UTILIZATION = 0.20
    WEIGHT_RISK = 0.15
    WEIGHT_MARKET_POSITION = 0.15
    WEIGHT_RESALE_STRENGTH = 0.10
    WEIGHT_REDUNDANCY = 0.10

    def __init__(self):
        self.tco_service = TCOService()
        self.risk_service = RiskService()
        self.alternative_service = AlternativeVehicleService()

    @staticmethod
    def _format_inr(amount: Optional[float]) -> str:
        if amount is None:
            return "—"
        abs_amt = abs(amount)
        sign = "-" if amount < 0 else ""
        if abs_amt >= 10000000:
            return f"{sign}₹{abs_amt / 10000000:.2f} Cr"
        if abs_amt >= 100000:
            return f"{sign}₹{abs_amt / 100000:.2f}L"
        if abs_amt >= 1000:
            return f"{sign}₹{abs_amt / 1000:.1f}K"
        return f"{sign}₹{abs_amt:,.0f}"

    # -------------------------------------------------------------------------
    # 1. Garage Vehicle CRUD & Persistence
    # -------------------------------------------------------------------------
    def create_vehicle(self, db: Session, user_id: str, data: GarageVehicleCreate) -> GarageVehicle:
        veh = GarageVehicle(
            user_id=user_id,
            valuation_id=data.valuation_id,
            brand=data.brand.strip(),
            model=data.model.strip(),
            variant=data.variant.strip() if data.variant else None,
            year=data.year,
            fuel_type=data.fuel_type or "Petrol",
            transmission=data.transmission or "Manual",
            city=data.city or "Bengaluru",
            nickname=data.nickname.strip() if data.nickname else None,
            ownership_status=data.ownership_status.value if data.ownership_status else OwnershipStatus.OWNED.value,
            purchase_price=data.purchase_price,
            purchase_date=data.purchase_date,
            current_odometer=data.current_odometer if data.current_odometer is not None else 35000,
            annual_km=data.annual_km if data.annual_km is not None else 12000,
            ownership_purpose=data.ownership_purpose,
            notes=data.notes
        )
        db.add(veh)
        db.commit()
        db.refresh(veh)
        return veh

    def get_vehicle(self, db: Session, user_id: str, vehicle_id: str) -> Optional[GarageVehicle]:
        return db.query(GarageVehicle).filter(
            GarageVehicle.id == vehicle_id,
            GarageVehicle.user_id == user_id
        ).first()

    def list_vehicles(
        self,
        db: Session,
        user_id: str,
        status: Optional[OwnershipStatus] = None
    ) -> List[GarageVehicle]:
        query = db.query(GarageVehicle).filter(GarageVehicle.user_id == user_id)
        if status:
            query = query.filter(GarageVehicle.ownership_status == status.value)
        return query.order_by(GarageVehicle.created_at.desc()).all()

    def update_vehicle(
        self,
        db: Session,
        user_id: str,
        vehicle_id: str,
        data: GarageVehicleUpdate
    ) -> Optional[GarageVehicle]:
        veh = self.get_vehicle(db, user_id, vehicle_id)
        if not veh:
            return None

        update_dict = data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            if field == "ownership_status" and value:
                setattr(veh, field, value.value if hasattr(value, "value") else str(value))
            elif value is not None:
                setattr(veh, field, value)

        veh.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(veh)
        return veh

    def delete_vehicle(self, db: Session, user_id: str, vehicle_id: str) -> bool:
        veh = self.get_vehicle(db, user_id, vehicle_id)
        if not veh:
            return False
        db.delete(veh)
        db.commit()
        return True

    # -------------------------------------------------------------------------
    # 2. Individual Vehicle Snapshot Extraction
    # -------------------------------------------------------------------------
    def evaluate_vehicle_snapshot(self, vehicle: GarageVehicle) -> GarageVehicleSnapshot:
        """
        Extracts a comprehensive economic, market, risk, and lifecycle snapshot for a single garage vehicle.
        Reuses valuation, TCO, risk, forecast, and lifecycle services.
        """
        val_req = ValuationRequestSchema(
            brand=vehicle.brand,
            model=vehicle.model,
            variant=vehicle.variant,
            year=vehicle.year,
            fuel_type=vehicle.fuel_type or "Petrol",
            transmission=vehicle.transmission or "Manual",
            km_driven=vehicle.current_odometer or 35000,
            city=vehicle.city or "Bengaluru",
            asking_price=vehicle.purchase_price
        )

        val_res = None
        fair_val = None
        market_med = None
        try:
            val_res = valuation_service.evaluate_valuation(val_req, include_shap=False)
            if val_res and val_res.valuation:
                fair_val = val_res.valuation.estimated_value
                market_med = val_res.market.median if val_res.market else None
        except Exception as e:
            logger.warning(f"Valuation exception in garage snapshot for {vehicle.model}: {e}")
            fair_val = None
            market_med = None
            val_res = None

        # TCO Calculation
        annual_km = vehicle.annual_km if vehicle.annual_km is not None else 12000
        tco_res = None
        if fair_val is not None and val_res is not None:
            tco_assump = TCOAssumptions(
                annual_km=annual_km,
                ownership_years=5,
                purchase_price_mode="CUSTOM" if vehicle.purchase_price else "FAIR_VALUE",
                custom_purchase_price=vehicle.purchase_price or fair_val
            )
            try:
                tco_res = self.tco_service.calculate_tco(val_req, val_res, tco_assump)
                five_y_tco = tco_res.ownership.net_tco
                annual_cost = tco_res.ownership.annual_cost
                cost_km = tco_res.ownership.cost_per_km
                resale_5y = tco_res.resale.estimated_resale_value
                deprec_rate = tco_res.resale.annual_depreciation_rate
                five_y_deprec = max(0.0, (vehicle.purchase_price or fair_val) - resale_5y)
            except Exception as e:
                logger.warning(f"TCO calculation failure in garage snapshot for {vehicle.model}: {e}")
                tco_res = None
                five_y_tco = None
                annual_cost = None
                cost_km = None
                resale_5y = None
                deprec_rate = None
                five_y_deprec = None
        else:
            five_y_tco = None
            annual_cost = None
            cost_km = None
            resale_5y = None
            deprec_rate = None
            five_y_deprec = None

        # Risk Analysis
        risk_res = None
        try:
            if val_res is not None:
                risk_res = self.risk_service.evaluate_risk(val_req, val_res)
                risk_score = risk_res.risk_score
                risk_level = risk_res.risk_level
            else:
                risk_score = 30.0
                risk_level = "LOW"
        except Exception:
            risk_res = None
            risk_score = 30.0
            risk_level = "LOW"

        # Market Forecast & Timing
        fc_res = None
        if fair_val is not None:
            fc_req = ForecastRequest(
                brand=vehicle.brand,
                model=vehicle.model,
                variant=vehicle.variant,
                year=vehicle.year,
                fuel_type=vehicle.fuel_type,
                transmission=vehicle.transmission,
                km_driven=vehicle.current_odometer or 35000,
                city=vehicle.city or "Bengaluru",
                asking_price=vehicle.purchase_price or fair_val,
                horizon_days=365
            )
            try:
                fc_res = market_forecast_service.forecast_vehicle_market(fc_req)
                market_trend = fc_res.overall_trend.value if fc_res.overall_trend else "STABLE"
                momentum_90d = fc_res.momentum.m90d.price_change_pct if (fc_res.momentum and fc_res.momentum.m90d and fc_res.momentum.m90d.price_change_pct is not None) else 0.0
                buy_timing = fc_res.buy_timing.score if (fc_res.buy_timing and fc_res.buy_timing.score is not None) else 50.0
                sell_timing = fc_res.sell_timing.score if (fc_res.sell_timing and fc_res.sell_timing.score is not None) else 50.0
                fc_conf = fc_res.forecast_confidence.value if fc_res.forecast_confidence else "MODERATE"
            except Exception:
                fc_res = None
                market_trend = "STABLE"
                momentum_90d = 0.0
                buy_timing = 50.0
                sell_timing = 50.0
                fc_conf = "MODERATE"
        else:
            market_trend = "STABLE"
            momentum_90d = 0.0
            buy_timing = 50.0
            sell_timing = 50.0
            fc_conf = "INSUFFICIENT_EVIDENCE"

        # Lifecycle Decision
        if fair_val is not None:
            lc_req = LifecycleDecisionRequest(
                mode=DecisionMode.OWNER if vehicle.ownership_status == OwnershipStatus.OWNED.value else DecisionMode.BUY,
                brand=vehicle.brand,
                model=vehicle.model,
                variant=vehicle.variant,
                year=vehicle.year,
                fuel_type=vehicle.fuel_type,
                transmission=vehicle.transmission,
                km_driven=vehicle.current_odometer,
                city=vehicle.city,
                current_market_value=fair_val,
                purchase_price=vehicle.purchase_price,
                annual_km=annual_km,
                include_alternatives=False
            )
            try:
                lc_res = lifecycle_service.evaluate_lifecycle(
                    lc_req,
                    valuation_response=val_res,
                    forecast_response=fc_res,
                    risk_response=risk_res,
                    tco_response=tco_res
                )
                lc_action = lc_res.recommended_action.value
                lc_score = lc_res.decision_score.overall_score
            except Exception as e:
                logger.warning(f"Lifecycle evaluation fallback in garage snapshot for {vehicle.model}: {e}")
                lc_action = LifecycleAction.KEEP.value
                lc_score = 70.0
        else:
            lc_action = LifecycleAction.INSUFFICIENT_EVIDENCE.value
            lc_score = 0.0

        # Utilization classification
        if annual_km is None or annual_km <= 0:
            util_class = UtilizationClass.INSUFFICIENT_EVIDENCE
        elif annual_km >= 16000:
            util_class = UtilizationClass.HIGH
        elif annual_km >= 8000:
            util_class = UtilizationClass.MODERATE
        else:
            util_class = UtilizationClass.LOW

        v_resp = GarageVehicleResponse(
            id=vehicle.id,
            user_id=vehicle.user_id,
            valuation_id=vehicle.valuation_id,
            brand=vehicle.brand,
            model=vehicle.model,
            variant=vehicle.variant,
            year=vehicle.year,
            fuel_type=vehicle.fuel_type,
            transmission=vehicle.transmission,
            city=vehicle.city,
            nickname=vehicle.nickname,
            ownership_status=OwnershipStatus(vehicle.ownership_status),
            purchase_price=vehicle.purchase_price,
            purchase_date=vehicle.purchase_date,
            current_odometer=vehicle.current_odometer,
            annual_km=vehicle.annual_km,
            ownership_purpose=vehicle.ownership_purpose,
            notes=vehicle.notes,
            created_at=vehicle.created_at,
            updated_at=vehicle.updated_at
        )

        return GarageVehicleSnapshot(
            vehicle=v_resp,
            current_estimated_value=fair_val,
            current_estimated_value_formatted=self._format_inr(fair_val),
            market_median=market_med,
            five_year_tco=five_y_tco,
            five_year_tco_formatted=self._format_inr(five_y_tco),
            annual_ownership_cost=annual_cost,
            annual_ownership_cost_formatted=self._format_inr(annual_cost),
            cost_per_km=cost_km,
            cost_per_km_formatted=f"₹{cost_km:.2f}/km" if cost_km is not None else "—",
            projected_resale_5y=resale_5y,
            projected_resale_formatted=self._format_inr(resale_5y),
            five_year_depreciation=five_y_deprec,
            five_year_depreciation_formatted=self._format_inr(five_y_deprec),
            annual_depreciation_rate=deprec_rate,
            risk_score=risk_score,
            risk_level=risk_level,
            market_trend=market_trend,
            momentum_90d=momentum_90d,
            buy_timing_score=buy_timing,
            sell_timing_score=sell_timing,
            lifecycle_action=lc_action,
            lifecycle_score=lc_score,
            confidence=fc_conf,
            utilization_class=util_class
        )

    # -------------------------------------------------------------------------
    # 3. Portfolio-Level Aggregation & Intelligence
    # -------------------------------------------------------------------------
    def evaluate_garage_intelligence(self, db: Session, user_id: str) -> GarageIntelligenceResponse:
        """
        Compiles authoritative portfolio intelligence across all user garage vehicles.
        """
        vehicles = self.list_vehicles(db, user_id)
        if not vehicles:
            return self._build_empty_garage_response()

        # Evaluate snapshots for all vehicles
        snapshots: List[GarageVehicleSnapshot] = [
            self.evaluate_vehicle_snapshot(v) for v in vehicles
        ]

        summary = self._compute_portfolio_summary(snapshots)
        redundancies = self._detect_vehicle_redundancies(snapshots)
        efficiency = self._compute_efficiency_score(snapshots, summary, redundancies=redundancies)
        rankings = self._compute_vehicle_rankings(snapshots)
        sell_first = self._compute_sell_first_ranking(snapshots)
        keep_first = self._compute_keep_first_ranking(snapshots)
        replacements = self._discover_replacement_opportunities(snapshots)
        recommendation = self._generate_portfolio_recommendation(
            summary=summary,
            efficiency=efficiency,
            sell_first=sell_first,
            keep_first=keep_first,
            redundancies=redundancies,
            replacements=replacements
        )

        return GarageIntelligenceResponse(
            summary=summary,
            efficiency=efficiency,
            efficiency_score=efficiency,
            recommendation=recommendation,
            sell_first_ranking=sell_first,
            keep_first_ranking=keep_first,
            replacement_opportunities=replacements,
            redundancies=redundancies,
            redundancy_analysis=redundancies,
            rankings=rankings,
            vehicle_rankings=rankings,
            vehicle_snapshots=snapshots,
            snapshots=snapshots,
            limitations=[
                "Portfolio calculations assume stated annual mileage and regular maintenance intervals.",
                "Vehicle mechanical condition and chassis integrity are uninspected online.",
                "Resale trajectories and market forecasts are statistical estimates and not guaranteed prices."
            ],
            provenance={
                "current_values": "DERIVED (Valuation Engine v002)",
                "ownership_costs": "DERIVED (Phase 13 TCO Engine)",
                "market_trends": "DERIVED (Phase 14 Market Forecast Engine)",
                "annual_mileage": "USER_DEFINED or DEFAULT_ASSUMPTION (12,000 km/yr)"
            },
            disclaimer="Portfolio intelligence is based on statistical valuation models and user inputs."
        )

    # -------------------------------------------------------------------------
    # Helper Computations
    # -------------------------------------------------------------------------
    def _compute_portfolio_summary(self, snapshots: List[GarageVehicleSnapshot]) -> GarageSummary:
        total_veh = len(snapshots)
        owned_veh = sum(1 for s in snapshots if s.vehicle.ownership_status == OwnershipStatus.OWNED)
        cons_veh = sum(1 for s in snapshots if s.vehicle.ownership_status == OwnershipStatus.CONSIDERING)
        watch_veh = sum(1 for s in snapshots if s.vehicle.ownership_status == OwnershipStatus.WATCHING)
        sold_veh = sum(1 for s in snapshots if s.vehicle.ownership_status == OwnershipStatus.SOLD)

        active_snaps = [s for s in snapshots if s.vehicle.ownership_status != OwnershipStatus.SOLD]
        owned_snaps = [s for s in snapshots if s.vehicle.ownership_status == OwnershipStatus.OWNED]
        target_snaps = owned_snaps or active_snaps

        # Excluded / unvalued vehicles tracking
        valued_active = [s for s in active_snaps if s.current_estimated_value is not None]
        unvalued_active = [s for s in active_snaps if s.current_estimated_value is None]
        excluded_count = len(unvalued_active)
        excluded_reasons = [
            f"{s.vehicle.brand} {s.vehicle.model} ({s.vehicle.year}): Valuation failed or insufficient evidence"
            for s in unvalued_active
        ]

        # Financial totals strictly summing valid values
        tot_val = sum(s.current_estimated_value for s in valued_active)
        tot_annual_cost = sum(s.annual_ownership_cost for s in target_snaps if s.annual_ownership_cost is not None)
        tot_5y_tco = sum(s.five_year_tco for s in target_snaps if s.five_year_tco is not None)
        tot_5y_resale = sum(s.projected_resale_5y for s in target_snaps if s.projected_resale_5y is not None)

        # Weighted metrics
        valid_tco_snaps = [s for s in target_snaps if s.annual_ownership_cost is not None]
        total_annual_km = sum((s.vehicle.annual_km or 12000) for s in valid_tco_snaps)
        avg_cost_km = (tot_annual_cost / total_annual_km) if total_annual_km > 0 else 0.0

        if tot_val > 0:
            weighted_risk = sum(s.risk_score * s.current_estimated_value for s in valued_active) / tot_val
            weighted_momentum = sum(s.momentum_90d * s.current_estimated_value for s in valued_active) / tot_val
        elif valued_active:
            weighted_risk = sum(s.risk_score for s in valued_active) / len(valued_active)
            weighted_momentum = sum(s.momentum_90d for s in valued_active) / len(valued_active)
        else:
            weighted_risk = 30.0
            weighted_momentum = 0.0

        if weighted_momentum >= 1.5:
            direction = "RISING"
        elif weighted_momentum <= -1.5:
            direction = "DECLINING"
        else:
            direction = "STABLE"

        risk_label = "LOW" if weighted_risk <= 35.0 else ("HIGH" if weighted_risk >= 65.0 else "MODERATE")

        return GarageSummary(
            total_vehicles=total_veh,
            owned_vehicles=owned_veh,
            owned_vehicles_count=owned_veh,
            considering_vehicles=cons_veh,
            watching_vehicles=watch_veh,
            sold_vehicles=sold_veh,
            total_current_value=tot_val,
            total_current_value_formatted=self._format_inr(tot_val),
            total_annual_cost=tot_annual_cost,
            total_annual_cost_formatted=self._format_inr(tot_annual_cost),
            total_5y_tco=tot_5y_tco,
            total_5y_tco_formatted=self._format_inr(tot_5y_tco),
            total_projected_5y_resale=tot_5y_resale,
            total_projected_5y_resale_formatted=self._format_inr(tot_5y_resale),
            average_cost_per_km=avg_cost_km,
            average_cost_per_km_formatted=f"₹{avg_cost_km:.2f}/km",
            weighted_average_risk=round(weighted_risk, 1),
            weighted_market_momentum=round(weighted_momentum, 2),
            overall_market_direction=direction,
            risk_level_label=risk_label,
            excluded_vehicles_count=excluded_count,
            excluded_vehicle_reasons=excluded_reasons
        )

    def _compute_efficiency_score(
        self,
        snapshots: List[GarageVehicleSnapshot],
        summary: GarageSummary,
        redundancies: Optional[List[VehicleRedundancyItem]] = None
    ) -> GarageEfficiencyScore:
        owned_snaps = [s for s in snapshots if s.vehicle.ownership_status == OwnershipStatus.OWNED] or snapshots

        # 1. Ownership Economics (30%)
        # Benchmarked against typical ₹10-14/km Indian automotive operating curve
        avg_km_cost = summary.average_cost_per_km
        if avg_km_cost <= 9.0:
            econ_score = 92.0
        elif avg_km_cost <= 13.0:
            econ_score = 80.0
        elif avg_km_cost <= 18.0:
            econ_score = 65.0
        elif avg_km_cost <= 25.0:
            econ_score = 48.0
        else:
            econ_score = 30.0

        # 2. Utilization (20%)
        # Higher score when vehicles are used regularly
        avg_annual_km = (sum((s.vehicle.annual_km or 12000) for s in owned_snaps) / len(owned_snaps)) if owned_snaps else 12000
        if avg_annual_km >= 14000:
            util_score = 90.0
        elif avg_annual_km >= 10000:
            util_score = 82.0
        elif avg_annual_km >= 6000:
            util_score = 65.0
        else:
            util_score = 45.0

        # 3. Risk (15%)
        # Lower weighted risk gives higher efficiency
        w_risk = summary.weighted_average_risk
        risk_comp_score = max(10.0, min(100.0, 100.0 - (w_risk * 1.1)))

        # 4. Market Position & Momentum (15%)
        w_mom = summary.weighted_market_momentum
        if w_mom >= 2.0:
            market_score = 88.0
        elif w_mom >= -1.0:
            market_score = 75.0
        else:
            market_score = 55.0

        # 5. Resale Strength (10%)
        if summary.total_current_value > 0:
            resale_retention = summary.total_projected_5y_resale / summary.total_current_value
        else:
            resale_retention = 0.40
        if resale_retention >= 0.45:
            resale_score = 88.0
        elif resale_retention >= 0.35:
            resale_score = 74.0
        else:
            resale_score = 52.0

        # 6. Redundancy (10%)
        if redundancies is None:
            redundancies = self._detect_vehicle_redundancies(snapshots)
        high_red_count = sum(1 for r in redundancies if r.redundancy_level == "HIGH")
        if high_red_count == 0:
            red_score = 90.0
        elif high_red_count == 1:
            red_score = 60.0
        else:
            red_score = 35.0

        cats = [
            GarageEfficiencyCategory(
                category_name="Ownership Economics",
                score=econ_score,
                weight=self.WEIGHT_ECONOMICS,
                contribution=round(econ_score * self.WEIGHT_ECONOMICS, 2),
                reasoning=f"Portfolio cost per km is {summary.average_cost_per_km_formatted} across {len(owned_snaps)} active vehicles."
            ),
            GarageEfficiencyCategory(
                category_name="Utilization",
                score=util_score,
                weight=self.WEIGHT_UTILIZATION,
                contribution=round(util_score * self.WEIGHT_UTILIZATION, 2),
                reasoning=f"Average utilization is {avg_annual_km:,.0f} km/year per vehicle."
            ),
            GarageEfficiencyCategory(
                category_name="Risk Exposure",
                score=risk_comp_score,
                weight=self.WEIGHT_RISK,
                contribution=round(risk_comp_score * self.WEIGHT_RISK, 2),
                reasoning=f"Weighted risk exposure is {summary.weighted_average_risk:.1f}/100 across portfolio assets."
            ),
            GarageEfficiencyCategory(
                category_name="Market Position",
                score=market_score,
                weight=self.WEIGHT_MARKET_POSITION,
                contribution=round(market_score * self.WEIGHT_MARKET_POSITION, 2),
                reasoning=f"Overall market trajectory is {summary.overall_market_direction} with {summary.weighted_market_momentum:+.2f}% 90D momentum."
            ),
            GarageEfficiencyCategory(
                category_name="Resale Strength",
                score=resale_score,
                weight=self.WEIGHT_RESALE_STRENGTH,
                contribution=round(resale_score * self.WEIGHT_RESALE_STRENGTH, 2),
                reasoning=f"5-Year residual recovery is projected at {self._format_inr(summary.total_projected_5y_resale)}."
            ),
            GarageEfficiencyCategory(
                category_name="Redundancy Efficiency",
                score=red_score,
                weight=self.WEIGHT_REDUNDANCY,
                contribution=round(red_score * self.WEIGHT_REDUNDANCY, 2),
                reasoning=f"Detected {high_red_count} high-overlap vehicle usage redundancies."
            ),
        ]

        total_score = sum(c.contribution for c in cats)
        total_score = max(10.0, min(100.0, round(total_score, 1)))

        if total_score >= 80.0:
            summary_txt = "Highly efficient garage configuration with balanced cost per km, strong usage, and minimal redundancy."
            rating_lbl = "Exceptional"
        elif total_score >= 60.0:
            summary_txt = "Moderate garage efficiency. Opportunities exist to optimize annual maintenance or resolve low-utilization overlap."
            rating_lbl = "Moderate"
        else:
            summary_txt = "Suboptimal garage efficiency due to elevated depreciation, high cost per km, or overlapping vehicle roles."
            rating_lbl = "Suboptimal"

        return GarageEfficiencyScore(
            overall_score=total_score,
            categories=cats,
            summary_reasoning=summary_txt,
            rating_label=rating_lbl
        )

    def _compute_vehicle_rankings(self, snapshots: List[GarageVehicleSnapshot]) -> VehicleRankings:
        def rank_list(items: List[Tuple[str, str, Optional[float], str]], reverse: bool = True) -> List[VehicleRankingItem]:
            valid_items = [item for item in items if item[2] is not None]
            sorted_items = sorted(valid_items, key=lambda x: x[2], reverse=reverse)
            return [
                VehicleRankingItem(
                    vehicle_id=item[0],
                    vehicle_label=item[1],
                    metric_value=round(item[2], 2),
                    metric_formatted=item[3],
                    rank=idx + 1
                )
                for idx, item in enumerate(sorted_items)
            ]

        annual_items = [
            (s.vehicle.id, f"{s.vehicle.year} {s.vehicle.brand} {s.vehicle.model}", s.annual_ownership_cost, s.annual_ownership_cost_formatted)
            for s in snapshots
        ]
        tco_items = [
            (s.vehicle.id, f"{s.vehicle.year} {s.vehicle.brand} {s.vehicle.model}", s.five_year_tco, s.five_year_tco_formatted)
            for s in snapshots
        ]
        cost_km_items = [
            (s.vehicle.id, f"{s.vehicle.year} {s.vehicle.brand} {s.vehicle.model}", s.cost_per_km, s.cost_per_km_formatted)
            for s in snapshots
        ]
        deprec_items = [
            (s.vehicle.id, f"{s.vehicle.year} {s.vehicle.brand} {s.vehicle.model}", s.five_year_depreciation, s.five_year_depreciation_formatted)
            for s in snapshots
        ]
        risk_items = [
            (s.vehicle.id, f"{s.vehicle.year} {s.vehicle.brand} {s.vehicle.model}", s.risk_score, f"{s.risk_score:.0f}/100")
            for s in snapshots
        ]

        return VehicleRankings(
            most_expensive_annual=rank_list(annual_items),
            highest_5y_tco=rank_list(tco_items),
            highest_cost_per_km=rank_list(cost_km_items),
            highest_depreciation=rank_list(deprec_items),
            highest_risk=rank_list(risk_items)
        )

    def _compute_sell_first_ranking(self, snapshots: List[GarageVehicleSnapshot]) -> List[SellFirstItem]:
        items: List[SellFirstItem] = []
        for s in snapshots:
            label = f"{s.vehicle.year} {s.vehicle.brand} {s.vehicle.model}"
            factors: List[str] = []

            # Multi-factor Sell Priority calculation (0-100)
            score = 30.0

            # 1. Sell timing score contribution
            score += (s.sell_timing_score * 0.30)
            if s.sell_timing_score >= 65:
                factors.append(f"Sell timing score is elevated ({s.sell_timing_score:.0f}/100) indicating strong seasonal liquidity.")

            # 2. Lifecycle action signal
            if s.lifecycle_action == LifecycleAction.SELL_NOW.value:
                score += 20.0
                factors.append("Vehicle lifecycle engine explicitly recommends SELL_NOW.")
            elif s.lifecycle_action == LifecycleAction.WAIT.value:
                score += 5.0

            # 3. Depreciation pressure
            if s.annual_depreciation_rate is not None and s.annual_depreciation_rate >= 0.16:
                score += 15.0
                factors.append(f"Accelerating compound annual depreciation ({s.annual_depreciation_rate*100:.1f}%/yr).")

            # 4. Low utilization penalty
            if s.utilization_class == UtilizationClass.LOW:
                score += 12.0
                factors.append(f"Low driving utilization ({s.vehicle.annual_km:,} km/yr) incurs high fixed insurance & maintenance cost.")

            # 5. Market momentum
            if s.momentum_90d < -2.0:
                score += 10.0
                factors.append(f"Market prices are falling ({s.momentum_90d:.1f}% 90D momentum).")
            elif s.momentum_90d > 2.0:
                score -= 10.0
                factors.append(f"Market prices currently rising (+{s.momentum_90d:.1f}% 90D momentum), reducing urgency to liquidate.")

            score = max(5.0, min(100.0, round(score, 1)))

            if score >= 75.0:
                recom = "High priority candidate for divestment. Market timing and operating economics favor selling."
            elif score >= 50.0:
                recom = "Moderate sell candidate. Monitor upcoming depreciation milestones."
            else:
                recom = "Low sell priority. Vehicle continues to provide strong ownership utility."

            deprec_pct = round(s.annual_depreciation_rate * 100, 1) if s.annual_depreciation_rate is not None else None

            items.append(SellFirstItem(
                vehicle_id=s.vehicle.id,
                vehicle_label=label,
                vehicle_display_name=label,
                sell_priority_score=score,
                current_value=s.current_estimated_value,
                current_value_formatted=s.current_estimated_value_formatted,
                sell_timing_score=s.sell_timing_score,
                depreciation_rate=s.annual_depreciation_rate,
                projected_resale_decline_pct=deprec_pct,
                annual_cost=s.annual_ownership_cost,
                annual_cost_formatted=s.annual_ownership_cost_formatted,
                annual_ownership_cost_formatted=s.annual_ownership_cost_formatted,
                factors=factors,
                reasons=factors,
                recommendation=recom
            ))

        items.sort(key=lambda x: x.sell_priority_score, reverse=True)
        return items

    def _compute_keep_first_ranking(self, snapshots: List[GarageVehicleSnapshot]) -> List[KeepFirstItem]:
        items: List[KeepFirstItem] = []
        for s in snapshots:
            label = f"{s.vehicle.year} {s.vehicle.brand} {s.vehicle.model}"
            factors: List[str] = []

            # Multi-factor Keep Priority calculation (0-100)
            score = 35.0

            # 1. Lifecycle KEEP signal
            if s.lifecycle_action == LifecycleAction.KEEP.value:
                score += 25.0
                factors.append("Lifecycle engine recommends KEEP with high economic support.")

            # 2. Operating efficiency (Cost/km)
            if s.cost_per_km is not None:
                if s.cost_per_km <= 10.0:
                    score += 20.0
                    factors.append(f"Highly cost-effective running rate ({s.cost_per_km_formatted}).")
                elif s.cost_per_km <= 14.0:
                    score += 10.0

            # 3. High utilization
            if s.utilization_class == UtilizationClass.HIGH:
                score += 15.0
                factors.append(f"High annual utilization ({s.vehicle.annual_km:,} km/yr) maximizes capital asset efficiency.")

            # 4. Low risk
            if s.risk_score <= 25.0:
                score += 10.0
                factors.append(f"Low market and mechanical risk ({s.risk_score:.0f}/100).")

            score = max(5.0, min(100.0, round(score, 1)))

            items.append(KeepFirstItem(
                vehicle_id=s.vehicle.id,
                vehicle_label=label,
                vehicle_display_name=label,
                keep_priority_score=score,
                five_year_tco=s.five_year_tco,
                five_year_tco_formatted=s.five_year_tco_formatted,
                risk_score=s.risk_score,
                risk_level=s.risk_level,
                market_trend=s.market_trend,
                cost_per_km=s.cost_per_km,
                cost_per_km_formatted=s.cost_per_km_formatted,
                factors=factors,
                reasons=factors
            ))

        items.sort(key=lambda x: x.keep_priority_score, reverse=True)
        return items

    def _discover_replacement_opportunities(
        self,
        snapshots: List[GarageVehicleSnapshot]
    ) -> List[ReplacementOpportunityItem]:
        opportunities: List[ReplacementOpportunityItem] = []

        for s in snapshots:
            if s.current_estimated_value is None or s.five_year_tco is None or s.projected_resale_5y is None:
                continue

            alt_query = AlternativeVehicleQuery(
                target_budget=s.current_estimated_value,
                budget_min=max(50000.0, s.current_estimated_value * 0.70),
                budget_max=s.current_estimated_value * 1.30,
                city=s.vehicle.city,
                limit=3
            )
            try:
                alt_resp: AlternativeVehicleResponse = self.alternative_service.find_alternatives(alt_query)
                if not alt_resp.results:
                    continue

                best = alt_resp.results[0]
                cand_val_req = ValuationRequestSchema(
                    brand=best.brand,
                    model=best.model,
                    variant=best.variant,
                    year=best.year,
                    fuel_type=best.fuel_type or "Petrol",
                    transmission=best.transmission or "Manual",
                    km_driven=best.km_driven or 35000,
                    city=best.city or s.vehicle.city or "Bengaluru"
                )
                c_val = valuation_service.evaluate_valuation(cand_val_req, include_shap=False)
                c_fair = c_val.valuation.estimated_value
                c_tco_assump = TCOAssumptions(
                    annual_km=s.vehicle.annual_km or 12000,
                    ownership_years=5,
                    purchase_price_mode="CUSTOM" if best.listed_price else "FAIR_VALUE",
                    custom_purchase_price=best.listed_price or c_fair
                )
                c_tco = self.tco_service.calculate_tco(cand_val_req, c_val, c_tco_assump)

                tco_savings = s.five_year_tco - c_tco.ownership.net_tco
                resale_diff = c_tco.resale.estimated_resale_value - s.projected_resale_5y
                p_diff = (best.listed_price or c_fair) - s.current_estimated_value

                # Break-even months calculation
                ann_savings = tco_savings / 5.0
                if ann_savings > 0.0:
                    acq_diff = max(0.0, p_diff)
                    if acq_diff > 0.0:
                        break_even = round(acq_diff / (ann_savings / 12.0), 1)
                    else:
                        break_even = 0.0
                else:
                    break_even = None

                # Replacement advantage score
                r_score = 50.0
                if tco_savings > 0:
                    r_score += min(35.0, (tco_savings / 100000.0) * 15.0)
                else:
                    r_score -= min(30.0, (abs(tco_savings) / 100000.0) * 15.0)

                if tco_savings > 40000:
                    reason = f"Switching to {best.brand} {best.model} reduces 5Y ownership expenditure by {self._format_inr(tco_savings)}."
                else:
                    reason = f"Marginal economic difference with {best.brand} {best.model}."

                opportunities.append(ReplacementOpportunityItem(
                    current_vehicle_id=s.vehicle.id,
                    current_vehicle_label=f"{s.vehicle.year} {s.vehicle.brand} {s.vehicle.model}",
                    current_vehicle_name=f"{s.vehicle.year} {s.vehicle.brand} {s.vehicle.model}",
                    candidate_brand=best.brand,
                    candidate_model=best.model,
                    candidate_year=best.year,
                    candidate_replacement_name=f"{best.year} {best.brand} {best.model}",
                    candidate_replacement_brand=best.brand,
                    candidate_replacement_model=best.model,
                    estimated_purchase_diff=p_diff,
                    purchase_difference_formatted=self._format_inr(p_diff),
                    tco_savings_5y=tco_savings,
                    tco_savings_5y_formatted=f"{'+' if tco_savings >= 0 else ''}{self._format_inr(tco_savings)}",
                    tco_difference_formatted=f"{'+' if tco_savings >= 0 else ''}{self._format_inr(tco_savings)}",
                    resale_advantage=resale_diff,
                    resale_difference_formatted=self._format_inr(resale_diff),
                    risk_difference=-5.0,
                    break_even_months=break_even,
                    replacement_score=max(10.0, min(100.0, round(r_score, 1))),
                    replacement_opportunity_score=max(10.0, min(100.0, round(r_score, 1))),
                    recommendation_reason=reason,
                    recommendation_rationale=reason
                ))
            except Exception as e:
                logger.warning(f"Alternative search failure in garage: {e}")
                continue

        opportunities.sort(key=lambda x: x.replacement_score, reverse=True)
        return opportunities

    def _detect_vehicle_redundancies(
        self,
        snapshots: List[GarageVehicleSnapshot]
    ) -> List[VehicleRedundancyItem]:
        redundancies: List[VehicleRedundancyItem] = []
        owned_snaps = [s for s in snapshots if s.vehicle.ownership_status == OwnershipStatus.OWNED]
        if len(owned_snaps) < 2:
            return redundancies

        # Segment categories
        suvs = {"creta", "seltos", "brezza", "venue", "nexon", "harrier", "xuv700", "scorpio", "fortuner"}
        sedans = {"city", "verna", "ciaz", "slavia", "virtus", "amaze", "dzire"}
        hatchbacks = {"swift", "baleno", "i20", "wagon r", "alto", "kwid", "tiago", "polo"}

        def get_category(model_name: str) -> str:
            m = model_name.lower().strip()
            if any(s in m for s in suvs):
                return "SUV / Crossover"
            if any(s in m for s in sedans):
                return "Sedan"
            if any(s in m for s in hatchbacks):
                return "Hatchback / Commuter"
            return "General Passenger"

        for i in range(len(owned_snaps)):
            for j in range(i + 1, len(owned_snaps)):
                va = owned_snaps[i]
                vb = owned_snaps[j]

                cat_a = get_category(va.vehicle.model)
                cat_b = get_category(vb.vehicle.model)
                purpose_a = va.vehicle.ownership_purpose
                purpose_b = vb.vehicle.ownership_purpose

                overlap_reasons: List[str] = []
                red_level = "LOW"

                # 1. Purpose overlap
                if purpose_a and purpose_b and purpose_a.lower() == purpose_b.lower():
                    overlap_reasons.append(f"Identical stated usage purpose: '{purpose_a}'.")
                    red_level = "HIGH"

                # 2. Segment and powertrain overlap
                if cat_a == cat_b:
                    overlap_reasons.append(f"Matching vehicle body format: {cat_a}.")
                    if red_level != "HIGH":
                        red_level = "MODERATE"

                # 3. Fuel type overlap
                if va.vehicle.fuel_type == vb.vehicle.fuel_type:
                    overlap_reasons.append(f"Same fuel architecture ({va.vehicle.fuel_type}).")

                # 4. Low utilization on one vehicle
                if va.utilization_class == UtilizationClass.LOW or vb.utilization_class == UtilizationClass.LOW:
                    overlap_reasons.append("One vehicle exhibits low annual mileage (<8,000 km/yr).")
                    if red_level == "MODERATE":
                        red_level = "HIGH"

                if red_level in ["HIGH", "MODERATE"]:
                    cost_a = va.annual_ownership_cost or 0.0
                    cost_b = vb.annual_ownership_cost or 0.0
                    pot_savings = min(cost_a, cost_b) if (cost_a > 0 and cost_b > 0) else max(cost_a, cost_b)
                    label_a = f"{va.vehicle.year} {va.vehicle.brand} {va.vehicle.model}"
                    label_b = f"{vb.vehicle.year} {vb.vehicle.brand} {vb.vehicle.model}"
                    redundancies.append(VehicleRedundancyItem(
                        vehicle_a_id=va.vehicle.id,
                        vehicle_a_label=label_a,
                        vehicle_a_name=label_a,
                        vehicle_b_id=vb.vehicle.id,
                        vehicle_b_label=label_b,
                        vehicle_b_name=label_b,
                        redundancy_level=red_level,
                        overlap_reasons=overlap_reasons,
                        overlap_factors=overlap_reasons,
                        potential_annual_savings=pot_savings,
                        potential_annual_savings_formatted=self._format_inr(pot_savings),
                        recommendation=f"Consider consolidating or divesting one vehicle to optimize ~{self._format_inr(pot_savings)}/yr in holding costs."
                    ))

        return redundancies

    def _generate_portfolio_recommendation(
        self,
        summary: GarageSummary,
        efficiency: GarageEfficiencyScore,
        sell_first: List[SellFirstItem],
        keep_first: List[KeepFirstItem],
        redundancies: List[VehicleRedundancyItem],
        replacements: List[ReplacementOpportunityItem]
    ) -> GarageRecommendation:
        reasons: List[str] = []
        high_red = [r for r in redundancies if r.redundancy_level == "HIGH"]
        top_sell = sell_first[0] if sell_first else None
        top_repl = replacements[0] if replacements else None

        if high_red:
            action = PortfolioAction.CONSOLIDATE
            conf = PortfolioConfidence.HIGH
            conf_score = 85.0
            reasons.append(f"Identified high usage redundancy between {high_red[0].vehicle_a_label} and {high_red[0].vehicle_b_label}.")
            reasons.append(f"Consolidating could save up to {high_red[0].potential_annual_savings_formatted} per year in fixed ownership costs.")
            impact = f"Potential annual savings of {high_red[0].potential_annual_savings_formatted} with minimal utility sacrifice."

        elif top_sell and top_sell.sell_priority_score >= 75.0:
            action = PortfolioAction.SELL_VEHICLE
            conf = PortfolioConfidence.HIGH if top_sell.sell_priority_score >= 82.0 else PortfolioConfidence.MODERATE
            conf_score = top_sell.sell_priority_score
            reasons.append(f"{top_sell.vehicle_label} has strong divestment metrics (Sell Priority {top_sell.sell_priority_score:.0f}/100).")
            reasons.extend(top_sell.factors[:2])
            impact = f"Divesting {top_sell.vehicle_label} liquidates {top_sell.current_value_formatted} and saves {top_sell.annual_cost_formatted}/yr in ownership expenses."

        elif top_repl and top_repl.tco_savings_5y >= 60000:
            action = PortfolioAction.REPLACE_VEHICLE
            conf = PortfolioConfidence.MODERATE
            conf_score = top_repl.replacement_score
            reasons.append(f"Replacing {top_repl.current_vehicle_label} with {top_repl.candidate_brand} {top_repl.candidate_model} yields {top_repl.tco_savings_5y_formatted} 5Y TCO reduction.")
            if top_repl.break_even_months is not None:
                reasons.append(f"Estimated acquisition break-even is ~{top_repl.break_even_months:.0f} months.")
            impact = f"5-Year net ownership savings of {top_repl.tco_savings_5y_formatted}."

        else:
            action = PortfolioAction.KEEP_GARAGE
            conf = PortfolioConfidence.HIGH
            conf_score = efficiency.overall_score
            reasons.append(f"Current garage portfolio demonstrates high efficiency ({efficiency.overall_score:.0f}/100).")
            reasons.append(f"Vehicles are cost-effective (average {summary.average_cost_per_km_formatted}) with balanced utilization.")
            impact = "Maintain current ownership configuration. No immediate transaction required."

        return GarageRecommendation(
            action=action,
            confidence=conf,
            confidence_score=conf_score,
            reasons=reasons,
            economic_impact_summary=impact,
            headline=f"Portfolio Action: {action.value.replace('_', ' ').title()}",
            primary_reasons=reasons,
            caution_factors=["Resale trajectories and market forecasts are statistical estimates."],
            suggested_next_steps=["Review high depreciation vehicles", "Monitor seasonal sell timing"],
            portfolio_action_score=conf_score
        )

    def _build_empty_garage_response(self) -> GarageIntelligenceResponse:
        empty_summary = GarageSummary(
            total_vehicles=0,
            owned_vehicles=0,
            owned_vehicles_count=0,
            considering_vehicles=0,
            watching_vehicles=0,
            sold_vehicles=0,
            total_current_value=0.0,
            total_current_value_formatted="₹0",
            total_annual_cost=0.0,
            total_annual_cost_formatted="₹0",
            total_5y_tco=0.0,
            total_5y_tco_formatted="₹0",
            total_projected_5y_resale=0.0,
            total_projected_5y_resale_formatted="₹0",
            average_cost_per_km=0.0,
            average_cost_per_km_formatted="₹0.00/km",
            weighted_average_risk=0.0,
            weighted_market_momentum=0.0,
            overall_market_direction="STABLE",
            risk_level_label="LOW",
            excluded_vehicles_count=0,
            excluded_vehicle_reasons=[]
        )
        empty_efficiency = GarageEfficiencyScore(
            overall_score=0.0,
            categories=[],
            summary_reasoning="Garage contains no vehicle records.",
            rating_label="Suboptimal"
        )
        empty_recommendation = GarageRecommendation(
            action=PortfolioAction.INSUFFICIENT_EVIDENCE,
            confidence=PortfolioConfidence.INSUFFICIENT_EVIDENCE,
            confidence_score=0.0,
            reasons=["No vehicles currently saved in your garage."],
            economic_impact_summary="Add your vehicles to compute personalized portfolio intelligence.",
            headline="Portfolio Action: Insufficient Evidence",
            primary_reasons=["No vehicles currently saved in your garage."],
            caution_factors=[],
            suggested_next_steps=["Add your first vehicle to get started."],
            portfolio_action_score=0.0
        )
        empty_rankings = VehicleRankings(
            most_expensive_annual=[],
            highest_5y_tco=[],
            highest_cost_per_km=[],
            highest_depreciation=[],
            highest_risk=[]
        )

        return GarageIntelligenceResponse(
            summary=empty_summary,
            efficiency=empty_efficiency,
            efficiency_score=empty_efficiency,
            recommendation=empty_recommendation,
            sell_first_ranking=[],
            keep_first_ranking=[],
            replacement_opportunities=[],
            redundancies=[],
            redundancy_analysis=[],
            rankings=empty_rankings,
            vehicle_rankings=empty_rankings,
            vehicle_snapshots=[],
            snapshots=[],
            limitations=["Add vehicles to your garage to evaluate portfolio intelligence."],
            provenance={}
        )

    # -------------------------------------------------------------------------
    # 4. Garage Scenario Simulation
    # -------------------------------------------------------------------------
    def simulate_garage_scenario(
        self,
        db: Session,
        user_id: str,
        request: GarageScenarioRequest
    ) -> GarageScenarioResponse:
        """
        Simulates what-if modifications (sell, replace, add, update mileage) on the user's garage.
        """
        vehicles = self.list_vehicles(db, user_id)
        baseline_snapshots = [self.evaluate_vehicle_snapshot(v) for v in vehicles]
        baseline_summary = self._compute_portfolio_summary(baseline_snapshots)
        baseline_eff = self._compute_efficiency_score(baseline_snapshots, baseline_summary)

        # Build modified vehicle list
        action_map = {a.vehicle_id: a for a in request.actions if a.vehicle_id}
        simulated_vehicles: List[GarageVehicle] = []
        removed_ids = set()

        # Handle removals / replacements / mileage updates
        for v in vehicles:
            if v.id in action_map:
                act = action_map[v.id]
                if act.action_type == GarageScenarioActionType.SELL:
                    removed_ids.add(v.id)
                    continue
                elif act.action_type == GarageScenarioActionType.REPLACE and act.replacement_vehicle:
                    removed_ids.add(v.id)
                    rep = act.replacement_vehicle
                    sim_v = GarageVehicle(
                        id=f"sim_{rep.brand}_{rep.model}".lower().replace(" ", "_"),
                        user_id=user_id,
                        brand=rep.brand,
                        model=rep.model,
                        variant=rep.variant,
                        year=rep.year,
                        fuel_type=rep.fuel_type or "Petrol",
                        transmission=rep.transmission or "Manual",
                        city=rep.city or v.city,
                        purchase_price=rep.purchase_price,
                        annual_km=act.annual_km_override or rep.annual_km or v.annual_km,
                        current_odometer=rep.current_odometer or 35000,
                        ownership_status=OwnershipStatus.OWNED.value
                    )
                    simulated_vehicles.append(sim_v)
                elif act.action_type == GarageScenarioActionType.UPDATE_MILEAGE and act.annual_km_override is not None:
                    # Clone with updated mileage
                    sim_v = GarageVehicle(
                        id=v.id,
                        user_id=user_id,
                        brand=v.brand,
                        model=v.model,
                        variant=v.variant,
                        year=v.year,
                        fuel_type=v.fuel_type,
                        transmission=v.transmission,
                        city=v.city,
                        purchase_price=v.purchase_price,
                        annual_km=act.annual_km_override,
                        current_odometer=v.current_odometer,
                        ownership_status=v.ownership_status
                    )
                    simulated_vehicles.append(sim_v)
                else:
                    simulated_vehicles.append(v)
            else:
                simulated_vehicles.append(v)

        # Handle standalone ADD actions
        for act in request.actions:
            if act.action_type == GarageScenarioActionType.ADD and act.replacement_vehicle:
                rep = act.replacement_vehicle
                sim_v = GarageVehicle(
                    id=f"sim_add_{rep.brand}_{rep.model}".lower().replace(" ", "_"),
                    user_id=user_id,
                    brand=rep.brand,
                    model=rep.model,
                    variant=rep.variant,
                    year=rep.year,
                    fuel_type=rep.fuel_type or "Petrol",
                    transmission=rep.transmission or "Manual",
                    city=rep.city or "Bengaluru",
                    purchase_price=rep.purchase_price,
                    annual_km=act.annual_km_override or rep.annual_km or 12000,
                    current_odometer=rep.current_odometer or 35000,
                    ownership_status=OwnershipStatus.OWNED.value
                )
                simulated_vehicles.append(sim_v)

        scenario_snapshots = [self.evaluate_vehicle_snapshot(v) for v in simulated_vehicles]
        scenario_summary = self._compute_portfolio_summary(scenario_snapshots)
        scenario_eff = self._compute_efficiency_score(scenario_snapshots, scenario_summary)

        delta_annual = scenario_summary.total_annual_cost - baseline_summary.total_annual_cost
        delta_tco = scenario_summary.total_5y_tco - baseline_summary.total_5y_tco
        delta_eff = round(scenario_eff.overall_score - baseline_eff.overall_score, 1)

        # Break-even calculation if replacement happened
        if delta_annual < 0:
            acq_capital = max(0.0, scenario_summary.total_current_value - baseline_summary.total_current_value)
            if acq_capital > 0:
                break_even_m = round(acq_capital / (abs(delta_annual) / 12.0), 1)
            else:
                break_even_m = 0.0
        else:
            break_even_m = None

        if delta_annual < 0:
            exec_summary = f"Scenario reduces annual portfolio expenditure by {self._format_inr(abs(delta_annual))} (-{abs(delta_tco/max(1, baseline_summary.total_5y_tco))*100:.1f}% 5Y TCO) with efficiency delta of {delta_eff:+.1f} points."
        elif delta_annual > 0:
            exec_summary = f"Scenario increases annual portfolio expenditure by {self._format_inr(delta_annual)} (+{abs(delta_tco/max(1, baseline_summary.total_5y_tco))*100:.1f}% 5Y TCO) with efficiency delta of {delta_eff:+.1f} points."
        else:
            exec_summary = f"Scenario maintains flat annual operating expenditure with efficiency delta of {delta_eff:+.1f} points."

        return GarageScenarioResponse(
            baseline_summary=baseline_summary,
            scenario_summary=scenario_summary,
            delta_annual_cost=delta_annual,
            delta_annual_cost_formatted=f"{'+' if delta_annual >= 0 else ''}{self._format_inr(delta_annual)}",
            delta_5y_tco=delta_tco,
            delta_5y_tco_formatted=f"{'+' if delta_tco >= 0 else ''}{self._format_inr(delta_tco)}",
            delta_efficiency_score=delta_eff,
            break_even_months=break_even_m,
            executive_summary=exec_summary,
            scenario_vehicles=scenario_snapshots
        )

    # -------------------------------------------------------------------------
    # 5. Multi-Vehicle Garage Comparison
    # -------------------------------------------------------------------------
    def compare_garage_vehicles(
        self,
        db: Session,
        user_id: str,
        request: GarageCompareRequest
    ) -> GarageCompareResponse:
        """
        Generates comparative economic matrix across up to 10 selected garage vehicles.
        """
        vehicles = db.query(GarageVehicle).filter(
            GarageVehicle.user_id == user_id,
            GarageVehicle.id.in_(request.vehicle_ids)
        ).all()

        if not vehicles:
            raise ValueError("No matching garage vehicles found for comparison.")

        snapshots = [self.evaluate_vehicle_snapshot(v) for v in vehicles]

        # Economic rankings
        rank_lowest_cost_km = sorted(snapshots, key=lambda s: s.cost_per_km)
        rank_lowest_tco = sorted(snapshots, key=lambda s: s.five_year_tco)
        rank_highest_resale = sorted(snapshots, key=lambda s: s.projected_resale_5y, reverse=True)
        rank_lowest_risk = sorted(snapshots, key=lambda s: s.risk_score)

        best_keep = rank_lowest_cost_km[0].vehicle.id if rank_lowest_cost_km else None
        sell_first_list = self._compute_sell_first_ranking(snapshots)
        best_sell = sell_first_list[0].vehicle_id if sell_first_list else None

        economic_ranks = {
            "lowest_cost_per_km": [s.vehicle.id for s in rank_lowest_cost_km],
            "lowest_five_year_tco": [s.vehicle.id for s in rank_lowest_tco],
            "highest_resale_retention": [s.vehicle.id for s in rank_highest_resale],
            "lowest_risk": [s.vehicle.id for s in rank_lowest_risk]
        }

        best_keep_name = rank_lowest_cost_km[0].vehicle.brand + " " + rank_lowest_cost_km[0].vehicle.model if rank_lowest_cost_km else "N/A"
        summary_txt = f"Comparing {len(snapshots)} vehicles. {best_keep_name} delivers the most economical cost per km ({rank_lowest_cost_km[0].cost_per_km_formatted})."

        return GarageCompareResponse(
            total_vehicles=len(snapshots),
            vehicles=snapshots,
            economic_rankings=economic_ranks,
            best_keep_vehicle_id=best_keep,
            best_sell_vehicle_id=best_sell,
            summary=summary_txt
        )


garage_intelligence_service = GarageIntelligenceService()
