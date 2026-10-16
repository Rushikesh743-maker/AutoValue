"""
AutoValue What-If Vehicle Simulator Service (Phase 11).
Executes fast, interactive counterfactual simulations using the active XGBoost model
without mutating saved valuations or relying on hardcoded depreciation rules.
"""
from typing import Dict, Any, List
import copy
import logging

from backend.app.schemas.intelligence import ScenarioRequest, ScenarioResponse
from backend.app.schemas.valuation import ValuationRequestSchema
from backend.app.services.valuation_service import valuation_service
from data_pipeline.feature_engineering.features import calculate_car_age, calculate_km_per_year

logger = logging.getLogger("autovalue.scenario_service")


class ScenarioService:
    """
    Counterfactual scenario engine using the active model inference pipeline.
    """

    def simulate_scenario(self, request: ScenarioRequest) -> ScenarioResponse:
        """
        Runs model inference on the base vehicle and modified scenario vehicle,
        computing exact model-driven differences and generating human-readable explanations.
        """
        base_veh = request.base_vehicle
        changes = request.changes or {}

        if not valuation_service.is_model_ready:
            from backend.app.core.exceptions import ModelNotFoundError
            raise ModelNotFoundError(
                valuation_service.model_version,
                "Active model is unavailable for scenario simulation."
            )

        # 1. Prepare Base Vehicle Payload
        ref_year = 2024
        norm_brand = valuation_service.normalizer.normalize_brand(base_veh.brand) or base_veh.brand.strip().title()
        norm_model = base_veh.model.strip().title()
        norm_city = base_veh.city.strip().title()
        base_age = calculate_car_age(base_veh.year, reference_year=ref_year)
        base_km_yr = calculate_km_per_year(base_veh.km_driven, base_age)

        base_dict = {
            "brand": norm_brand,
            "model": norm_model,
            "variant": base_veh.variant or "Unspecified",
            "year": base_veh.year,
            "fuel_type": base_veh.fuel_type.strip().capitalize(),
            "transmission": base_veh.transmission.strip().capitalize(),
            "km_driven": base_veh.km_driven,
            "engine_cc": base_veh.engine_cc,
            "mileage": base_veh.mileage,
            "owner_count": base_veh.owner_count or 1,
            "city": norm_city,
            "state": "Unspecified",
            "seller_type": base_veh.seller_type or "Individual",
            "car_age": base_age,
            "km_per_year": base_km_yr
        }

        # 2. Prepare Scenario Vehicle Payload by applying changes
        scenario_dict = copy.deepcopy(base_dict)
        changed_features: List[str] = []
        explanation_lines: List[str] = []

        for field, new_val in changes.items():
            if field in ["km_driven", "year", "city", "fuel_type", "transmission", "engine_cc", "owner_count", "variant", "mileage"]:
                old_val = base_dict.get(field)
                if old_val != new_val:
                    changed_features.append(field)
                    if field in ["fuel_type", "transmission"]:
                        scenario_dict[field] = str(new_val).strip().capitalize()
                    elif field in ["city", "brand", "model"]:
                        scenario_dict[field] = str(new_val).strip().title()
                    elif field in ["year", "km_driven", "engine_cc", "owner_count"]:
                        scenario_dict[field] = int(new_val)
                    elif field == "mileage":
                        scenario_dict[field] = float(new_val)
                    else:
                        scenario_dict[field] = new_val

        # Recalculate derived features if year or km changed
        scen_age = calculate_car_age(scenario_dict["year"], reference_year=ref_year)
        scen_km_yr = calculate_km_per_year(scenario_dict["km_driven"], scen_age)
        scenario_dict["car_age"] = scen_age
        scenario_dict["km_per_year"] = scen_km_yr

        # 3. Predict on Base and Scenario
        base_pred_res = valuation_service.predictor.predict(base_dict)
        base_estimate = float(round(base_pred_res["predicted_price"], 2))

        scen_pred_res = valuation_service.predictor.predict(scenario_dict)
        scenario_estimate = float(round(scen_pred_res["predicted_price"], 2))

        estimated_change = float(round(scenario_estimate - base_estimate, 2))
        pct_change = float(round((estimated_change / base_estimate * 100.0) if base_estimate > 0 else 0.0, 2))

        # 4. Generate Clear Explanations
        sign_change = "+" if estimated_change >= 0 else ""
        if not changed_features:
            explanation_lines.append("No feature modifications specified; simulation estimate matches baseline.")
        else:
            for feat in changed_features:
                old_v = base_dict.get(feat)
                new_v = scenario_dict.get(feat)
                if feat == "km_driven":
                    diff_km = new_v - old_v
                    direction_txt = "increasing" if diff_km > 0 else "reducing"
                    explanation_lines.append(
                        f"By {direction_txt} odometer mileage from {old_v:,} km to {new_v:,} km ({diff_km:+,} km), "
                        f"the model projects an estimated value change of ₹{estimated_change:+,.0f} ({pct_change:+.1f}%)."
                    )
                elif feat == "year":
                    diff_yr = new_v - old_v
                    explanation_lines.append(
                        f"Adjusting manufacturing year from {old_v} to {new_v} ({diff_yr:+d} yrs) shifts vehicle age to {scen_age} yr(s), "
                        f"resulting in a projected value adjustment of ₹{estimated_change:+,.0f} ({pct_change:+.1f}%)."
                    )
                elif feat in ["fuel_type", "transmission"]:
                    explanation_lines.append(
                        f"Switching powertrain configuration from {old_v} to {new_v} adjusts valuation by ₹{estimated_change:+,.0f} ({pct_change:+.1f}%)."
                    )
                elif feat == "city":
                    explanation_lines.append(
                        f"Changing market location from {old_v} to {new_v} applies regional demand differential of ₹{estimated_change:+,.0f} ({pct_change:+.1f}%)."
                    )
                elif feat == "owner_count":
                    explanation_lines.append(
                        f"Changing owner history from {old_v} owner(s) to {new_v} owner(s) shifts value by ₹{estimated_change:+,.0f} ({pct_change:+.1f}%)."
                    )
                else:
                    explanation_lines.append(
                        f"Modifying '{feat}' from {old_v} to {new_v} yields a net change of ₹{estimated_change:+,.0f} ({pct_change:+.1f}%)."
                    )

        return ScenarioResponse(
            base_estimate=base_estimate,
            scenario_estimate=scenario_estimate,
            estimated_change=estimated_change,
            percentage_change=pct_change,
            changed_features=changed_features,
            explanation=explanation_lines,
            simulation_note=f"Simulated using active AutoValue {valuation_service.model_version} model inference pipeline."
        )


# Global singleton
scenario_service = ScenarioService()
