"""
Data Quality and Machine Learning Readiness Gate.
Audits transformed datasets to verify statistical viability, field completeness, and leak-free structure before model training.
"""
from typing import Dict, Any, List, Optional
import pandas as pd
from dataclasses import dataclass, field
from ..feature_engineering.features import check_target_leakage


@dataclass
class ReadinessGateReport:
    is_ready: bool
    status: str  # "READY" or "NOT READY"
    record_count: int
    min_required_records: int
    failed_checks: List[str] = field(default_factory=list)
    passed_checks: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_summary_text(self) -> str:
        lines = [
            "=" * 50,
            f"AutoValue ML Readiness Gate: {self.status}",
            "=" * 50,
            f"Available Records   : {self.record_count}",
            f"Minimum Required    : {self.min_required_records}",
            "-" * 50,
            "Passed Checks:"
        ]
        for p in self.passed_checks:
            lines.append(f"  [PASS] {p}")

        if self.failed_checks:
            lines.append("-" * 50)
            lines.append("Failed Checks / Blockers:")
            for f in self.failed_checks:
                lines.append(f"  [FAIL] {f}")

        if self.recommendations:
            lines.append("-" * 50)
            lines.append("Actionable Recommendations:")
            for r in self.recommendations:
                lines.append(f"  - {r}")

        lines.append("=" * 50)
        return "\n".join(lines)


class MLReadinessGate:
    """
    Quality gate ensuring dataset satisfies strict ML training readiness criteria.
    """

    def __init__(self, min_records: int = 50, min_unique_brands: int = 3):
        self.min_records = min_records
        self.min_unique_brands = min_unique_brands

    def evaluate(self, df: pd.DataFrame, target_col: str = "listed_price") -> ReadinessGateReport:
        passed: List[str] = []
        failed: List[str] = []
        recommendations: List[str] = []
        n_records = len(df)

        # 1. Sample size verification
        if n_records >= self.min_records:
            passed.append(f"Dataset volume check passed ({n_records} >= {self.min_records})")
        else:
            failed.append(f"Insufficient dataset volume: Only {n_records} records available (minimum {self.min_records} required for 5-fold cross-validation)")
            recommendations.append(f"Collect additional real-world listings (target: 1,000+ records) before training machine learning regression models.")

        # 2. Target existence and validity
        if target_col in df.columns:
            valid_targets = df[target_col].dropna()
            if len(valid_targets) == n_records and (valid_targets > 0).all():
                passed.append(f"Target '{target_col}' present with 100% positive non-null values")
            else:
                failed.append(f"Target '{target_col}' has null or non-positive values")
        else:
            failed.append(f"Target column '{target_col}' is missing")

        # 3. Core feature existence
        required_features = ["brand", "model", "year", "km_driven", "car_age", "km_per_year"]
        missing_features = [f for f in required_features if f not in df.columns]
        if not missing_features:
            passed.append("All essential baseline features present")
        else:
            failed.append(f"Missing essential baseline features: {missing_features}")

        # 4. Brand diversity check
        if "brand" in df.columns:
            unique_brands = df["brand"].nunique()
            if unique_brands >= self.min_unique_brands:
                passed.append(f"Brand diversity verified ({unique_brands} distinct makes)")
            else:
                failed.append(f"Low brand diversity ({unique_brands} < {self.min_unique_brands})")

        # 5. Target leakage check
        feature_cols = [c for c in df.columns if c != target_col]
        leakage = check_target_leakage(feature_cols, target_col=target_col)
        if not leakage:
            passed.append("Data leakage audit passed (no target-derived features detected)")
        else:
            failed.append(f"Target leakage detected in features: {leakage}")

        is_ready = len(failed) == 0
        status = "READY" if is_ready else "NOT READY"

        return ReadinessGateReport(
            is_ready=is_ready,
            status=status,
            record_count=n_records,
            min_required_records=self.min_records,
            failed_checks=failed,
            passed_checks=passed,
            recommendations=recommendations
        )
