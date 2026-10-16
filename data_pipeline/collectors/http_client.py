"""
Polite, rate-limited HTTP client with exponential backoff and retry mechanisms.
Ensures responsible, conservative network interaction strictly respecting rate limits.
"""
import time
import logging
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from backend.app.core.config import settings

logger = logging.getLogger("autovalue.http_client")


class RateLimitedHttpClient:
    """
    Polite HTTP Client configured with:
      - Conservative User-Agent header identifying the project
      - Automatic retries on status codes 429, 500, 502, 503, 504
      - Exponential backoff
      - Configurable per-request delays
      - Request timeouts
    """

    def __init__(
        self,
        user_agent: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        request_delay_seconds: Optional[float] = None,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
    ):
        self.user_agent = user_agent or settings.USER_AGENT
        self.timeout_seconds = timeout_seconds or settings.REQUEST_TIMEOUT_SECONDS
        self.request_delay_seconds = request_delay_seconds if request_delay_seconds is not None else settings.REQUEST_DELAY_SECONDS
        self.last_request_time: float = 0.0

        # Configure session with robust retry strategy
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
        })

        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "HEAD"],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _enforce_rate_limit(self) -> None:
        """Enforces inter-request delay to prevent overwhelming remote servers."""
        if self.request_delay_seconds > 0:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.request_delay_seconds:
                sleep_time = self.request_delay_seconds - elapsed
                logger.debug(f"Rate limiter sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
        self.last_request_time = time.time()

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> requests.Response:
        """Executes a rate-limited GET request with error handling."""
        self._enforce_rate_limit()
        req_timeout = timeout or self.timeout_seconds
        try:
            response = self.session.get(url, params=params, headers=headers, timeout=req_timeout)
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP GET failed for {url}: {e}")
            raise

    def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> requests.Response:
        """Executes a rate-limited POST request with error handling."""
        self._enforce_rate_limit()
        req_timeout = timeout or self.timeout_seconds
        try:
            response = self.session.post(url, json=json, data=data, headers=headers, timeout=req_timeout)
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP POST failed for {url}: {e}")
            raise
