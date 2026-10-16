"""
AutoValue Alternative Vehicle Discovery Service (Phase 11).
Identifies the closest evidence-supported vehicle alternatives from the empirical dataset
based on budget constraints, powertrain preferences, and multi-factor ranking.
"""
from typing import Dict, Any, List, Optional
import os
import pandas as pd
import numpy as np
import logging

from backend.app.core.config import settings
from backend.app.schemas.intelligence import (
    AlternativeVehicleQuery,
    AlternativeVehicleItem,
    AlternativeVehicleResponse
)
from backend.app.services.valuation_service import valuation_service

logger = logging.getLogger("autovalue.alternative_service")


class AlternativeVehicleService:
    """
    Discovers evidence-backed vehicle alternatives within specified budget boundaries.
    """

    def __init__(self, processed_data_path: Optional[str] = None):
        self.processed_data_path = processed_data_path or os.path.join(
            settings.PROCESSED_DATA_DIR, "autovalue_processed.csv"
        )
        self._df: Optional[pd.DataFrame] = None
        self._load_dataset()

    def _load_dataset(self):
        if os.path.exists(self.processed_data_path):
            try:
                self._df = pd.read_csv(self.processed_data_path)
            except Exception as e:
                logger.error(f"Failed to load dataset for alternatives: {e}")
                self._df = pd.DataFrame()
        else:
            self._df = pd.DataFrame()

    def find_alternatives(self, query: AlternativeVehicleQuery) -> AlternativeVehicleResponse:
        """
        Filters and scores real listing records to produce ranked evidence-supported alternatives.
        """
        if self._df is None or self._df.empty:
            self._load_dataset()

        if self._df is None or self._df.empty:
            return AlternativeVehicleResponse(
                query=query.model_dump(),
                count=0,
                results=[],
                ranking_methodology="Dataset unavailable",
                disclaimer="Alternative vehicle search requires active listing dataset."
            )

        df = self._df.copy()

        # Determine budget boundaries
        target_budget = query.target_budget
        min_budget = query.budget_min
        max_budget = query.budget_max

        if target_budget and target_budget > 0:
            if min_budget is None:
                min_budget = target_budget * 0.75
            if max_budget is None:
                max_budget = target_budget * 1.25
        else:
            if min_budget is None:
                min_budget = 0.0
            if max_budget is None:
                max_budget = 50000000.0
            target_budget = (min_budget + max_budget) / 2.0

        # Filter by price bounds
        if "listed_price" in df.columns:
            df = df[(df["listed_price"] >= min_budget) & (df["listed_price"] <= max_budget)]

        # Filter by brand if specified
        if query.brand and str(query.brand).strip():
            b_str = query.brand.strip().lower()
            df = df[df["brand"].str.lower() == b_str]

        # Filter by fuel if specified
        if query.fuel_type and str(query.fuel_type).strip():
            f_str = query.fuel_type.strip().lower()
            df = df[df["fuel_type"].str.lower() == f_str]

        # Filter by transmission if specified
        if query.transmission and str(query.transmission).strip():
            t_str = query.transmission.strip().lower()
            df = df[df["transmission"].str.lower() == t_str]

        # Filter by city if specified
        if query.city and str(query.city).strip():
            c_str = query.city.strip().lower()
            df = df[df["city"].str.lower() == c_str]

        # Filter by min_year
        if query.min_year:
            df = df[df["year"] >= query.min_year]

        # Filter by max_km
        if query.max_km:
            df = df[df["km_driven"] <= query.max_km]

        if df.empty:
            return AlternativeVehicleResponse(
                query=query.model_dump(),
                count=0,
                results=[],
                ranking_methodology="Multi-attribute proximity scoring (Price 40%, Mileage 30%, Year 30%)",
                disclaimer="No vehicle listings found matching all specified search criteria."
            )

        # Multi-factor candidate scoring
        items: List[AlternativeVehicleItem] = []

        for idx, row in df.iterrows():
            price = float(row.get("listed_price", 0))
            year = int(row.get("year", 2018))
            km = int(row.get("km_driven", 50000))

            # 1. Price Proximity Score (0–100)
            if target_budget > 0:
                pct_price_diff = abs(price - target_budget) / target_budget
                price_prox_score = max(0.0, 100.0 - (pct_price_diff * 150.0))
            else:
                price_prox_score = 75.0

            # 2. Mileage Score (0–100)
            # 20k km -> 95, 60k km -> 70, 120k km -> 40
            mileage_score = float(np.clip(100.0 - (km / 1500.0), 10.0, 100.0))

            # 3. Year/Age Score (0–100)
            age = max(1, 2024 - year)
            age_score = float(np.clip(100.0 - (age * 7.5), 15.0, 100.0))

            # Overall Match Score (Price 40%, Mileage 30%, Year 30%)
            overall_score = round(
                (0.40 * price_prox_score) + (0.30 * mileage_score) + (0.30 * age_score),
                1
            )

            # Match reasons
            reasons = []
            if price_prox_score >= 85:
                reasons.append(f"Price ₹{price:,.0f} closely matches budget target.")
            if km <= 45000:
                reasons.append(f"Low odometer reading ({km:,} km).")
            if year >= 2021:
                reasons.append(f"Modern vehicle year ({year}).")
            if not reasons:
                reasons.append("Supported comparable listing matching search filters.")

            listing_id = str(row.get("id", f"alt-{idx}"))

            items.append(
                AlternativeVehicleItem(
                    listing_id=listing_id,
                    brand=str(row.get("brand", "")),
                    model=str(row.get("model", "")),
                    variant=str(row.get("variant", "")) if pd.notna(row.get("variant")) else None,
                    year=year,
                    km_driven=km,
                    fuel_type=str(row.get("fuel_type", "")) if pd.notna(row.get("fuel_type")) else None,
                    transmission=str(row.get("transmission", "")) if pd.notna(row.get("transmission")) else None,
                    city=str(row.get("city", "")) if pd.notna(row.get("city")) else None,
                    listed_price=price,
                    listed_price_formatted=f"₹{price:,.0f}",
                    estimated_value=float(row.get("predicted_price", price)) if "predicted_price" in row else None,
                    price_proximity_score=round(price_prox_score, 1),
                    age_score=round(age_score, 1),
                    mileage_score=round(mileage_score, 1),
                    overall_match_score=overall_score,
                    match_reasons=reasons
                )
            )

        # Sort by highest overall match score and limit
        items.sort(key=lambda x: x.overall_match_score, reverse=True)
        top_results = items[:query.limit]

        return AlternativeVehicleResponse(
            query=query.model_dump(),
            count=len(top_results),
            results=top_results,
            ranking_methodology="Multi-attribute proximity scoring (Price Proximity 40%, Usage Mileage 30%, Manufacturing Year 30%)",
            disclaimer="Rankings reflect empirical proximity to criteria from available listings. AutoValue does not endorse or certify specific vehicles."
        )


# Global singleton
alternative_vehicle_service = AlternativeVehicleService()
