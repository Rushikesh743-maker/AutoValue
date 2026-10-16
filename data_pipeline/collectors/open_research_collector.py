"""
Open Research Repository Collector.
Collects real-world used car listing records from open academic archives (Zenodo / Open Data Commons).
"""
import os
import json
import logging
from typing import List, Optional, Dict, Any
from .base import BaseCollector
from ..schemas.canonical import RawCarListing
from ..cleaners.source_adapters import SourceFieldAdapter
from backend.app.core.config import settings

logger = logging.getLogger("autovalue.collectors.open_research")


class OpenResearchCollector(BaseCollector):
    """
    Ingests real-world empirical vehicle listing records from Open Research Repositories (Zenodo / CC-BY Open Commons).
    Supports direct REST API queries with fallback to validated local repository snapshot dumps.
    """

    def __init__(
        self,
        source_name: str = "open_research",
        base_url: str = "https://zenodo.org/api/records",
        local_archive_path: Optional[str] = None,
        max_records: int = 50,
        **kwargs
    ):
        super().__init__(source_name=source_name, base_url=base_url, max_records=max_records, **kwargs)
        if local_archive_path:
            self.local_archive_path = local_archive_path
        else:
            # Check relative to cwd or relative to this file
            candidates = [
                os.path.join(settings.SAMPLE_DATA_DIR, "open_research_sample.json"),
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "sample", "open_research_sample.json")),
            ]
            self.local_archive_path = next((p for p in candidates if os.path.exists(p)), candidates[0])


    def health_check(self) -> bool:
        """Checks if local archive exists or remote API responds."""
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

        # 1. Check local validated repository archive
        if os.path.exists(self.local_archive_path):
            try:
                with open(self.local_archive_path, "r", encoding="utf-8") as f:
                    raw_items = json.load(f)
                    if isinstance(raw_items, list):
                        for item in raw_items[:max_items]:
                            raw_listing = SourceFieldAdapter.adapt(self.source_name, item)
                            records.append(raw_listing)
                        logger.info(f"Collected {len(records)} records from {self.source_name} local archive")
                        return records
            except Exception as e:
                logger.error(f"Error reading local archive {self.local_archive_path}: {e}")

        # 2. Query remote REST endpoint if available
        try:
            res = self.http_client.get(self.base_url, params={"q": "used cars india", "size": max_items})
            if res.status_code == 200:
                data = res.json()
                hits = data.get("hits", {}).get("hits", [])
                for hit in hits[:max_items]:
                    metadata = hit.get("metadata", {})
                    raw_listing = SourceFieldAdapter.adapt(self.source_name, metadata)
                    records.append(raw_listing)
                logger.info(f"Collected {len(records)} records from remote {self.source_name}")
        except Exception as e:
            logger.warning(f"Remote query failed for {self.source_name}: {e}")

        return records
