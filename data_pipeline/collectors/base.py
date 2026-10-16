"""
Abstract base interface and common capabilities for data collectors.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import logging
from ..schemas.canonical import RawCarListing
from .http_client import RateLimitedHttpClient

logger = logging.getLogger("autovalue.collectors")


class BaseCollector(ABC):
    """
    Abstract Base Class for all data source collectors.
    Handles rate-limited HTTP interactions, collection limits, and error isolation.
    """

    def __init__(
        self,
        source_name: str,
        base_url: str,
        http_client: Optional[RateLimitedHttpClient] = None,
        max_records: int = 50,
    ):
        self.source_name = source_name.strip().lower()
        self.base_url = base_url
        self.http_client = http_client or RateLimitedHttpClient()
        self.max_records = max_records

    @abstractmethod
    def health_check(self) -> bool:
        """Verifies endpoint connectivity and readiness."""
        pass

    @abstractmethod
    def collect(self, limit: Optional[int] = None) -> List[RawCarListing]:
        """
        Executes data collection from the source.
        Returns a list of RawCarListing instances.
        """
        pass
