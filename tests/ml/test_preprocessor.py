"""
Unit tests for ML feature preprocessor and ColumnTransformer.
"""
import pytest
import pandas as pd
import numpy as np
from ml.features.preprocessor import (
    create_preprocessor_pipeline,
    get_feature_names_out,
    NUMERICAL_FEATURES,
    CATEGORICAL_FEATURES
)


class TestPreprocessor:
    def test_preprocessor_fit_and_transform(self):
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
            }
        ])

        preprocessor = create_preprocessor_pipeline()
        X_train_trans = preprocessor.fit_transform(train_df)

        assert X_train_trans is not None
        assert X_train_trans.shape[0] == 2
        assert X_train_trans.shape[1] >= len(NUMERICAL_FEATURES)

        # Test unseen category handling on test record
        test_df = pd.DataFrame([
            {
                "year": 2020, "km_driven": 25000, "car_age": 4, "km_per_year": 6250.0,
                "engine_cc": np.nan, "mileage": np.nan, "owner_count": np.nan,
                "brand": "NewBrandUnseen", "model": "NewModel", "variant": "Unknown",
                "fuel_type": "Electric", "transmission": "Automatic",
                "city": "UnknownCity", "state": "UnknownState", "seller_type": "Certified Dealer"
            }
        ])

        X_test_trans = preprocessor.transform(test_df)
        assert X_test_trans.shape[0] == 1
        assert X_test_trans.shape[1] == X_train_trans.shape[1]
        assert not np.isnan(X_test_trans).any()
