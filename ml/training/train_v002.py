"""
AutoValue ML Model Training Pipeline — Clean Evaluation & Calibration.
Executes hyperparameter tuning, group-safe train/val/test partitioning, 5-Fold CV,
leakage-free model selection, dedicated calibration set residual calibration,
final held-out test evaluation, and experiment registry tracking.
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
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.model_selection import KFold, cross_val_score
from sklearn.pipeline import Pipeline

from backend.app.core.config import settings
from data_pipeline.transformers.readiness_gate import MLReadinessGate, ReadinessGateReport
from data_pipeline.feature_engineering.features import CarFeatureEngineer, check_target_leakage
from ml.features.preprocessor import create_preprocessor_pipeline, NUMERICAL_FEATURES, CATEGORICAL_FEATURES
from ml.training.split import (
    standard_train_test_split,
    duplicate_safe_train_test_split,
    duplicate_safe_train_val_test_split,
    temporal_train_test_split
)
from ml.evaluation.metrics import calculate_regression_metrics, format_metrics_table
from ml.evaluation.error_analysis import ErrorAnalyzer
from ml.evaluation.uncertainty import PredictionUncertaintyEstimator
from ml.tuning.hyperparameter_tuner import HyperparameterTuner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("autovalue.ml.train_v002")


def run_training_v002(
    processed_csv_path: Optional[str] = None,
    models_dir: Optional[str] = None,
    experiments_dir: Optional[str] = None,
    model_version: str = "v003_candidate",
    random_state: int = 42,
    allow_overwrite: bool = False
) -> Dict[str, Any]:
    """
    Executes ML training pipeline with strict separation of train, calibration/validation,
    and final held-out test data partitions. Model selection uses cross-validation MAE only;
    residual calibration uses a dedicated held-out partition; final test evaluation is performed
    strictly after freezing the pipeline and calibration bounds.
    """
    csv_path = processed_csv_path or os.path.join(settings.PROCESSED_DATA_DIR, "autovalue_processed.csv")
    output_models_dir = models_dir or settings.MODELS_DIR
    exp_dir = experiments_dir or os.path.join(os.path.dirname(__file__), "..", "experiments")

    os.makedirs(output_models_dir, exist_ok=True)
    os.makedirs(exp_dir, exist_ok=True)

    # Immutability safeguard for production v002 artifact
    if model_version == "v002" and not allow_overwrite:
        v002_meta = os.path.join(output_models_dir, "metadata_v002.json")
        if os.path.exists(v002_meta):
            logger.warning(
                "Active production model v002 is immutable. Storing revised outputs in candidate version 'v003_candidate'."
            )
            model_version = "v003_candidate"

    print("\n" + "=" * 70)
    print(f"AutoValue Model Training Pipeline — Candidate {model_version}")
    print("=" * 70)

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Processed dataset not found at {csv_path}")

    df = pd.read_csv(csv_path)
    print(f"Loaded processed dataset: {len(df)} records from {csv_path}")

    # 1. Feature Engineering
    engineer = CarFeatureEngineer()
    engineered_df = engineer.transform(df)

    # 2. ML Readiness Gate Evaluation
    min_rec = 500 if len(engineered_df) >= 500 else 50
    min_b = 5 if len(engineered_df) >= 500 else 3
    gate = MLReadinessGate(min_records=min_rec, min_unique_brands=min_b)
    readiness_report: ReadinessGateReport = gate.evaluate(engineered_df, target_col="listed_price")
    print("\n" + readiness_report.to_summary_text() + "\n")

    if not readiness_report.is_ready:
        raise ValueError(f"ML readiness gate failed: {readiness_report.failed_checks}")

    # Leakage Audit on feature columns
    feature_cols = [c for c in engineered_df.columns if c not in [
        "id", "listing_id", "listing_url", "raw_payload", "is_outlier", "outlier_reasons",
        "is_duplicate_candidate", "duplicate_similarity", "duplicate_of_id", "duplicate_notes",
        "date_collected", "listed_price"
    ]]
    leakage = check_target_leakage(feature_cols, target_col="listed_price")
    if leakage:
        raise ValueError(f"Target leakage detected: {leakage}")

    # 3. Establish Disjoint Partitions (Train / Calibration / Held-Out Test)
    # 70% Train, 15% Validation/Calibration, 15% Final Test with group-aware cluster integrity
    train_df, val_df, test_df = duplicate_safe_train_val_test_split(
        engineered_df,
        val_size=0.15,
        test_size=0.15,
        random_state=random_state
    )

    print(f"Dataset Partitioning (Group-Aware Duplicate-Safe Split):")
    print(f"  Training Split    : {len(train_df)} records ({(len(train_df)/len(df)*100):.1f}%)")
    print(f"  Calibration Split : {len(val_df)} records ({(len(val_df)/len(df)*100):.1f}%)")
    print(f"  Held-Out Test Set : {len(test_df)} records ({(len(test_df)/len(df)*100):.1f}%)")

    X_train = train_df[NUMERICAL_FEATURES + CATEGORICAL_FEATURES].copy()
    y_train = train_df["listed_price"].copy()

    X_val = val_df[NUMERICAL_FEATURES + CATEGORICAL_FEATURES].copy()
    y_val = val_df["listed_price"].copy()

    X_test = test_df[NUMERICAL_FEATURES + CATEGORICAL_FEATURES].copy()
    y_test = test_df["listed_price"].copy()

    # 4. Hyperparameter Tuning (Fitted strictly on Training partition)
    print("\nRunning Hyperparameter Tuning on Training Split (5-Fold CV)...", flush=True)
    cv_folds = 5 if len(train_df) >= 30 else 3
    tuner = HyperparameterTuner(cv_folds=cv_folds, n_iter=8, random_state=random_state)
    
    tuned_rf, best_rf_params, best_rf_cv_mae = tuner.tune_random_forest(X_train, y_train)
    tuned_hgb, best_hgb_params, best_hgb_cv_mae = tuner.tune_hist_gradient_boosting(X_train, y_train)

    # 5. Model Candidate Definition
    model_candidates: Dict[str, Tuple[Any, Dict[str, Any]]] = {
        "Linear Regression (Baseline)": (LinearRegression(), {}),
        "v001 Random Forest (Baseline)": (RandomForestRegressor(n_estimators=100, max_depth=10, random_state=random_state), {"n_estimators": 100, "max_depth": 10}),
        "Tuned Random Forest Candidate": (tuned_rf, best_rf_params),
        "Tuned HistGradientBoosting Candidate": (tuned_hgb, best_hgb_params)
    }

    # Add XGBoost candidate if installed
    try:
        from xgboost import XGBRegressor
        xgb = XGBRegressor(n_estimators=150, max_depth=6, learning_rate=0.06, random_state=random_state, verbosity=0)
        model_candidates["XGBoost Regressor Candidate"] = (xgb, {"n_estimators": 150, "max_depth": 6, "learning_rate": 0.06})
    except ImportError:
        pass

    cv_kfold = KFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    fitted_pipelines: Dict[str, Pipeline] = {}
    candidate_cv_results: Dict[str, Dict[str, Any]] = {}

    print(f"\nEvaluating Model Candidates via {cv_folds}-Fold Cross Validation on Training Data...")
    for name, (model, params) in model_candidates.items():
        pipe = Pipeline([
            ("preprocessor", create_preprocessor_pipeline()),
            ("regressor", model)
        ])

        # Cross Validation evaluated strictly on training split
        cv_scores = cross_val_score(pipe, X_train, y_train, cv=cv_kfold, scoring="neg_mean_absolute_error")
        cv_mae_mean = float(-cv_scores.mean())
        cv_mae_std = float(cv_scores.std())

        cv_r2_scores = cross_val_score(pipe, X_train, y_train, cv=cv_kfold, scoring="r2")
        cv_r2_mean = float(cv_r2_scores.mean())
        cv_r2_std = float(cv_r2_scores.std())

        # Fit on full training split
        pipe.fit(X_train, y_train)
        fitted_pipelines[name] = pipe

        # Validation set evaluation (separate from fitting)
        val_preds = pipe.predict(X_val) if len(X_val) > 0 else np.array([])
        val_metrics = calculate_regression_metrics(y_val, val_preds) if len(val_preds) > 0 else {}

        candidate_cv_results[name] = {
            "cv_mae_mean": round(cv_mae_mean, 2),
            "cv_mae_std": round(cv_mae_std, 2),
            "cv_r2_mean": round(cv_r2_mean, 4),
            "cv_r2_std": round(cv_r2_std, 4),
            "val_mae": val_metrics.get("mae"),
            "val_r2": val_metrics.get("r2"),
            "hyperparameters": params
        }
        print(f"  {name:36s} | CV MAE: INR {cv_mae_mean:,.0f} (+/- {cv_mae_std:,.0f}) | Val MAE: INR {val_metrics.get('mae', 0):,.0f}")

    # 6. Model Selection (Strictly on Cross-Validation score on Training Split, zero test leakage)
    sorted_models = sorted(candidate_cv_results.items(), key=lambda x: x[1]["cv_mae_mean"])
    best_model_name, best_cv_info = sorted_models[0]
    best_pipeline = fitted_pipelines[best_model_name]

    print("\n" + "=" * 70)
    print(f"Selected Candidate Model: {best_model_name}")
    print(f"Selection Criterion: Lowest Training CV MAE = INR {best_cv_info['cv_mae_mean']:,.0f} (+/- {best_cv_info['cv_mae_std']:,.0f})")
    print("=" * 70)

    # 7. Prediction Uncertainty Calibration (Fitted strictly on Dedicated Calibration Split)
    uncertainty_estimator = PredictionUncertaintyEstimator()
    if len(X_val) > 0:
        y_val_pred = best_pipeline.predict(X_val)
        uncertainty_stats = uncertainty_estimator.fit_residuals(
            y_val.values,
            y_val_pred,
            calibration_method="dedicated_calibration_split"
        )
    else:
        # Fallback to out-of-fold training predictions if dataset is too small
        from sklearn.model_selection import cross_val_predict
        y_oof_pred = cross_val_predict(best_pipeline, X_train, y_train, cv=cv_kfold)
        uncertainty_stats = uncertainty_estimator.fit_residuals(
            y_train.values,
            y_oof_pred,
            calibration_method="out_of_fold_cv"
        )

    print(f"Uncertainty Calibration on {uncertainty_stats['calibration_sample_count']} samples ({uncertainty_stats['calibration_method']}):")
    print(f"  Empirical 80% Residual Bound : INR {uncertainty_stats['residual_q80']:,.0f}")
    print(f"  Empirical 90% Residual Bound : INR {uncertainty_stats['residual_q90']:,.0f}")

    # 8. Final Held-Out Test Set Evaluation (Evaluated ONLY after model and calibration are frozen)
    print("\nEvaluating Frozen Pipeline on Held-Out Test Set (Unbiased Final Evaluation)...")
    final_test_results: Dict[str, Dict[str, Any]] = {}
    for name, pipe in fitted_pipelines.items():
        y_pred_test = pipe.predict(X_test)
        test_metrics = calculate_regression_metrics(y_test, y_pred_test)
        test_metrics.update(candidate_cv_results[name])
        final_test_results[name] = test_metrics

    best_test_metrics = final_test_results[best_model_name]
    print(f"Final Test Metrics for {best_model_name}:")
    print(f"  Test MAE       : INR {best_test_metrics['mae']:,.0f}")
    print(f"  Test RMSE      : INR {best_test_metrics['rmse']:,.0f}")
    print(f"  Test R²        : {best_test_metrics['r2']:.4f}")
    print(f"  Test Median AE : INR {best_test_metrics['median_ae']:,.0f}")

    # Error & Segment Analysis on test predictions
    error_analyzer = ErrorAnalyzer(min_segment_size=5)
    y_test_pred = best_pipeline.predict(X_test)
    error_report = error_analyzer.run_full_error_analysis(y_test.values, y_test_pred, test_df)

    # 9. Persist Candidate Artifacts (Separate from Active v002)
    model_artifact_path = os.path.join(output_models_dir, f"model_{model_version}.joblib")
    prep_artifact_path = os.path.join(output_models_dir, f"preprocessor_{model_version}.joblib")
    meta_artifact_path = os.path.join(output_models_dir, f"metadata_{model_version}.json")

    joblib.dump(best_pipeline.named_steps["regressor"], model_artifact_path)
    joblib.dump(best_pipeline.named_steps["preprocessor"], prep_artifact_path)

    metadata_payload = {
        "model_version": model_version,
        "selected_model": best_model_name,
        "dataset_version": "v0.3",
        "status": "candidate",
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "random_state": random_state,
        "total_records": len(df),
        "train_records": len(train_df),
        "calibration_records": len(val_df),
        "test_records": len(test_df),
        "cv_folds": cv_folds,
        "evaluation_strategy": "duplicate_safe_train_val_test_split",
        "model_selection_criterion": "lowest_training_cv_mae",
        "hyperparameters": best_test_metrics["hyperparameters"],
        "metrics_test": best_test_metrics,
        "uncertainty_calibration": uncertainty_stats,
        "all_model_comparison": final_test_results,
        "error_analysis_summary": {
            "by_price_band": error_report["by_price_band"],
            "by_fuel": error_report["by_fuel"],
            "by_transmission": error_report["by_transmission"],
            "by_age_band": error_report["by_age_band"],
            "by_km_band": error_report["by_km_band"]
        },
        "model_artifact": model_artifact_path,
        "preprocessor_artifact": prep_artifact_path
    }

    with open(meta_artifact_path, "w", encoding="utf-8") as f:
        json.dump(metadata_payload, f, indent=2)

    # 10. Experiments Registry Tracking (Record candidate without mutating active v002)
    registry_file = os.path.join(exp_dir, "experiments_registry.json")
    registry: List[Dict[str, Any]] = []
    if os.path.exists(registry_file):
        try:
            with open(registry_file, "r", encoding="utf-8") as f:
                registry = json.load(f)
        except Exception:
            registry = []

    # Check if this model_version already exists in registry
    existing_idx = next((i for i, r in enumerate(registry) if r.get("model_version") == model_version), None)
    registry_entry = {
        "model_version": model_version,
        "dataset_version": "v0.3",
        "status": "candidate",
        "selected_model": best_model_name,
        "metrics": best_test_metrics,
        "training_timestamp": metadata_payload["training_timestamp"],
        "model_artifact": model_artifact_path,
        "preprocessor_artifact": prep_artifact_path,
        "metadata_path": meta_artifact_path
    }

    if existing_idx is not None:
        registry[existing_idx] = registry_entry
    else:
        registry.append(registry_entry)

    with open(registry_file, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

    print(f"\nSuccessfully created and saved candidate model artifacts ({model_version}):")
    print(f"  Model        : {model_artifact_path}")
    print(f"  Preprocessor : {prep_artifact_path}")
    print(f"  Metadata     : {meta_artifact_path}")
    print(f"  Registry     : {registry_file}\n")

    return {
        "status": "SUCCESS",
        "model_version": model_version,
        "selected_model": best_model_name,
        "metrics": best_test_metrics,
        "candidate_cv_results": candidate_cv_results,
        "final_test_results": final_test_results,
        "error_report": error_report,
        "uncertainty_stats": uncertainty_stats,
        "metadata": metadata_payload
    }


if __name__ == "__main__":
    run_training_v002()
