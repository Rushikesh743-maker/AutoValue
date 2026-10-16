"""
Unit tests for canonical schema validation and data integrity checks.
"""
import pytest
from data_pipeline.validators.validator import ListingValidator


class TestListingValidator:
    @pytest.fixture
    def validator(self):
        return ListingValidator()

    def test_valid_canonical_record(self, validator):
        valid_data = {
            "listing_id": "test-123",
            "source": "cars24",
            "brand": "Hyundai",
            "model": "Creta",
            "year": 2021,
            "listed_price": 1250000.0,
            "km_driven": 25000,
            "fuel_type": "Petrol",
            "transmission": "Manual",
            "city": "Bengaluru"
        }
        res = validator.validate_record(valid_data)
        assert res.is_valid is True
        assert res.record is not None
        assert res.record.brand == "Hyundai"
        assert res.record.listed_price == 1250000.0

    def test_missing_required_fields(self, validator):
        invalid_data = {
            "listing_id": "test-124",
            # Missing source, brand, model, year, listed_price
        }
        res = validator.validate_record(invalid_data)
        assert res.is_valid is False
        assert len(res.errors) > 0

    def test_unrealistic_price_rejected(self, validator):
        too_low = {
            "listing_id": "test-125",
            "source": "cars24",
            "brand": "Maruti Suzuki",
            "model": "Swift",
            "year": 2020,
            "listed_price": 500.0  # Unrealistic price (< ₹10,000)
        }
        res = validator.validate_record(too_low)
        assert res.is_valid is False

    def test_batch_validation(self, validator):
        batch = [
            {
                "listing_id": "valid-1",
                "source": "spinny",
                "brand": "Honda",
                "model": "City",
                "year": 2019,
                "listed_price": 850000.0
            },
            {
                "listing_id": "invalid-2",
                "source": "spinny",
                "brand": "Honda",
                "model": "City",
                "year": 1850,  # Invalid year
                "listed_price": 850000.0
            }
        ]
        valid_records, rejected = validator.validate_batch(batch)
        assert len(valid_records) == 1
        assert len(rejected) == 1
        assert valid_records[0].listing_id == "valid-1"
