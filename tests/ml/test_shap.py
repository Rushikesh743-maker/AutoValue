"""
Unit tests for SHAP explainer foundation module.
"""
import pytest
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from ml.features.preprocessor import create_preprocessor_pipeline, NUMERICAL_FEATURES, CATEGORICAL_FEATURES
from ml.evaluation.shap_explainer import AutoValueSHAPExplainer, SHAP_AVAILABLE


class TestSHAPExplainer:
    def test_shap_explainer_initialization_and_attribution(self):
        train_df = pd.DataFrame([
            {
                "year": 2021, "km_driven": 35000, "car_age": 3, "km_per_year": 11666.67,
                "engine_cc": 1493, "mileage": 21.4, "owner_count": 1,
                "brand": "Hyundai", "model": "Creta", "variant": "SX",
                "fuel_type": "Diesel", "transmission": "Manual",
                "city": "Bengaluru", "state": "Karnataka", "seller_type": "Individual"
            },
            {
                "year": 2019, "km_driven": 42000, "car_age": 5, "km_per_year": 8400.0,
                "engine_cc": 1197, "mileage": 21.21, "owner_count": 1,
                "brand": "Maruti Suzuki", "model": "Swift", "variant": "ZXi",
                "fuel_type": "Petrol", "transmission": "Manual",
                "city": "Mumbai", "state": "Maharashtra", "seller_type": "Dealer"
            },
            {
                "year": 2022, "km_driven": 20000, "car_age": 2, "km_per_year": 10000.0,
                "engine_cc": 1498, "mileage": 18.4, "owner_count": 1,
                "brand": "Honda", "model": "City", "variant": "ZX",
                "fuel_type": "Petrol", "transmission": "Automatic",
                "city": "Delhi NCR", "state": "Delhi", "seller_type": "Individual"
            }
        ])
        y_train = np.array([1350000.0, 625000.0, 1425000.0])

        preprocessor = create_preprocessor_pipeline()
        X_trans = preprocessor.fit_transform(train_df)

        model = RandomForestRegressor(n_estimators=10, random_state=42)
        model.fit(X_trans, y_train)

        explainer = AutoValueSHAPExplainer(model=model, preprocessor=preprocessor)

        sample_input = train_df.iloc[[0]]
        explanation = explainer.explain_prediction(sample_input)

        if SHAP_AVAILABLE and explainer.is_available:
            assert explanation["available"] is True
            assert "base_value_inr" in explanation
            assert "attributions" in explanation
        else:
            assert "available" in explanation
