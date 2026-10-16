import re
from typing import Optional, Dict, Any, Union
from datetime import datetime, timezone
from .base import BaseCleaner
from ..schemas.canonical import RawCarListing



def normalize_text(text: Optional[str]) -> Optional[str]:
    """
    Cleans raw text by stripping leading/trailing whitespace, normalizing multi-spaces,
    and removing non-standard control characters.
    """
    if text is None:
        return None
    text = str(text)
    # Replace non-breaking spaces and redundant whitespaces
    text = text.replace("\u00a0", " ").replace("\u200b", "")
    text = re.sub(r"\s+", " ", text)
    cleaned = text.strip()
    return cleaned if cleaned else None


def parse_price_inr(price_val: Union[str, int, float, None]) -> Optional[float]:
    """
    Parses various Indian price formats into a clean numeric float in Rupees.
    Supports formats like:
      - '₹ 12,50,000' -> 1250000.0
      - '12.5 Lakh' / '12.50L' / '12.5 Lac' -> 1250000.0
      - '1.25 Crore' / '1.25 Cr' -> 12500000.0
      - 'Rs. 4,75,000' -> 475000.0
      - 850000 -> 850000.0
    """
    if price_val is None:
        return None
    
    if isinstance(price_val, (int, float)):
        return float(price_val) if price_val > 0 else None

    text = str(price_val).strip().lower()
    if not text:
        return None

    # Handle Crore notations: e.g. "1.25 cr", "1.25 crore", "1.25crores"
    cr_match = re.search(r"([\d\.]+)\s*(?:cr|crore|crores)", text)
    if cr_match:
        try:
            return round(float(cr_match.group(1)) * 10000000.0, 2)
        except ValueError:
            pass

    # Handle Lakh notations: e.g. "12.5 lakh", "12.50l", "12.5 lac", "12.5 lacs"
    lakh_match = re.search(r"([\d\.]+)\s*(?:lakh|lakhs|lac|lacs|l)\b", text)
    if lakh_match:
        try:
            return round(float(lakh_match.group(1)) * 100000.0, 2)
        except ValueError:
            pass

    # Strip currency symbols and letters, retain digits and decimal point
    cleaned = re.sub(r"[₹,rs\.\s]", "", text)
    # Check if there was an explicit standard number
    number_match = re.search(r"\d+", cleaned)
    if number_match:
        try:
            return float(number_match.group(0))
        except ValueError:
            pass

    return None


def parse_kilometers(km_val: Union[str, int, float, None]) -> Optional[int]:
    """
    Parses various odometer representations into integer kilometers.
    Supports:
      - '45,000 km' -> 45000
      - '45K' / '45 k' -> 45000
      - '45000 kms' -> 45000
      - '1.2 Lakh km' -> 120000
      - 35000 -> 35000
    """
    if km_val is None:
        return None

    if isinstance(km_val, (int, float)):
        return int(km_val) if km_val >= 0 else None

    text = str(km_val).strip().lower()
    if not text:
        return None

    # Handle Lakh km: e.g. "1.2 lakh km"
    lakh_match = re.search(r"([\d\.]+)\s*(?:lakh|lakhs|lac|lacs)\s*(?:km|kms)?", text)
    if lakh_match:
        try:
            return int(float(lakh_match.group(1)) * 100000)
        except ValueError:
            pass

    # Handle 'k' notation: e.g. "45k", "45.5 k"
    k_match = re.search(r"([\d\.]+)\s*k(?:\s*km|\s*kms)?\b", text)
    if k_match:
        try:
            return int(float(k_match.group(1)) * 1000)
        except ValueError:
            pass

    # Standard comma-separated or plain integer with 'km' suffix: "45,000 kms"
    cleaned = re.sub(r"[,\s]", "", text)
    match = re.search(r"(\d+)(?:\s*(?:km|kms|kilometers))?", cleaned)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass

    return None


def parse_year(year_val: Union[str, int, None]) -> Optional[int]:
    """
    Extracts a 4-digit manufacturing or registration year (1990-2030).
    Supports:
      - 2018 -> 2018
      - '2019' -> 2019
      - 'Oct 2018' -> 2018
      - '2018-05' -> 2018
    """
    if year_val is None:
        return None

    if isinstance(year_val, int):
        return year_val if 1990 <= year_val <= 2030 else None

    text = str(year_val).strip()
    match = re.search(r"\b(199\d|20[0-2]\d|2030)\b", text)
    if match:
        return int(match.group(1))

    return None


def parse_fuel_type(fuel_val: Optional[str]) -> Optional[str]:
    """
    Normalizes fuel strings to canonical choices:
    'Petrol', 'Diesel', 'CNG', 'Electric', 'Hybrid', 'LPG'.
    """
    if fuel_val is None:
        return None

    text = str(fuel_val).strip().lower()
    if not text:
        return None

    if "hybrid" in text:
        return "Hybrid"
    elif "electric" in text or text == "ev":
        return "Electric"
    elif "cng" in text:
        return "CNG"
    elif "lpg" in text:
        return "LPG"
    elif "diesel" in text:
        return "Diesel"
    elif "petrol" in text or "gasoline" in text:
        return "Petrol"

    return text.capitalize()



def parse_transmission(trans_val: Optional[str]) -> Optional[str]:
    """
    Normalizes transmission strings to 'Manual' or 'Automatic'.
    Recognizes AMT, CVT, DCT, DSG, AT as Automatic, and MT, iMT as Manual.
    """
    if trans_val is None:
        return None

    text = str(trans_val).strip().lower()
    if not text:
        return None

    if any(k in text for k in ["auto", "amt", "cvt", "dct", "dsg", "at", "torque converter"]):
        return "Automatic"
    elif any(k in text for k in ["manual", "mt", "imt", "stick"]):
        return "Manual"

    return text.capitalize()


def parse_owner_count(owner_val: Union[str, int, None]) -> Optional[int]:
    """
    Normalizes owner strings like '1st Owner', 'First', '2nd Owner', '3' into integer count.
    """
    if owner_val is None:
        return None

    if isinstance(owner_val, int):
        return owner_val if 1 <= owner_val <= 10 else None

    text = str(owner_val).strip().lower()
    if not text:
        return None

    if "first" in text or "1st" in text or "1" in text:
        return 1
    elif "second" in text or "2nd" in text or "2" in text:
        return 2
    elif "third" in text or "3rd" in text or "3" in text:
        return 3
    elif "fourth" in text or "4th" in text or "4" in text:
        return 4

    digits = re.findall(r"\d+", text)
    if digits:
        val = int(digits[0])
        return val if 1 <= val <= 10 else None

    return None


def parse_engine_cc(cc_val: Union[str, int, float, None]) -> Optional[int]:
    """
    Parses engine displacement in cubic centimeters.
    Supports formats like '1493 cc', '1.5L', '1197cc', 1493.
    """
    if cc_val is None:
        return None
    if isinstance(cc_val, (int, float)):
        return int(cc_val) if 500 <= cc_val <= 10000 else None

    text = str(cc_val).strip().lower()
    if not text:
        return None

    # Handle liter notation e.g. '1.5L' / '2.0 L'
    l_match = re.search(r"([\d\.]+)\s*l\b", text)
    if l_match:
        try:
            return int(float(l_match.group(1)) * 1000)
        except ValueError:
            pass

    digits = re.findall(r"\d+", text)
    if digits:
        val = int(digits[0])
        return val if 500 <= val <= 10000 else None

    return None


def parse_mileage(mileage_val: Union[str, int, float, None]) -> Optional[float]:
    """
    Parses fuel efficiency in kmpl or km/kg.
    Supports formats like '18.5 kmpl', '21.4 km/kg', 18.5.
    """
    if mileage_val is None:
        return None
    if isinstance(mileage_val, (int, float)):
        return round(float(mileage_val), 2) if 0.0 <= mileage_val <= 100.0 else None

    text = str(mileage_val).strip().lower()
    if not text:
        return None

    match = re.search(r"([\d\.]+)", text)
    if match:
        try:
            val = float(match.group(1))
            return round(val, 2) if 0.0 <= val <= 100.0 else None
        except ValueError:
            pass

    return None


class CarDataCleaner(BaseCleaner):
    """
    Standard cleaner applying parser rules across raw dictionary or RawCarListing models.
    """

    def clean_record(self, raw_record: Union[RawCarListing, Dict[str, Any]]) -> Dict[str, Any]:
        if isinstance(raw_record, RawCarListing):
            data = raw_record.model_dump()
        else:
            data = dict(raw_record)

        raw_specs = data.get("raw_specs") or {}
        if not isinstance(raw_specs, dict):
            raw_specs = {}

        # Prioritize explicit seller vs owner fields
        seller_candidate = data.get("seller_type") or raw_specs.get("seller_type") or data.get("raw_seller")
        owner_candidate = raw_specs.get("owner_count") or data.get("owner_count") or (data.get("raw_seller") if "owner" in str(data.get("raw_seller") or "").lower() else None)

        cleaned: Dict[str, Any] = {
            "listing_id": str(data.get("raw_id") or data.get("listing_id") or "").strip(),
            "source": str(data.get("source") or "unknown").strip().lower(),
            "listing_url": normalize_text(data.get("source_url") or data.get("listing_url")),
            "brand": normalize_text(data.get("brand") or data.get("raw_title")),
            "model": normalize_text(data.get("model")),
            "variant": normalize_text(data.get("variant") or raw_specs.get("variant")),
            "year": parse_year(data.get("raw_year") or data.get("year")),
            "fuel_type": parse_fuel_type(data.get("raw_fuel") or data.get("fuel_type")),
            "transmission": parse_transmission(data.get("raw_transmission") or data.get("transmission")),
            "km_driven": parse_kilometers(data.get("raw_km") or data.get("km_driven")),
            "engine_cc": parse_engine_cc(data.get("engine_cc") or raw_specs.get("engine_cc")),
            "mileage": parse_mileage(data.get("mileage") or raw_specs.get("mileage")),
            "owner_count": parse_owner_count(owner_candidate),
            "city": normalize_text(data.get("city") or data.get("raw_location")),
            "state": normalize_text(data.get("state") or raw_specs.get("state")),
            "seller_type": normalize_text(seller_candidate),
            "listed_price": parse_price_inr(data.get("raw_price") or data.get("listed_price")),
            "date_collected": data.get("date_collected") or datetime.now(timezone.utc)
        }

        return cleaned

