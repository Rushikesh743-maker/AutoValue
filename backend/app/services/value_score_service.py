"""
AutoValue Transparent Value-for-Money Scoring Service (Phase 11).
Computes a clear, multi-attribute composite rating (0–100) combining price advantage,
usage intensity, vehicle age lifecycle, and marketplace statistical density.
"""
from typing import Optional, Dict, Any
import numpy as np

from backend.app.schemas.intelligence import ValueScore


class ValueScoreService:
    """
    Deterministic Value-for-Money Engine.
    All score formulas and weights are fully documented and explainable.
    """

    # Weights when asking price is provided
    WEIGHT_PRICE_WITH_ASK = 0.40
    WEIGHT_MILEAGE_WITH_ASK = 0.25
    WEIGHT_AGE_WITH_ASK = 0.15
    WEIGHT_SUPPORT_WITH_ASK = 0.20

    # Weights when asking price is omitted
    WEIGHT_MILEAGE_NO_ASK = 0.40
    WEIGHT_AGE_NO_ASK = 0.25
    WEIGHT_SUPPORT_NO_ASK = 0.35

    def calculate_value_score(
        self,
        year: int,
        km_driven: int,
        estimated_value: float,
        asking_price: Optional[float] = None,
        market_median: Optional[float] = None,
        comparable_count: int = 0,
        reference_year: int = 2024
    ) -> ValueScore:
        """
        Calculates normalized sub-scores and weighted composite value score.
        """
        car_age = max(1, reference_year - year)

        # 1. Price Value Score (0–100)
        price_score: Optional[float] = None
        price_formula_desc = "Price score not evaluated (no asking price supplied)."
        benchmark_price = market_median if (market_median and comparable_count >= 2) else estimated_value

        if asking_price is not None and asking_price > 0 and benchmark_price > 0:
            pct_diff = ((asking_price - benchmark_price) / benchmark_price) * 100.0
            # Formula: 70 base score, +2.0 pts per 1% discount, -2.0 pts per 1% premium
            # e.g., -10% discount -> 90; +10% premium -> 50
            raw_price = 70.0 - (pct_diff * 2.0)
            price_score = float(np.clip(raw_price, 0.0, 100.0))
            price_formula_desc = (
                f"Evaluated against benchmark ₹{benchmark_price:,.0f} ({pct_diff:+.1f}% deviation): "
                f"Formula = clip(70 - ({pct_diff:.1f} * 2.0)) = {price_score:.1f}/100"
            )

        # 2. Mileage Value Score (0–100)
        # Standard average passenger car usage in India is ~12,000 km per year
        expected_km = max(10000, car_age * 12000)
        mileage_ratio = km_driven / expected_km
        # Formula: 70 base score for exactly average mileage (ratio = 1.0)
        # Ratio <= 0.5 (low usage) -> 90+; Ratio >= 2.0 (high usage) -> 30
        raw_mileage = 70.0 - ((mileage_ratio - 1.0) * 40.0)
        mileage_score = float(np.clip(raw_mileage, 0.0, 100.0))
        mileage_formula_desc = (
            f"Expected benchmark {expected_km:,} km for {car_age} yr old vehicle. "
            f"Actual {km_driven:,} km (ratio {mileage_ratio:.2f}x): "
            f"Formula = clip(70 - (({mileage_ratio:.2f} - 1.0) * 40)) = {mileage_score:.1f}/100"
        )

        # 3. Age Lifecycle Value Score (0–100)
        # Newer vehicles provide modern safety, emission compliance, and longer remaining life
        if car_age <= 2:
            age_score = 92.0
        elif car_age <= 4:
            age_score = 82.0
        elif car_age <= 6:
            age_score = 70.0
        elif car_age <= 8:
            age_score = 56.0
        elif car_age <= 10:
            age_score = 42.0
        else:
            age_score = max(15.0, 42.0 - ((car_age - 10) * 5.0))
        age_score = float(np.clip(age_score, 0.0, 100.0))
        age_formula_desc = f"Vehicle age {car_age} years relative to modern passenger car lifecycle."

        # 4. Market Statistical Support Score (0–100)
        if comparable_count >= 8:
            support_score = 95.0
            evidence_confidence = "HIGH"
        elif comparable_count >= 5:
            support_score = 85.0
            evidence_confidence = "HIGH"
        elif comparable_count >= 3:
            support_score = 72.0
            evidence_confidence = "MEDIUM"
        elif comparable_count >= 1:
            support_score = 52.0
            evidence_confidence = "LOW"
        else:
            support_score = 25.0
            evidence_confidence = "INSUFFICIENT"
        support_formula_desc = f"Empirical density: {comparable_count} comparable listings observed in database."

        # 5. Overall Weighted Composite Score
        if price_score is not None:
            overall = (
                (self.WEIGHT_PRICE_WITH_ASK * price_score) +
                (self.WEIGHT_MILEAGE_WITH_ASK * mileage_score) +
                (self.WEIGHT_AGE_WITH_ASK * age_score) +
                (self.WEIGHT_SUPPORT_WITH_ASK * support_score)
            )
            weights_applied = {
                "price_weight": self.WEIGHT_PRICE_WITH_ASK,
                "mileage_weight": self.WEIGHT_MILEAGE_WITH_ASK,
                "age_weight": self.WEIGHT_AGE_WITH_ASK,
                "market_support_weight": self.WEIGHT_SUPPORT_WITH_ASK
            }
        else:
            overall = (
                (self.WEIGHT_MILEAGE_NO_ASK * mileage_score) +
                (self.WEIGHT_AGE_NO_ASK * age_score) +
                (self.WEIGHT_SUPPORT_NO_ASK * support_score)
            )
            weights_applied = {
                "price_weight": 0.0,
                "mileage_weight": self.WEIGHT_MILEAGE_NO_ASK,
                "age_weight": self.WEIGHT_AGE_NO_ASK,
                "market_support_weight": self.WEIGHT_SUPPORT_NO_ASK
            }

        overall = float(np.clip(overall, 0.0, 100.0))

        # Rating Label
        if overall >= 85:
            rating_label = "EXCELLENT_VALUE"
        elif overall >= 72:
            rating_label = "GOOD_VALUE"
        elif overall >= 55:
            rating_label = "FAIR_VALUE"
        elif overall >= 40:
            rating_label = "BELOW_AVERAGE_VALUE"
        else:
            rating_label = "POOR_VALUE"

        return ValueScore(
            price_value_score=round(price_score, 1) if price_score is not None else None,
            mileage_value_score=round(mileage_score, 1),
            age_value_score=round(age_score, 1),
            market_support_score=round(support_score, 1),
            evidence_confidence=evidence_confidence,
            overall_value_score=round(overall, 1),
            rating_label=rating_label,
            score_breakdown={
                "weights_applied": weights_applied,
                "price_formula": price_formula_desc,
                "mileage_formula": mileage_formula_desc,
                "age_formula": age_formula_desc,
                "market_support_formula": support_formula_desc,
                "overall_calculation": f"Sum of (component_score * component_weight) = {overall:.1f}/100"
            },
            disclaimer="The Value-for-Money Score evaluates statistical price competitiveness and usage intensity relative to marketplace benchmarks. It does NOT evaluate physical, mechanical, or accident condition."
        )


# Global singleton
value_score_service = ValueScoreService()
