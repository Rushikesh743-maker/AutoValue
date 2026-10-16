"""
Vehicle entity normalizer using dictionary matching, regex parsing, and RapidFuzz fuzzy matching.
"""
import re
from typing import Dict, Any, Optional, Tuple, List
from .base import BaseNormalizer

try:
    from rapidfuzz import process, fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False


# Canonical brand dictionary with common aliases and misspellings
CANONICAL_BRANDS: Dict[str, str] = {
    "maruti": "Maruti Suzuki",
    "maruti suzuki": "Maruti Suzuki",
    "suzuki": "Maruti Suzuki",
    "hyundai": "Hyundai",
    "tata": "Tata",
    "mahindra": "Mahindra",
    "honda": "Honda",
    "toyota": "Toyota",
    "kia": "Kia",
    "volkswagen": "Volkswagen",
    "vw": "Volkswagen",
    "skoda": "Skoda",
    "mg": "MG",
    "mg motors": "MG",
    "renault": "Renault",
    "nissan": "Nissan",
    "ford": "Ford",
    "bmw": "BMW",
    "mercedes": "Mercedes-Benz",
    "mercedes-benz": "Mercedes-Benz",
    "audi": "Audi",
    "jeep": "Jeep",
    "volvo": "Volvo",
    "land rover": "Land Rover",
    "jaguar": "Jaguar",
}

# Known popular models per brand for parsing combined titles (e.g. "Hyundai Creta 1.5 SX")
KNOWN_BRAND_MODELS: Dict[str, List[str]] = {
    "Maruti Suzuki": [
        "Swift", "Baleno", "Dzire", "Brezza", "Vitara Brezza", "Wagon R", "Ertiga",
        "Alto", "Alto 800", "Alto K10", "Celerio", "Ciaz", "S-Presso", "Ignis", "XL6", "Grand Vitara", "Fronx", "Jimny"
    ],
    "Hyundai": [
        "Creta", "i20", "Grand i10", "Grand i10 Nios", "Venue", "Verna", "Santro",
        "Aura", "Tucson", "Alcazar", "Elantra", "Exter", "i10", "Eon", "Kona"
    ],
    "Tata": [
        "Nexon", "Punch", "Altroz", "Harrier", "Safari", "Tiago", "Tigor", "Hexa", "Nano", "Bolt", "Zest"
    ],
    "Mahindra": [
        "Scorpio", "Scorpio-N", "Scorpio Classic", "XUV700", "XUV300", "XUV500",
        "Thar", "Bolero", "Bolero Neo", "KUV100", "Marazzo", "XUV 3XO"
    ],
    "Honda": [
        "City", "Amaze", "Civic", "WR-V", "Jazz", "BR-V", "CR-V", "Elevate", "Brio", "Mobilio"
    ],
    "Toyota": [
        "Innova", "Innova Crysta", "Innova Hycross", "Fortuner", "Urban Cruiser",
        "Glanza", "Hyryder", "Corolla", "Corolla Altis", "Etios", "Etios Liva", "Yaris", "Hilux", "Camry"
    ],
    "Kia": [
        "Seltos", "Sonet", "Carens", "Carnival", "EV6"
    ],
    "Volkswagen": [
        "Polo", "Vento", "Taigun", "Virtus", "Tiguan", "Ameo", "Passat", "Jetta"
    ],
    "Skoda": [
        "Rapid", "Kushaq", "Slavia", "Octavia", "Superb", "Kodiaq", "Fabia", "Yeti"
    ],
    "MG": [
        "Hector", "Hector Plus", "Astor", "ZS EV", "Gloster", "Comet EV"
    ],
    "Renault": [
        "Kwid", "Triber", "Kiger", "Duster", "Lodgy", "Captur", "Pulse", "Scala"
    ],
    "Nissan": [
        "Magnite", "Kicks", "Micra", "Sunny", "Terrano"
    ],
    "Ford": [
        "EcoSport", "Endeavour", "Figo", "Aspire", "Freestyle", "Fiesta"
    ]
}


class VehicleNormalizer(BaseNormalizer):
    """
    Standardizes vehicle brand, model, variant, and location entities.
    """

    def normalize_brand(self, raw_brand: Optional[str]) -> Optional[str]:
        """Matches a raw brand string against canonical brands dictionary and fuzzy matcher."""
        if not raw_brand:
            return None

        cleaned = raw_brand.strip().lower()

        # Direct dictionary match
        if cleaned in CANONICAL_BRANDS:
            return CANONICAL_BRANDS[cleaned]

        # Fuzzy match if RapidFuzz is available
        if RAPIDFUZZ_AVAILABLE:
            match = process.extractOne(
                cleaned,
                list(CANONICAL_BRANDS.keys()),
                scorer=fuzz.token_sort_ratio,
                score_cutoff=85
            )
            if match:
                return CANONICAL_BRANDS[match[0]]

        # Capitalize fallback
        return raw_brand.strip().title()

    def extract_brand_and_model(self, full_title_or_brand: str, model_candidate: Optional[str] = None) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extracts standardized (brand, model, variant) from raw input strings.
        Example: "Hyundai Creta 1.5 CRDi SX" -> ("Hyundai", "Creta", "1.5 CRDi SX")
        """
        if not full_title_or_brand:
            return (None, None, None)

        combined_text = full_title_or_brand
        if model_candidate and model_candidate.lower() not in combined_text.lower():
            combined_text = f"{full_title_or_brand} {model_candidate}"

        # 1. Detect Brand (Check longest aliases first, e.g. "maruti suzuki" before "maruti")
        detected_brand: Optional[str] = None
        sorted_brand_keys = sorted(CANONICAL_BRANDS.keys(), key=len, reverse=True)
        for brand_key in sorted_brand_keys:
            canonical_name = CANONICAL_BRANDS[brand_key]
            pattern = rf"\b{re.escape(brand_key)}\b"
            if re.search(pattern, combined_text, re.IGNORECASE):
                detected_brand = canonical_name
                # Remove matched brand from combined text for easier model extraction
                combined_text = re.sub(pattern, "", combined_text, flags=re.IGNORECASE).strip()
                break


        if not detected_brand:
            detected_brand = self.normalize_brand(full_title_or_brand.split()[0])
            combined_text = " ".join(full_title_or_brand.split()[1:])

        # 2. Detect Model from known models of the detected brand
        detected_model: Optional[str] = None
        remaining_variant: Optional[str] = None

        if detected_brand and detected_brand in KNOWN_BRAND_MODELS:
            models_list = KNOWN_BRAND_MODELS[detected_brand]
            # Check longest model names first (e.g., 'Vitara Brezza' before 'Brezza')
            sorted_models = sorted(models_list, key=len, reverse=True)
            for m in sorted_models:
                pattern = rf"\b{re.escape(m)}\b"
                match = re.search(pattern, combined_text, re.IGNORECASE)
                if match:
                    detected_model = m
                    remaining_variant = re.sub(pattern, "", combined_text, flags=re.IGNORECASE).strip()
                    break

        # Fallback for model if not in known dictionary
        if not detected_model:
            if model_candidate:
                detected_model = model_candidate.strip().title()
                remaining_variant = combined_text.replace(model_candidate, "").strip()
            else:
                words = combined_text.split()
                if words:
                    detected_model = words[0].title()
                    remaining_variant = " ".join(words[1:]) if len(words) > 1 else None

        # Clean remaining variant string
        if remaining_variant:
            remaining_variant = re.sub(r"\s+", " ", remaining_variant).strip()
            if not remaining_variant:
                remaining_variant = None

        return (detected_brand, detected_model, remaining_variant)

    def normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Normalizes a dictionary record by extracting clean brand, model, and variant."""
        res = dict(record)

        raw_brand = res.get("brand") or ""
        raw_model = res.get("model") or ""
        raw_variant = res.get("variant")

        brand, model, extracted_variant = self.extract_brand_and_model(raw_brand, raw_model)
        res["brand"] = brand or raw_brand
        res["model"] = model or raw_model
        if not res.get("variant") and extracted_variant:
            res["variant"] = extracted_variant

        # Capitalize location
        if res.get("city"):
            res["city"] = str(res["city"]).strip().title()
        if res.get("state"):
            res["state"] = str(res["state"]).strip().title()

        return res
