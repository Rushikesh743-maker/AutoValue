"""
Example/Placeholder collector implementation illustrating how legitimate real-world
data sources will be attached in subsequent phases.
"""
from typing import List
from .base import BaseCollector
from ..schemas.canonical import RawCarListing


class ExampleCollector(BaseCollector):
    """
    Placeholder collector showing the interface contract.
    Does NOT connect to external networks or scrape unauthorised endpoints in Phase 1.
    """

    def __init__(self, source_name: str = "example_source", base_url: str = "https://example.com"):
        super().__init__(source_name=source_name, base_url=base_url)

    def health_check(self) -> bool:
        """Simulates checking endpoint access."""
        return True

    def collect(self, limit: int = 100) -> List[RawCarListing]:
        """
        Placeholder collector returns an empty list or configured stream.
        Real collectors will be implemented in Phase 2 following source validation and legal compliance checks.
        """
        return []
