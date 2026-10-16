"""
AutoValue Evidence-Based Negotiation Intelligence Service (Phase 11).
Generates empirically grounded target price ranges and tactical talking points
for buyers and sellers without fabricating guarantee claims.
"""
from typing import Optional, List, Dict, Any

from backend.app.schemas.intelligence import NegotiationAnalysis


class NegotiationService:
    """
    Computes statistical negotiation corridors and evidence-supported targets.
    """

    def analyze_negotiation(
        self,
        asking_price: Optional[float],
        estimated_value: float,
        model_interval_low: Optional[float] = None,
        model_interval_high: Optional[float] = None,
        market_median: Optional[float] = None,
        market_p25: Optional[float] = None,
        market_p75: Optional[float] = None,
        comparable_count: int = 0
    ) -> NegotiationAnalysis:
        """
        Derives conservative, evidence-supported, and aggressive negotiation targets.
        """
        # Baseline reference: blend market median and model estimate if median exists
        if market_median is not None and comparable_count >= 2:
            central_target = (0.60 * market_median) + (0.40 * estimated_value)
        else:
            central_target = estimated_value

        # Lower bound / Aggressive target (grounded in P25 or model interval lower bound)
        if market_p25 is not None:
            aggressive_target = (0.70 * market_p25) + (0.30 * (model_interval_low or (0.90 * estimated_value)))
        elif model_interval_low is not None:
            aggressive_target = model_interval_low
        else:
            aggressive_target = estimated_value * 0.92

        # Upper bound / Conservative target (grounded in P75 or central target)
        if market_p75 is not None:
            conservative_target = (0.60 * market_p75) + (0.40 * central_target)
        elif model_interval_high is not None:
            conservative_target = min(model_interval_high, central_target * 1.05)
        else:
            conservative_target = central_target * 1.05

        # Enforce strict monotonicity: aggressive <= central <= conservative
        aggressive_target = min(aggressive_target, central_target * 0.97)
        conservative_target = max(conservative_target, central_target * 1.02)

        # Gap calculation
        ask = asking_price if (asking_price is not None and asking_price > 0) else None
        gap = (ask - central_target) if ask is not None else None

        # Determine Buyer Leverage
        talking_points: List[str] = []
        if ask is None:
            buyer_leverage = "BALANCED"
            talking_points.append(
                f"Statistical fair market benchmark is estimated at ₹{central_target:,.0f}."
            )
            if market_p25 and market_p75:
                talking_points.append(
                    f"Central 50% of observed comparable listings fall between ₹{market_p25:,.0f} and ₹{market_p75:,.0f}."
                )
        else:
            pct_above_median = ((ask - central_target) / central_target) * 100.0 if central_target > 0 else 0.0

            if pct_above_median > 8.0:
                buyer_leverage = "STRONG_BUYER_LEVERAGE"
                talking_points.append(
                    f"Current asking price (₹{ask:,.0f}) is ₹{abs(gap):,.0f} ({pct_above_median:+.1f}%) above central evidence benchmark."
                )
                talking_points.append(
                    f"Propose an opening counter-offer around ₹{aggressive_target:,.0f} to anchor conversation toward the lower market quartile."
                )
                if market_median:
                    talking_points.append(
                        f"Reference the observed marketplace median of ₹{market_median:,.0f} across {comparable_count} similar listings."
                    )
            elif pct_above_median > 2.0:
                buyer_leverage = "MODERATE_BUYER_LEVERAGE"
                talking_points.append(
                    f"Asking price is slightly above central valuation (₹{central_target:,.0f})."
                )
                talking_points.append(
                    f"Aim to negotiate a concession toward the evidence-supported target of ₹{central_target:,.0f}."
                )
            elif pct_above_median >= -5.0:
                buyer_leverage = "BALANCED"
                talking_points.append(
                    f"Vehicle asking price (₹{ask:,.0f}) is aligned with empirical fair market value."
                )
                talking_points.append(
                    "Focus negotiations on auxiliary costs such as insurance renewal, transfer fees, or mechanical inspection concessions."
                )
            else:
                buyer_leverage = "SELLER_ADVANTAGE"
                talking_points.append(
                    f"Asking price is ₹{abs(gap):,.0f} below standard market benchmarks."
                )
                talking_points.append(
                    "Verify vehicle history, documentation, and condition promptly to confirm legitimate pricing rationale."
                )

        formatted_range = f"₹{aggressive_target:,.0f} – ₹{conservative_target:,.0f}"

        return NegotiationAnalysis(
            observed_market_median=float(round(market_median, 2)) if market_median is not None else None,
            observed_market_p25=float(round(market_p25, 2)) if market_p25 is not None else None,
            observed_market_p75=float(round(market_p75, 2)) if market_p75 is not None else None,
            model_estimate=float(round(estimated_value, 2)),
            model_interval_low=float(round(model_interval_low, 2)) if model_interval_low is not None else None,
            model_interval_high=float(round(model_interval_high, 2)) if model_interval_high is not None else None,
            asking_price=float(round(ask, 2)) if ask is not None else None,
            negotiation_gap=float(round(gap, 2)) if gap is not None else None,
            evidence_supported_target=float(round(central_target, 2)),
            conservative_target=float(round(conservative_target, 2)),
            aggressive_target=float(round(aggressive_target, 2)),
            negotiation_range_formatted=formatted_range,
            buyer_leverage=buyer_leverage,
            talking_points=talking_points,
            disclaimer="Evidence-supported negotiation range derived from statistical models and observed marketplace listings. Not a guaranteed transaction price."
        )


# Global singleton
negotiation_service = NegotiationService()
