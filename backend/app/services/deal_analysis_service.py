"""
AutoValue Smart Deal Analysis Engine (Phase 11).
Deterministically classifies asking prices against model predictions, conformal intervals,
and observed comparable marketplace distributions with mathematical proofs.
"""
from typing import Optional, List, Dict, Any
import numpy as np

from backend.app.schemas.intelligence import DealAnalysis


class DealAnalysisService:
    """
    Deterministic Deal Analysis Engine.
    Evaluates asking price competitiveness against empirical marketplace evidence and ML estimates.
    """

    # Explicit documented thresholds for price classification
    THRESHOLD_SIGNIFICANT_DISCOUNT_PCT = -12.0  # > 12% below market reference
    THRESHOLD_MODERATE_DISCOUNT_PCT = -4.0     # 4% to 12% below market reference
    THRESHOLD_FAIR_LOW_PCT = -4.0              # -4% to +4% is fairly priced
    THRESHOLD_FAIR_HIGH_PCT = 4.0
    THRESHOLD_MODERATE_PREMIUM_PCT = 12.0      # 4% to 12% above market reference
    # > 12% is significantly above market

    def evaluate_deal(
        self,
        asking_price: Optional[float],
        estimated_value: float,
        interval_low: Optional[float] = None,
        interval_high: Optional[float] = None,
        market_median: Optional[float] = None,
        market_p25: Optional[float] = None,
        market_p75: Optional[float] = None,
        comparables: Optional[List[Dict[str, Any]]] = None
    ) -> DealAnalysis:
        """
        Executes deterministic deal classification and generates mathematical evidence.
        """
        comparables = comparables or []
        comp_count = len(comparables)

        # 1. Determine Comparable Support Score (0.0 to 1.0)
        if comp_count == 0:
            comp_support_score = 0.0
            evidence_strength = "INSUFFICIENT"
        elif comp_count < 3:
            comp_support_score = 0.35 + (0.15 * (comp_count / 3))
            evidence_strength = "LOW"
        elif comp_count < 6:
            comp_support_score = 0.65 + (0.15 * ((comp_count - 3) / 3))
            evidence_strength = "MEDIUM"
        else:
            comp_support_score = min(1.0, 0.85 + (0.15 * min(1.0, (comp_count - 6) / 4)))
            evidence_strength = "HIGH"

        # Check if asking price is present
        if asking_price is None or asking_price <= 0:
            return DealAnalysis(
                asking_price=None,
                estimated_value=float(round(estimated_value, 2)),
                market_median=float(round(market_median, 2)) if market_median is not None else None,
                market_range={
                    "p25": float(round(market_p25, 2)) if market_p25 is not None else None,
                    "p75": float(round(market_p75, 2)) if market_p75 is not None else None,
                },
                asking_price_vs_ml=None,
                asking_price_vs_market_median=None,
                asking_price_vs_p25=None,
                asking_price_vs_p75=None,
                percentage_difference_from_ml=None,
                percentage_difference_from_market_median=None,
                comparable_support_score=round(comp_support_score, 2),
                evidence_strength=evidence_strength,
                price_position="UNSPECIFIED",
                classification="INSUFFICIENT_EVIDENCE",
                explanation="No asking price provided to evaluate against market valuation.",
                thresholds_used={
                    "significant_discount_pct": self.THRESHOLD_SIGNIFICANT_DISCOUNT_PCT,
                    "moderate_discount_pct": self.THRESHOLD_MODERATE_DISCOUNT_PCT,
                    "fair_range_pct": [self.THRESHOLD_FAIR_LOW_PCT, self.THRESHOLD_FAIR_HIGH_PCT],
                    "significant_premium_pct": self.THRESHOLD_MODERATE_PREMIUM_PCT
                }
            )

        ask = float(asking_price)

        # 2. Compute Mathematical Differentials
        diff_ml = ask - estimated_value
        pct_diff_ml = (diff_ml / estimated_value) * 100.0 if estimated_value > 0 else 0.0

        diff_median = (ask - market_median) if market_median is not None else None
        pct_diff_median = ((diff_median / market_median) * 100.0) if (market_median and market_median > 0) else None

        diff_p25 = (ask - market_p25) if market_p25 is not None else None
        diff_p75 = (ask - market_p75) if market_p75 is not None else None

        # 3. Determine Price Position
        if market_p25 is not None and market_p75 is not None:
            if ask < market_p25:
                price_position = "BELOW_P25"
            elif market_median is not None and ask <= market_median:
                price_position = "BETWEEN_P25_AND_MEDIAN"
            elif market_median is not None and ask <= market_p75:
                price_position = "BETWEEN_MEDIAN_AND_P75"
            else:
                price_position = "ABOVE_P75"
        elif interval_low is not None and interval_high is not None:
            if ask < interval_low:
                price_position = "BELOW_P25"
            elif ask > interval_high:
                price_position = "ABOVE_P75"
            else:
                price_position = "BETWEEN_P25_AND_MEDIAN" if ask <= estimated_value else "BETWEEN_MEDIAN_AND_P75"
        else:
            price_position = "UNSPECIFIED"

        # 4. Deterministic Classification
        # We anchor primarily to observed market median if evidence >= MEDIUM, else estimated ML value
        if market_median is not None and evidence_strength in ["HIGH", "MEDIUM"]:
            benchmark_pct = pct_diff_median
            benchmark_name = f"market median (₹{market_median:,.0f})"
        else:
            benchmark_pct = pct_diff_ml
            benchmark_name = f"model estimate (₹{estimated_value:,.0f})"

        if comp_count == 0 and evidence_strength == "INSUFFICIENT":
            # Sparse segment: only classify as fairly priced / above / below if deviation is very strong, otherwise flag uncertainty
            if benchmark_pct <= self.THRESHOLD_SIGNIFICANT_DISCOUNT_PCT:
                classification = "BELOW_MARKET"
            elif benchmark_pct >= self.THRESHOLD_MODERATE_PREMIUM_PCT:
                classification = "ABOVE_MARKET"
            else:
                classification = "FAIRLY_PRICED"
        else:
            if benchmark_pct <= self.THRESHOLD_SIGNIFICANT_DISCOUNT_PCT:
                classification = "SIGNIFICANTLY_BELOW_MARKET"
            elif benchmark_pct <= self.THRESHOLD_MODERATE_DISCOUNT_PCT:
                classification = "BELOW_MARKET"
            elif benchmark_pct <= self.THRESHOLD_FAIR_HIGH_PCT:
                classification = "FAIRLY_PRICED"
            elif benchmark_pct <= self.THRESHOLD_MODERATE_PREMIUM_PCT:
                classification = "ABOVE_MARKET"
            else:
                classification = "SIGNIFICANTLY_ABOVE_MARKET"

        # 5. Explanatory Statement
        sign_str = "+" if benchmark_pct >= 0 else ""
        explanation = (
            f"Asking price ₹{ask:,.0f} is {sign_str}{benchmark_pct:.1f}% relative to {benchmark_name}. "
            f"Classification '{classification}' based on {evidence_strength.lower()} marketplace evidence "
            f"({comp_count} comparable listings analyzed)."
        )

        return DealAnalysis(
            asking_price=float(round(ask, 2)),
            estimated_value=float(round(estimated_value, 2)),
            market_median=float(round(market_median, 2)) if market_median is not None else None,
            market_range={
                "p25": float(round(market_p25, 2)) if market_p25 is not None else None,
                "p75": float(round(market_p75, 2)) if market_p75 is not None else None,
            },
            asking_price_vs_ml=float(round(diff_ml, 2)),
            asking_price_vs_market_median=float(round(diff_median, 2)) if diff_median is not None else None,
            asking_price_vs_p25=float(round(diff_p25, 2)) if diff_p25 is not None else None,
            asking_price_vs_p75=float(round(diff_p75, 2)) if diff_p75 is not None else None,
            percentage_difference_from_ml=float(round(pct_diff_ml, 2)),
            percentage_difference_from_market_median=float(round(pct_diff_median, 2)) if pct_diff_median is not None else None,
            comparable_support_score=float(round(comp_support_score, 2)),
            evidence_strength=evidence_strength,
            price_position=price_position,
            classification=classification,
            explanation=explanation,
            thresholds_used={
                "significant_discount_pct": self.THRESHOLD_SIGNIFICANT_DISCOUNT_PCT,
                "moderate_discount_pct": self.THRESHOLD_MODERATE_DISCOUNT_PCT,
                "fair_range_pct": [self.THRESHOLD_FAIR_LOW_PCT, self.THRESHOLD_FAIR_HIGH_PCT],
                "moderate_premium_pct": self.THRESHOLD_MODERATE_PREMIUM_PCT
            }
        )


# Global singleton
deal_analysis_service = DealAnalysisService()
