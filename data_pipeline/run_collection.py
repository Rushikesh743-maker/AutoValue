"""
AutoValue Data Collection & Ingestion CLI Runner.
Provides safe, controlled execution of data collectors with rate limiting and quality reporting.
"""
import argparse
import sys
import os
from datetime import datetime

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.db.session import SessionLocal, engine
from backend.app.db.base import Base
# Load models
from backend.app.models import CarListing, Source, CollectionRun
from data_pipeline.collectors.open_research_collector import OpenResearchCollector
from data_pipeline.collectors.dealer_feed_collector import DealerFeedCollector
from data_pipeline.collectors.community_portal_collector import CommunityPortalCollector
from data_pipeline.collectors.commercial_api_collector import CommercialApiCollector
from data_pipeline.services.ingestion_service import IngestionService


def run_pipeline(source_type: str = "all", limit: int = 50, verbose: bool = True):
    # Attempt connecting to configured DB, with transparent fallback to local SQLite if PostgreSQL is offline
    current_engine = engine
    current_session_maker = SessionLocal

    try:
        with current_engine.connect() as conn:
            pass
    except Exception as e:
        print(f"[AutoValue Pipeline] PostgreSQL not detected on localhost ({e}). Using local storage fallback (data/autovalue.db)...")
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        os.makedirs("data", exist_ok=True)
        sqlite_url = "sqlite:///data/autovalue.db"
        current_engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
        current_session_maker = sessionmaker(autocommit=False, autoflush=False, bind=current_engine)

    # Ensure tables exist
    Base.metadata.create_all(bind=current_engine)
    db = current_session_maker()

    ingestion_service = IngestionService(db=db)


    collectors = []
    if source_type in ["open_research", "all"]:
        collectors.append(OpenResearchCollector())
    if source_type in ["dealer_feed", "all"]:
        collectors.append(DealerFeedCollector())
    if source_type in ["community_portal", "all"]:
        collectors.append(CommunityPortalCollector())
    if source_type in ["commercial_api", "all"]:
        collectors.append(CommercialApiCollector())

    print(f"\n[AutoValue Pipeline] Starting Collection Run at {datetime.utcnow().isoformat()}")
    print(f"[AutoValue Pipeline] Target Limit: {limit} records per source\n")

    results = []
    for col in collectors:
        print(f"--- Ingesting Source: {col.source_name} ---")
        try:
            res = ingestion_service.execute_collection(col, limit=limit)
            results.append(res)
            print(f"  Status       : {res.status.upper()}")
            print(f"  Collected    : {res.total_collected}")
            print(f"  Valid Saved  : {res.valid_count}")
            print(f"  Rejected     : {res.rejected_count}")
            print(f"  Duplicates   : {res.duplicates_detected}")
            if res.raw_storage_path:
                print(f"  Raw Snapshot : {res.raw_storage_path}")
            if verbose:
                print(res.quality_report.to_summary_text())
            print()
        except Exception as e:
            print(f"  [ERROR] Ingestion failed for {col.source_name}: {e}\n")

    db.close()
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoValue Data Collection Pipeline Runner")
    parser.add_argument("--source", type=str, default="all", choices=["all", "open_research", "dealer_feed", "community_portal", "commercial_api"], help="Source to collect from")
    parser.add_argument("--limit", type=int, default=50, help="Max records per source")
    parser.add_argument("--quiet", action="store_true", help="Suppress detailed quality reports")
    args = parser.parse_args()

    run_pipeline(source_type=args.source, limit=args.limit, verbose=not args.quiet)
