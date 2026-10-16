"""
AutoValue ML Model Training & Cross-Validation Runner.
Trains baseline and tree-based regression models with strict readiness gate checking,
leakage protection, and versioned artifact persistence.
"""
import sys
import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import joblib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sklearn.linear_model import LinearRegression
from sklearn.ensemble import (
    RandomForestRegressor,
    GradientBoostingRegressor,
    HistGradientBoostingRegressor
)
from sklearn.model_selection import KFold, cross_val_score
from sklearn.pipeline import Pipeline

from backend.app.core.config import settings
from data_pipeline.transformers.readiness_gate import MLReadinessGate, ReadinessGateReport
from data_pipeline.feature_engineering.features import CarFeatureEngineer, check_target_leakage
from ml.features.preprocessor import create_preprocessor_pipeline, NUMERICAL_FEATURES, CATEGORICAL_FEATURES
from ml.training.split import duplicate_safe_train_test_split
from ml.evaluation.metrics import calculate_regression_metrics, format_metrics_table

logger = logging.getLogger("autovalue.ml.train")


def train_and_evaluate_models(
    processed_csv_path: Optional[str] = None,
    models_dir: Optional[str] = None,
    experiments_dir: Optional[str] = None,
    model_version: str = "v001",
    random_state: int = 42
) -> Dict[str, Any]:
    """
    Executes end-to-end ML training workflow if dataset satisfies ML readiness gate.
    """
    csv_path = processed_csv_path or os.path.join(settings.PROCESSED_DATA_DIR, "autovalue_processed.csv")
    output_models_dir = models_dir or settings.MODELS_DIR
    exp_dir = experiments_dir or os.path.join(os.path.dirname(__file__), "..", "experiments")
    
    os.makedirs(output_models_dir, exist_ok=True)
    os.makedirs(exp_dir, exist_ok=True)

    print("\n" + "=" * 60)
    print("AutoValue Machine Learning Training Pipeline")
    print("=" * 60)

    if not os.path.exists(csv_path):
        print(f"[AutoValue ML] Error: Processed dataset not found at {csv_path}. Run data_pipeline/run_transformations.py first.")
        return {"status": "FAILED", "reason": f"File not found: {csv_path}"}

    df = pd.read_csv(csv_path)
    print(f"[AutoValue ML] Loaded processed dataset: {len(df)} records from {csv_path}")

    # 1. Feature Engineering & Leakage Protection
    engineer = CarFeatureEngineer()
    engineered_df = engineer.transform(df)

    # 2. Evaluate ML Readiness Gate
    gate = MLReadinessGate(min_records=50, min_unique_brands=3)
    readiness_report: ReadinessGateReport = gate.evaluate(engineered_df, target_col="listed_price")

    print("\n" + readiness_report.to_summary_text() + "\n")

    if not readiness_report.is_ready:
        print("[AutoValue ML] BLOCKED: Dataset does not satisfy ML readiness requirements. Final models will NOT be trained.")
        return {
            "status": "NOT_READY",
            "readiness_report": readiness_report,
            "models_trained": []
        }

    # Verify no target leakage in independent features
    feature_cols = [c for c in engineered_df.columns if c not in ["id", "listing_id", "listing_url", "raw_payload", "is_outlier", "outlier_reasons", "is_duplicate_candidate", "duplicate_similarity", "duplicate_of_id", "duplicate_notes", "date_collected", "listed_price"]]
    leakage = check_target_leakage(feature_cols, target_col="listed_price")
    if leakage:
        raise ValueError(f"Target leakage detected: {leakage}")

    # 3. Duplicate-Safe Train/Test Partition (80/20)
    train_df, test_df = duplicate_safe_train_test_split(engineered_df, test_size=0.20, random_state=random_state)
    print(f"[AutoValue ML] Dataset Split:")
    print(f"  Training Split : {len(train_df)} records ({(len(train_df)/len(df)*100):.1f}%)")
    print(f"  Test Split     : {len(test_df)} records ({(len(test_df)/len(df)*100):.1f}%)")

    X_train = train_df[NUMERICAL_FEATURES + CATEGORICAL_FEATURES].copy()
    y_train = train_df["listed_price"].copy()

    X_test = test_df[NUMERICAL_FEATURES + CATEGORICAL_FEATURES].copy()
    y_test = test_df["listed_price"].copy()

    # 4. Define Model Candidates
    model_candidates: Dict[str, Any] = {
        "Linear Regression": LinearRegression(),
        "Random Forest": RandomForestRegressor(n_estimators=100, max_depth=10, random_state=random_state),
        "Gradient Boosting": GradientBoostingRegressor(n_estimators=100, learning_rate=0.08, max_depth=4, random_state=random_state),
        "HistGradientBoosting": HistGradientBoostingRegressor(max_iter=100, random_state=random_state)
    }

    # Try optional XGBoost if installed
    try:
        from xgboost import XGBRegressor
        model_candidates["XGBoost"] = XGBRegressor(n_estimators=100, max_depth=4, learning_rate=0.08, random_state=random_state, verbosity=0)
    except ImportError:
        logger.info("XGBoost not available; proceeding with scikit-learn tree models.")

    # 5. Cross-Validation & Test Set Evaluation
    results: Dict[str, Dict[str, Any]] = {}
    fitted_pipelines: Dict[str, Pipeline] = {}
    cv_folds = 5 if len(train_df) >= 30 else 3

    print(f"\n[AutoValue ML] Training & Evaluating {len(model_candidates)} Models with {cv_folds}-Fold Cross-Validation...")

    for name, model in model_candidates.items():
        preprocessor = create_preprocessor_pipeline()
        pipe = Pipeline(steps=[
            ("preprocessor", preprocessor),
            ("regressor", model)
        ])

        # K-Fold CV on training split only (evaluating negative MAE)
        try:
            cv_scores = cross_val_score(pipe, X_train, y_train, cv=KFold(n_splits=cv_folds, shuffle=True, random_state=random_state), scoring="neg_mean_absolute_error")
            cv_mae_mean = float(-cv_scores.mean())
            cv_mae_std = float(cv_scores.std())
        except Exception as e:
            logger.warning(f"Cross-validation failed for {name}: {e}")
            cv_mae_mean = float("nan")
            cv_mae_std = float("nan")

        # Fit on full training split
        pipe.fit(X_train, y_train)
        fitted_pipelines[name] = pipe

        results[name] = {
            "cv_mae_mean": round(cv_mae_mean, 2),
            "cv_mae_std": round(cv_mae_std, 2)
        }

    # 6. Model Selection (Strictly on Cross-Validation score, no test set leakage)
    # Select best model candidate by lowest training CV MAE
    sorted_models = sorted(results.items(), key=lambda x: x[1]["cv_mae_mean"] if not np.isnan(x[1]["cv_mae_mean"]) else float("inf"))
    best_model_name, best_cv_info = sorted_models[0]

    # 7. Final Test Set Evaluation (Evaluated on selected model only after selection is frozen)
    for name, pipe in fitted_pipelines.items():
        y_pred = pipe.predict(X_test)
        metrics = calculate_regression_metrics(y_test, y_pred)
        results[name].update(metrics)

    best_metrics = results[best_model_name]

    print("\n" + "=" * 60)
    print("Model Evaluation Comparison Table (Held-Out Test Set):")
    print("=" * 60)
    print(format_metrics_table(results))
    print(f"\n[AutoValue ML] Selected Best Production Candidate (via CV): {best_model_name}")
    print(f"  CV MAE   : INR {best_cv_info['cv_mae_mean']:,.0f} (+/- {best_cv_info['cv_mae_std']:,.0f})")
    print(f"  Test MAE : INR {best_metrics['mae']:,.0f}")
    print(f"  Test R²  : {best_metrics['r2']:.4f}\n")

    # 7. Persist Versioned Artifacts
    best_pipeline = fitted_pipelines[best_model_name]
    model_artifact_path = os.path.join(output_models_dir, f"model_{model_version}.joblib")
    prep_artifact_path = os.path.join(output_models_dir, f"preprocessor_{model_version}.joblib")
    metadata_path = os.path.join(output_models_dir, f"metadata_{model_version}.json")

    # Save fitted regressor and fitted preprocessor
    joblib.dump(best_pipeline.named_steps["regressor"], model_artifact_path)
    joblib.dump(best_pipeline.named_steps["preprocessor"], prep_artifact_path)

    metadata = {
        "model_version": model_version,
        "selected_model": best_model_name,
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "random_state": random_state,
        "total_records": len(df),
        "train_records": len(train_df),
        "test_records": len(test_df),
        "cv_folds": cv_folds,
        "target_col": "listed_price",
        "numerical_features": NUMERICAL_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "metrics_test": best_metrics,
        "all_model_comparison": results,
        "model_artifact": model_artifact_path,
        "preprocessor_artifact": prep_artifact_path
    }

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    # 8. Append to Experiments Registry
    registry_file = os.path.join(exp_dir, "experiments_registry.json")
    registry: List[Dict[str, Any]] = []
    if os.path.exists(registry_file):
        try:
            with open(registry_file, "r", encoding="utf-8") as f:
                registry = json.load(f)
        except Exception:
            registry = []

    registry.append(metadata)
    with open(registry_file, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

    print(f"[AutoValue ML] Persisted Model Artifact        : {model_artifact_path}")
    print(f"[AutoValue ML] Persisted Preprocessor Artifact : {prep_artifact_path}")
    print(f"[AutoValue ML] Persisted Metadata Artifact     : {metadata_path}")
    print(f"[AutoValue ML] Logged Experiment to Registry   : {registry_file}")

    return {
        "status": "SUCCESS",
        "selected_model": best_model_name,
        "metrics": best_metrics,
        "comparison": results,
        "metadata_path": metadata_path,
        "model_path": model_artifact_path,
        "preprocessor_path": prep_artifact_path
    }


if __name__ == "__main__":
    train_and_evaluate_models()
