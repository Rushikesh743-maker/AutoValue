"""
Unit tests for vehicle brand, model, and entity normalizers.
"""
import pytest
from data_pipeline.normalizers.normalizer import VehicleNormalizer


class TestVehicleNormalizer:
    @pytest.fixture
    def normalizer(self):
        return VehicleNormalizer()

    def test_brand_normalization(self, normalizer):
        assert normalizer.normalize_brand("hyundai") == "Hyundai"
        assert normalizer.normalize_brand("MARUTI") == "Maruti Suzuki"
        assert normalizer.normalize_brand("maruti suzuki") == "Maruti Suzuki"
        assert normalizer.normalize_brand("vw") == "Volkswagen"
        assert normalizer.normalize_brand("mercedes") == "Mercedes-Benz"

    def test_extract_brand_and_model(self, normalizer):
        brand, model, variant = normalizer.extract_brand_and_model("Hyundai Creta 1.5 CRDi SX")
        assert brand == "Hyundai"
        assert model == "Creta"
        assert variant == "1.5 CRDi SX"

    def test_extract_brand_and_multiword_model(self, normalizer):
        brand, model, variant = normalizer.extract_brand_and_model("Maruti Suzuki Vitara Brezza ZDi Plus")
        assert brand == "Maruti Suzuki"
        assert model == "Vitara Brezza"
        assert variant == "ZDi Plus"

    def test_normalize_record_dictionary(self, normalizer):
        record = {
            "brand": "hyundai",
            "model": "creta",
            "city": "bengaluru",
            "state": "karnataka"
        }
        normalized = normalizer.normalize_record(record)
        assert normalized["brand"] == "Hyundai"
        assert normalized["model"] == "Creta"
        assert normalized["city"] == "Bengaluru"
        assert normalized["state"] == "Karnataka"
