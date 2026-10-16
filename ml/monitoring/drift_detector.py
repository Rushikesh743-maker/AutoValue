"""
AutoValue ML Model & Feature Drift Monitoring Module.
Calculates Population Stability Index (PSI), Kolmogorov-Smirnov (KS) statistics,
and feature distribution shifts between baseline training data and runtime/incoming batches.
"""
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from scipy import stats


def calculate_psi(
    expected: np.ndarray,
    actual: np.ndarray,
    num_buckets: int = 10,
    epsilon: float = 1e-4
) -> float:
    """
    Computes the Population Stability Index (PSI) between expected (baseline)
    and actual (production/inference) distributions.
    
    PSI Rule of Thumb:
      - PSI < 0.10: Insignificant change / Stable.
      - 0.10 <= PSI < 0.25: Moderate shift / Warning.
      - PSI >= 0.25: Significant drift / Action recommended.
    """
    if len(expected) == 0 or len(actual) == 0:
        return 0.0

    # Determine quantiles based on expected distribution
    percentiles = np.linspace(0, 100, num_buckets + 1)
    try:
        bin_edges = np.percentile(expected, percentiles)
        bin_edges[0] = -np.inf
        bin_edges[-1] = np.inf
        # Deduplicate edges if constant values exist
        bin_edges = np.unique(bin_edges)
        if len(bin_edges) < 2:
            return 0.0
    except Exception:
        return 0.0

    exp_counts, _ = np.histogram(expected, bins=bin_edges)
    act_counts, _ = np.histogram(actual, bins=bin_edges)

    exp_pct = exp_counts / float(len(expected))
    act_pct = act_counts / float(len(actual))

    # Add epsilon to prevent div-by-zero or log(0)
    exp_pct = np.clip(exp_pct, epsilon, 1.0)
    act_pct = np.clip(act_pct, epsilon, 1.0)

    # Renormalize
    exp_pct = exp_pct / exp_pct.sum()
    act_pct = act_pct / act_pct.sum()

    psi_value = np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct))
    return float(max(0.0, psi_value))


class DriftDetector:
    """
    Detects dataset and prediction drift between baseline and runtime datasets.
    """

    def __init__(self, baseline_df: pd.DataFrame):
        self.baseline_df = baseline_df.copy()

    def audit_numerical_drift(
        self,
        current_df: pd.DataFrame,
        numerical_cols: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Audits numerical features for distribution drift using PSI and KS-test.
        """
        cols = numerical_cols or ["km_driven", "year", "car_age", "km_per_year", "listed_price"]
        results = []

        for col in cols:
            if col in self.baseline_df.columns and col in current_df.columns:
                base_vals = self.baseline_df[col].dropna().values
                curr_vals = current_df[col].dropna().values

                if len(base_vals) >= 5 and len(curr_vals) >= 5:
                    psi = calculate_psi(base_vals, curr_vals)
                    ks_stat, p_val = stats.ks_2samp(base_vals, curr_vals)

                    if psi < 0.10:
                        status = "STABLE"
                    elif psi < 0.25:
                        status = "MODERATE_DRIFT"
                    else:
                        status = "SIGNIFICANT_DRIFT"

                    results.append({
                        "feature": col,
                        "psi": round(psi, 4),
                        "ks_stat": round(float(ks_stat), 4),
                        "p_value": round(float(p_val), 4),
                        "status": status,
                        "baseline_mean": round(float(np.mean(base_vals)), 2),
                        "current_mean": round(float(np.mean(curr_vals)), 2)
                    })

        return results

    def generate_drift_report(
        self,
        current_df: pd.DataFrame,
        model_version: str = "v002"
    ) -> Dict[str, Any]:
        """
        Generates full drift monitoring audit summary.
        """
        num_drift = self.audit_numerical_drift(current_df)
        drift_count = sum(1 for item in num_drift if item["status"] != "STABLE")

        return {
            "model_version": model_version,
            "baseline_count": len(self.baseline_df),
            "current_count": len(current_df),
            "overall_status": "DRIFT_DETECTED" if drift_count > 0 else "HEALTHY",
            "drifted_features_count": drift_count,
            "feature_audits": num_drift
        }
