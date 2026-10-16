"""
Unit tests for duplicate listing detection and similarity scoring.
"""
import pytest
from data_pipeline.deduplication.detector import DuplicateDetector


class TestDuplicateDetector:
    @pytest.fixture
    def detector(self):
        return DuplicateDetector(duplicate_threshold=0.80)

    def test_identical_listings_different_source(self, detector):
        listing_a = {
            "listing_id": "cars24-101",
            "source": "cars24",
            "brand": "Hyundai",
            "model": "Creta",
            "year": 2020,
            "km_driven": 45000,
            "listed_price": 1200000.0,
            "city": "Mumbai"
        }
        listing_b = {
            "listing_id": "spinny-999",
            "source": "spinny",
            "brand": "Hyundai",
            "model": "Creta",
            "year": 2020,
            "km_driven": 45500,  # Slight variation
            "listed_price": 1220000.0,  # Slight variation
            "city": "Mumbai"
        }
        score = detector.calculate_similarity_breakdown(listing_a, listing_b)
        assert score.total_score >= 0.80
        assert score.is_likely_duplicate is True
        assert score.brand_score == 1.0
        assert score.model_score == 1.0

    def test_different_brand_listings(self, detector):
        listing_a = {
            "listing_id": "1",
            "source": "cars24",
            "brand": "Hyundai",
            "model": "Creta",
            "year": 2020,
            "km_driven": 45000,
            "listed_price": 1200000.0,
            "city": "Mumbai"
        }
        listing_b = {
            "listing_id": "2",
            "source": "spinny",
            "brand": "Kia",
            "model": "Seltos",
            "year": 2020,
            "km_driven": 45000,
            "listed_price": 1200000.0,
            "city": "Mumbai"
        }
        score = detector.calculate_similarity_breakdown(listing_a, listing_b)
        assert score.total_score == 0.0
        assert score.is_likely_duplicate is False

    def test_different_year_and_mileage_same_model(self, detector):
        listing_a = {
            "listing_id": "1",
            "source": "cars24",
            "brand": "Honda",
            "model": "City",
            "year": 2016,
            "km_driven": 90000,
            "listed_price": 600000.0,
            "city": "Delhi"
        }
        listing_b = {
            "listing_id": "2",
            "source": "spinny",
            "brand": "Honda",
            "model": "City",
            "year": 2022,
            "km_driven": 15000,
            "listed_price": 1350000.0,
            "city": "Delhi"
        }
        score = detector.calculate_similarity_breakdown(listing_a, listing_b)
        assert score.total_score < 0.70
        assert score.is_likely_duplicate is False
