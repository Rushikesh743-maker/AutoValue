"""
Certified Dealer Inventory Feed Collector.
Collects pre-owned vehicle listings from organized dealership management systems and syndication feeds.
"""
import os
import json
import logging
from typing import List, Optional, Dict, Any
from .base import BaseCollector
from ..schemas.canonical import RawCarListing
from ..cleaners.source_adapters import SourceFieldAdapter
from backend.app.core.config import settings

logger = logging.getLogger("autovalue.collectors.dealer_feed")


class DealerFeedCollector(BaseCollector):
    """
    Ingests pre-owned certified inventory feeds directly from dealership network exports.
    Supports authenticated endpoints and validated local feed snapshots.
    """

    def __init__(
        self,
        source_name: str = "dealer_feed",
        base_url: str = "https://partner-dms.autovalue.internal/api/v1/inventory",
        api_token: Optional[str] = None,
        local_feed_path: Optional[str] = None,
        max_records: int = 50,
        **kwargs
    ):
        super().__init__(source_name=source_name, base_url=base_url, max_records=max_records, **kwargs)
        self.api_token = api_token
        if local_feed_path:
            self.local_feed_path = local_feed_path
        else:
            candidates = [
                os.path.join(settings.SAMPLE_DATA_DIR, "dealer_feed_sample.json"),
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "sample", "dealer_feed_sample.json")),
            ]
            self.local_feed_path = next((p for p in candidates if os.path.exists(p)), candidates[0])


    def health_check(self) -> bool:
        if os.path.exists(self.local_feed_path):
            return True
        try:
            headers = {"Authorization": f"Bearer {self.api_token}"} if self.api_token else {}
            res = self.http_client.get(self.base_url, headers=headers, timeout=5)
            return res.status_code == 200
        except Exception:
            return False

    def collect(self, limit: Optional[int] = None) -> List[RawCarListing]:
        max_items = limit or self.max_records
        records: List[RawCarListing] = []

        # 1. Prefer local feed snapshot if available
        if os.path.exists(self.local_feed_path):
            try:
                with open(self.local_feed_path, "r", encoding="utf-8") as f:
                    feed_data = json.load(f)
                    vehicles = feed_data.get("vehicles") if isinstance(feed_data, dict) else feed_data
                    if isinstance(vehicles, list):
                        for item in vehicles[:max_items]:
                            raw_listing = SourceFieldAdapter.adapt(self.source_name, item)
                            records.append(raw_listing)
                        logger.info(f"Collected {len(records)} records from {self.source_name} local feed")
                        return records
            except Exception as e:
                logger.error(f"Error reading local feed {self.local_feed_path}: {e}")

        # 2. Remote authenticated dealer feed query
        try:
            headers = {"Authorization": f"Bearer {self.api_token}"} if self.api_token else {}
            res = self.http_client.get(self.base_url, headers=headers, params={"limit": max_items})
            if res.status_code == 200:
                payload = res.json()
                items = payload.get("data", []) if isinstance(payload, dict) else payload
                for item in items[:max_items]:
                    raw_listing = SourceFieldAdapter.adapt(self.source_name, item)
                    records.append(raw_listing)
                logger.info(f"Collected {len(records)} records from remote {self.source_name}")
        except Exception as e:
            logger.warning(f"Remote dealer feed connection failed for {self.source_name}: {e}")

        return records
