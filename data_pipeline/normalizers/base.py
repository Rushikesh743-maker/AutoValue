"""Abstract base class interface for data normalizers."""
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseNormalizer(ABC):
    """
    Base interface for normalizing entity fields (brand, model, variant, location)
    into standardized canonical entities.
    """

    @abstractmethod
    def normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes brand, model, variant, and categorical fields in the input record dictionary.
        """
        pass
