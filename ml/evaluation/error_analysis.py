"""
AutoValue ML Model Error & Residual Analysis.
Computes empirical residual distributions and breaks down error metrics across
vehicle brands, models, price bands, age bands, mileage tiers, and locations.
"""
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np


class ErrorAnalyzer:
    """
    Analyzes model prediction errors and segment performance.
    """

    def __init__(self, min_segment_size: int = 5):
        self.min_segment_size = min_segment_size

    def calculate_residuals(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        features_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Builds a comprehensive residual analysis DataFrame.
        """
        res_df = features_df.copy().reset_index(drop=True)
        res_df["actual_price"] = np.array(y_true, dtype=float)
        res_df["predicted_price"] = np.array(y_pred, dtype=float)
        res_df["residual"] = res_df["actual_price"] - res_df["predicted_price"]
        res_df["absolute_error"] = np.abs(res_df["residual"])
        res_df["percentage_error"] = (res_df["absolute_error"] / np.maximum(1000.0, res_df["actual_price"])) * 100.0

        # Create price bands
        res_df["price_band"] = pd.cut(
            res_df["actual_price"],
            bins=[0, 500000, 1000000, 2000000, np.inf],
            labels=["< ₹5L", "₹5L–₹10L", "₹10L–₹20L", "> ₹20L"]
        )

        # Create age bands
        if "car_age" in res_df.columns:
            res_df["age_band"] = pd.cut(
                res_df["car_age"],
                bins=[-np.inf, 3, 6, 9, np.inf],
                labels=["< 3 yrs", "3–6 yrs", "6–9 yrs", "≥ 9 yrs"]
            )
        elif "year" in res_df.columns:
            age = 2026 - res_df["year"]
            res_df["age_band"] = pd.cut(
                age,
                bins=[-np.inf, 3, 6, 9, np.inf],
                labels=["< 3 yrs", "3–6 yrs", "6–9 yrs", "≥ 9 yrs"]
            )

        # Create km bands
        if "km_driven" in res_df.columns:
            res_df["km_band"] = pd.cut(
                res_df["km_driven"],
                bins=[-np.inf, 30000, 60000, 100000, np.inf],
                labels=["< 30k km", "30k–60k km", "60k–100k km", "≥ 100k km"]
            )

        return res_df

    def summarize_segment(
        self,
        res_df: pd.DataFrame,
        segment_col: str
    ) -> List[Dict[str, Any]]:
        """
        Calculates error summary metrics for a given category column.
        """
        if segment_col not in res_df.columns:
            return []

        summaries = []
        for segment, group in res_df.groupby(segment_col, observed=True):
            count = len(group)
            if count < self.min_segment_size:
                summaries.append({
                    "segment": str(segment),
                    "count": count,
                    "status": "Insufficient observations",
                    "mae": None,
                    "median_ae": None,
                    "mape": None,
                    "rmse": None
                })
            else:
                mae = float(group["absolute_error"].mean())
                med_ae = float(group["absolute_error"].median())
                mape = float(group["percentage_error"].mean())
                rmse = float(np.sqrt((group["residual"] ** 2).mean()))
                summaries.append({
                    "segment": str(segment),
                    "count": count,
                    "status": "Adequate",
                    "mae": round(mae, 2),
                    "median_ae": round(med_ae, 2),
                    "mape": round(mape, 2),
                    "rmse": round(rmse, 2)
                })

        return sorted(summaries, key=lambda x: x["count"], reverse=True)

    def run_full_error_analysis(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        features_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Runs comprehensive residual analysis across all core dimensions.
        """
        res_df = self.calculate_residuals(y_true, y_pred, features_df)

        overall_mae = float(res_df["absolute_error"].mean())
        overall_med_ae = float(res_df["absolute_error"].median())
        overall_mape = float(res_df["percentage_error"].mean())
        overall_rmse = float(np.sqrt((res_df["residual"] ** 2).mean()))

        return {
            "overall_metrics": {
                "count": len(res_df),
                "mae": round(overall_mae, 2),
                "median_ae": round(overall_med_ae, 2),
                "mape": round(overall_mape, 2),
                "rmse": round(overall_rmse, 2)
            },
            "by_price_band": self.summarize_segment(res_df, "price_band"),
            "by_brand": self.summarize_segment(res_df, "brand"),
            "by_fuel": self.summarize_segment(res_df, "fuel_type"),
            "by_transmission": self.summarize_segment(res_df, "transmission"),
            "by_age_band": self.summarize_segment(res_df, "age_band"),
            "by_km_band": self.summarize_segment(res_df, "km_band"),
            "by_city": self.summarize_segment(res_df, "city"),
            "residuals_dataframe": res_df
        }
