"""
Unit tests for data cleaning utility functions.
Tests cover price parsing, odometer parsing, year extraction, fuel & transmission normalization, and text cleaning.
"""
import pytest
from data_pipeline.cleaners.cleaner import (
    normalize_text,
    parse_price_inr,
    parse_kilometers,
    parse_year,
    parse_fuel_type,
    parse_transmission,
    parse_owner_count,
    CarDataCleaner
)


class TestTextNormalization:
    def test_normalize_empty(self):
        assert normalize_text(None) is None
        assert normalize_text("") is None
        assert normalize_text("   ") is None

    def test_normalize_whitespace(self):
        assert normalize_text("  Hyundai   Creta   SX  ") == "Hyundai Creta SX"
        assert normalize_text("Maruti\u00a0Swift\u200b VXi") == "Maruti Swift VXi"


class TestPriceNormalization:
    def test_lakh_formats(self):
        assert parse_price_inr("12.5 Lakh") == 1250000.0
        assert parse_price_inr("12.50L") == 1250000.0
        assert parse_price_inr("₹ 12.50 Lakh") == 1250000.0
        assert parse_price_inr("8.75 lac") == 875000.0
        assert parse_price_inr("5 Lakhs") == 500000.0

    def test_crore_formats(self):
        assert parse_price_inr("1.25 Crore") == 12500000.0
        assert parse_price_inr("1.50 Cr") == 15000000.0

    def test_comma_separated_inr(self):
        assert parse_price_inr("₹ 12,50,000") == 1250000.0
        assert parse_price_inr("Rs. 4,75,000") == 475000.0
        assert parse_price_inr("850000") == 850000.0
        assert parse_price_inr(850000) == 850000.0

    def test_invalid_price(self):
        assert parse_price_inr(None) is None
        assert parse_price_inr("") is None
        assert parse_price_inr("Ask for price") is None


class TestKilometerNormalization:
    def test_km_string_formats(self):
        assert parse_kilometers("45,000 km") == 45000
        assert parse_kilometers("45,000 kms") == 45000
        assert parse_kilometers("45000") == 45000
        assert parse_kilometers(45000) == 45000

    def test_k_notation(self):
        assert parse_kilometers("45K") == 45000
        assert parse_kilometers("45.5 k") == 45500
        assert parse_kilometers("85k km") == 85000

    def test_lakh_km_notation(self):
        assert parse_kilometers("1.2 Lakh km") == 120000
        assert parse_kilometers("1.5 Lacs kms") == 150000

    def test_invalid_km(self):
        assert parse_kilometers(None) is None
        assert parse_kilometers("") is None


class TestYearNormalization:
    def test_valid_years(self):
        assert parse_year("2019") == 2019
        assert parse_year(2019) == 2019
        assert parse_year("Oct 2018") == 2018
        assert parse_year("2021-06") == 2021

    def test_out_of_bounds_year(self):
        assert parse_year("1980") is None
        assert parse_year("2045") is None
        assert parse_year(None) is None


class TestFuelAndTransmission:
    def test_fuel_types(self):
        assert parse_fuel_type("petrol") == "Petrol"
        assert parse_fuel_type("DIESEL") == "Diesel"
        assert parse_fuel_type("cng + petrol") == "CNG"
        assert parse_fuel_type("Electric") == "Electric"
        assert parse_fuel_type("EV") == "Electric"
        assert parse_fuel_type("Hybrid Petrol") == "Hybrid"

    def test_transmissions(self):
        assert parse_transmission("Manual") == "Manual"
        assert parse_transmission("5-Speed MT") == "Manual"
        assert parse_transmission("Automatic") == "Automatic"
        assert parse_transmission("7-Speed DCT") == "Automatic"
        assert parse_transmission("CVT") == "Automatic"
        assert parse_transmission("AMT") == "Automatic"


class TestCarDataCleaner:
    def test_clean_record(self):
        cleaner = CarDataCleaner()
        raw = {
            "raw_id": "item-1234",
            "source": "Spinny",
            "source_url": "https://example.com/car/1234",
            "brand": "Hyundai",
            "model": "Creta",
            "raw_year": "2020",
            "raw_price": "₹ 11,50,000",
            "raw_km": "32,000 km",
            "raw_fuel": "Diesel",
            "raw_transmission": "Automatic",
            "raw_location": "Bangalore"
        }
        cleaned = cleaner.clean_record(raw)
        assert cleaned["listing_id"] == "item-1234"
        assert cleaned["source"] == "spinny"
        assert cleaned["year"] == 2020
        assert cleaned["listed_price"] == 1150000.0
        assert cleaned["km_driven"] == 32000
        assert cleaned["fuel_type"] == "Diesel"
        assert cleaned["transmission"] == "Automatic"
