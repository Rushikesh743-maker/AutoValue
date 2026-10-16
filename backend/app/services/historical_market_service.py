"""
AutoValue Historical Market Intelligence Service.
Aggregates historical asking prices and volume trends across time periods
(e.g., 3 months, 6 months, 12 months, all-time) for specific vehicles.
"""
from typing import Dict, Any, List, Optional
import os
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from backend.app.core.config import settings


class HistoricalMarketService:
    """
    Computes time-series pricing trajectories and market movement statistics
    from empirical listing date collections.
    """

    def __init__(self, processed_csv_path: Optional[str] = None):
        self.csv_path = processed_csv_path or os.path.join(settings.PROCESSED_DATA_DIR, "autovalue_processed.csv")
        self._df: Optional[pd.DataFrame] = None
        self._load_data()

    def _load_data(self):
        if os.path.exists(self.csv_path):
            try:
                df = pd.read_csv(self.csv_path)
                if "date_collected" in df.columns:
                    df["date_collected"] = pd.to_datetime(df["date_collected"], errors="coerce")
                self._df = df
            except Exception:
                self._df = pd.DataFrame()
        else:
            self._df = pd.DataFrame()

    def get_market_history(
        self,
        brand: Optional[str] = None,
        model: Optional[str] = None,
        city: Optional[str] = None,
        time_period: str = "all",  # "3m", "6m", "12m", "all"
        min_points_required: int = 3
    ) -> Dict[str, Any]:
        """
        Calculates monthly historical listing price aggregation and price changes.
        """
        if self._df is None or self._df.empty:
            return {
                "status": "UNAVAILABLE",
                "message": "Historical trend unavailable — dataset empty or offline.",
                "history": [],
                "observed_change": None
            }

        df = self._df.copy()

        # Apply vehicle filters (case-insensitive)
        if brand:
            df = df[df["brand"].str.lower() == brand.lower().strip()]
        if model:
            df = df[df["model"].str.lower() == model.lower().strip()]
        if city:
            df = df[df["city"].str.lower() == city.lower().strip()]

        if df.empty or "date_collected" not in df.columns:
            return {
                "status": "INSUFFICIENT_DATA",
                "message": "Historical trend unavailable — insufficient observations for specified vehicle.",
                "history": [],
                "observed_change": None
            }

        # Filter by time period
        df = df.dropna(subset=["date_collected", "listed_price"])
        if df.empty:
            return {
                "status": "INSUFFICIENT_DATA",
                "message": "Historical trend unavailable — missing collection timestamps.",
                "history": [],
                "observed_change": None
            }

        max_date = df["date_collected"].max()
        if time_period == "3m":
            cutoff = max_date - timedelta(days=90)
            df = df[df["date_collected"] >= cutoff]
        elif time_period == "6m":
            cutoff = max_date - timedelta(days=180)
            df = df[df["date_collected"] >= cutoff]
        elif time_period == "12m":
            cutoff = max_date - timedelta(days=365)
            df = df[df["date_collected"] >= cutoff]

        if len(df) < min_points_required:
            return {
                "status": "INSUFFICIENT_DATA",
                "message": f"Historical trend unavailable — found only {len(df)} observation(s), minimum {min_points_required} required.",
                "history": [],
                "observed_change": None
            }

        # Aggregate by Year-Month
        df["period"] = df["date_collected"].dt.to_period("M").astype(str)
        grouped = df.groupby("period")

        history_items = []
        for period_str, group in sorted(grouped, key=lambda x: x[0]):
            prices = group["listed_price"].values
            history_items.append({
                "period": period_str,
                "listing_count": int(len(prices)),
                "median_price": float(round(np.median(prices), 2)),
                "mean_price": float(round(np.mean(prices), 2)),
                "p25": float(round(np.percentile(prices, 25), 2)),
                "p75": float(round(np.percentile(prices, 75), 2)),
                "min_price": float(round(np.min(prices), 2)),
                "max_price": float(round(np.max(prices), 2))
            })

        # Calculate observed change between first and last period
        observed_change = None
        if len(history_items) >= 2:
            first_median = history_items[0]["median_price"]
            last_median = history_items[-1]["median_price"]
            abs_change = last_median - first_median
            pct_change = (abs_change / first_median) * 100.0 if first_median > 0 else 0.0

            observed_change = {
                "initial_period": history_items[0]["period"],
                "latest_period": history_items[-1]["period"],
                "initial_median_price": first_median,
                "latest_median_price": last_median,
                "absolute_change": round(abs_change, 2),
                "percentage_change": round(pct_change, 2),
                "description": f"Observed listing-price change of {abs_change:+,.0f} INR ({pct_change:+.1f}%) from {history_items[0]['period']} to {history_items[-1]['period']}."
            }

        return {
            "status": "AVAILABLE",
            "time_period": time_period,
            "total_listings_analyzed": len(df),
            "periods_count": len(history_items),
            "history": history_items,
            "observed_change": observed_change,
            "disclaimer": "Historical trends represent observed listing asking prices over time, not completed transaction prices or guaranteed future asset appreciation."
        }


# Global singleton
historical_market_service = HistoricalMarketService()
