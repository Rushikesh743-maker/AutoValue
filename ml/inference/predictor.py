"""
AutoValue ML Inference and Prediction Service.
Loads versioned model and preprocessor artifacts to deliver fair-market point estimates and feature attributions.
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
import numpy as np
import joblib

from backend.app.core.config import settings
from data_pipeline.feature_engineering.features import calculate_car_age, calculate_km_per_year
from ml.features.preprocessor import NUMERICAL_FEATURES, CATEGORICAL_FEATURES, get_feature_names_out

logger = logging.getLogger("autovalue.ml.predictor")


class AutoValuePredictor:
    """
    Inference service for used-car valuation using trained regression artifacts.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        preprocessor_path: Optional[str] = None,
        metadata_path: Optional[str] = None,
        model_version: Optional[str] = None
    ):
        self.model_version = model_version or settings.AUTOVALUE_MODEL_VERSION
        self.models_dir = settings.MODELS_DIR
        self.model_path = model_path or os.path.join(self.models_dir, f"model_{self.model_version}.joblib")
        self.preprocessor_path = preprocessor_path or os.path.join(self.models_dir, f"preprocessor_{self.model_version}.joblib")
        self.metadata_path = metadata_path or os.path.join(self.models_dir, f"metadata_{self.model_version}.json")

        self.model = None
        self.preprocessor = None
        self.metadata = {}
        self._load_artifacts()

    def _load_artifacts(self) -> bool:
        try:
            from backend.app.services.model_registry import model_registry
            model, prep, meta = model_registry.load_model_bundle(self.model_version)
            self.model = model
            self.preprocessor = prep
            self.metadata = meta
            return True
        except Exception as e:
            logger.error(f"Failed to load model artifacts for {self.model_version}: {e}")
            self.model = None
            self.preprocessor = None
            self.metadata = {}
            return False

    @property
    def is_loaded(self) -> bool:
        return self.model is not None and self.preprocessor is not None

    def predict(self, car_data: Dict[str, Any], reference_year: int = 2024) -> Dict[str, Any]:
        """
        Predicts fair asking price for a single vehicle dictionary.
        """
        if not self.is_loaded:
            raise RuntimeError(f"Model or preprocessor artifact for version '{self.model_version}' is not loaded.")

        # Prepare single row DataFrame
        row = dict(car_data)
        
        # Calculate engineered features if not already present
        year = int(row.get("year", reference_year))
        car_age = row.get("car_age")
        if car_age is None:
            car_age = calculate_car_age(year, reference_year=reference_year)
            row["car_age"] = car_age

        km = float(row.get("km_driven", 0))
        km_per_year = row.get("km_per_year")
        if km_per_year is None:
            km_per_year = calculate_km_per_year(km, car_age)
            row["km_per_year"] = km_per_year

        # Fill missing attributes with safe defaults
        for num_col in NUMERICAL_FEATURES:
            if num_col not in row or row[num_col] is None or pd.isnull(row[num_col]):
                row[num_col] = np.nan

        for cat_col in CATEGORICAL_FEATURES:
            if cat_col not in row or not row[cat_col]:
                row[cat_col] = "Unspecified"
            else:
                row[cat_col] = str(row[cat_col]).strip()

        df_input = pd.DataFrame([row])[NUMERICAL_FEATURES + CATEGORICAL_FEATURES]
        
        # Transform features
        X_trans = self.preprocessor.transform(df_input)
        pred_val = float(self.model.predict(X_trans)[0])
        pred_val = max(10000.0, round(pred_val, 2))

        return {
            "predicted_price": pred_val,
            "predicted_price_formatted": f"₹ {pred_val:,.0f}",
            "transformed_features": X_trans,
            "model_type": self.metadata.get("selected_model", type(self.model).__name__),
            "model_version": self.metadata.get("model_version", self.model_version),
            "input_features": {
                "brand": row.get("brand"),
                "model": row.get("model"),
                "year": year,
                "car_age": car_age,
                "km_driven": km,
                "km_per_year": km_per_year,
                "fuel_type": row.get("fuel_type"),
                "transmission": row.get("transmission"),
                "city": row.get("city")
            }
        }
