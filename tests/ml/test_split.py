"""
Unit tests for standard, duplicate-safe (group-aware), 3-way, and temporal dataset partitioning.
"""
import pytest
import pandas as pd
import numpy as np
from ml.training.split import (
    standard_train_test_split,
    duplicate_safe_train_test_split,
    duplicate_safe_train_val_test_split,
    temporal_train_test_split,
    build_vehicle_clusters
)


class TestSplit:
    def test_duplicate_safe_partitioning(self):
        df = pd.DataFrame([
            {"id": 1, "brand": "Hyundai", "model": "Creta", "listed_price": 1300000.0, "duplicate_of_id": None},
            {"id": 2, "brand": "Hyundai", "model": "Creta", "listed_price": 1305000.0, "duplicate_of_id": 1},
            {"id": 3, "brand": "Hyundai", "model": "Creta", "listed_price": 1310000.0, "duplicate_of_id": 1},
            {"id": 4, "brand": "Honda", "model": "City", "listed_price": 1000000.0, "duplicate_of_id": None},
            {"id": 5, "brand": "Tata", "model": "Nexon", "listed_price": 1100000.0, "duplicate_of_id": None},
            {"id": 6, "brand": "Toyota", "model": "Innova", "listed_price": 1800000.0, "duplicate_of_id": None},
            {"id": 7, "brand": "Mahindra", "model": "XUV700", "listed_price": 2100000.0, "duplicate_of_id": None},
            {"id": 8, "brand": "Kia", "model": "Seltos", "listed_price": 1200000.0, "duplicate_of_id": None},
            {"id": 9, "brand": "Volkswagen", "model": "Polo", "listed_price": 750000.0, "duplicate_of_id": None},
            {"id": 10, "brand": "Skoda", "model": "Kushaq", "listed_price": 1500000.0, "duplicate_of_id": None},
        ])

        train_df, test_df = duplicate_safe_train_test_split(df, test_size=0.3, random_state=42)

        assert len(train_df) + len(test_df) == len(df)
        assert len(train_df) > 0
        assert len(test_df) > 0

        # Verify records 1, 2, and 3 are in the EXACT same partition
        cluster_ids = {1, 2, 3}
        in_train = cluster_ids.issubset(set(train_df["id"]))
        in_test = cluster_ids.issubset(set(test_df["id"]))

        assert in_train or in_test, "Duplicate candidates must be grouped into the same partition!"
        assert not (any(i in train_df["id"].values for i in cluster_ids) and any(i in test_df["id"].values for i in cluster_ids))

    def test_duplicate_safe_with_null_duplicate_of_id_and_same_listing_id(self):
        # Simulating processed data where duplicate_of_id is null, but listing_id or physical specs match
        df = pd.DataFrame([
            {"id": 101, "listing_id": "car-A", "brand": "Hyundai", "model": "Creta", "variant": "SX", "year": 2021, "fuel_type": "Petrol", "transmission": "Manual", "km_driven": 25000, "city": "Bengaluru", "listed_price": 1400000.0, "duplicate_of_id": None},
            {"id": 102, "listing_id": "car-A", "brand": "Hyundai", "model": "Creta", "variant": "SX", "year": 2021, "fuel_type": "Petrol", "transmission": "Manual", "km_driven": 25000, "city": "Bengaluru", "listed_price": 1400000.0, "duplicate_of_id": None},
            {"id": 103, "listing_id": "car-B", "brand": "Honda", "model": "City", "variant": "V", "year": 2020, "fuel_type": "Petrol", "transmission": "CVT", "km_driven": 35000, "city": "Mumbai", "listed_price": 1050000.0, "duplicate_of_id": None},
            {"id": 104, "listing_id": "car-C", "brand": "Tata", "model": "Nexon", "variant": "XZ+", "year": 2022, "fuel_type": "Diesel", "transmission": "Manual", "km_driven": 18000, "city": "Pune", "listed_price": 1150000.0, "duplicate_of_id": None},
            {"id": 105, "listing_id": "car-D", "brand": "Toyota", "model": "Innova", "variant": "GX", "year": 2019, "fuel_type": "Diesel", "transmission": "Manual", "km_driven": 75000, "city": "Hyderabad", "listed_price": 1650000.0, "duplicate_of_id": None},
            {"id": 106, "listing_id": "car-E", "brand": "Mahindra", "model": "XUV700", "variant": "AX7", "year": 2022, "fuel_type": "Petrol", "transmission": "Automatic", "km_driven": 22000, "city": "Delhi Ncr", "listed_price": 2100000.0, "duplicate_of_id": None},
        ])

        train_df, test_df = duplicate_safe_train_test_split(df, test_size=0.33, random_state=42)

        # 101 and 102 must NOT be split across train and test
        ids_in_train = set(train_df["id"])
        ids_in_test = set(test_df["id"])

        assert not (101 in ids_in_train and 102 in ids_in_test)
        assert not (101 in ids_in_test and 102 in ids_in_train)

    def test_duplicate_safe_train_val_test_split(self):
        records = []
        for i in range(30):
            records.append({
                "id": i + 1,
                "listing_id": f"lid-{i // 2}",  # pairs of identical listing IDs
                "brand": f"Brand-{i % 5}",
                "model": f"Model-{i % 5}",
                "variant": "V1",
                "year": 2020 + (i % 4),
                "fuel_type": "Petrol",
                "transmission": "Manual",
                "km_driven": 20000 + i * 1000,
                "city": "Bengaluru",
                "listed_price": 800000.0 + i * 20000.0,
                "duplicate_of_id": None
            })
        df = pd.DataFrame(records)

        train_df, val_df, test_df = duplicate_safe_train_val_test_split(
            df,
            val_size=0.20,
            test_size=0.20,
            random_state=42
        )

        assert len(train_df) + len(val_df) + len(test_df) == len(df)
        assert len(train_df) > 0
        assert len(val_df) > 0
        assert len(test_df) > 0

        # No listing_id may appear in more than one partition
        train_lids = set(train_df["listing_id"])
        val_lids = set(val_df["listing_id"])
        test_lids = set(test_df["listing_id"])

        assert train_lids.isdisjoint(val_lids), "Train and validation splits share listing IDs!"
        assert train_lids.isdisjoint(test_lids), "Train and test splits share listing IDs!"
        assert val_lids.isdisjoint(test_lids), "Validation and test splits share listing IDs!"

    def test_split_reproducibility(self):
        records = []
        for i in range(25):
            records.append({
                "id": i + 1,
                "listing_id": f"item-{i}",
                "brand": "Maruti Suzuki" if i % 2 == 0 else "Hyundai",
                "model": "Swift" if i % 2 == 0 else "i20",
                "variant": "Top",
                "year": 2019,
                "fuel_type": "Petrol",
                "transmission": "Manual",
                "km_driven": 30000 + i * 500,
                "city": "Mumbai",
                "listed_price": 600000.0 + i * 15000,
                "duplicate_of_id": None
            })
        df = pd.DataFrame(records)

        tr1, val1, te1 = duplicate_safe_train_val_test_split(df, val_size=0.2, test_size=0.2, random_state=42)
        tr2, val2, te2 = duplicate_safe_train_val_test_split(df, val_size=0.2, test_size=0.2, random_state=42)

        pd.testing.assert_frame_equal(tr1.reset_index(drop=True), tr2.reset_index(drop=True))
        pd.testing.assert_frame_equal(val1.reset_index(drop=True), val2.reset_index(drop=True))
        pd.testing.assert_frame_equal(te1.reset_index(drop=True), te2.reset_index(drop=True))

    def test_standard_train_test_split(self):
        df = pd.DataFrame({"x": range(20), "y": range(20)})
        tr, te = standard_train_test_split(df, test_size=0.25, random_state=42)
        assert len(tr) == 15
        assert len(te) == 5

    def test_temporal_train_test_split(self):
        df = pd.DataFrame({
            "id": range(10),
            "date_collected": [
                "2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01", "2024-05-01",
                "2024-06-01", "2024-07-01", "2024-08-01", "2024-09-01", "2024-10-01"
            ]
        })
        tr, te = temporal_train_test_split(df, test_size=0.20, date_col="date_collected")
        assert len(tr) == 8
        assert len(te) == 2
        assert pd.to_datetime(tr["date_collected"].max()) < pd.to_datetime(te["date_collected"].min())
