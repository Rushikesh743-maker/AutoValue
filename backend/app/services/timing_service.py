"""
AutoValue Buy/Sell Market Timing Intelligence Engine (Phase 14).
Computes evidence-grounded 0-100 buy and sell timing scores with transparent factor
breakdowns, deterministic scoring rules, and strict insufficient-evidence guards.
Not financial or investment advice.
"""
from typing import Dict, Any, Optional, List, Tuple
import math

from backend.app.schemas.forecast import (
    TimingScore,
    TimingSignal,
    TimingFactor,
    TrendDirection,
    ForecastConfidenceLevel,
    MarketVolatilityLevel
)


class TimingService:
    """
    Computes decision-support buy and sell timing indicators from empirical market metrics.
    """

    # Signal Thresholds
    STRONGLY_FAVORABLE_MIN = 80.0
    FAVORABLE_MIN = 65.0
    NEUTRAL_MIN = 45.0
    LESS_FAVORABLE_MIN = 25.0

    def compute_buy_timing(
        self,
        current_median: Optional[float],
        asking_price: Optional[float],
        m90d_pct: Optional[float],
        m180d_pct: Optional[float],
        overall_trend: TrendDirection,
        volatility_level: MarketVolatilityLevel,
        annual_depreciation_pct: float,
        confidence_level: ForecastConfidenceLevel,
        confidence_score: float,
        historical_percentile: Optional[float]
    ) -> TimingScore:
        """
        Computes buyer timing score (0-100) and factors.
        Higher score indicates more favorable buyer conditions (e.g. attractive pricing,
        stable or cooling momentum, strong data confidence).
        """
        if (
            confidence_level == ForecastConfidenceLevel.INSUFFICIENT_EVIDENCE
            or current_median is None
            or current_median <= 0
        ):
            return TimingScore(
                score=None,
                signal=TimingSignal.INSUFFICIENT_EVIDENCE,
                rating_label="Insufficient Evidence",
                factors=[],
                positive_factors=[],
                negative_factors=["Insufficient historical observations to establish a reliable buy timing indicator."],
                methodology_summary="Timing engine refused evaluation due to sparse or unreliable historical evidence.",
                disclaimer="Analytical market timing indicator, not financial advice."
            )

        base_score = 50.0
        factors: List[TimingFactor] = []
        positive_factors: List[str] = []
        negative_factors: List[str] = []

        # 1. Price Position vs Market Median / Asking Price (up to +/- 20 pts)
        effective_price = asking_price if (asking_price and asking_price > 0) else current_median
        price_diff_pct = ((effective_price - current_median) / current_median) * 100.0

        if price_diff_pct < -5.0:
            impact = min(20.0, abs(price_diff_pct) * 1.5)
            base_score += impact
            msg = f"Vehicle asking price is {abs(price_diff_pct):.1f}% below current market median."
            factors.append(TimingFactor(factor_type="POSITIVE", title="Attractive Price Position", description=msg, impact_weight=0.25))
            positive_factors.append(msg)
        elif price_diff_pct > 5.0:
            impact = min(20.0, price_diff_pct * 1.5)
            base_score -= impact
            msg = f"Vehicle asking price is {price_diff_pct:.1f}% above current market median."
            factors.append(TimingFactor(factor_type="NEGATIVE", title="Premium Price Position", description=msg, impact_weight=0.25))
            negative_factors.append(msg)
        else:
            msg = "Asking price is aligned within fair market range (±5% of median)."
            factors.append(TimingFactor(factor_type="NEUTRAL", title="Fair Market Price", description=msg, impact_weight=0.10))

        # 2. Historical Percentile Position (up to +/- 10 pts)
        if historical_percentile is not None:
            if historical_percentile <= 35.0:
                base_score += 10.0
                msg = f"Current price sits in the lower {historical_percentile:.0f}th percentile of observed historical values."
                factors.append(TimingFactor(factor_type="POSITIVE", title="Favorable Historical Percentile", description=msg, impact_weight=0.15))
                positive_factors.append(msg)
            elif historical_percentile >= 75.0:
                base_score -= 10.0
                msg = f"Current price sits in the upper {historical_percentile:.0f}th percentile of observed historical values."
                factors.append(TimingFactor(factor_type="NEGATIVE", title="High Historical Percentile", description=msg, impact_weight=0.15))
                negative_factors.append(msg)

        # 3. Market Momentum & Velocity (up to +/- 15 pts)
        if overall_trend == TrendDirection.DECLINING:
            base_score += 12.0
            msg = "Market prices are currently softening, providing greater buyer negotiation leverage."
            factors.append(TimingFactor(factor_type="POSITIVE", title="Softening Market Momentum", description=msg, impact_weight=0.20))
            positive_factors.append(msg)
        elif overall_trend == TrendDirection.RISING:
            base_score -= 10.0
            msg = "Market prices are currently rising (+momentum), reducing immediate buyer discount room."
            factors.append(TimingFactor(factor_type="NEGATIVE", title="Rising Market Trend", description=msg, impact_weight=0.20))
            negative_factors.append(msg)
        else:
            base_score += 5.0
            msg = "Market prices are stable, allowing predictable valuation benchmarks."
            factors.append(TimingFactor(factor_type="POSITIVE", title="Stable Price Environment", description=msg, impact_weight=0.10))
            positive_factors.append(msg)

        # 4. Market Volatility (up to +/- 10 pts)
        if volatility_level == MarketVolatilityLevel.LOW:
            base_score += 8.0
            msg = "Low market dispersion confirms tight, dependable pricing consensus."
            factors.append(TimingFactor(factor_type="POSITIVE", title="Low Price Dispersion", description=msg, impact_weight=0.10))
            positive_factors.append(msg)
        elif volatility_level == MarketVolatilityLevel.HIGH:
            base_score -= 8.0
            msg = "High price dispersion indicates wide variance across seller asking prices."
            factors.append(TimingFactor(factor_type="NEGATIVE", title="High Price Volatility", description=msg, impact_weight=0.10))
            negative_factors.append(msg)

        # 5. Evidence Confidence Scaling (+/- 10 pts)
        conf_bonus = ((confidence_score - 50.0) / 50.0) * 8.0
        base_score += conf_bonus
        if confidence_score >= 70.0:
            msg = f"High historical evidence density ({confidence_score:.0f}/100) supports high timing reliability."
            factors.append(TimingFactor(factor_type="POSITIVE", title="Robust Historical Evidence", description=msg, impact_weight=0.15))
            positive_factors.append(msg)
        elif confidence_score < 45.0:
            msg = f"Limited historical observation density ({confidence_score:.0f}/100) widens estimation uncertainty."
            factors.append(TimingFactor(factor_type="NEGATIVE", title="Limited Data Coverage", description=msg, impact_weight=0.15))
            negative_factors.append(msg)

        final_score = round(max(0.0, min(100.0, base_score)), 1)

        if final_score >= self.STRONGLY_FAVORABLE_MIN:
            signal = TimingSignal.FAVORABLE
            label = "Strongly Favorable to Buy"
        elif final_score >= self.FAVORABLE_MIN:
            signal = TimingSignal.FAVORABLE
            label = "Favorable to Buy"
        elif final_score >= self.NEUTRAL_MIN:
            signal = TimingSignal.NEUTRAL
            label = "Neutral Timing"
        elif final_score >= self.LESS_FAVORABLE_MIN:
            signal = TimingSignal.UNFAVORABLE
            label = "Less Favorable to Buy"
        else:
            signal = TimingSignal.UNFAVORABLE
            label = "Unfavorable to Buy"

        summary = (
            f"Buy timing score of {final_score:.0f}/100 ({label.lower()}). "
            f"Derived from {len(positive_factors)} favorable and {len(negative_factors)} cautionary market factors."
        )

        return TimingScore(
            score=final_score,
            signal=signal,
            rating_label=label,
            factors=factors,
            positive_factors=positive_factors,
            negative_factors=negative_factors,
            methodology_summary=summary,
            disclaimer="Buy timing score evaluates empirical marketplace asking price velocity and discount positioning. It does not constitute investment advice."
        )

    def compute_sell_timing(
        self,
        current_median: Optional[float],
        asking_price: Optional[float],
        m90d_pct: Optional[float],
        m180d_pct: Optional[float],
        overall_trend: TrendDirection,
        volatility_level: MarketVolatilityLevel,
        annual_depreciation_pct: float,
        confidence_level: ForecastConfidenceLevel,
        confidence_score: float,
        historical_percentile: Optional[float]
    ) -> TimingScore:
        """
        Computes seller timing score (0-100) and factors.
        Higher score indicates more favorable selling conditions (e.g. rising prices,
        peak market cycle, imminent depreciation pressure).
        """
        if (
            confidence_level == ForecastConfidenceLevel.INSUFFICIENT_EVIDENCE
            or current_median is None
            or current_median <= 0
        ):
            return TimingScore(
                score=None,
                signal=TimingSignal.INSUFFICIENT_EVIDENCE,
                rating_label="Insufficient Evidence",
                factors=[],
                positive_factors=[],
                negative_factors=["Insufficient historical observations to establish a reliable sell timing indicator."],
                methodology_summary="Timing engine refused evaluation due to sparse or unreliable historical evidence.",
                disclaimer="Analytical market timing indicator, not financial advice."
            )

        base_score = 50.0
        factors: List[TimingFactor] = []
        positive_factors: List[str] = []
        negative_factors: List[str] = []

        # 1. Market Direction & Momentum (up to +/- 20 pts)
        if overall_trend == TrendDirection.RISING:
            base_score += 15.0
            msg = "Market prices are trending upward (+momentum), giving sellers strong asking-price retention."
            factors.append(TimingFactor(factor_type="POSITIVE", title="Strong Seller Pricing Power", description=msg, impact_weight=0.25))
            positive_factors.append(msg)
        elif overall_trend == TrendDirection.DECLINING:
            base_score -= 10.0
            msg = "Market prices are softening, reducing seller pricing power."
            factors.append(TimingFactor(factor_type="NEGATIVE", title="Cooling Marketplace Momentum", description=msg, impact_weight=0.20))
            negative_factors.append(msg)
        else:
            base_score += 4.0
            msg = "Stable market conditions support orderly transaction values."
            factors.append(TimingFactor(factor_type="POSITIVE", title="Stable Market Valuation", description=msg, impact_weight=0.10))
            positive_factors.append(msg)

        # 2. Historical Percentile Position (up to +/- 15 pts)
        if historical_percentile is not None:
            if historical_percentile >= 70.0:
                base_score += 12.0
                msg = f"Current valuation is in the top {100 - historical_percentile:.0f}% of observed historical pricing."
                factors.append(TimingFactor(factor_type="POSITIVE", title="Near Historical Highs", description=msg, impact_weight=0.20))
                positive_factors.append(msg)
            elif historical_percentile <= 30.0:
                base_score -= 10.0
                msg = f"Current valuation is near historical lows ({historical_percentile:.0f}th percentile)."
                factors.append(TimingFactor(factor_type="NEGATIVE", title="Below Average Valuation Cycle", description=msg, impact_weight=0.20))
                negative_factors.append(msg)

        # 3. Depreciation Pressure (up to +/- 10 pts)
        if annual_depreciation_pct >= 9.0:
            base_score += 8.0
            msg = f"Annual depreciation rate is significant ({annual_depreciation_pct:.1f}%/yr); selling sooner protects asset equity."
            factors.append(TimingFactor(factor_type="POSITIVE", title="Imminent Depreciation Realization", description=msg, impact_weight=0.15))
            positive_factors.append(msg)
        elif annual_depreciation_pct <= 5.0:
            base_score -= 4.0
            msg = f"Low annual depreciation rate ({annual_depreciation_pct:.1f}%/yr) allows flexible holding time."
            factors.append(TimingFactor(factor_type="NEGATIVE", title="Slow Value Decay", description=msg, impact_weight=0.10))
            negative_factors.append(msg)

        # 4. Market Volatility (up to +/- 8 pts)
        if volatility_level == MarketVolatilityLevel.LOW:
            base_score += 6.0
            msg = "Consistent market pricing enables rapid liquidation with minimal discounting."
            factors.append(TimingFactor(factor_type="POSITIVE", title="High Transaction Consistency", description=msg, impact_weight=0.10))
            positive_factors.append(msg)
        elif volatility_level == MarketVolatilityLevel.HIGH:
            base_score -= 6.0
            msg = "High price dispersion means buyers have diverse alternative options."
            factors.append(TimingFactor(factor_type="NEGATIVE", title="Market Dispersion", description=msg, impact_weight=0.10))
            negative_factors.append(msg)

        # 5. Evidence Confidence Scaling (+/- 8 pts)
        conf_bonus = ((confidence_score - 50.0) / 50.0) * 6.0
        base_score += conf_bonus
        if confidence_score >= 70.0:
            msg = f"Robust evidence density ({confidence_score:.0f}/100) confirms reliable seller timing."
            factors.append(TimingFactor(factor_type="POSITIVE", title="Empirical Market Evidence", description=msg, impact_weight=0.10))
            positive_factors.append(msg)

        final_score = round(max(0.0, min(100.0, base_score)), 1)

        if final_score >= self.STRONGLY_FAVORABLE_MIN:
            signal = TimingSignal.FAVORABLE
            label = "Strongly Favorable to Sell"
        elif final_score >= self.FAVORABLE_MIN:
            signal = TimingSignal.FAVORABLE
            label = "Favorable to Sell"
        elif final_score >= self.NEUTRAL_MIN:
            signal = TimingSignal.NEUTRAL
            label = "Neutral Timing"
        elif final_score >= self.LESS_FAVORABLE_MIN:
            signal = TimingSignal.UNFAVORABLE
            label = "Less Favorable to Sell"
        else:
            signal = TimingSignal.UNFAVORABLE
            label = "Unfavorable to Sell"

        summary = (
            f"Sell timing score of {final_score:.0f}/100 ({label.lower()}). "
            f"Derived from {len(positive_factors)} favorable and {len(negative_factors)} cautionary market factors."
        )

        return TimingScore(
            score=final_score,
            signal=signal,
            rating_label=label,
            factors=factors,
            positive_factors=positive_factors,
            negative_factors=negative_factors,
            methodology_summary=summary,
            disclaimer="Sell timing score evaluates empirical marketplace asking price velocity and value retention. It does not constitute investment advice."
        )


timing_service = TimingService()
