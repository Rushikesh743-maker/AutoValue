"""
Unit tests for ComparableService matching, ranking, and market statistics.
"""
import pytest
import pandas as pd
from backend.app.services.comparable_service import ComparableService, ComparableConfig


class TestComparableService:
    def test_compute_similarity_exact_and_partial(self):
        service = ComparableService()

        query = {
            "brand": "Hyundai",
            "model": "Creta",
            "variant": "SX",
            "year": 2021,
            "fuel_type": "Diesel",
            "transmission": "Manual",
            "km_driven": 35000,
            "city": "Bengaluru"
        }

        exact_candidate = {
            "brand": "Hyundai",
            "model": "Creta",
            "variant": "SX",
            "year": 2021,
            "fuel_type": "Diesel",
            "transmission": "Manual",
            "km_driven": 35000,
            "city": "Bengaluru",
            "listed_price": 1350000.0
        }

        diff_brand_candidate = {
            "brand": "Toyota",
            "model": "Innova",
            "variant": "ZX",
            "year": 2018,
            "fuel_type": "Diesel",
            "transmission": "Automatic",
            "km_driven": 80000,
            "city": "Mumbai",
            "listed_price": 1800000.0
        }

        score_exact = service.compute_similarity(query, exact_candidate)
        score_diff = service.compute_similarity(query, diff_brand_candidate)

        assert score_exact > 0.90
        assert score_diff < 0.40
        assert score_exact > score_diff

    def test_find_comparables_and_market_statistics(self):
        service = ComparableService()
        query = {
            "brand": "Hyundai",
            "model": "Creta",
            "year": 2021,
            "fuel_type": "Diesel",
            "transmission": "Manual",
            "km_driven": 38000,
            "city": "Bengaluru"
        }

        sample_df = pd.DataFrame([
            {"id": 1, "listing_id": "c1", "brand": "Hyundai", "model": "Creta", "variant": "SX", "year": 2021, "fuel_type": "Diesel", "transmission": "Manual", "km_driven": 38000, "city": "Bengaluru", "listed_price": 1350000.0, "source": "open_research"},
            {"id": 2, "listing_id": "c2", "brand": "Hyundai", "model": "Creta", "variant": "SX (O)", "year": 2021, "fuel_type": "Diesel", "transmission": "Manual", "km_driven": 41000, "city": "Bengaluru", "listed_price": 1380000.0, "source": "dealer_feed"},
            {"id": 3, "listing_id": "c3", "brand": "Hyundai", "model": "Creta", "variant": "S", "year": 2020, "fuel_type": "Diesel", "transmission": "Manual", "km_driven": 45000, "city": "Pune", "listed_price": 1250000.0, "source": "community_portal"},
            {"id": 4, "listing_id": "c4", "brand": "Hyundai", "model": "Creta", "variant": "SX", "year": 2022, "fuel_type": "Diesel", "transmission": "Manual", "km_driven": 25000, "city": "Bengaluru", "listed_price": 1420000.0, "source": "commercial_api"},
        ])

        comparables, stats, source_analysis, range_info = service.find_comparables(query, sample_df)

        assert len(comparables) == 4
        assert stats.comparable_count == 4
        assert stats.median is not None
        assert stats.min == 1250000.0
        assert stats.max == 1420000.0
        assert range_info["range_low"] is not None
        assert range_info["range_high"] is not None
        assert len(source_analysis) == 4
