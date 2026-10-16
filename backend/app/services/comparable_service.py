"""
Comparable vehicle search and market analytics service.
Ranks processed listings based on multidimensional vehicle attribute similarity (excluding price)
and computes robust empirical market statistics and source-level distributions.
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import pandas as pd
import logging

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False

from backend.app.schemas.valuation import (
    ComparableCarItem,
    MarketStatistics,
    SourceAnalysisItem
)

logger = logging.getLogger("autovalue.comparable_service")


@dataclass
class ComparableConfig:
    """
    Configurable weights and thresholds for multi-attribute comparable ranking.
    """
    weight_model: float = 0.35
    weight_year: float = 0.20
    weight_fuel: float = 0.15
    weight_transmission: float = 0.10
    weight_km: float = 0.10
    weight_variant: float = 0.05
    weight_city: float = 0.05
    minimum_similarity: float = 0.35
    top_k: int = 10


class ComparableService:
    """
    Identifies nearest comparable listings and computes market statistical distributions.
    """

    def __init__(self, config: Optional[ComparableConfig] = None):
        self.config = config or ComparableConfig()

    def compute_similarity(self, query: Dict[str, Any], candidate: Dict[str, Any]) -> float:
        """
        Computes price-independent similarity score (0.0 to 1.0) between query vehicle and a database candidate.
        """
        c = self.config
        total_score = 0.0

        # 1. Model & Brand Similarity
        q_model = str(query.get("model") or "").strip().lower()
        c_model = str(candidate.get("model") or "").strip().lower()
        q_brand = str(query.get("brand") or "").strip().lower()
        c_brand = str(candidate.get("brand") or "").strip().lower()

        if q_brand == c_brand and q_brand:
            if q_model == c_model and q_model:
                model_score = 1.0
            elif RAPIDFUZZ_AVAILABLE:
                model_score = fuzz.token_sort_ratio(q_model, c_model) / 100.0
            else:
                model_score = 0.5 if q_model in c_model or c_model in q_model else 0.0
        else:
            # Different brand penalty
            model_score = 0.0
        total_score += c.weight_model * model_score

        # 2. Year Similarity (Decays linearly up to 8 years)
        q_year = query.get("year")
        c_year = candidate.get("year")
        if q_year and c_year:
            year_diff = abs(int(q_year) - int(c_year))
            year_score = max(0.0, 1.0 - (year_diff / 8.0))
        else:
            year_score = 0.5
        total_score += c.weight_year * year_score

        # 3. Fuel Compatibility
        q_fuel = str(query.get("fuel_type") or "").strip().lower()
        c_fuel = str(candidate.get("fuel_type") or "").strip().lower()
        if q_fuel and c_fuel:
            fuel_score = 1.0 if q_fuel == c_fuel else 0.0
        else:
            fuel_score = 0.5
        total_score += c.weight_fuel * fuel_score

        # 4. Transmission Compatibility
        q_trans = str(query.get("transmission") or "").strip().lower()
        c_trans = str(candidate.get("transmission") or "").strip().lower()
        if q_trans and c_trans:
            trans_score = 1.0 if q_trans == c_trans else 0.4
        else:
            trans_score = 0.5
        total_score += c.weight_transmission * trans_score

        # 5. Odometer (KM Driven) Similarity
        q_km = query.get("km_driven")
        c_km = candidate.get("km_driven")
        if q_km is not None and c_km is not None and pd.notnull(c_km):
            km_diff = abs(float(q_km) - float(c_km))
            km_score = max(0.0, 1.0 - (km_diff / 80000.0))
        else:
            km_score = 0.5
        total_score += c.weight_km * km_score

        # 6. Variant Similarity
        q_var = str(query.get("variant") or "").strip().lower()
        c_var = str(candidate.get("variant") or "").strip().lower()
        if q_var and c_var and q_var != "unspecified" and c_var != "unspecified":
            if RAPIDFUZZ_AVAILABLE:
                var_score = fuzz.token_sort_ratio(q_var, c_var) / 100.0
            else:
                var_score = 1.0 if q_var == c_var else 0.0
        else:
            var_score = 0.5
        total_score += c.weight_variant * var_score

        # 7. City / Location Similarity
        q_city = str(query.get("city") or "").strip().lower()
        c_city = str(candidate.get("city") or "").strip().lower()
        if q_city and c_city:
            city_score = 1.0 if q_city == c_city else 0.2
        else:
            city_score = 0.5
        total_score += c.weight_city * city_score

        return round(total_score, 4)

    def find_comparables(
        self,
        query: Dict[str, Any],
        listings_df: pd.DataFrame
    ) -> Tuple[List[ComparableCarItem], MarketStatistics, List[SourceAnalysisItem], Dict[str, Any]]:
        """
        Scans listings DataFrame, filters by similarity threshold, ranks top K,
        and computes market statistics and cross-source analysis.
        """
        if listings_df.empty:
            empty_market = MarketStatistics(comparable_count=0)
            return [], empty_market, [], {"range_low": None, "range_high": None, "range_method": "Insufficient comparable market evidence"}

        scored_candidates = []
        q_brand = str(query.get("brand") or "").strip().lower()
        
        if hasattr(listings_df, "_records_cache"):
            candidates = listings_df._records_cache
        elif isinstance(listings_df, pd.DataFrame):
            candidates = listings_df.to_dict('records')
            try:
                listings_df._records_cache = candidates
            except Exception:
                pass
        else:
            candidates = listings_df

        for cand_dict in candidates:
            c_brand = str(cand_dict.get("brand") or "").strip().lower()
            if q_brand and c_brand and q_brand != c_brand:
                continue
            score = self.compute_similarity(query, cand_dict)
            if score >= self.config.minimum_similarity:
                scored_candidates.append((score, cand_dict))

        # Fallback if no same-brand comparables found
        if not scored_candidates and q_brand:
            for cand_dict in candidates:
                score = self.compute_similarity(query, cand_dict)
                if score >= self.config.minimum_similarity:
                    scored_candidates.append((score, cand_dict))

        # Sort descending by similarity score
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        top_matches = scored_candidates[:self.config.top_k]

        if not top_matches:
            empty_market = MarketStatistics(comparable_count=0)
            return [], empty_market, [], {"range_low": None, "range_high": None, "range_method": "Insufficient comparable market evidence"}

        # Build ComparableCarItem list
        comparable_items: List[ComparableCarItem] = []
        prices: List[float] = []

        for score, item in top_matches:
            price = float(item.get("listed_price", 0))
            prices.append(price)
            comparable_items.append(ComparableCarItem(
                listing_id=str(item.get("listing_id") or item.get("id")),
                brand=str(item.get("brand")),
                model=str(item.get("model")),
                variant=item.get("variant") if item.get("variant") != "Unspecified" else None,
                year=int(item.get("year", 0)),
                fuel_type=item.get("fuel_type"),
                transmission=item.get("transmission"),
                km_driven=int(item.get("km_driven")) if pd.notnull(item.get("km_driven")) else None,
                city=item.get("city"),
                state=item.get("state") if item.get("state") != "Unspecified" else None,
                listed_price=price,
                listed_price_formatted=f"INR {price:,.0f}",
                source=str(item.get("source", "unknown")),
                similarity_score=score,
                similarity_percentage=f"{int(score * 100)}%",
                date_collected=str(item.get("date_collected")) if item.get("date_collected") else None
            ))

        # Compute Market Statistics
        np_prices = np.array(prices)
        med_price = float(np.median(np_prices))
        mean_price = float(np.mean(np_prices))
        min_p = float(np.min(np_prices))
        max_p = float(np.max(np_prices))
        std_p = float(np.std(np_prices)) if len(np_prices) > 1 else 0.0

        p25 = float(np.percentile(np_prices, 25)) if len(np_prices) >= 4 else None
        p75 = float(np.percentile(np_prices, 75)) if len(np_prices) >= 4 else None

        market_stats = MarketStatistics(
            median=round(med_price, 2),
            mean=round(mean_price, 2),
            min=round(min_p, 2),
            max=round(max_p, 2),
            p25=round(p25, 2) if p25 is not None else None,
            p75=round(p75, 2) if p75 is not None else None,
            comparable_count=len(top_matches),
            price_dispersion_std=round(std_p, 2)
        )

        # Cross-Source Aggregation
        source_groups: Dict[str, List[float]] = {}
        for item in comparable_items:
            source_groups.setdefault(item.source, []).append(item.listed_price)

        source_analysis: List[SourceAnalysisItem] = []
        for src, src_prices in source_groups.items():
            arr = np.array(src_prices)
            source_analysis.append(SourceAnalysisItem(
                source=src,
                listing_count=len(src_prices),
                median_price=round(float(np.median(arr)), 2),
                mean_price=round(float(np.mean(arr)), 2),
                min_price=round(float(np.min(arr)), 2),
                max_price=round(float(np.max(arr)), 2)
            ))

        # Range Methodology
        if len(prices) >= 4 and p25 is not None and p75 is not None:
            range_low = p25
            range_high = p75
            range_method = "Comparable listing P25-P75 observed interquartile range"
        elif len(prices) >= 1:
            range_low = min_p
            range_high = max_p
            range_method = "Comparable listing observed Min-Max range (small sample)"
        else:
            range_low = None
            range_high = None
            range_method = "Insufficient comparable market evidence"

        range_info = {
            "range_low": range_low,
            "range_high": range_high,
            "range_method": range_method
        }

        return comparable_items, market_stats, source_analysis, range_info
