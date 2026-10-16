"""
AutoValue Valuation Intelligence Service.
Coordinates input normalization, feature engineering, cached ML model inference,
prediction uncertainty estimation, comparable listing search, empirical market statistics,
SHAP explainability, and structured request observability.
"""
import os
import json
import time
import uuid
import logging
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

from backend.app.core.config import settings
from backend.app.schemas.valuation import (
    ValuationRequestSchema,
    ValuationResponse,
    ValuationDetails,
    ModelInterval,
    ModelEvidence,
    MarketStatistics,
    MarketPosition,
    SHAPExplanationItem,
    ComparableCarItem,
    SourceAnalysisItem
)
from data_pipeline.normalizers.normalizer import VehicleNormalizer
from data_pipeline.feature_engineering.features import calculate_car_age, calculate_km_per_year
from ml.inference.predictor import AutoValuePredictor
from ml.evaluation.shap_explainer import AutoValueSHAPExplainer
from ml.evaluation.uncertainty import PredictionUncertaintyEstimator
from .comparable_service import ComparableService, ComparableConfig

logger = logging.getLogger("autovalue.valuation_service")


class ValuationService:
    """
    End-to-end valuation service delivering model predictions, prediction uncertainty intervals,
    comparable evidence, market statistics, and feature attributions.
    """

    def __init__(
        self,
        model_version: Optional[str] = None,
        processed_data_path: Optional[str] = None
    ):
        self.model_version = model_version or getattr(settings, "AUTOVALUE_MODEL_VERSION", "v002")
        self.processed_data_path = processed_data_path or os.path.join(settings.PROCESSED_DATA_DIR, "autovalue_processed.csv")
        
        self.normalizer = VehicleNormalizer()
        self.comparable_service = ComparableService()
        
        # Load Predictor and SHAP Explainer
        self.predictor = AutoValuePredictor(model_version=self.model_version)
        self.shap_explainer = None
        if self.predictor.is_loaded:
            feature_names = None
            try:
                from ml.features.preprocessor import get_feature_names_out
                feature_names = get_feature_names_out(self.predictor.preprocessor)
            except Exception as e:
                logger.warning(f"Could not extract feature names from preprocessor: {e}")

            self.shap_explainer = AutoValueSHAPExplainer(
                model=self.predictor.model,
                preprocessor=self.predictor.preprocessor,
                feature_names=feature_names
            )

        # Load Metadata & Uncertainty Calibration
        self.metadata: Dict[str, Any] = {}
        self.uncertainty_estimator = PredictionUncertaintyEstimator()
        self._load_metadata()

        # Cache processed listings dataset
        self._listings_df: Optional[pd.DataFrame] = None
        self._load_listings()

    def _load_metadata(self):
        meta_path = os.path.join(settings.MODELS_DIR, f"metadata_{self.model_version}.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
                    calib = self.metadata.get("uncertainty_calibration", {})
                    if calib:
                        self.uncertainty_estimator.residual_quantile_80 = calib.get("residual_q80")
                        self.uncertainty_estimator.residual_quantile_90 = calib.get("residual_q90")
            except Exception as e:
                logger.error(f"Failed to load metadata from {meta_path}: {e}")

    def _load_listings(self):
        if os.path.exists(self.processed_data_path):
            try:
                self._listings_df = pd.read_csv(self.processed_data_path)
                logger.info(f"ValuationService loaded {len(self._listings_df)} processed listings.")
            except Exception as e:
                logger.error(f"Failed to load processed listings: {e}")
                self._listings_df = pd.DataFrame()
        else:
            self._listings_df = pd.DataFrame()

    @property
    def is_model_ready(self) -> bool:
        return self.predictor.is_loaded

    def generate_human_explanation(self, feature_name: str, impact_inr: float, direction: str) -> str:
        """
        Translates mathematical SHAP impact values into clear, factual explanations.
        """
        impact_abs = abs(impact_inr)
        f_lower = feature_name.lower()
        if "year" in f_lower or "age" in f_lower:
            if impact_inr < 0:
                return f"Vehicle age depreciation contributed approximately INR {impact_abs:,.0f} downward relative to baseline."
            else:
                return f"Newer manufacturing year contributed approximately INR {impact_abs:,.0f} upward."
        elif "km" in f_lower or "odometer" in f_lower:
            if impact_inr < 0:
                return f"Accumulated odometer mileage contributed approximately INR {impact_abs:,.0f} downward."
            else:
                return f"Lower usage intensity contributed approximately INR {impact_abs:,.0f} upward."
        elif "brand" in f_lower or "model" in f_lower:
            if impact_inr > 0:
                return f"Brand and model tier contributed approximately INR {impact_abs:,.0f} premium."
            else:
                return f"Segment baseline adjustment contributed INR {impact_abs:,.0f}."
        elif "engine" in f_lower or "displacement" in f_lower:
            return f"Engine capacity contributed approximately INR {impact_abs:,.0f} to the valuation."
        elif "fuel" in f_lower:
            action = "premium" if impact_inr > 0 else "adjustment"
            return f"Fuel type specification contributed approximately INR {impact_abs:,.0f} {action}."
        elif "trans" in f_lower:
            action = "premium" if impact_inr > 0 else "adjustment"
            return f"Transmission configuration contributed approximately INR {impact_abs:,.0f} {action}."
        elif "city" in f_lower or "state" in f_lower:
            action = "premium" if impact_inr > 0 else "adjustment"
            return f"Regional market location contributed approximately INR {impact_abs:,.0f} {action}."
        elif "owner" in f_lower:
            return f"Ownership history contributed approximately INR {impact_abs:,.0f} to the valuation."
        elif "mileage" in f_lower:
            return f"Fuel efficiency rating contributed approximately INR {impact_abs:,.0f} to the valuation."
        else:
            action = "increased" if direction == "increases_price" else "decreased"
            return f"Feature '{feature_name}' {action} the estimated value by approximately INR {impact_abs:,.0f}."

    def evaluate_valuation(
        self,
        request: ValuationRequestSchema,
        include_shap: bool = True
    ) -> ValuationResponse:
        """
        Executes full valuation workflow for the provided vehicle request with structured latency logging.
        """
        start_time = time.time()
        request_id = f"val-{uuid.uuid4().hex[:8]}"

        # 1. Normalization
        norm_brand = self.normalizer.normalize_brand(request.brand) or request.brand.strip().title()
        norm_model = request.model.strip().title()
        norm_city = request.city.strip().title()

        # 2. Feature Engineering
        ref_year = 2024
        car_age = calculate_car_age(request.year, reference_year=ref_year)
        km_per_year = calculate_km_per_year(request.km_driven, car_age)

        req_dict = {
            "brand": norm_brand,
            "model": norm_model,
            "variant": request.variant or "Unspecified",
            "year": request.year,
            "fuel_type": request.fuel_type.strip().capitalize(),
            "transmission": request.transmission.strip().capitalize(),
            "km_driven": request.km_driven,
            "engine_cc": request.engine_cc,
            "mileage": request.mileage,
            "owner_count": request.owner_count or 1,
            "city": norm_city,
            "state": "Unspecified",
            "seller_type": request.seller_type or "Individual",
            "car_age": car_age,
            "km_per_year": km_per_year
        }

        # 3. Model Inference
        if not self.is_model_ready:
            from backend.app.core.exceptions import ModelNotFoundError
            raise ModelNotFoundError(
                self.model_version,
                f"Configured active valuation model '{self.model_version}' is unavailable."
            )

        pred_result = self.predictor.predict(req_dict)
        predicted_value = float(pred_result["predicted_price"])

        # Model Uncertainty Interval Calculation
        transformed_arr = pred_result.get("transformed_features")
        interval_data = self.uncertainty_estimator.estimate_interval(
            point_prediction=predicted_value,
            model_estimator=self.predictor.model,
            transformed_features=transformed_arr,
            confidence_level=0.80
        )
        model_interval = ModelInterval(
            interval_low=interval_data["interval_low"],
            interval_high=interval_data["interval_high"],
            interval_low_formatted=f"INR {interval_data['interval_low']:,.0f}",
            interval_high_formatted=f"INR {interval_data['interval_high']:,.0f}",
            confidence_level=interval_data["confidence_level"],
            method=interval_data["method"]
        )

        # 4. Search Comparable Listings
        if self._listings_df is None or self._listings_df.empty:
            self._load_listings()

        comparables, market_stats, source_analysis, range_info = self.comparable_service.find_comparables(
            query=req_dict,
            listings_df=self._listings_df
        )

        range_low = range_info.get("range_low")
        range_high = range_info.get("range_high")
        range_method = range_info.get("range_method", "Comparable listing range")

        # 5. SHAP Explanations
        explanation_items: List[SHAPExplanationItem] = []
        if include_shap and self.shap_explainer and self.shap_explainer.is_available:
            input_df = pd.DataFrame([req_dict])
            shap_result = self.shap_explainer.explain_prediction(input_df)
            if shap_result.get("available"):
                for attr in shap_result.get("attributions", []):
                    f_name = attr["feature"]
                    f_impact = attr["impact_inr"]
                    f_dir = attr["direction"]
                    text = self.generate_human_explanation(f_name, f_impact, f_dir)
                    explanation_items.append(SHAPExplanationItem(
                        feature=f_name,
                        impact_inr=f_impact,
                        direction=f_dir,
                        human_readable_text=text
                    ))

        # 6. Market Position (if asking_price provided)
        market_position: Optional[MarketPosition] = None
        if request.asking_price is not None and request.asking_price > 0:
            ask = float(request.asking_price)
            pos_label = "Within observed comparable range"
            if range_low is not None and ask < range_low:
                pos_label = "Below observed comparable range"
            elif range_high is not None and ask > range_high:
                pos_label = "Above observed comparable range"

            ref_median = market_stats.median if market_stats.median is not None else predicted_value
            diff = round(ask - ref_median, 2)
            pct_diff = round((diff / ref_median * 100.0) if ref_median > 0 else 0.0, 2)

            market_position = MarketPosition(
                asking_price=ask,
                position=pos_label,
                difference_from_median=diff,
                percentage_difference_from_median=pct_diff
            )

        # 7. Model Evidence
        dataset_version = self.metadata.get("dataset_version", "v0.3")
        metrics_test = self.metadata.get("metrics_test", {})
        model_evidence = ModelEvidence(
            selected_model=self.metadata.get("selected_model", "XGBoost Regressor"),
            dataset_records=self.metadata.get("total_records", len(self._listings_df) if self._listings_df is not None else 999),
            test_mae=metrics_test.get("mae"),
            test_r2=metrics_test.get("r2"),
            evaluation_strategy=self.metadata.get("evaluation_strategy", "duplicate_safe_80_20")
        )

        latency_ms = round((time.time() - start_time) * 1000.0, 2)

        # Structured Observability Logging (without sensitive user PII)
        logger.info(
            f"[ValuationRequest] req_id={request_id} model={self.model_version} "
            f"dataset={dataset_version} brand={norm_brand} model_name={norm_model} "
            f"comparables={len(comparables)} latency_ms={latency_ms} status=SUCCESS"
        )

        # 8. Construct Full Response
        return ValuationResponse(
            model_version=self.model_version,
            dataset_version=dataset_version,
            valuation=ValuationDetails(
                estimated_value=predicted_value,
                estimated_value_formatted=f"INR {predicted_value:,.0f}",
                range_low=range_low,
                range_high=range_high,
                range_low_formatted=f"INR {range_low:,.0f}" if range_low is not None else None,
                range_high_formatted=f"INR {range_high:,.0f}" if range_high is not None else None,
                range_method=range_method,
                combination_method="Trained regression estimator point prediction paired with empirical comparable market range",
                model_interval=model_interval
            ),
            market=market_stats,
            model_evidence=model_evidence,
            comparables=comparables,
            source_analysis=source_analysis,
            explanation=explanation_items,
            market_position=market_position,
            transparency_notice="AutoValue estimates are computed from trained machine learning models and observed asking prices. Observed listing prices represent asking prices and may differ from completed transaction settlement prices.",
            request_id=request_id,
            latency_ms=latency_ms
        )


# Global singleton service instance
valuation_service = ValuationService()
