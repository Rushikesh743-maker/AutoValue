"""
Unit tests for feature engineering calculations, car_age, km_per_year, and leakage checking.
"""
import pytest
import pandas as pd
import numpy as np
from data_pipeline.feature_engineering.features import (
    calculate_car_age,
    calculate_km_per_year,
    check_target_leakage,
    CarFeatureEngineer
)


class TestFeatureEngineering:
    def test_calculate_car_age_scalar_and_series(self):
        assert calculate_car_age(2021, reference_year=2024) == 3
        assert calculate_car_age(2024, reference_year=2024) == 0
        assert calculate_car_age(2025, reference_year=2024) == 0  # Non-negative clipped
        assert calculate_car_age(None, reference_year=2024) == 0

        years = pd.Series([2020, 2022, 2018])
        ages = calculate_car_age(years, reference_year=2024)
        assert list(ages) == [4, 2, 6]

    def test_calculate_km_per_year(self):
        # 3 year old car with 45,000 km -> 15,000 km/year
        assert calculate_km_per_year(45000, 3) == 15000.0
        # Brand new car (age 0) -> divisor clipped to 1 -> 5,000 km/year
        assert calculate_km_per_year(5000, 0) == 5000.0

        km_series = pd.Series([30000, 50000])
        age_series = pd.Series([2, 5])
        res = calculate_km_per_year(km_series, age_series)
        assert list(res) == [15000.0, 10000.0]

    def test_check_target_leakage(self):
        clean_features = ["brand", "model", "year", "km_driven", "car_age", "km_per_year", "fuel_type"]
        leakage = check_target_leakage(clean_features, target_col="listed_price")
        assert len(leakage) == 0

        leaky_features = ["brand", "listed_price", "price_per_km", "year"]
        detected = check_target_leakage(leaky_features, target_col="listed_price")
        assert "listed_price" in detected
        assert "price_per_km" in detected

    def test_car_feature_engineer_transform(self):
        engineer = CarFeatureEngineer(reference_year=2024)
        df = pd.DataFrame([
            {
                "brand": "Hyundai",
                "model": "Creta",
                "variant": "1.5 CRDi SX",
                "year": 2021,
                "km_driven": 36000,
                "listed_price": 1350000.0,
                "fuel_type": "Diesel",
                "transmission": "Manual",
                "city": "Bengaluru"
            }
        ])
        engineered = engineer.transform(df)

        assert "car_age" in engineered.columns
        assert engineered.loc[0, "car_age"] == 3
        assert "km_per_year" in engineered.columns
        assert engineered.loc[0, "km_per_year"] == 12000.0

        X, y = engineer.get_feature_and_target_matrices(df)
        assert "listed_price" not in X.columns
        assert len(y) == 1
        assert y.iloc[0] == 1350000.0
