"""
Commercial Partner Marketplace API Collector.
Standardized connector for official B2B automotive marketplace APIs with API key authentication.
"""
import os
import json
import logging
from typing import List, Optional, Dict, Any
from .base import BaseCollector
from ..schemas.canonical import RawCarListing
from ..cleaners.source_adapters import SourceFieldAdapter
from backend.app.core.config import settings

logger = logging.getLogger("autovalue.collectors.commercial_api")


class CommercialApiCollector(BaseCollector):
    """
    Adapter for licensed B2B marketplace API partners.
    Requires official API credentials.
    """

    def __init__(
        self,
        source_name: str = "commercial_api",
        base_url: str = "https://partner-api.cardata.internal/v2/listings",
        api_key: Optional[str] = None,
        local_fixture_path: Optional[str] = None,
        max_records: int = 50,
        **kwargs
    ):
        super().__init__(source_name=source_name, base_url=base_url, max_records=max_records, **kwargs)
        self.api_key = api_key
        if local_fixture_path:
            self.local_fixture_path = local_fixture_path
        else:
            candidates = [
                os.path.join(settings.SAMPLE_DATA_DIR, "commercial_api_sample.json"),
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "sample", "commercial_api_sample.json")),
            ]
            self.local_fixture_path = next((p for p in candidates if os.path.exists(p)), candidates[0])


    def health_check(self) -> bool:
        if os.path.exists(self.local_fixture_path):
            return True
        if not self.api_key:
            return False
        try:
            headers = {"X-API-Key": self.api_key}
            res = self.http_client.get(f"{self.base_url}/status", headers=headers, timeout=5)
            return res.status_code == 200
        except Exception:
            return False

    def collect(self, limit: Optional[int] = None) -> List[RawCarListing]:
        max_items = limit or self.max_records
        records: List[RawCarListing] = []

        if os.path.exists(self.local_fixture_path):
            try:
                with open(self.local_fixture_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        items = data.get("data") or data.get("listings") or []
                    elif isinstance(data, list):
                        items = data
                    else:
                        items = []
                    for item in items[:max_items]:
                        raw_listing = SourceFieldAdapter.adapt(self.source_name, item)
                        records.append(raw_listing)
                    logger.info(f"Collected {len(records)} records from {self.source_name} local fixture")
                    return records
            except Exception as e:
                logger.error(f"Error reading commercial API fixture {self.local_fixture_path}: {e}")

        if not self.api_key:
            logger.warning(f"{self.source_name} requires API key for remote ingestion.")
            return records

        try:
            headers = {"X-API-Key": self.api_key}
            res = self.http_client.get(self.base_url, headers=headers, params={"limit": max_items})
            if res.status_code == 200:
                payload = res.json()
                items = payload.get("data", []) if isinstance(payload, dict) else payload
                for item in items[:max_items]:
                    raw_listing = SourceFieldAdapter.adapt(self.source_name, item)
                    records.append(raw_listing)
        except Exception as e:
            logger.error(f"Commercial API query failed: {e}")

        return records
