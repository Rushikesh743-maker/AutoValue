"""
AutoValue Market Timing Intelligence Service (Phase 11).
Analyzes historical listing price trajectories and price velocity
without claiming guaranteed future asset price predictions.
"""
from typing import Dict, Any, Optional
import os
import pandas as pd
import numpy as np
import logging

from backend.app.schemas.intelligence import MarketTiming
from backend.app.services.historical_market_service import historical_market_service

logger = logging.getLogger("autovalue.market_timing_service")


class MarketTimingService:
    """
    Computes empirical market momentum and observed asking-price movement.
    """

    # Movement thresholds
    THRESHOLD_RISING_PCT = 2.0     # > +2% observed increase
    THRESHOLD_DECLINING_PCT = -2.0  # < -2% observed decrease
    # Between -2% and +2% is STABLE

    def analyze_market_timing(
        self,
        brand: str,
        model: str,
        city: Optional[str] = None,
        time_period: str = "6m"
    ) -> MarketTiming:
        """
        Evaluates historical price progression to determine trajectory and evidence strength.
        """
        history_res = historical_market_service.get_market_history(
            brand=brand,
            model=model,
            city=city,
            time_period=time_period,
            min_points_required=3
        )

        status = history_res.get("status")
        if status != "AVAILABLE" or not history_res.get("history"):
            return MarketTiming(
                brand=brand,
                model=model,
                city=city,
                recent_median=None,
                previous_median=None,
                percentage_movement=None,
                direction="INSUFFICIENT_DATA",
                observation_count=history_res.get("total_listings_analyzed", 0),
                evidence_strength="INSUFFICIENT",
                summary=f"Insufficient historical observations to calculate price trajectory for {brand} {model}.",
                disclaimer="Observed market movement is based on historical listing snapshots and does not guarantee future valuation trends."
            )

        history_items = history_res["history"]
        total_obs = history_res.get("total_listings_analyzed", len(history_items))

        if len(history_items) < 2:
            single_med = history_items[0]["median_price"]
            return MarketTiming(
                brand=brand,
                model=model,
                city=city,
                recent_median=single_med,
                previous_median=single_med,
                percentage_movement=0.0,
                direction="STABLE",
                observation_count=total_obs,
                evidence_strength="LOW",
                summary=f"Observed pricing concentrated in a single time period around ₹{single_med:,.0f}.",
                disclaimer="Observed market movement is based on historical listing snapshots and does not guarantee future valuation trends."
            )

        first_period = history_items[0]
        latest_period = history_items[-1]

        prev_median = first_period["median_price"]
        rec_median = latest_period["median_price"]

        if prev_median > 0:
            pct_move = ((rec_median - prev_median) / prev_median) * 100.0
        else:
            pct_move = 0.0

        # Determine direction
        if pct_move >= self.THRESHOLD_RISING_PCT:
            direction = "RISING"
        elif pct_move <= self.THRESHOLD_DECLINING_PCT:
            direction = "DECLINING"
        else:
            direction = "STABLE"

        # Evidence strength
        if total_obs >= 25 and len(history_items) >= 4:
            evidence_strength = "HIGH"
        elif total_obs >= 8:
            evidence_strength = "MEDIUM"
        else:
            evidence_strength = "LOW"

        # Factual summary
        sign_str = "+" if pct_move >= 0 else ""
        summary = (
            f"Observed marketplace median shifted from ₹{prev_median:,.0f} ({first_period['period']}) "
            f"to ₹{rec_median:,.0f} ({latest_period['period']}), reflecting a {sign_str}{pct_move:.1f}% "
            f"observed listing price movement across {total_obs} data points ({direction.lower()} momentum)."
        )

        return MarketTiming(
            brand=brand,
            model=model,
            city=city,
            recent_median=float(round(rec_median, 2)),
            previous_median=float(round(prev_median, 2)),
            percentage_movement=float(round(pct_move, 2)),
            direction=direction,
            observation_count=total_obs,
            evidence_strength=evidence_strength,
            summary=summary,
            disclaimer="Observed market movement reflects past asking-price trends from advertised listings, not guaranteed future asset performance or transaction values."
        )


# Global singleton
market_timing_service = MarketTimingService()
