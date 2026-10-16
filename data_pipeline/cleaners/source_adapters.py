"""
Source-specific field adapters mapping diverse upstream field nomenclatures
into standardized RawCarListing dictionary structures.
"""
from typing import Dict, Any, Optional
from ..schemas.canonical import RawCarListing


class SourceFieldAdapter:
    """
    Translates heterogeneous field names across various data sources into
    standard raw key names before canonical cleaning and validation.
    """

    # Synonyms for field key mapping
    KM_KEYS = ["km_driven", "km", "kms", "kilometers", "distance_driven", "odometer", "mileage_km", "kms_run"]
    PRICE_KEYS = ["listed_price", "price", "asking_price", "selling_price", "cost", "val", "amount", "listing_price"]
    YEAR_KEYS = ["year", "reg_year", "manufacturing_year", "model_year", "registration_year", "mfg_year"]
    BRAND_KEYS = ["brand", "make", "manufacturer", "oem", "company"]
    MODEL_KEYS = ["model", "car_model", "model_name", "vehicle_model"]
    VARIANT_KEYS = ["variant", "trim", "version", "edition", "sub_model"]
    FUEL_KEYS = ["fuel_type", "fuel", "fuelType", "engine_type"]
    TRANS_KEYS = ["transmission", "gearbox", "trans", "transmission_type"]
    CITY_KEYS = ["city", "location", "hub_city", "metro", "region", "district"]
    STATE_KEYS = ["state", "province", "region_state"]
    OWNER_KEYS = ["owner_count", "owners", "no_of_owners", "previous_owners", "ownership"]
    SELLER_KEYS = ["seller_type", "seller", "seller_category", "dealer_type", "posted_by", "seller_name"]
    ENGINE_KEYS = ["engine_cc", "engine", "displacement", "engine_displacement", "cc", "motor_cc", "engine_size"]
    MILEAGE_KEYS = ["mileage", "fuel_economy", "kmpl", "efficiency", "mileage_kmpl"]
    URL_KEYS = ["listing_url", "url", "link", "source_url", "permalink"]
    ID_KEYS = ["listing_id", "id", "listingId", "car_id", "vehicle_id", "ad_id", "raw_id"]

    @classmethod
    def _find_first_value(cls, data: Dict[str, Any], keys: list) -> Optional[Any]:
        for k in keys:
            if k in data and data[k] is not None:
                return data[k]
            # Check lowercase variant
            lower_map = {orig_k.lower(): orig_k for orig_k in data.keys()}
            if k.lower() in lower_map and data[lower_map[k.lower()]] is not None:
                return data[lower_map[k.lower()]]
        return None

    @classmethod
    def adapt(cls, source_name: str, raw_item: Dict[str, Any]) -> RawCarListing:
        """
        Converts a source-specific dictionary into a RawCarListing object.
        """
        raw_id = str(cls._find_first_value(raw_item, cls.ID_KEYS) or "").strip() or None
        source_url = cls._find_first_value(raw_item, cls.URL_KEYS)
        if source_url:
            source_url = str(source_url).strip()

        brand_val = cls._find_first_value(raw_item, cls.BRAND_KEYS)
        model_val = cls._find_first_value(raw_item, cls.MODEL_KEYS)
        raw_title = raw_item.get("title") or raw_item.get("name") or (f"{brand_val or ''} {model_val or ''}".strip() or None)

        raw_listing = RawCarListing(
            raw_id=raw_id,
            source=source_name.lower().strip(),
            source_url=source_url,
            raw_title=raw_title,
            raw_price=str(cls._find_first_value(raw_item, cls.PRICE_KEYS) or "") or None,
            raw_km=str(cls._find_first_value(raw_item, cls.KM_KEYS) or "") or None,
            raw_year=str(cls._find_first_value(raw_item, cls.YEAR_KEYS) or "") or None,
            raw_fuel=str(cls._find_first_value(raw_item, cls.FUEL_KEYS) or "") or None,
            raw_transmission=str(cls._find_first_value(raw_item, cls.TRANS_KEYS) or "") or None,
            raw_location=str(cls._find_first_value(raw_item, cls.CITY_KEYS) or "") or None,
            raw_seller=str(cls._find_first_value(raw_item, cls.SELLER_KEYS) or "") or None,
            raw_specs={
                "variant": cls._find_first_value(raw_item, cls.VARIANT_KEYS),
                "state": cls._find_first_value(raw_item, cls.STATE_KEYS),
                "owner_count": cls._find_first_value(raw_item, cls.OWNER_KEYS),
                "engine_cc": cls._find_first_value(raw_item, cls.ENGINE_KEYS),
                "mileage": cls._find_first_value(raw_item, cls.MILEAGE_KEYS),
                "original_payload": {k: v for k, v in raw_item.items() if k not in ["photos", "images", "binary_data"]}
            }
        )
        return raw_listing
