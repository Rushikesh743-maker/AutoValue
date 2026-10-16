"""
Community & Open Vehicle Ingestion Collector.
Collects verified listings submitted through the AutoValue ingestion portal or open submissions.
"""
import os
import json
import logging
from typing import List, Optional, Dict, Any
from .base import BaseCollector
from ..schemas.canonical import RawCarListing
from ..cleaners.source_adapters import SourceFieldAdapter
from backend.app.core.config import settings

logger = logging.getLogger("autovalue.collectors.community_portal")


class CommunityPortalCollector(BaseCollector):
    """
    Ingests verified pre-owned car listings submitted directly via user/dealer portal.
    """

    def __init__(
        self,
        source_name: str = "community_portal",
        base_url: str = "https://ingest.autovalue.internal/api/v1/listings",
        local_archive_path: Optional[str] = None,
        max_records: int = 50,
        **kwargs
    ):
        super().__init__(source_name=source_name, base_url=base_url, max_records=max_records, **kwargs)
        if local_archive_path:
            self.local_archive_path = local_archive_path
        else:
            candidates = [
                os.path.join(settings.SAMPLE_DATA_DIR, "community_portal_sample.json"),
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "sample", "community_portal_sample.json")),
            ]
            self.local_archive_path = next((p for p in candidates if os.path.exists(p)), candidates[0])


    def health_check(self) -> bool:
        if os.path.exists(self.local_archive_path):
            return True
        try:
            res = self.http_client.get(self.base_url, timeout=5)
            return res.status_code == 200
        except Exception:
            return False

    def collect(self, limit: Optional[int] = None) -> List[RawCarListing]:
        max_items = limit or self.max_records
        records: List[RawCarListing] = []

        if os.path.exists(self.local_archive_path):
            try:
                with open(self.local_archive_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    items = data if isinstance(data, list) else data.get("listings", [])
                    for item in items[:max_items]:
                        raw_listing = SourceFieldAdapter.adapt(self.source_name, item)
                        records.append(raw_listing)
                    logger.info(f"Collected {len(records)} records from {self.source_name} local archive")
                    return records
            except Exception as e:
                logger.error(f"Error reading local community portal archive {self.local_archive_path}: {e}")

        try:
            res = self.http_client.get(self.base_url, params={"limit": max_items})
            if res.status_code == 200:
                payload = res.json()
                items = payload.get("data", []) if isinstance(payload, dict) else payload
                for item in items[:max_items]:
                    raw_listing = SourceFieldAdapter.adapt(self.source_name, item)
                    records.append(raw_listing)
        except Exception as e:
            logger.warning(f"Remote community portal query failed: {e}")

        return records
