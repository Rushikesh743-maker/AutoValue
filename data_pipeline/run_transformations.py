"""
AutoValue Dataset Transformation CLI Runner.
Transforms collected database listings into processed dataset and generates metadata.
"""
import sys
import os
import argparse
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.core.config import settings
from backend.app.db.session import engine, SessionLocal
from backend.app.models import CarListing
from data_pipeline.transformers.pipeline import DatasetTransformationPipeline


def run_transformations():
    print("[AutoValue Transformation] Starting Dataset Transformation Pipeline...")

    # Connect to DB or fallback SQLite
    current_engine = engine
    current_session_maker = SessionLocal
    try:
        with current_engine.connect() as conn:
            pass
    except Exception:
        sqlite_url = "sqlite:///data/autovalue.db"
        current_engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
        current_session_maker = sessionmaker(autocommit=False, autoflush=False, bind=current_engine)

    db = current_session_maker()
    pipeline = DatasetTransformationPipeline()

    raw_df = pipeline.load_from_db(db)
    db.close()

    if raw_df.empty:
        print("[AutoValue Transformation] Warning: No records found in database. Run 'python data_pipeline/run_collection.py' first.")
        return None

    processed_df, csv_path, metadata_path = pipeline.run_pipeline_and_save(raw_df)

    print(f"[AutoValue Transformation] Success!")
    print(f"  Raw records loaded      : {len(raw_df)}")
    print(f"  Processed records saved : {len(processed_df)}")
    print(f"  Processed dataset path  : {csv_path}")
    print(f"  Dataset metadata path   : {metadata_path}\n")

    # Read and print metadata summary
    with open(metadata_path, "r", encoding="utf-8") as f:
        import json
        meta = json.load(f)
        print("ML Readiness Status:")
        print(f"  Status       : {meta['ml_readiness']['status']}")
        for p in meta['ml_readiness']['passed_checks']:
            print(f"  [PASS] {p}")
        for f in meta['ml_readiness']['failed_checks']:
            print(f"  [FAIL] {f}")

    return processed_df


if __name__ == "__main__":
    run_transformations()
