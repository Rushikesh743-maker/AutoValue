"""
Outlier detection and domain constraint auditing for used car data.
Flags anomalous or implausible records using statistical bounds (IQR) and domain rules without blind deletion.
"""
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass, field


@dataclass
class OutlierAuditResult:
    total_records: int
    outlier_count: int
    outlier_flags_by_type: Dict[str, int]
    flagged_indices: List[int] = field(default_factory=list)
    audit_notes: List[str] = field(default_factory=list)


class OutlierDetector:
    """
    Applies automotive domain bounds and statistical IQR fences to flag suspicious listing values.
    """

    def __init__(
        self,
        min_price: float = 25000.0,
        max_price: float = 25000000.0, # 2.5 Crore threshold
        min_year: int = 1995,
        max_year: int = 2026,
        max_km: int = 500000,
        max_km_per_year: float = 75000.0,
        iqr_multiplier: float = 2.5 # Generous multiplier to preserve rare high-end vehicles
    ):
        self.min_price = min_price
        self.max_price = max_price
        self.min_year = min_year
        self.max_year = max_year
        self.max_km = max_km
        self.max_km_per_year = max_km_per_year
        self.iqr_multiplier = iqr_multiplier

    def audit_dataframe(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, OutlierAuditResult]:
        """
        Audits DataFrame, adds boolean column 'is_outlier' and 'outlier_reasons',
        and returns audit statistics.
        """
        out_df = df.copy()
        out_df["is_outlier"] = False
        out_df["outlier_reasons"] = ""

        flags_by_type: Dict[str, int] = {
            "price_domain_bound": 0,
            "year_domain_bound": 0,
            "km_domain_bound": 0,
            "km_intensity_anomaly": 0,
            "statistical_price_iqr": 0,
        }
        flagged_indices: List[int] = []
        notes: List[str] = []

        # 1. Price domain bounds
        if "listed_price" in out_df.columns:
            price_mask = (out_df["listed_price"] < self.min_price) | (out_df["listed_price"] > self.max_price)
            for idx in out_df[price_mask].index:
                out_df.loc[idx, "is_outlier"] = True
                curr_reason = out_df.loc[idx, "outlier_reasons"]
                out_df.loc[idx, "outlier_reasons"] = f"{curr_reason}; Price outside [₹{self.min_price:,.0f}, ₹{self.max_price:,.0f}]".strip("; ")
                flags_by_type["price_domain_bound"] += 1
                flagged_indices.append(idx)

            # Statistical IQR fence (on non-null prices)
            valid_prices = out_df["listed_price"].dropna()
            if len(valid_prices) >= 4:
                q25 = valid_prices.quantile(0.25)
                q75 = valid_prices.quantile(0.75)
                iqr = q75 - q25
                upper_fence = q75 + (self.iqr_multiplier * iqr)
                lower_fence = max(0, q25 - (self.iqr_multiplier * iqr))
                iqr_mask = (out_df["listed_price"] > upper_fence) | (out_df["listed_price"] < lower_fence)
                for idx in out_df[iqr_mask].index:
                    if idx not in flagged_indices:
                        flags_by_type["statistical_price_iqr"] += 1

        # 2. Year domain bounds
        if "year" in out_df.columns:
            year_mask = (out_df["year"] < self.min_year) | (out_df["year"] > self.max_year)
            for idx in out_df[year_mask].index:
                out_df.loc[idx, "is_outlier"] = True
                curr_reason = out_df.loc[idx, "outlier_reasons"]
                out_df.loc[idx, "outlier_reasons"] = f"{curr_reason}; Year outside [{self.min_year}, {self.max_year}]".strip("; ")
                flags_by_type["year_domain_bound"] += 1
                if idx not in flagged_indices:
                    flagged_indices.append(idx)

        # 3. KM domain bounds
        if "km_driven" in out_df.columns:
            km_mask = (out_df["km_driven"] < 0) | (out_df["km_driven"] > self.max_km)
            for idx in out_df[km_mask].index:
                out_df.loc[idx, "is_outlier"] = True
                curr_reason = out_df.loc[idx, "outlier_reasons"]
                out_df.loc[idx, "outlier_reasons"] = f"{curr_reason}; KM outside [0, {self.max_km:,}]".strip("; ")
                flags_by_type["km_domain_bound"] += 1
                if idx not in flagged_indices:
                    flagged_indices.append(idx)

        # 4. KM per year intensity check
        if "km_driven" in out_df.columns and "year" in out_df.columns:
            ref_year = 2024
            approx_age = (ref_year - out_df["year"]).clip(lower=1)
            km_year_intensity = out_df["km_driven"] / approx_age
            intense_mask = km_year_intensity > self.max_km_per_year
            for idx in out_df[intense_mask].index:
                out_df.loc[idx, "is_outlier"] = True
                curr_reason = out_df.loc[idx, "outlier_reasons"]
                out_df.loc[idx, "outlier_reasons"] = f"{curr_reason}; Implausible KM intensity (> {self.max_km_per_year:,.0f} km/year)".strip("; ")
                flags_by_type["km_intensity_anomaly"] += 1
                if idx not in flagged_indices:
                    flagged_indices.append(idx)

        unique_flagged = list(set(flagged_indices))
        notes.append(f"Audit inspected {len(out_df)} records; flagged {len(unique_flagged)} potential outlier records.")

        result = OutlierAuditResult(
            total_records=len(out_df),
            outlier_count=len(unique_flagged),
            outlier_flags_by_type=flags_by_type,
            flagged_indices=unique_flagged,
            audit_notes=notes
        )

        return out_df, result
