"""
AutoValue Total Cost of Ownership (TCO) & Resale Intelligence Service (Phase 13).
Delivers transparent, multi-year ownership economics, market-anchored depreciation,
resale value projections with empirical uncertainty intervals, sensitivity analysis,
and multi-vehicle comparison matrices.
"""
import math
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

from backend.app.schemas.valuation import ValuationRequestSchema, ValuationResponse
from backend.app.schemas.tco import (
    TCOAssumptions,
    TCOPurchaseInfo,
    TCOCostBreakdown,
    ResaleProjection,
    YearlyProjectionItem,
    TCOSensitivityItem,
    ScenarioSummary,
    TCOResponse,
    TCOCompareItem,
    TCOCompareResponse
)
from backend.app.services.valuation_service import valuation_service
from backend.app.services.market_timing_service import MarketTimingService

logger = logging.getLogger("autovalue.tco_service")


class TCOService:
    """
    Core engine for Vehicle Total Cost of Ownership and Resale Intelligence.
    """

    # Transparent, centralized default parameters for Indian automotive market
    DEFAULT_FUEL_PRICES: Dict[str, float] = {
        "petrol": 104.50,
        "diesel": 92.50,
        "cng": 86.00,
        "electric": 10.00,
        "ev": 10.00,
        "hybrid": 104.50
    }

    DEFAULT_EFFICIENCIES: Dict[str, float] = {
        "petrol": 16.0,       # km/L
        "diesel": 18.5,       # km/L
        "cng": 22.0,          # km/kg
        "electric": 15.0,     # kWh per 100km
        "ev": 15.0,           # kWh per 100km
        "hybrid": 22.5        # km/L
    }

    DEFAULT_MAINTENANCE_ANNUAL: Dict[str, float] = {
        "petrol": 15000.0,
        "diesel": 18000.0,
        "cng": 16000.0,
        "electric": 10000.0,
        "ev": 10000.0,
        "hybrid": 16000.0
    }

    DEFAULT_INSURANCE_RATE: float = 0.03  # 3% of vehicle value per annum
    SUPPORTED_FUEL_TYPES: List[str] = ["petrol", "diesel", "cng", "electric", "ev", "hybrid"]

    def __init__(self):
        self.market_timing_service = MarketTimingService()

    def normalize_fuel_type(self, fuel_type: str) -> str:
        """
        Normalizes and validates fuel type string.
        """
        f = (fuel_type or "").strip().lower()
        if f in ["electric", "ev"]:
            return "electric"
        if f in self.SUPPORTED_FUEL_TYPES:
            return f
        raise ValueError(
            f"Unsupported fuel type '{fuel_type}'. Supported fuel types: Petrol, Diesel, CNG, Electric, Hybrid."
        )

    def resolve_purchase_price(
        self,
        mode: str,
        custom_price: Optional[float],
        asking_price: Optional[float],
        estimated_fair_value: float
    ) -> Tuple[float, str, str]:
        """
        Determines effective purchase price based on selected mode.
        Returns (price, mode_name, source_label).
        """
        m = (mode or "FAIR_VALUE").upper()
        if m == "CUSTOM" and custom_price is not None and custom_price > 0:
            return round(custom_price, 2), "CUSTOM", "User Custom Negotiated Price"
        elif m == "ASKING_PRICE" and asking_price is not None and asking_price > 0:
            return round(asking_price, 2), "ASKING_PRICE", "Advertised Seller Asking Price"
        else:
            return round(estimated_fair_value, 2), "FAIR_VALUE", "AutoValue ML Estimated Fair Value"

    def calculate_annual_fuel_cost(
        self,
        annual_km: int,
        fuel_type: str,
        fuel_price_override: Optional[float],
        efficiency_override: Optional[float],
        vehicle_mileage: Optional[float]
    ) -> Tuple[float, float, float, Dict[str, str]]:
        """
        Calculates annual fuel/energy consumption and expenditure.
        Returns (annual_cost, effective_fuel_price, effective_efficiency, provenance_tags).
        """
        norm_fuel = self.normalize_fuel_type(fuel_type)
        provenance = {}

        # 1. Resolve Fuel Price
        if fuel_price_override is not None and fuel_price_override > 0:
            fuel_price = fuel_price_override
            provenance["fuel_price"] = "USER_INPUT"
        else:
            fuel_price = self.DEFAULT_FUEL_PRICES.get(norm_fuel, 104.50)
            provenance["fuel_price"] = "DEFAULT_CONFIG"

        # 2. Resolve Efficiency
        if efficiency_override is not None and efficiency_override > 0:
            efficiency = efficiency_override
            provenance["fuel_efficiency"] = "USER_INPUT"
        elif vehicle_mileage is not None and vehicle_mileage > 0 and norm_fuel != "electric":
            efficiency = vehicle_mileage
            provenance["fuel_efficiency"] = "OBSERVED_MARKET"
        else:
            efficiency = self.DEFAULT_EFFICIENCIES.get(norm_fuel, 16.0)
            provenance["fuel_efficiency"] = "DEFAULT_CONFIG"

        if efficiency <= 0:
            raise ValueError("Fuel efficiency must be strictly greater than 0.")

        # 3. Compute consumption
        if norm_fuel == "electric":
            # efficiency is kWh per 100km
            annual_kwh = (annual_km * (efficiency / 100.0))
            annual_cost = annual_kwh * fuel_price
        else:
            # efficiency is km per L or kg
            annual_units = annual_km / efficiency
            annual_cost = annual_units * fuel_price

        return round(annual_cost, 2), round(fuel_price, 2), round(efficiency, 2), provenance

    def project_market_depreciation(
        self,
        purchase_price: float,
        initial_age: int,
        ownership_years: int,
        annual_km: int,
        comparable_count: int,
        market_stats: Any,
        brand: str,
        model: str,
        city: str
    ) -> Tuple[List[Dict[str, float]], ResaleProjection]:
        """
        Calculates market-anchored annual depreciation and resale range intervals.
        """
        # Baseline annual depreciation rates by vehicle age tier
        # Year 1-3: ~13.5%, Year 4-7: ~9.5%, Year 8+: ~7.0%
        # High annual mileage increases depreciation rate (+0.5% to +2.0%)
        km_penalty = max(-0.02, min(0.03, (annual_km - 12000) / 100000.0 * 0.05))

        # Check market timing / historical trend if available (cached for performance)
        trend_adjustment = 0.0
        cache_key = (brand or "").strip().lower(), (model or "").strip().lower(), (city or "").strip().lower()
        if not hasattr(self, "_timing_cache"):
            self._timing_cache = {}

        if cache_key in self._timing_cache:
            trend_adjustment = self._timing_cache[cache_key]
        else:
            try:
                timing = self.market_timing_service.analyze_market_timing(brand=brand, model=model, city=city)
                if timing.percentage_movement is not None:
                    # Modest anchoring to observed 6m market trend (max +/- 2%)
                    trend_adjustment = max(-0.02, min(0.02, -(timing.percentage_movement / 100.0) * 0.2))
            except Exception:
                trend_adjustment = 0.0
            self._timing_cache[cache_key] = trend_adjustment

        current_val = purchase_price
        yearly_resale: List[Dict[str, float]] = []

        for t in range(1, ownership_years + 1):
            curr_age = initial_age + t
            if curr_age <= 3:
                base_rate = 0.135
            elif curr_age <= 7:
                base_rate = 0.095
            else:
                base_rate = 0.070

            effective_rate = max(0.04, min(0.25, base_rate + km_penalty + trend_adjustment))
            current_val = current_val * (1.0 - effective_rate)

            # Residual scrap floor (at least 12% of purchase price or 40,000 INR)
            min_floor = max(40000.0, purchase_price * 0.12)
            current_val = max(min_floor, current_val)

            # Uncertainty width grows with projection horizon
            # Baseline uncertainty 6% + 2.5% per projection year
            dispersion_factor = 0.04
            if market_stats and getattr(market_stats, "median", None) and getattr(market_stats, "p25", None) and getattr(market_stats, "p75", None):
                if market_stats.median > 0:
                    dispersion_factor = min(0.12, (market_stats.p75 - market_stats.p25) / market_stats.median * 0.25)

            half_width_pct = min(0.28, 0.06 + (t * 0.025) + dispersion_factor)
            low_bound = max(35000.0, current_val * (1.0 - half_width_pct))
            high_bound = current_val * (1.0 + half_width_pct)

            yearly_resale.append({
                "year": t,
                "age": curr_age,
                "resale_value": round(current_val, 2),
                "resale_low": round(low_bound, 2),
                "resale_high": round(high_bound, 2),
                "annual_depreciation_rate": round(effective_rate, 4)
            })

        final_resale = yearly_resale[-1]
        final_val = final_resale["resale_value"]
        retention_pct = round((final_val / purchase_price * 100.0) if purchase_price > 0 else 0.0, 1)
        avg_deprec_rate = round(1.0 - math.pow(final_val / purchase_price, 1.0 / ownership_years), 4) if (purchase_price > 0 and final_val > 0) else 0.10

        # Determine evidence confidence
        if comparable_count >= 8:
            confidence = "HIGH"
        elif comparable_count >= 3:
            confidence = "MODERATE"
        elif comparable_count >= 1:
            confidence = "LOW"
        else:
            confidence = "INSUFFICIENT_EVIDENCE"

        resale_summary = ResaleProjection(
            estimated_resale_value=final_val,
            lower_bound=final_resale["resale_low"],
            upper_bound=final_resale["resale_high"],
            confidence=confidence,
            projected_retention_pct=retention_pct,
            annual_depreciation_rate=round(avg_deprec_rate * 100.0, 1),
            methodology=f"Market-anchored geometric depreciation ({avg_deprec_rate*100.0:.1f}% avg/yr) calibrated against vehicle age curves and mileage intensity."
        )

        return yearly_resale, resale_summary

    def calculate_tco(
        self,
        vehicle_data: Any,
        valuation_resp: ValuationResponse,
        assumptions: Optional[TCOAssumptions] = None
    ) -> TCOResponse:
        """
        Executes complete multi-year Total Cost of Ownership and Resale Intelligence calculations.
        """
        if hasattr(vehicle_data, "model_dump"):
            v_dict = vehicle_data.model_dump()
        elif not isinstance(vehicle_data, dict):
            v_dict = dict(vehicle_data)
        else:
            v_dict = dict(vehicle_data)

        if assumptions is None:
            assumptions = TCOAssumptions()

        # Horizon validation
        years = max(1, min(10, assumptions.ownership_years))
        annual_km = max(0, min(100000, assumptions.annual_km))
        fuel_type = self.normalize_fuel_type(v_dict.get("fuel_type", "Petrol"))
        current_year = 2024
        reg_year = int(v_dict.get("year", 2020))
        initial_age = max(0, current_year - reg_year)

        # Provenance tracking dictionary
        provenance: Dict[str, str] = {
            "annual_km": "USER_INPUT" if assumptions.annual_km != 12000 else "DEFAULT_CONFIG",
            "ownership_years": "USER_INPUT" if assumptions.ownership_years != 5 else "DEFAULT_CONFIG",
            "purchase_price_mode": "USER_INPUT" if assumptions.purchase_price_mode != "FAIR_VALUE" else "DEFAULT_CONFIG"
        }

        # 1. Resolve Purchase Price
        est_fair_val = valuation_resp.valuation.estimated_value
        ask_price = v_dict.get("asking_price")
        purchase_price, p_mode, p_source = self.resolve_purchase_price(
            mode=assumptions.purchase_price_mode,
            custom_price=assumptions.custom_purchase_price,
            asking_price=ask_price,
            estimated_fair_value=est_fair_val
        )
        purchase_info = TCOPurchaseInfo(
            mode=p_mode,
            price=purchase_price,
            source=p_source
        )

        # 2. Fuel / Energy Calculation
        veh_mileage = v_dict.get("mileage")
        annual_fuel_cost, eff_fuel_price, eff_efficiency, fuel_prov = self.calculate_annual_fuel_cost(
            annual_km=annual_km,
            fuel_type=fuel_type,
            fuel_price_override=assumptions.fuel_price,
            efficiency_override=assumptions.fuel_efficiency,
            vehicle_mileage=veh_mileage
        )
        provenance.update(fuel_prov)

        # 3. Maintenance Budget
        if assumptions.annual_maintenance is not None and assumptions.annual_maintenance >= 0:
            base_maintenance = assumptions.annual_maintenance
            provenance["annual_maintenance"] = "USER_INPUT"
        else:
            base_maintenance = self.DEFAULT_MAINTENANCE_ANNUAL.get(fuel_type, 15000.0)
            provenance["annual_maintenance"] = "DEFAULT_CONFIG"

        # 4. Insurance Budget
        if assumptions.custom_annual_insurance is not None and assumptions.custom_annual_insurance >= 0:
            fixed_insurance = assumptions.custom_annual_insurance
            insurance_rate = assumptions.annual_insurance_rate
            provenance["annual_insurance"] = "USER_INPUT"
        else:
            fixed_insurance = None
            insurance_rate = assumptions.annual_insurance_rate
            provenance["annual_insurance_rate"] = "DEFAULT_CONFIG" if insurance_rate == 0.03 else "USER_INPUT"

        # 5. Depreciation & Resale Projection
        comp_count = valuation_resp.market.comparable_count if valuation_resp.market else 0
        yearly_resale, resale_summary = self.project_market_depreciation(
            purchase_price=purchase_price,
            initial_age=initial_age,
            ownership_years=years,
            annual_km=annual_km,
            comparable_count=comp_count,
            market_stats=valuation_resp.market,
            brand=v_dict.get("brand", "Unknown"),
            model=v_dict.get("model", "Unknown"),
            city=v_dict.get("city", "Mumbai")
        )

        # 6. Build Year-by-Year Progression
        yearly_items: List[YearlyProjectionItem] = []
        cumulative_expenditure = purchase_price + assumptions.upfront_tax_registration
        total_fuel = 0.0
        total_insurance = 0.0
        total_maintenance = 0.0
        total_other = 0.0

        for idx, r_item in enumerate(yearly_resale):
            t = r_item["year"]
            cum_km = annual_km * t
            prev_val = purchase_price if t == 1 else yearly_resale[idx - 1]["resale_value"]

            # Year t Insurance
            if fixed_insurance is not None:
                yr_ins = fixed_insurance
            else:
                yr_ins = max(4000.0, prev_val * insurance_rate)

            # Year t Maintenance (slight aging curve +4% per year after age 5)
            age_t = r_item["age"]
            age_multiplier = 1.0 + (max(0, age_t - 5) * 0.04)
            yr_maint = base_maintenance * age_multiplier

            yr_fuel = annual_fuel_cost
            yr_other = assumptions.other_annual_cost
            yr_running = yr_fuel + yr_ins + yr_maint + yr_other

            total_fuel += yr_fuel
            total_insurance += yr_ins
            total_maintenance += yr_maint
            total_other += yr_other
            cumulative_expenditure += yr_running

            net_to_date = cumulative_expenditure - r_item["resale_value"]
            cost_per_km_yr = round(net_to_date / cum_km, 2) if cum_km > 0 else 0.0

            resale_val = round(r_item["resale_value"], 2)
            resale_low = round(r_item["resale_low"], 2)
            resale_high = round(r_item["resale_high"], 2)
            cum_exp = round(cumulative_expenditure, 2)
            net_cost = round(net_to_date, 2)

            def _fmt(val: float) -> str:
                if val >= 10000000:
                    return f"₹{val / 10000000:.2f} Cr"
                elif val >= 100000:
                    return f"₹{val / 100000:.2f} Lakh"
                return f"₹{val:,.0f}"

            yearly_items.append(YearlyProjectionItem(
                year=t,
                vehicle_age=age_t,
                cumulative_km=cum_km,
                annual_fuel_cost=round(yr_fuel, 2),
                annual_insurance_cost=round(yr_ins, 2),
                annual_maintenance_cost=round(yr_maint, 2),
                annual_running_cost=round(yr_running, 2),
                cumulative_expenditure=cum_exp,
                projected_resale_value=resale_val,
                projected_resale_low=resale_low,
                projected_resale_high=resale_high,
                net_cost_to_date=net_cost,
                cost_per_km_to_date=cost_per_km_yr,
                resale_value_formatted=_fmt(resale_val),
                resale_low_formatted=_fmt(resale_low),
                resale_high_formatted=_fmt(resale_high),
                cumulative_gross_formatted=_fmt(cum_exp),
                net_cost_to_date_formatted=_fmt(net_cost)
            ))

        # 7. Overall Cost Breakdown
        gross_cost = round(cumulative_expenditure, 2)
        final_resale_val = resale_summary.estimated_resale_value
        net_tco = round(gross_cost - final_resale_val, 2)
        annual_cost = round(net_tco / years, 2)
        total_projected_km = annual_km * years
        cost_per_km = round((net_tco / total_projected_km) if total_projected_km > 0 else 0.0, 2)

        cost_breakdown = TCOCostBreakdown(
            purchase_cost=purchase_price,
            fuel_cost=round(total_fuel, 2),
            insurance_cost=round(total_insurance, 2),
            maintenance_cost=round(total_maintenance, 2),
            taxes_and_fees=round(assumptions.upfront_tax_registration, 2),
            other_costs=round(total_other, 2),
            gross_cost=gross_cost,
            estimated_resale=round(final_resale_val, 2),
            net_tco=net_tco,
            annual_cost=annual_cost,
            cost_per_km=cost_per_km,
            total_projected_km=total_projected_km
        )

        # 8. Scenario Analysis (Conservative, Base, Optimistic)
        scenarios = self._build_scenarios(
            purchase_price=purchase_price,
            total_fuel=total_fuel,
            total_insurance=total_insurance,
            total_maintenance=total_maintenance,
            total_other=total_other,
            taxes_fees=assumptions.upfront_tax_registration,
            resale_val=final_resale_val,
            years=years,
            total_km=total_projected_km
        )

        # 9. Sensitivity Analysis
        sensitivity = self._build_sensitivity(
            net_tco=net_tco,
            total_fuel=total_fuel,
            total_maintenance=total_maintenance,
            resale_val=final_resale_val,
            purchase_price=purchase_price,
            retention_pct=resale_summary.projected_retention_pct / 100.0,
            years=years
        )

        # Resolved Assumptions Output
        resolved_assumptions = {
            "annual_km": annual_km,
            "ownership_years": years,
            "purchase_price_mode": p_mode,
            "effective_purchase_price": purchase_price,
            "fuel_price": eff_fuel_price,
            "fuel_efficiency": eff_efficiency,
            "annual_fuel_cost": round(annual_fuel_cost, 2),
            "annual_maintenance_base": round(base_maintenance, 2),
            "annual_insurance_rate": insurance_rate,
            "upfront_tax_registration": assumptions.upfront_tax_registration,
            "other_annual_cost": assumptions.other_annual_cost
        }

        return TCOResponse(
            vehicle={
                "brand": v_dict.get("brand"),
                "model": v_dict.get("model"),
                "variant": v_dict.get("variant"),
                "year": reg_year,
                "fuel_type": v_dict.get("fuel_type", "Petrol"),
                "transmission": v_dict.get("transmission", "Manual"),
                "city": v_dict.get("city", "Mumbai")
            },
            purchase=purchase_info,
            assumptions=resolved_assumptions,
            assumptions_provenance=provenance,
            ownership=cost_breakdown,
            resale=resale_summary,
            yearly_projection=yearly_items,
            scenarios=scenarios,
            sensitivity=sensitivity
        )

    def _build_scenarios(
        self,
        purchase_price: float,
        total_fuel: float,
        total_insurance: float,
        total_maintenance: float,
        total_other: float,
        taxes_fees: float,
        resale_val: float,
        years: int,
        total_km: int
    ) -> Dict[str, ScenarioSummary]:
        """
        Generates Base, Conservative, and Optimistic scenario metrics.
        """
        # 1. Base Scenario
        base_gross = purchase_price + total_fuel + total_insurance + total_maintenance + total_other + taxes_fees
        base_net = base_gross - resale_val
        base_summary = ScenarioSummary(
            name="Base",
            gross_cost=round(base_gross, 2),
            estimated_resale=round(resale_val, 2),
            net_tco=round(base_net, 2),
            annual_cost=round(base_net / years, 2),
            cost_per_km=round((base_net / total_km) if total_km > 0 else 0.0, 2)
        )

        # 2. Conservative Scenario: Fuel +10%, Maint +25%, Resale -10%
        cons_gross = purchase_price + (total_fuel * 1.10) + total_insurance + (total_maintenance * 1.25) + total_other + taxes_fees
        cons_resale = resale_val * 0.90
        cons_net = cons_gross - cons_resale
        cons_summary = ScenarioSummary(
            name="Conservative",
            gross_cost=round(cons_gross, 2),
            estimated_resale=round(cons_resale, 2),
            net_tco=round(cons_net, 2),
            annual_cost=round(cons_net / years, 2),
            cost_per_km=round((cons_net / total_km) if total_km > 0 else 0.0, 2)
        )

        # 3. Optimistic Scenario: Fuel -10%, Maint -15%, Resale +10%
        opt_gross = purchase_price + (total_fuel * 0.90) + total_insurance + (total_maintenance * 0.85) + total_other + taxes_fees
        opt_resale = resale_val * 1.10
        opt_net = opt_gross - opt_resale
        opt_summary = ScenarioSummary(
            name="Optimistic",
            gross_cost=round(opt_gross, 2),
            estimated_resale=round(opt_resale, 2),
            net_tco=round(opt_net, 2),
            annual_cost=round(opt_net / years, 2),
            cost_per_km=round((opt_net / total_km) if total_km > 0 else 0.0, 2)
        )

        return {
            "BASE": base_summary,
            "CONSERVATIVE": cons_summary,
            "OPTIMISTIC": opt_summary
        }

    def _build_sensitivity(
        self,
        net_tco: float,
        total_fuel: float,
        total_maintenance: float,
        resale_val: float,
        purchase_price: float,
        retention_pct: float,
        years: int
    ) -> List[TCOSensitivityItem]:
        """
        Calculates mathematical sensitivity deltas across core cost variables.
        """
        items: List[TCOSensitivityItem] = []

        # 1. Fuel Price +10%
        delta_fuel = total_fuel * 0.10
        items.append(TCOSensitivityItem(
            variable="fuel_price",
            change_description="Fuel price increases by +10%",
            delta_tco=round(delta_fuel, 2),
            percentage_impact=round((delta_fuel / net_tco * 100.0) if net_tco > 0 else 0.0, 1),
            new_net_tco=round(net_tco + delta_fuel, 2)
        ))

        # 2. Annual Mileage +20% (increases fuel + slight depreciation impact)
        delta_km = (total_fuel * 0.20) + (resale_val * 0.03)
        items.append(TCOSensitivityItem(
            variable="annual_km",
            change_description="Annual driving distance increases by +20%",
            delta_tco=round(delta_km, 2),
            percentage_impact=round((delta_km / net_tco * 100.0) if net_tco > 0 else 0.0, 1),
            new_net_tco=round(net_tco + delta_km, 2)
        ))

        # 3. Purchase Price -₹50,000 (negotiation discount)
        # Net saving = 50,000 - (50,000 * retention_pct)
        delta_price = -50000.0 * (1.0 - retention_pct)
        items.append(TCOSensitivityItem(
            variable="purchase_price",
            change_description="Negotiate purchase price down by ₹50,000",
            delta_tco=round(delta_price, 2),
            percentage_impact=round((delta_price / net_tco * 100.0) if net_tco > 0 else 0.0, 1),
            new_net_tco=round(net_tco + delta_price, 2)
        ))

        # 4. Annual Maintenance +₹10,000/yr
        delta_maint = 10000.0 * years
        items.append(TCOSensitivityItem(
            variable="maintenance",
            change_description="Maintenance budget increases by ₹10,000/year",
            delta_tco=round(delta_maint, 2),
            percentage_impact=round((delta_maint / net_tco * 100.0) if net_tco > 0 else 0.0, 1),
            new_net_tco=round(net_tco + delta_maint, 2)
        ))

        # 5. Resale Value -10%
        delta_resale = resale_val * 0.10
        items.append(TCOSensitivityItem(
            variable="resale_value",
            change_description="Resale market drops -10% below projection",
            delta_tco=round(delta_resale, 2),
            percentage_impact=round((delta_resale / net_tco * 100.0) if net_tco > 0 else 0.0, 1),
            new_net_tco=round(net_tco + delta_resale, 2)
        ))

        return items

    def compare_tco(
        self,
        vehicles: List[ValuationRequestSchema],
        shared_assumptions: Optional[TCOAssumptions] = None
    ) -> TCOCompareResponse:
        """
        Executes bounded comparison across multiple candidate vehicles (max 10).
        """
        if len(vehicles) > 10:
            raise ValueError("Comparison is limited to a maximum of 10 vehicles.")

        assumptions = shared_assumptions or TCOAssumptions()
        results: List[TCOCompareItem] = []
        detailed_responses: List[TCOResponse] = []

        for idx, req in enumerate(vehicles):
            val_resp = valuation_service.evaluate_valuation(req, include_shap=False)
            tco_resp = self.calculate_tco(req.model_dump(), val_resp, assumptions)
            detailed_responses.append(tco_resp)

            item = TCOCompareItem(
                vehicle_identifier=f"{req.brand} {req.model} ({req.year}) - #{idx+1}",
                brand=req.brand,
                model=req.model,
                year=req.year,
                fuel_type=req.fuel_type,
                purchase_price=tco_resp.purchase.price,
                gross_cost=tco_resp.ownership.gross_cost,
                estimated_resale=tco_resp.ownership.estimated_resale,
                net_tco=tco_resp.ownership.net_tco,
                annual_cost=tco_resp.ownership.annual_cost,
                cost_per_km=tco_resp.ownership.cost_per_km,
                resale_confidence=tco_resp.resale.confidence
            )
            results.append(item)

        # Break-even analysis if exactly 2 vehicles compared
        break_even_data = None
        if len(detailed_responses) == 2:
            break_even_data = self._calculate_break_even(detailed_responses[0], detailed_responses[1])

        return TCOCompareResponse(
            total_vehicles=len(results),
            horizon_years=assumptions.ownership_years,
            results=results,
            break_even_analysis=break_even_data
        )

    def _calculate_break_even(self, resp_a: TCOResponse, resp_b: TCOResponse) -> Dict[str, Any]:
        """
        Calculates break-even ownership crossover between two vehicles.
        """
        years_a = resp_a.yearly_projection
        years_b = resp_b.yearly_projection
        min_years = min(len(years_a), len(years_b))

        cross_year = None
        diff_at_year: List[Dict[str, Any]] = []

        for i in range(min_years):
            cost_a = years_a[i].net_cost_to_date
            cost_b = years_b[i].net_cost_to_date
            diff = cost_a - cost_b
            diff_at_year.append({
                "year": i + 1,
                "net_cost_a": cost_a,
                "net_cost_b": cost_b,
                "difference": round(diff, 2)
            })

            # Check for zero crossing
            if i > 0 and cross_year is None:
                prev_diff = diff_at_year[i - 1]["difference"]
                if (prev_diff < 0 and diff >= 0) or (prev_diff > 0 and diff <= 0):
                    # Linear interpolation for fractional year
                    fraction = abs(prev_diff) / (abs(prev_diff) + abs(diff)) if (abs(prev_diff) + abs(diff)) > 0 else 0.5
                    cross_year = round(i + fraction, 1)

        if cross_year:
            cheaper_first = resp_a.vehicle.get("model") if diff_at_year[0]["difference"] < 0 else resp_b.vehicle.get("model")
            cheaper_later = resp_b.vehicle.get("model") if diff_at_year[0]["difference"] < 0 else resp_a.vehicle.get("model")
            summary = f"Break-even crossover occurs at Year {cross_year}. {cheaper_first} is cheaper initially, but {cheaper_later} becomes more cost-effective after Year {cross_year}."
        else:
            cheaper_overall = resp_a.vehicle.get("model") if resp_a.ownership.net_tco < resp_b.ownership.net_tco else resp_b.vehicle.get("model")
            summary = f"No break-even crossover within the selected horizon. {cheaper_overall} remains consistently more economical throughout the ownership period."

        return {
            "status": "BREAK_EVEN_FOUND" if cross_year else "NO_BREAK_EVEN",
            "break_even_year": cross_year,
            "comparison_timeline": diff_at_year,
            "summary": summary
        }


tco_service = TCOService()
