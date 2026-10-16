"""
Unit tests for DataQualityReporter and quality metric computation.
"""
import pytest
from datetime import datetime, timezone
from data_pipeline.schemas.canonical import CanonicalCarListing
from data_pipeline.validators.validator import ValidationResult
from data_pipeline.validators.quality_report import DataQualityReporter


class TestQualityReport:
    def test_generate_report_completeness_and_rejection_metrics(self):
        reporter = DataQualityReporter()

        valid_sample = [
            CanonicalCarListing(
                listing_id="val-1",
                source="test_src",
                brand="Hyundai",
                model="Creta",
                variant="1.5 CRDi SX",
                year=2021,
                listed_price=1350000.0,
                km_driven=35000,
                fuel_type="Diesel",
                transmission="Manual",
                city="Bengaluru"
            ),
            CanonicalCarListing(
                listing_id="val-2",
                source="test_src",
                brand="Maruti Suzuki",
                model="Swift",
                variant=None, # Missing variant
                year=2019,
                listed_price=600000.0,
                km_driven=40000,
                fuel_type="Petrol",
                transmission=None, # Missing transmission
                city=None # Missing city
            )
        ]

        rejected_sample = [
            ValidationResult(
                is_valid=False,
                errors=["year: Must be after 1990", "listed_price: Must be positive"],
                raw_input={"brand": "Unknown"}
            )
        ]

        report = reporter.generate_report(
            source_name="test_src",
            total_collected=3,
            valid_records=valid_sample,
            rejected_results=rejected_sample,
            duplicate_count=1
        )

        assert report.total_records == 3
        assert report.valid_records == 2
        assert report.rejected_records == 1
        assert report.duplicate_candidates_count == 1

        # Check completeness percentages
        assert report.field_completeness["brand"] == 100.0
        assert report.field_completeness["model"] == 100.0
        assert report.field_completeness["variant"] == 50.0
        assert report.field_completeness["city"] == 50.0

        # Check summary formatting output
        summary = report.to_summary_text()
        assert "AutoValue Data Quality Report" in summary
        assert "Records Collected : 3" in summary
        assert "Valid Records     : 2" in summary
