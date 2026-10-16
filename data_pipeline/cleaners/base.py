"""Abstract base class interface for data cleaners."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..schemas.canonical import RawCarListing, CanonicalCarListing


class BaseCleaner(ABC):
    """
    Base interface for converting raw unstructured listing dictionaries or RawCarListing
    objects into intermediate cleaned dictionaries ready for normalization and validation.
    """

    @abstractmethod
    def clean_record(self, raw_record: RawCarListing | Dict[str, Any]) -> Dict[str, Any]:
        """
        Cleans raw attributes from a single record into canonical scalar types.
        """
        pass
