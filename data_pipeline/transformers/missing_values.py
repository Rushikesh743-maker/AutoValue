"""
Missing values analysis and strategy implementation for tabular used car data.
"""
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass



@dataclass
class MissingValueSummary:
    total_records: int
    missing_counts: Dict[str, int]
    missing_percentages: Dict[str, float]
    strategies_applied: Dict[str, str]


class MissingValueAnalyzer:
    """
    Analyzes missingness per feature and applies principled, documented imputation strategies.
    
    Strategies:
      - 'retain_category': For categorical features like variant/seller_type/state, missing is treated as 'Unknown' / 'Unspecified'.
      - 'median': For numerical continuous features (e.g. engine_cc, mileage, km_driven).
      - 'mode': For high-frequency categoricals if appropriate.
      - 'pass_through': Keep NaN without alteration.
    """

    DEFAULT_STRATEGIES: Dict[str, str] = {
        "brand": "error_if_missing",
        "model": "error_if_missing",
        "year": "error_if_missing",
        "listed_price": "error_if_missing",
        "variant": "retain_category",
        "fuel_type": "retain_category",
        "transmission": "retain_category",
        "city": "retain_category",
        "state": "retain_category",
        "seller_type": "retain_category",
        "km_driven": "median",
        "owner_count": "median",
        "engine_cc": "median",
        "mileage": "median",
    }

    def __init__(self, strategies: Optional[Dict[str, str]] = None):
        self.strategies = strategies or self.DEFAULT_STRATEGIES

    def analyze(self, df: pd.DataFrame) -> MissingValueSummary:
        """Computes missing value counts and percentages across all columns."""
        total = len(df)
        counts = df.isnull().sum().to_dict()
        pcts = {col: round((cnt / total * 100.0) if total > 0 else 0.0, 2) for col, cnt in counts.items()}
        
        return MissingValueSummary(
            total_records=total,
            missing_counts=counts,
            missing_percentages=pcts,
            strategies_applied=self.strategies
        )

    def handle_missing_values(self, df: pd.DataFrame, is_training: bool = True, reference_medians: Optional[Dict[str, float]] = None) -> Tuple[pd.DataFrame, Dict[str, float]]:
        """
        Applies missing value strategies without data leakage.
        Returns transformed DataFrame and learned reference values.
        """
        from typing import Tuple
        out_df = df.copy()
        learned_medians: Dict[str, float] = reference_medians.copy() if reference_medians else {}

        for col, strategy in self.strategies.items():
            if col not in out_df.columns:
                continue

            if strategy == "retain_category":
                out_df[col] = out_df[col].fillna("Unspecified").astype(str)
            elif strategy == "median":
                if is_training:
                    # Compute median from training data only
                    median_val = out_df[col].median()
                    learned_medians[col] = median_val if pd.notnull(median_val) else 0.0
                fill_val = learned_medians.get(col, 0.0)
                out_df[col] = out_df[col].fillna(fill_val)
            elif strategy == "error_if_missing":
                # Drop rows missing core identification fields
                out_df = out_df.dropna(subset=[col])

        return out_df, learned_medians
