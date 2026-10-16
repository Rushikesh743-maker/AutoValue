"""
Data Quality Report generator computing empirical completeness and integrity metrics.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field
from ..schemas.canonical import CanonicalCarListing, RawCarListing
from .validator import ValidationResult


@dataclass
class QualityReport:
    """Encapsulates empirical data quality metrics for a collection run."""
    source_name: str
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_records: int = 0
    valid_records: int = 0
    rejected_records: int = 0
    rejection_reasons: Dict[str, int] = field(default_factory=dict)
    field_completeness: Dict[str, float] = field(default_factory=dict)
    duplicate_candidates_count: int = 0

    def to_summary_text(self) -> str:
        """Renders human-readable formatted summary report."""
        valid_pct = (self.valid_records / self.total_records * 100.0) if self.total_records > 0 else 0.0
        lines = [
            "=" * 50,
            f"AutoValue Data Quality Report: {self.source_name}",
            f"Timestamp: {self.generated_at.isoformat()}",
            "=" * 50,
            f"Records Collected : {self.total_records}",
            f"Valid Records     : {self.valid_records} ({valid_pct:.1f}%)",
            f"Rejected Records  : {self.rejected_records}",
            f"Duplicate Candidates: {self.duplicate_candidates_count}",
            "-" * 50,
            "Field Completeness (Valid Records):"
        ]
        for field_name, pct in sorted(self.field_completeness.items()):
            lines.append(f"  {field_name:<16}: {pct:>5.1f}%")

        if self.rejection_reasons:
            lines.append("-" * 50)
            lines.append("Rejection Reasons Breakdown:")
            for reason, count in sorted(self.rejection_reasons.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  - {reason}: {count} records")

        lines.append("=" * 50)
        return "\n".join(lines)


class DataQualityReporter:
    """
    Computes field completeness percentages and error distributions across real collected records.
    """

    CANONICAL_FIELDS = [
        "brand",
        "model",
        "variant",
        "year",
        "listed_price",
        "km_driven",
        "fuel_type",
        "transmission",
        "city",
        "state",
        "owner_count",
        "listing_url"
    ]

    def generate_report(
        self,
        source_name: str,
        total_collected: int,
        valid_records: List[CanonicalCarListing],
        rejected_results: List[ValidationResult],
        duplicate_count: int = 0
    ) -> QualityReport:
        n_valid = len(valid_records)
        n_rejected = len(rejected_results)
        
        # 1. Compute field completeness on valid records
        completeness: Dict[str, float] = {}
        if n_valid > 0:
            for f in self.CANONICAL_FIELDS:
                non_null_count = sum(1 for r in valid_records if getattr(r, f, None) not in [None, ""])
                completeness[f] = round((non_null_count / n_valid) * 100.0, 1)
        else:
            for f in self.CANONICAL_FIELDS:
                completeness[f] = 0.0

        # 2. Compute rejection reasons breakdown
        reasons_map: Dict[str, int] = {}
        for rej in rejected_results:
            if rej.errors:
                for err in rej.errors:
                    reasons_map[err] = reasons_map.get(err, 0) + 1
            else:
                reasons_map["Unknown validation failure"] = reasons_map.get("Unknown validation failure", 0) + 1

        return QualityReport(
            source_name=source_name,
            total_records=total_collected,
            valid_records=n_valid,
            rejected_records=n_rejected,
            rejection_reasons=reasons_map,
            field_completeness=completeness,
            duplicate_candidates_count=duplicate_count
        )
