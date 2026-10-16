"""
Tabular feature preprocessing pipeline for used car pricing models.
Builds scikit-learn ColumnTransformer strictly fit on training partitions to prevent data leakage.
"""
from typing import List, Tuple, Dict, Any, Optional
import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder


NUMERICAL_FEATURES: List[str] = [
    "year",
    "km_driven",
    "car_age",
    "km_per_year",
    "engine_cc",
    "mileage",
    "owner_count"
]

CATEGORICAL_FEATURES: List[str] = [
    "brand",
    "model",
    "variant",
    "fuel_type",
    "transmission",
    "city",
    "state",
    "seller_type"
]


def create_preprocessor_pipeline(
    numeric_features: Optional[List[str]] = None,
    categorical_features: Optional[List[str]] = None
) -> ColumnTransformer:
    """
    Constructs a scikit-learn ColumnTransformer with median imputation + standard scaling
    for numeric attributes, and missing category retention + one-hot encoding for categorical attributes.
    """
    num_cols = numeric_features if numeric_features is not None else NUMERICAL_FEATURES
    cat_cols = categorical_features if categorical_features is not None else CATEGORICAL_FEATURES

    numeric_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler())
    ])

    categorical_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="constant", fill_value="Unspecified")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, num_cols),
            ("cat", categorical_transformer, cat_cols)
        ],
        remainder="drop"
    )

    return preprocessor


def get_feature_names_out(preprocessor: ColumnTransformer) -> List[str]:
    """
    Retrieves output feature column names after fitting the ColumnTransformer.
    """
    feature_names: List[str] = []
    for name, trans, cols in preprocessor.transformers_:
        if name == "remainder" or trans == "drop":
            continue
        if hasattr(trans, "named_steps"):
            if "onehot" in trans.named_steps:
                onehot = trans.named_steps["onehot"]
                if hasattr(onehot, "get_feature_names_out"):
                    encoded_names = list(onehot.get_feature_names_out(cols))
                    feature_names.extend(encoded_names)
                else:
                    feature_names.extend(cols)
            else:
                feature_names.extend(cols)
        else:
            feature_names.extend(cols)
    return feature_names
