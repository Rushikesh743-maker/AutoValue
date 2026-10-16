"""
Unit tests for RateLimitedHttpClient with mocked HTTP responses and error handling.
"""
import pytest
import time
from unittest.mock import patch, MagicMock
import requests
from data_pipeline.collectors.http_client import RateLimitedHttpClient


class TestRateLimitedHttpClient:
    def test_client_headers_and_defaults(self):
        client = RateLimitedHttpClient(
            user_agent="AutoValue-Test/0.1",
            timeout_seconds=5,
            request_delay_seconds=0.1
        )
        assert client.user_agent == "AutoValue-Test/0.1"
        assert client.timeout_seconds == 5
        assert client.request_delay_seconds == 0.1
        assert client.session.headers["User-Agent"] == "AutoValue-Test/0.1"

    @patch("requests.Session.get")
    def test_successful_get_request(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_resp

        client = RateLimitedHttpClient(request_delay_seconds=0.0)
        res = client.get("https://example.com/api/test")

        assert res.status_code == 200
        assert res.json() == {"status": "ok"}
        mock_get.assert_called_once()

    @patch("requests.Session.get")
    def test_http_error_handling(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        client = RateLimitedHttpClient(request_delay_seconds=0.0)
        with pytest.raises(requests.exceptions.RequestException):
            client.get("https://example.com/api/timeout")

    def test_rate_limiting_delay(self):
        client = RateLimitedHttpClient(request_delay_seconds=0.05)
        with patch.object(client.session, "get") as mock_get:
            mock_resp = MagicMock(status_code=200)
            mock_get.return_value = mock_resp
            
            t0 = time.time()
            client.get("https://example.com/1")
            client.get("https://example.com/2")
            t1 = time.time()

            assert (t1 - t0) >= 0.04

