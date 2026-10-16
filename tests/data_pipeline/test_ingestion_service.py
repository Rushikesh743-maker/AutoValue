"""
Integration tests for IngestionService verifying database persistence, collection runs, and duplicate flagging.
"""
import pytest
import os
import json
from sqlalchemy.orm import Session
from data_pipeline.services.ingestion_service import IngestionService
from data_pipeline.collectors.open_research_collector import OpenResearchCollector
from data_pipeline.collectors.dealer_feed_collector import DealerFeedCollector
from data_pipeline.collectors.community_portal_collector import CommunityPortalCollector
from backend.app.models.listing import CarListing
from backend.app.models.source import Source
from backend.app.models.collection_run import CollectionRun


class TestIngestionService:
    def test_execute_collection_with_open_research_collector(self, db_session: Session, tmp_path):
        service = IngestionService(db=db_session, raw_storage_dir=str(tmp_path))
        collector = OpenResearchCollector()

        result = service.execute_collection(collector, limit=10)

        assert result.status in ["completed", "partial"]
        assert result.total_collected > 0
        assert result.valid_count > 0
        assert result.collection_run_id > 0
        assert result.raw_storage_path is not None
        assert os.path.exists(result.raw_storage_path)

        # Verify DB records
        db_source = db_session.query(Source).filter(Source.name == "open_research").first()
        assert db_source is not None

        db_run = db_session.query(CollectionRun).filter(CollectionRun.id == result.collection_run_id).first()
        assert db_run is not None
        assert db_run.status == result.status
        assert db_run.records_valid == result.valid_count

        db_listings = db_session.query(CarListing).filter(CarListing.source == "open_research").all()
        assert len(db_listings) == result.valid_count
        assert all(l.raw_payload is not None for l in db_listings)

    def test_cross_source_duplicate_detection_during_ingestion(self, db_session: Session, tmp_path):
        service = IngestionService(db=db_session, raw_storage_dir=str(tmp_path))

        # First ingest dealer_feed
        res_a = service.execute_collection(DealerFeedCollector(), limit=5)
        assert res_a.valid_count > 0

        # Next ingest community_portal containing matching cross-posted vehicle
        res_b = service.execute_collection(CommunityPortalCollector(), limit=5)
        assert res_b.valid_count > 0

        # Check if duplicate candidate was flagged without deleting records
        duplicates = db_session.query(CarListing).filter(CarListing.is_duplicate_candidate == True).all()
        assert len(duplicates) >= 1
        assert duplicates[0].duplicate_similarity is not None
        assert duplicates[0].duplicate_of_id is not None
