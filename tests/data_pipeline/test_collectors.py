"""
Unit tests for source collector implementations with local fixtures and mocked HTTP.
"""
import pytest
from unittest.mock import patch, MagicMock
from data_pipeline.collectors.open_research_collector import OpenResearchCollector
from data_pipeline.collectors.dealer_feed_collector import DealerFeedCollector
from data_pipeline.collectors.community_portal_collector import CommunityPortalCollector
from data_pipeline.collectors.commercial_api_collector import CommercialApiCollector


class TestCollectors:
    def test_open_research_collector_with_local_fixture(self):
        collector = OpenResearchCollector()
        assert collector.health_check() is True

        records = collector.collect(limit=5)
        assert len(records) > 0
        assert records[0].source == "open_research"
        assert records[0].raw_price is not None
        assert records[0].raw_km is not None

    def test_dealer_feed_collector_with_local_fixture(self):
        collector = DealerFeedCollector()
        assert collector.health_check() is True

        records = collector.collect(limit=5)
        assert len(records) > 0
        assert records[0].source == "dealer_feed"
        assert records[0].raw_title is not None

    def test_community_portal_collector_with_local_fixture(self):
        collector = CommunityPortalCollector()
        assert collector.health_check() is True

        records = collector.collect(limit=5)
        assert len(records) > 0
        assert records[0].source == "community_portal"

    @patch("requests.Session.get")
    def test_commercial_api_collector_mocked_http(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "success",
            "data": [
                {
                    "vehicle_id": "test-mock-1",
                    "company": "Toyota",
                    "vehicle_model": "Fortuner",
                    "model_year": 2021,
                    "selling_price": "34.5 Lakh",
                    "odometer": "45000 km",
                    "city": "Bengaluru"
                }
            ]
        }
        mock_get.return_value = mock_resp

        collector = CommercialApiCollector(api_key="valid-key-123", local_fixture_path="non_existent_file_test.json")
        records = collector.collect(limit=5)

        assert len(records) == 1
        assert records[0].raw_id == "test-mock-1"
        assert records[0].source == "commercial_api"
        assert records[0].raw_price == "34.5 Lakh"

