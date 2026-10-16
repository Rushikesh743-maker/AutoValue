"""
AutoValue Data Confidence & Vehicle Condition Disclaimer System (Phase 11).
Quantifies statistical model certainty, input feature completeness, and comparable listing density,
while explicitly surfacing critical physical unknowns that AutoValue does NOT inspect.
"""
from typing import Dict, Any, List, Optional
from backend.app.schemas.intelligence import DataConfidence


class DataConfidenceService:
    """
    Evaluates dataset richness and enforces strict condition disclaimers.
    """

    UNVERIFIED_PHYSICAL_FACTORS = [
        "engine and transmission mechanical condition",
        "accident and collision repair history",
        "flood damage and water immersion",
        "odometer tampering and fraud",
        "authorized service and maintenance records",
        "tyre tread depth and suspension wear",
        "braking system and pad condition",
        "paint depth, body rust, and chassis integrity",
        "electrical components and sensor faults"
    ]

    def evaluate_confidence(
        self,
        vehicle_data: Dict[str, Any],
        comparable_count: int,
        estimated_value: float,
        interval_low: Optional[float] = None,
        interval_high: Optional[float] = None
    ) -> DataConfidence:
        """
        Computes completeness, statistical confidence, and attaches mandatory disclaimers.
        """
        # 1. Data Completeness Score (0.0 to 1.0)
        # Expected core and optional attributes
        evaluated_fields = [
            "brand", "model", "year", "km_driven", "city",
            "fuel_type", "transmission", "variant", "engine_cc",
            "mileage", "owner_count", "seller_type"
        ]
        present_fields = 0
        for f in evaluated_fields:
            val = vehicle_data.get(f)
            if val is not None and str(val).strip() != "" and str(val).lower() != "unspecified":
                present_fields += 1

        completeness = round(present_fields / len(evaluated_fields), 2)

        # 2. Comparable Quality & Market Confidence
        if comparable_count >= 8:
            comparable_quality = "HIGH"
            market_confidence = "HIGH"
        elif comparable_count >= 4:
            comparable_quality = "HIGH" if completeness >= 0.8 else "MEDIUM"
            market_confidence = "MEDIUM"
        elif comparable_count >= 1:
            comparable_quality = "LOW"
            market_confidence = "LOW"
        else:
            comparable_quality = "INSUFFICIENT"
            market_confidence = "LOW"

        # 3. Model Confidence (derived from conformal uncertainty interval width)
        if interval_low is not None and interval_high is not None and estimated_value > 0:
            interval_width_pct = ((interval_high - interval_low) / estimated_value) * 100.0
            if interval_width_pct <= 20.0 and completeness >= 0.7:
                model_confidence = "HIGH"
            elif interval_width_pct <= 35.0:
                model_confidence = "MEDIUM"
            else:
                model_confidence = "LOW"
        else:
            model_confidence = "MEDIUM" if completeness >= 0.75 else "LOW"

        disclaimer_text = (
            "IMPORTANT LIMITATION NOTICE: AutoValue provides mathematical market valuations derived from "
            "publicly advertised used car listings, historical trends, and machine learning models. "
            "AutoValue has NOT physically inspected this vehicle and does not verify mechanical health, "
            "accident history, flood damage, or odometer authenticity. Always conduct a professional physical inspection "
            "and title check before purchasing or selling."
        )

        return DataConfidence(
            market_confidence=market_confidence,
            data_completeness=completeness,
            comparable_quality=comparable_quality,
            model_confidence=model_confidence,
            condition_unknown_warning=True,
            unverified_factors=self.UNVERIFIED_PHYSICAL_FACTORS,
            disclaimer_text=disclaimer_text
        )


# Global singleton
data_confidence_service = DataConfidenceService()
