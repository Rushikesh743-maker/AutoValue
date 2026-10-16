"""
Duplicate listing detector computing multi-attribute similarity confidence scores.
"""
from typing import Dict, Any, Union, Optional
from dataclasses import dataclass
from .base import BaseDuplicateDetector
from ..schemas.canonical import CanonicalCarListing


@dataclass
class SimilarityScore:
    """Detailed breakdown of matching confidence between two car listings."""
    total_score: float
    brand_score: float
    model_score: float
    year_score: float
    km_score: float
    price_score: float
    city_score: float
    is_likely_duplicate: bool
    notes: str


class DuplicateDetector(BaseDuplicateDetector):
    """
    Computes evidence-backed similarity scores between two listings across
    make, model, year, odometer, price, and location.
    """

    def __init__(self, duplicate_threshold: float = 0.85):
        self.duplicate_threshold = duplicate_threshold

    def _to_dict(self, record: Any) -> Dict[str, Any]:
        if isinstance(record, CanonicalCarListing):
            return record.model_dump()
        if hasattr(record, "__table__"):
            return {c.name: getattr(record, c.name) for c in record.__table__.columns}
        if isinstance(record, dict):
            return dict(record)
        if hasattr(record, "__dict__"):
            return {k: v for k, v in record.__dict__.items() if not k.startswith("_")}
        return dict(record)


    def calculate_similarity_breakdown(
        self,
        listing_a: Union[CanonicalCarListing, Dict[str, Any]],
        listing_b: Union[CanonicalCarListing, Dict[str, Any]]
    ) -> SimilarityScore:
        a = self._to_dict(listing_a)
        b = self._to_dict(listing_b)

        # 1. Brand match (Hard requirement)
        brand_a = str(a.get("brand") or "").strip().lower()
        brand_b = str(b.get("brand") or "").strip().lower()
        brand_score = 1.0 if (brand_a and brand_a == brand_b) else 0.0

        if brand_score == 0.0:
            return SimilarityScore(
                total_score=0.0,
                brand_score=0.0,
                model_score=0.0,
                year_score=0.0,
                km_score=0.0,
                price_score=0.0,
                city_score=0.0,
                is_likely_duplicate=False,
                notes="Brands do not match"
            )

        # 2. Model match
        model_a = str(a.get("model") or "").strip().lower()
        model_b = str(b.get("model") or "").strip().lower()
        model_score = 1.0 if (model_a and model_a == model_b) else (0.5 if (model_a in model_b or model_b in model_a) else 0.0)

        # 3. Year match (Must be identical or within 1 year for registration/mfg mismatch)
        year_a = a.get("year")
        year_b = b.get("year")
        if year_a and year_b:
            diff = abs(int(year_a) - int(year_b))
            if diff == 0:
                year_score = 1.0
            elif diff == 1:
                year_score = 0.5
            else:
                year_score = 0.0
        else:
            year_score = 0.5  # Neutral if missing

        # 4. Kilometer distance match (Within 5-10% tolerance for driving between listing platforms)
        km_a = a.get("km_driven")
        km_b = b.get("km_driven")
        if km_a is not None and km_b is not None and km_a > 0 and km_b > 0:
            diff_km = abs(km_a - km_b)
            max_km = max(km_a, km_b)
            ratio = diff_km / max_km
            if ratio <= 0.05:
                km_score = 1.0
            elif ratio <= 0.15:
                km_score = 0.8
            elif ratio <= 0.30:
                km_score = 0.4
            else:
                km_score = 0.0
        else:
            km_score = 0.5

        # 5. Price match (Within 10-15% tolerance for different dealer platform markup)
        p_a = a.get("listed_price")
        p_b = b.get("listed_price")
        if p_a and p_b and p_a > 0 and p_b > 0:
            diff_p = abs(p_a - p_b)
            max_p = max(p_a, p_b)
            p_ratio = diff_p / max_p
            if p_ratio <= 0.05:
                price_score = 1.0
            elif p_ratio <= 0.12:
                price_score = 0.8
            elif p_ratio <= 0.25:
                price_score = 0.4
            else:
                price_score = 0.0
        else:
            price_score = 0.5

        # 6. City / location match
        city_a = str(a.get("city") or "").strip().lower()
        city_b = str(b.get("city") or "").strip().lower()
        if city_a and city_b:
            city_score = 1.0 if city_a == city_b else 0.0
        else:
            city_score = 0.5

        # Weighted calculation
        # Weights: Brand 25%, Model 25%, Year 15%, KM 15%, Price 10%, City 10%
        weights = [0.25, 0.25, 0.15, 0.15, 0.10, 0.10]
        scores = [brand_score, model_score, year_score, km_score, price_score, city_score]
        total_score = round(sum(w * s for w, s in zip(weights, scores)), 4)

        is_dup = total_score >= self.duplicate_threshold

        notes = "Likely duplicate listing across sources" if is_dup else "Distinct listing or insufficient match confidence"

        return SimilarityScore(
            total_score=total_score,
            brand_score=brand_score,
            model_score=model_score,
            year_score=year_score,
            km_score=km_score,
            price_score=price_score,
            city_score=city_score,
            is_likely_duplicate=is_dup,
            notes=notes
        )

    def calculate_similarity(
        self,
        listing_a: Union[CanonicalCarListing, Dict[str, Any]],
        listing_b: Union[CanonicalCarListing, Dict[str, Any]]
    ) -> float:
        return self.calculate_similarity_breakdown(listing_a, listing_b).total_score
