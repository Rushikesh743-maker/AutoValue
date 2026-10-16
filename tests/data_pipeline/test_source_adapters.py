"""
Unit tests for SourceFieldAdapter normalizing heterogeneous upstream schemas.
"""
import pytest
from data_pipeline.cleaners.source_adapters import SourceFieldAdapter


class TestSourceFieldAdapter:
    def test_adapt_dealer_feed_nomenclatures(self):
        dealer_raw = {
            "listingId": "dms-101",
            "manufacturer": "Hyundai",
            "car_model": "Creta",
            "trim": "1.5 CRDi SX",
            "model_year": 2021,
            "asking_price": "13.85 Lakh",
            "odometer": "38,000 km",
            "fuelType": "Diesel",
            "gearbox": "Automatic",
            "metro": "Bengaluru",
            "dealer_type": "Certified Dealer",
            "url": "https://dealers.example.com/inv/101"
        }
        adapted = SourceFieldAdapter.adapt("dealer_feed", dealer_raw)
        assert adapted.raw_id == "dms-101"
        assert adapted.source == "dealer_feed"
        assert adapted.raw_price == "13.85 Lakh"
        assert adapted.raw_km == "38,000 km"
        assert adapted.raw_year == "2021"
        assert adapted.raw_fuel == "Diesel"
        assert adapted.raw_transmission == "Automatic"
        assert adapted.raw_location == "Bengaluru"
        assert adapted.source_url == "https://dealers.example.com/inv/101"

    def test_adapt_research_nomenclatures(self):
        research_raw = {
            "id": "res-999",
            "make": "Honda",
            "model_name": "City",
            "selling_price": "10.5 Lakh",
            "kms_run": "45,000",
            "year": 2020,
            "fuel_type": "Petrol",
            "transmission": "Manual",
            "city": "Mumbai"
        }
        adapted = SourceFieldAdapter.adapt("open_research", research_raw)
        assert adapted.raw_id == "res-999"
        assert adapted.source == "open_research"
        assert adapted.raw_price == "10.5 Lakh"
        assert adapted.raw_km == "45,000"
        assert adapted.raw_fuel == "Petrol"
        assert adapted.raw_location == "Mumbai"
