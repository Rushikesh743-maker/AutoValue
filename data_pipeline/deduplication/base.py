"""Abstract base interface for duplicate listing detection."""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from ..schemas.canonical import CanonicalCarListing


class BaseDuplicateDetector(ABC):
    """
    Base interface for computing pairwise similarity and identifying potential duplicate listings.
    """

    @abstractmethod
    def calculate_similarity(self, listing_a: CanonicalCarListing | Dict[str, Any], listing_b: CanonicalCarListing | Dict[str, Any]) -> float:
        """
        Returns a confidence score between 0.0 and 1.0 indicating probability that
        listing_a and listing_b describe the identical physical vehicle.
        """
        pass
