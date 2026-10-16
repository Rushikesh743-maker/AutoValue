"""
AutoValue Controlled v003 Candidate Evaluation Script.
Executes an end-to-end reproducible, leakage-free candidate training and evaluation protocol
preserving all existing production and candidate artifacts.
"""
import os
import sys
import json
import time
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List

# Ensure UTF-8 stdout on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure repository root is on path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

import pandas as pd
import numpy as np
import joblib
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.model_selection import KFold, cross_val_score
from sklearn.pipeline import Pipeline
import xgboost as xgb

from data_pipeline.transformers.readiness_gate import MLReadinessGate
from data_pipeline.feature_engineering.features import CarFeatureEngineer, check_target_leakage
from ml.features.preprocessor import create_preprocessor_pipeline, NUMERICAL_FEATURES, CATEGORICAL_FEATURES
from ml.training.split import duplicate_safe_train_val_test_split, build_vehicle_clusters
from ml.evaluation.metrics import calculate_regression_metrics
from ml.evaluation.uncertainty import PredictionUncertaintyEstimator
from ml.tuning.hyperparameter_tuner import HyperparameterTuner
from ml.evaluation.error_analysis import ErrorAnalyzer


def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def run_controlled_candidate_evaluation():
    start_time = time.time()
    random_state = 42
    output_dir = os.path.join(REPO_ROOT, "models", "candidates", "v003_controlled_eval")
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 80)
    print("AutoValue Controlled v003 Candidate Evaluation Protocol")
    print("=" * 80)
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Isolated Candidate Output Directory: {output_dir}")

    # Record baseline hashes to guarantee immutability
    prod_files = {
        "prod_model_v002": os.path.join(REPO_ROOT, "models", "model_v002.joblib"),
        "prod_prep_v002": os.path.join(REPO_ROOT, "models", "preprocessor_v002.joblib"),
        "prod_meta_v002": os.path.join(REPO_ROOT, "models", "metadata_v002.json"),
        "prev_candidate_model": os.path.join(REPO_ROOT, "models", "candidates", "v003_eval", "model_v003_candidate.joblib"),
        "prev_candidate_prep": os.path.join(REPO_ROOT, "models", "candidates", "v003_eval", "preprocessor_v003_candidate.joblib"),
        "prev_candidate_meta": os.path.join(REPO_ROOT, "models", "candidates", "v003_eval", "metadata_v003_candidate.json"),
    }
    baseline_hashes = {}
    for k, p in prod_files.items():
        if os.path.exists(p):
            baseline_hashes[k] = compute_sha256(p)
            print(f"[Baseline Hash] {k:25s}: {baseline_hashes[k]}")

    # STEP 1: Preflight Verification
    print("\n--- STEP 1: PREFLIGHT VERIFICATION ---")
    data_path = os.path.join(REPO_ROOT, "data", "processed", "autovalue_processed.csv")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Processed dataset not found at {data_path}")

    dataset_hash = compute_sha256(data_path)
    df = pd.read_csv(data_path)
    print(f"Dataset path: {data_path}")
    print(f"Dataset SHA-256: {dataset_hash}")
    print(f"Total raw records loaded: {len(df)}")
    print("Source distribution:")
    for src, cnt in df["source"].value_counts().items():
        print(f"  - {src}: {cnt} ({cnt/len(df)*100:.2f}%)")

    # Feature Engineering
    engineer = CarFeatureEngineer(reference_year=2024)
    engineered_df = engineer.transform(df)

    # Readiness Gate
    gate = MLReadinessGate(min_records=500, min_unique_brands=5)
    readiness_report = gate.evaluate(engineered_df, target_col="listed_price")
    print(f"\nML Readiness Gate Status: {'READY' if readiness_report.is_ready else 'FAILED'}")
    for p in readiness_report.passed_checks:
        print(f"  [PASS] {p}")
    if readiness_report.failed_checks:
        for f in readiness_report.failed_checks:
            print(f"  [FAIL] {f}")
        raise ValueError("ML Readiness gate failed")

    # Target leakage check
    feature_cols = [c for c in engineered_df.columns if c not in [
        "id", "listing_id", "listing_url", "raw_payload", "is_outlier", "outlier_reasons",
        "is_duplicate_candidate", "duplicate_similarity", "duplicate_of_id", "duplicate_notes",
        "date_collected", "listed_price"
    ]]
    leakage = check_target_leakage(feature_cols, target_col="listed_price")
    if leakage:
        raise ValueError(f"Target leakage detected: {leakage}")
    print("  [PASS] Independent feature leakage audit passed (0 leaky features)")

    # Partitioning & Vehicle-Cluster Disjointness Check
    print("\nExecuting Vehicle-Cluster Partitioning (70% Train, 15% Calib, 15% Test)...")
    t_split_start = time.time()
    train_df, val_df, test_df = duplicate_safe_train_val_test_split(
        engineered_df, val_size=0.15, test_size=0.15, random_state=random_state
    )
    print(f"Partitioning completed in {time.time()-t_split_start:.2f}s")

    # Calculate cluster IDs on full engineered_df to rigorously audit cluster isolation
    full_clusters = build_vehicle_clusters(engineered_df)
    engineered_df["_cluster_id"] = full_clusters

    train_clusters = set(engineered_df.loc[train_df.index, "_cluster_id"])
    val_clusters = set(engineered_df.loc[val_df.index, "_cluster_id"])
    test_clusters = set(engineered_df.loc[test_df.index, "_cluster_id"])

    print(f"Cluster counts:")
    print(f"  - Total unique clusters: {len(np.unique(full_clusters))}")
    print(f"  - Training clusters    : {len(train_clusters)} ({len(train_df)} records, {len(train_df)/len(df)*100:.1f}%)")
    print(f"  - Calibration clusters : {len(val_clusters)} ({len(val_df)} records, {len(val_df)/len(df)*100:.1f}%)")
    print(f"  - Held-out Test clusters: {len(test_clusters)} ({len(test_df)} records, {len(test_df)/len(df)*100:.1f}%)")

    overlap_train_val = train_clusters & val_clusters
    overlap_train_test = train_clusters & test_clusters
    overlap_val_test = val_clusters & test_clusters

    print(f"Cluster Overlap Audit:")
    print(f"  - Train intersect Calib overlap: {len(overlap_train_val)}")
    print(f"  - Train intersect Test overlap : {len(overlap_train_test)}")
    print(f"  - Calib intersect Test overlap : {len(overlap_val_test)}")

    assert len(overlap_train_val) == 0, "Train and Calib clusters overlap!"
    assert len(overlap_train_test) == 0, "Train and Test clusters overlap!"
    assert len(overlap_val_test) == 0, "Calib and Test clusters overlap!"
    print("  [PASS] Vehicle-Cluster Disjointness verified: 100% strictly zero leakage across partitions.")

    # Prepare feature matrices
    X_train = train_df[NUMERICAL_FEATURES + CATEGORICAL_FEATURES].copy()
    y_train = train_df["listed_price"].copy()

    X_val = val_df[NUMERICAL_FEATURES + CATEGORICAL_FEATURES].copy()
    y_val = val_df["listed_price"].copy()

    X_test = test_df[NUMERICAL_FEATURES + CATEGORICAL_FEATURES].copy()
    y_test = test_df["listed_price"].copy()

    # STEP 2: Isolated Candidate Training & Model Selection
    print("\n--- STEP 2: ISOLATED CANDIDATE TRAINING & MODEL SELECTION ---")
    cv_folds = 5
    print(f"Tuning tree models using {cv_folds}-Fold CV strictly on Training partition...")
    tuner = HyperparameterTuner(cv_folds=cv_folds, n_iter=8, random_state=random_state)
    tuned_rf, best_rf_params, best_rf_cv_mae = tuner.tune_random_forest(X_train, y_train)
    tuned_hgb, best_hgb_params, best_hgb_cv_mae = tuner.tune_hist_gradient_boosting(X_train, y_train)

    xgb_model = xgb.XGBRegressor(
        n_estimators=150, max_depth=6, learning_rate=0.06, random_state=random_state, verbosity=0
    )
    xgb_params = {"n_estimators": 150, "max_depth": 6, "learning_rate": 0.06}

    candidate_models = {
        "Linear Regression (Baseline)": (LinearRegression(), {}),
        "v001 Random Forest (Baseline)": (RandomForestRegressor(n_estimators=100, max_depth=10, random_state=random_state), {"n_estimators": 100, "max_depth": 10}),
        "Tuned Random Forest Candidate": (tuned_rf, best_rf_params),
        "Tuned HistGradientBoosting Candidate": (tuned_hgb, best_hgb_params),
        "XGBoost Regressor Candidate": (xgb_model, xgb_params)
    }

    cv_kfold = KFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    fitted_pipelines = {}
    candidate_cv_metrics = {}

    print(f"\nEvaluating candidates via 5-Fold Training-CV...")
    for name, (model, params) in candidate_models.items():
        pipe = Pipeline([
            ("preprocessor", create_preprocessor_pipeline()),
            ("regressor", model)
        ])
        cv_mae_scores = -cross_val_score(pipe, X_train, y_train, cv=cv_kfold, scoring="neg_mean_absolute_error")
        cv_r2_scores = cross_val_score(pipe, X_train, y_train, cv=cv_kfold, scoring="r2")

        # Fit strictly on full training split
        pipe.fit(X_train, y_train)
        fitted_pipelines[name] = pipe

        candidate_cv_metrics[name] = {
            "cv_mae_mean": round(float(cv_mae_scores.mean()), 2),
            "cv_mae_std": round(float(cv_mae_scores.std()), 2),
            "cv_r2_mean": round(float(cv_r2_scores.mean()), 4),
            "cv_r2_std": round(float(cv_r2_scores.std()), 4),
            "hyperparameters": params
        }
        print(f"  {name:36s} | CV MAE: INR {cv_mae_scores.mean():,.0f} (+/- {cv_mae_scores.std():,.0f}) | CV R²: {cv_r2_scores.mean():.4f}")

    # Model Selection (strictly on Training-CV MAE, zero calibration/test leakage)
    sorted_by_cv = sorted(candidate_cv_metrics.items(), key=lambda x: x[1]["cv_mae_mean"])
    selected_model_name, selected_cv_info = sorted_by_cv[0]
    selected_pipeline = fitted_pipelines[selected_model_name]
    print(f"\n[Model Selection] Best candidate selected by lowest training-CV MAE: {selected_model_name}")
    print(f"  Selection Training-CV MAE: INR {selected_cv_info['cv_mae_mean']:,.0f} (+/- {selected_cv_info['cv_mae_std']:,.0f})")

    # STEP 3A: Calibration on Dedicated Calibration Split
    print("\n--- STEP 3A: PREDICTION UNCERTAINTY CALIBRATION (DEDICATED CALIBRATION SPLIT) ---")
    # Uncertainty calibration strictly on calibration split
    y_val_pred = selected_pipeline.predict(X_val)
    val_metrics = calculate_regression_metrics(y_val, y_val_pred)

    uncertainty_estimator = PredictionUncertaintyEstimator()
    uncertainty_stats = uncertainty_estimator.fit_residuals(
        y_val.values, y_val_pred, calibration_method="dedicated_calibration_split"
    )

    q80 = uncertainty_stats["residual_q80"]
    q90 = uncertainty_stats["residual_q90"]
    print(f"Calibration completed on {uncertainty_stats['calibration_sample_count']} dedicated calibration samples:")
    print(f"  - Calibration Split MAE           : INR {val_metrics['mae']:,.0f}")
    print(f"  - Calibration Median Abs Residual : INR {uncertainty_stats['median_abs_residual']:,.0f}")
    print(f"  - Empirical Residual q80 Bound    : INR {q80:,.0f} (Nominal 80% half-width)")
    print(f"  - Empirical Residual q90 Bound    : INR {q90:,.0f} (Nominal 90% half-width)")

    # FREEZE candidate model and uncertainty estimator
    print("\n[FREEZE] Freezing candidate pipeline weights and residual calibration bounds.")
    print("Zero updates to model parameters or uncertainty bounds will occur during or after test evaluation.")

    # STEP 3B: Held-Out Test Evaluation
    print("\n--- STEP 3B: HELD-OUT TEST EVALUATION ---")
    y_test_pred = selected_pipeline.predict(X_test)
    test_metrics = calculate_regression_metrics(y_test, y_test_pred)

    # Calculate interval coverage and mean interval width on Test Set
    test_abs_residuals = np.abs(y_test.values - y_test_pred)
    coverage_80 = float((test_abs_residuals <= q80).mean() * 100)
    coverage_90 = float((test_abs_residuals <= q90).mean() * 100)

    # Prediction interval width:
    # Under symmetric interval [y_hat - q, y_hat + q] clamped at 50,000 INR minimum price
    low_80 = np.maximum(50000.0, y_test_pred - q80)
    high_80 = y_test_pred + q80
    width_80 = float(np.mean(high_80 - low_80))

    low_90 = np.maximum(50000.0, y_test_pred - q90)
    high_90 = y_test_pred + q90
    width_90 = float(np.mean(high_90 - low_90))

    test_metrics["nominal_80_coverage"] = round(coverage_80, 2)
    test_metrics["nominal_80_mean_width"] = round(width_80, 2)
    test_metrics["nominal_90_coverage"] = round(coverage_90, 2)
    test_metrics["nominal_90_mean_width"] = round(width_90, 2)
    test_metrics["test_sample_count"] = len(test_df)
    test_metrics["calibration_sample_count"] = len(val_df)

    print(f"Held-Out Test Results ({len(test_df)} records):")
    print(f"  - MAE                     : INR {test_metrics['mae']:,.0f}")
    print(f"  - Median Absolute Error   : INR {test_metrics['median_ae']:,.0f}")
    print(f"  - RMSE                    : INR {test_metrics['rmse']:,.0f}")
    print(f"  - R²                      : {test_metrics['r2']:.4f}")
    print(f"  - Nominal 80% Coverage    : {coverage_80:.2f}% (Mean Width: INR {width_80:,.0f})")
    print(f"  - Nominal 90% Coverage    : {coverage_90:.2f}% (Mean Width: INR {width_90:,.0f})")

    # Evaluate all models on held-out test set for complete comparison table
    all_models_eval = {}
    for name, pipe in fitted_pipelines.items():
        preds = pipe.predict(X_test)
        m = calculate_regression_metrics(y_test, preds)
        m.update(candidate_cv_metrics[name])
        # Also compute interval coverage for each if evaluated with same bounds
        m_abs_res = np.abs(y_test.values - preds)
        m["nominal_80_coverage"] = round(float((m_abs_res <= q80).mean() * 100), 2)
        m["nominal_90_coverage"] = round(float((m_abs_res <= q90).mean() * 100), 2)
        all_models_eval[name] = m

    # Subgroup and Error Analysis with Interval Coverage
    print("\nRunning Subgroup & Price Tier Error Analysis...")
    error_analyzer = ErrorAnalyzer(min_segment_size=5)
    base_error_report = error_analyzer.run_full_error_analysis(y_test.values, y_test_pred, test_df)

    # Augment segment analysis with 80% and 90% coverage
    def augment_segments(segment_list, group_col):
        augmented = []
        for seg_info in segment_list:
            seg_name = seg_info["segment"]
            cnt = seg_info["count"]
            if cnt < 5:
                augmented.append({**seg_info, "coverage_80": None, "coverage_90": None})
                continue
            # find mask
            if group_col == "price_band":
                if seg_name == "< ₹5L":
                    mask = test_df["listed_price"] < 500000
                elif seg_name == "₹5L–₹10L":
                    mask = (test_df["listed_price"] >= 500000) & (test_df["listed_price"] < 1000000)
                elif seg_name == "₹10L–₹20L":
                    mask = (test_df["listed_price"] >= 1000000) & (test_df["listed_price"] < 2000000)
                elif seg_name == "> ₹20L":
                    mask = test_df["listed_price"] >= 2000000
                else:
                    mask = pd.Series(False, index=test_df.index)
            elif group_col == "age_band":
                if seg_name == "< 3 yrs":
                    mask = test_df["car_age"] < 3
                elif seg_name == "3–6 yrs":
                    mask = (test_df["car_age"] >= 3) & (test_df["car_age"] < 6)
                elif seg_name == "6–9 yrs":
                    mask = (test_df["car_age"] >= 6) & (test_df["car_age"] < 9)
                elif seg_name == "≥ 9 yrs":
                    mask = test_df["car_age"] >= 9
                else:
                    mask = pd.Series(False, index=test_df.index)
            elif group_col == "km_band":
                if seg_name == "< 30k km":
                    mask = test_df["km_driven"] < 30000
                elif seg_name == "30k–60k km":
                    mask = (test_df["km_driven"] >= 30000) & (test_df["km_driven"] < 60000)
                elif seg_name == "60k–100k km":
                    mask = (test_df["km_driven"] >= 60000) & (test_df["km_driven"] < 100000)
                elif seg_name == "≥ 100k km":
                    mask = test_df["km_driven"] >= 100000
                else:
                    mask = pd.Series(False, index=test_df.index)
            else:
                mask = test_df[group_col].astype(str) == seg_name

            sub_residuals = test_abs_residuals[mask.values]
            c80 = round(float((sub_residuals <= q80).mean() * 100), 2) if len(sub_residuals) > 0 else None
            c90 = round(float((sub_residuals <= q90).mean() * 100), 2) if len(sub_residuals) > 0 else None
            augmented.append({**seg_info, "coverage_80": c80, "coverage_90": c90})
        return augmented

    detailed_segments = {
        "by_price_tier": augment_segments(base_error_report["by_price_band"], "price_band"),
        "by_fuel": augment_segments(base_error_report["by_fuel"], "fuel_type"),
        "by_transmission": augment_segments(base_error_report["by_transmission"], "transmission"),
        "by_age_band": augment_segments(base_error_report["by_age_band"], "age_band"),
        "by_km_band": augment_segments(base_error_report["by_km_band"], "km_band")
    }

    # STEP 4: Persist Artifacts to Isolated Directory
    print("\n--- STEP 4: PERSISTING ISOLATED ARTIFACTS ---")
    model_artifact_path = os.path.join(output_dir, "model_v003_candidate.joblib")
    prep_artifact_path = os.path.join(output_dir, "preprocessor_v003_candidate.joblib")
    meta_artifact_path = os.path.join(output_dir, "metadata_v003_candidate.json")

    joblib.dump(selected_pipeline.named_steps["regressor"], model_artifact_path)
    joblib.dump(selected_pipeline.named_steps["preprocessor"], prep_artifact_path)

    metadata_payload = {
        "model_version": "v003_candidate",
        "selected_model": selected_model_name,
        "dataset_version": "v0.3",
        "dataset_sha256": dataset_hash,
        "status": "candidate",
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "random_state": random_state,
        "total_records": len(df),
        "train_records": len(train_df),
        "calibration_records": len(val_df),
        "test_records": len(test_df),
        "train_clusters": len(train_clusters),
        "calibration_clusters": len(val_clusters),
        "test_clusters": len(test_clusters),
        "cv_folds": cv_folds,
        "evaluation_strategy": "duplicate_safe_train_val_test_split",
        "model_selection_criterion": "lowest_training_cv_mae",
        "hyperparameters": selected_cv_info["hyperparameters"],
        "metrics_training_cv": selected_cv_info,
        "metrics_calibration": {
            "val_mae": val_metrics["mae"],
            "val_rmse": val_metrics["rmse"],
            "val_r2": val_metrics["r2"],
            "val_median_ae": val_metrics["median_ae"],
            "sample_count": len(val_df)
        },
        "uncertainty_calibration": uncertainty_stats,
        "metrics_test": test_metrics,
        "all_model_comparison": all_models_eval,
        "error_analysis_summary": detailed_segments,
        "model_artifact": model_artifact_path,
        "preprocessor_artifact": prep_artifact_path,
        "artifact_integrity": {
            "model_sha256": compute_sha256(model_artifact_path),
            "preprocessor_sha256": compute_sha256(prep_artifact_path)
        }
    }

    with open(meta_artifact_path, "w", encoding="utf-8") as f:
        json.dump(metadata_payload, f, indent=2)

    # Compute final metadata SHA-256
    meta_sha256 = compute_sha256(meta_artifact_path)
    print(f"Persisted isolated candidate artifacts:")
    print(f"  - Model       : {model_artifact_path} (SHA-256: {metadata_payload['artifact_integrity']['model_sha256']})")
    print(f"  - Preprocessor: {prep_artifact_path} (SHA-256: {metadata_payload['artifact_integrity']['preprocessor_sha256']})")
    print(f"  - Metadata    : {meta_artifact_path} (SHA-256: {meta_sha256})")

    # STEP 5: Verification of Invariance for Production and Prior Candidates
    print("\n--- STEP 5: IMMUTABILITY VERIFICATION ---")
    immutability_passed = True
    for k, p in prod_files.items():
        if os.path.exists(p):
            curr_h = compute_sha256(p)
            if curr_h != baseline_hashes[k]:
                print(f"[FAIL] {k} was altered! Baseline: {baseline_hashes[k]}, Current: {curr_h}")
                immutability_passed = False
            else:
                print(f"[PASS] {k:25s} unchanged (SHA-256: {curr_h[:16]}...)")

    assert immutability_passed, "Baseline artifact immutability violation detected!"

    total_time = time.time() - start_time
    print(f"\nEvaluation protocol executed cleanly in {total_time:.2f} seconds.")
    return metadata_payload


if __name__ == "__main__":
    run_controlled_candidate_evaluation()
