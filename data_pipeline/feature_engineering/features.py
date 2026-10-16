"""
Deterministic feature engineering module for tabular used car data.
Computes vehicle age, annual kilometer usage intensity, categorical groupings, and enforces strict target leakage prevention.
"""
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime, timezone
import pandas as pd
import numpy as np


def calculate_car_age(year: int | float | pd.Series, reference_year: int = 2024) -> int | float | pd.Series:
    """
    Computes vehicle age relative to a reference year.
    Formula: car_age = reference_year - year (clipped to non-negative)
    """
    if isinstance(year, pd.Series):
        return (reference_year - year).clip(lower=0)
    
    if pd.isnull(year):
        return 0
    age = int(reference_year) - int(year)
    return max(0, age)


def calculate_km_per_year(km_driven: int | float | pd.Series, car_age: int | float | pd.Series) -> float | pd.Series:
    """
    Computes annualized kilometer driving intensity.
    Formula: km_driven / max(car_age, 1)
    Avoids division by zero for brand-new/same-year vehicles.
    """
    if isinstance(km_driven, pd.Series) and isinstance(car_age, pd.Series):
        effective_age = car_age.clip(lower=1.0)
        return (km_driven / effective_age).round(2)

    if pd.isnull(km_driven):
        return 0.0
    effective_age = max(1.0, float(car_age) if pd.notnull(car_age) else 1.0)
    return round(float(km_driven) / effective_age, 2)


def check_target_leakage(feature_columns: List[str], target_col: str = "listed_price") -> List[str]:
    """
    Scans feature column names to verify that no target-derived features or the target itself
    leak into the independent feature matrix X.
    """
    leakage_suspects: List[str] = []
    forbidden_prefixes_suffixes = [
        target_col,
        "price",
        "log_price",
        "price_per_km",
        "asking_price",
        "selling_price",
        "target"
    ]

    for col in feature_columns:
        col_lower = col.lower().strip()
        if col_lower == target_col.lower():
            leakage_suspects.append(col)
        elif any(forbidden in col_lower for forbidden in ["price_per", "price_ratio", "predicted_price", "target_"]):
            leakage_suspects.append(col)

    return leakage_suspects


class CarFeatureEngineer:
    """
    Generates tabular machine-learning features from clean canonical listings.
    """

    CATEGORICAL_COLUMNS = [
        "brand",
        "model",
        "variant",
        "fuel_type",
        "transmission",
        "seller_type",
        "city",
        "state"
    ]

    NUMERICAL_COLUMNS = [
        "year",
        "km_driven",
        "car_age",
        "km_per_year",
        "owner_count",
        "engine_cc",
        "mileage"
    ]

    def __init__(self, reference_year: int = 2024):
        self.reference_year = reference_year

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Computes engineered features on input DataFrame.
        """
        out_df = df.copy()

        # 1. Compute vehicle age
        if "year" in out_df.columns:
            out_df["car_age"] = calculate_car_age(out_df["year"], reference_year=self.reference_year)
        else:
            out_df["car_age"] = 0

        # 2. Compute annual kilometer intensity
        if "km_driven" in out_df.columns and "car_age" in out_df.columns:
            out_df["km_per_year"] = calculate_km_per_year(out_df["km_driven"], out_df["car_age"])
        else:
            out_df["km_per_year"] = 0.0

        # 3. Categorical standardizations
        for col in self.CATEGORICAL_COLUMNS:
            if col in out_df.columns:
                out_df[col] = out_df[col].fillna("Unspecified").astype(str).str.strip()

        # 4. Fill defaults for missing numeric columns if absent
        for col in ["owner_count", "engine_cc", "mileage"]:
            if col not in out_df.columns:
                out_df[col] = np.nan

        return out_df

    def get_feature_and_target_matrices(self, df: pd.DataFrame, target_col: str = "listed_price") -> Tuple[pd.DataFrame, pd.Series]:
        """
        Extracts independent feature matrix X and target vector y with leakage protection.
        """
        engineered_df = self.transform(df)

        if target_col not in engineered_df.columns:
            raise ValueError(f"Target column '{target_col}' not found in dataframe.")

        y = engineered_df[target_col].copy()

        # Feature matrix excludes target, IDs, raw payloads, and internal audit columns
        excluded_cols = [
            target_col,
            "id",
            "listing_id",
            "listing_url",
            "raw_payload",
            "is_outlier",
            "outlier_reasons",
            "is_duplicate_candidate",
            "duplicate_similarity",
            "duplicate_of_id",
            "duplicate_notes",
            "date_collected",
            "created_at",
            "updated_at"
        ]

        feature_cols = [c for c in engineered_df.columns if c not in excluded_cols]
        
        # Check for potential target leakage
        leakage = check_target_leakage(feature_cols, target_col=target_col)
        if leakage:
            raise ValueError(f"Target leakage detected in feature columns: {leakage}")

        X = engineered_df[feature_cols].copy()
        return X, y
