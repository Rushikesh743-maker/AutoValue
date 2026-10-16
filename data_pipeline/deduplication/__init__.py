"""Deduplication package for identifying cross-source duplicate car listings."""
from .detector import DuplicateDetector, SimilarityScore

__all__ = ["DuplicateDetector", "SimilarityScore"]
