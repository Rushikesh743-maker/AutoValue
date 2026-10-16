"""
Ingestion Service coordinating:
Collector -> Raw Preservation -> Validation -> Cleaning -> Normalization -> Duplicate Detection -> Database Persistence -> Quality Reporting.
"""
import os
import json
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.listing import CarListing
from backend.app.models.source import Source
from backend.app.models.collection_run import CollectionRun
from ..schemas.canonical import CanonicalCarListing, RawCarListing
from ..cleaners.cleaner import CarDataCleaner
from ..normalizers.normalizer import VehicleNormalizer
from ..deduplication.detector import DuplicateDetector
from ..validators.validator import ListingValidator, ValidationResult
from ..validators.quality_report import DataQualityReporter, QualityReport
from ..collectors.base import BaseCollector

logger = logging.getLogger("autovalue.ingestion")


@dataclass
class IngestionResult:
    collection_run_id: int
    source_name: str
    status: str
    total_collected: int
    valid_count: int
    rejected_count: int
    duplicates_detected: int
    raw_storage_path: Optional[str]
    quality_report: QualityReport
    saved_listings: List[CarListing]


class IngestionService:
    """
    Production ingestion orchestrator enforcing data provenance, multi-stage cleaning,
    normalization, similarity scoring, database persistence, and collection metrics.
    """

    def __init__(
        self,
        db: Session,
        cleaner: Optional[CarDataCleaner] = None,
        normalizer: Optional[VehicleNormalizer] = None,
        validator: Optional[ListingValidator] = None,
        deduplicator: Optional[DuplicateDetector] = None,
        reporter: Optional[DataQualityReporter] = None,
        raw_storage_dir: Optional[str] = None
    ):
        self.db = db
        self.cleaner = cleaner or CarDataCleaner()
        self.normalizer = normalizer or VehicleNormalizer()
        self.validator = validator or ListingValidator()
        self.deduplicator = deduplicator or DuplicateDetector(duplicate_threshold=0.82)
        self.reporter = reporter or DataQualityReporter()
        self.raw_storage_dir = raw_storage_dir or settings.RAW_DATA_DIR
        os.makedirs(self.raw_storage_dir, exist_ok=True)

    def _get_or_create_source(self, name: str, base_url: str = "https://example.com") -> Source:
        source_obj = self.db.query(Source).filter(Source.name == name.lower().strip()).first()
        if not source_obj:
            source_obj = Source(
                name=name.lower().strip(),
                base_url=base_url,
                active=True,
                created_at=datetime.now(timezone.utc)
            )
            self.db.add(source_obj)
            self.db.commit()
            self.db.refresh(source_obj)
        return source_obj

    def _save_raw_snapshot(self, source_name: str, run_id: int, raw_records: List[RawCarListing]) -> str:
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{source_name}_run{run_id}_{timestamp_str}.json"
        filepath = os.path.join(self.raw_storage_dir, filename)
        
        raw_serializable = [r.model_dump(mode="json") for r in raw_records]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(raw_serializable, f, indent=2, default=str)
        return filepath

    def execute_collection(self, collector: BaseCollector, limit: Optional[int] = None) -> IngestionResult:
        """
        Runs complete ingestion pipeline for a given BaseCollector instance.
        """
        source_obj = self._get_or_create_source(collector.source_name, collector.base_url)

        # 1. Initialize CollectionRun record in PENDING / RUNNING status
        collection_run = CollectionRun(
            source_id=source_obj.id,
            started_at=datetime.now(timezone.utc),
            status="running",
            records_collected=0,
            records_valid=0,
            records_rejected=0
        )
        self.db.add(collection_run)
        self.db.commit()
        self.db.refresh(collection_run)

        raw_snapshot_path = None
        try:
            # 2. Collect raw records
            raw_records = collector.collect(limit=limit)
            collection_run.records_collected = len(raw_records)

            # 3. Preserve raw snapshot
            if raw_records:
                raw_snapshot_path = self._save_raw_snapshot(collector.source_name, collection_run.id, raw_records)

            # 4. Ingest and process raw records
            result = self.process_raw_records(
                source_name=collector.source_name,
                raw_records=raw_records,
                collection_run=collection_run,
                raw_snapshot_path=raw_snapshot_path
            )
            return result

        except Exception as e:
            logger.error(f"Collection pipeline failed for source {collector.source_name}: {e}")
            self.db.rollback()
            collection_run.completed_at = datetime.now(timezone.utc)
            collection_run.status = "failed"
            self.db.commit()
            raise

    def process_raw_records(
        self,
        source_name: str,
        raw_records: List[RawCarListing],
        collection_run: Optional[CollectionRun] = None,
        raw_snapshot_path: Optional[str] = None
    ) -> IngestionResult:
        """
        Transforms raw records -> Validate -> Clean -> Normalize -> Deduplicate -> Database Persist.
        """
        valid_canonical_records: List[CanonicalCarListing] = []
        rejected_results: List[ValidationResult] = []
        saved_db_listings: List[CarListing] = []
        duplicate_count = 0

        # Load existing active listings in memory for duplicate candidate comparisons
        existing_db_listings = self.db.query(CarListing).filter(CarListing.is_duplicate_candidate == False).all()

        for raw_item in raw_records:
            # Stage A: Cleaning
            cleaned_dict = self.cleaner.clean_record(raw_item)

            # Stage B: Vehicle Normalization
            normalized_dict = self.normalizer.normalize_record(cleaned_dict)

            # Stage C: Schema Validation
            val_res = self.validator.validate_record(normalized_dict)
            if not val_res.is_valid or not val_res.record:
                rejected_results.append(val_res)
                continue

            canonical = val_res.record
            valid_canonical_records.append(canonical)

            # Stage D: Duplicate Similarity Scoring against existing listings
            is_duplicate = False
            best_sim_score = 0.0
            matched_listing_id = None
            dup_notes = None

            for existing in existing_db_listings:
                if existing.source != canonical.source: # Check cross-source duplicates
                    score_obj = self.deduplicator.calculate_similarity_breakdown(canonical, existing)
                    if score_obj.total_score > best_sim_score:
                        best_sim_score = score_obj.total_score
                        matched_listing_id = existing.id
                        dup_notes = f"Matched with #{existing.id} ({existing.source}) score={score_obj.total_score:.2f}: {score_obj.notes}"
                        if score_obj.is_likely_duplicate:
                            is_duplicate = True

            if is_duplicate:
                duplicate_count += 1

            # Stage E: Database Persistence
            raw_payload_str = json.dumps(raw_item.model_dump(mode="json"), default=str)
            db_listing = CarListing(
                listing_id=canonical.listing_id,
                source=canonical.source,
                listing_url=canonical.listing_url,
                brand=canonical.brand,
                model=canonical.model,
                variant=canonical.variant,
                year=canonical.year,
                fuel_type=canonical.fuel_type,
                transmission=canonical.transmission,
                km_driven=canonical.km_driven,
                engine_cc=canonical.engine_cc,
                mileage=canonical.mileage,
                owner_count=canonical.owner_count,
                city=canonical.city,
                state=canonical.state,
                seller_type=canonical.seller_type,
                listed_price=canonical.listed_price,
                date_collected=canonical.date_collected,
                is_duplicate_candidate=is_duplicate,
                duplicate_similarity=best_sim_score if best_sim_score > 0 else None,
                duplicate_of_id=matched_listing_id if is_duplicate else None,
                duplicate_notes=dup_notes if is_duplicate else None,
                raw_payload=raw_payload_str,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            self.db.add(db_listing)
            saved_db_listings.append(db_listing)

        self.db.commit()

        # Stage F: Quality Report Generation
        quality_report = self.reporter.generate_report(
            source_name=source_name,
            total_collected=len(raw_records),
            valid_records=valid_canonical_records,
            rejected_results=rejected_results,
            duplicate_count=duplicate_count
        )

        # Stage G: Update Collection Run Record
        final_status = "completed" if len(rejected_results) == 0 else ("partial" if len(valid_canonical_records) > 0 else "failed")
        run_id = 0
        if collection_run:
            collection_run.completed_at = datetime.now(timezone.utc)
            collection_run.records_valid = len(valid_canonical_records)
            collection_run.records_rejected = len(rejected_results)
            collection_run.status = final_status
            self.db.commit()
            run_id = collection_run.id

        return IngestionResult(
            collection_run_id=run_id,
            source_name=source_name,
            status=final_status,
            total_collected=len(raw_records),
            valid_count=len(valid_canonical_records),
            rejected_count=len(rejected_results),
            duplicates_detected=duplicate_count,
            raw_storage_path=raw_snapshot_path,
            quality_report=quality_report,
            saved_listings=saved_db_listings
        )
