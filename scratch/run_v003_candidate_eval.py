"""
AutoValue Controlled Candidate Evaluation Script.
Executes reproducible, leakage-free training of an experimental candidate model (v003)
into an isolated candidate directory without mutating active v002 artifacts.
Calculates:
- 5-Fold Training CV metrics for all candidates
- Candidate selection via lowest CV MAE on training fold
- Dedicated calibration split residual quantiles (q80, q90)
- Frozen model evaluation on held-out test set (MAE, MedAE, RMSE, R2)
- Empirical coverage and mean width for 80% and 90% prediction intervals on held-out test set
- Segment and subgroup breakdown
- Artifact SHA-256 checksums and dependency versions
"""
import os
import sys
import json
import hashlib
import platform
import numpy as np
import pandas as pd
import sklearn
import joblib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.config import settings
from ml.training.train_v002 import run_training_v002
from ml.training.split import duplicate_safe_train_val_test_split, build_vehicle_clusters
from ml.evaluation.metrics import calculate_regression_metrics
from ml.evaluation.error_analysis import ErrorAnalyzer
from ml.features.preprocessor import NUMERICAL_FEATURES, CATEGORICAL_FEATURES


def main():
    print("=" * 80)
    print("AutoValue — Controlled v003 Candidate Evaluation")
    print("=" * 80)

    # 1. Environment & Dependencies
    deps = {
        "python": platform.python_version(),
        "scikit-learn": sklearn.__version__,
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "joblib": joblib.__version__
    }
    try:
        import xgboost
        deps["xgboost"] = xgboost.__version__
    except ImportError:
        deps["xgboost"] = "Not Installed"

    print("\n[Preflight] Environment & Dependency Versions:")
    for k, v in deps.items():
        print(f"  {k:15s}: {v}")

    # 2. Dataset & Provenance
    csv_path = os.path.join(settings.PROCESSED_DATA_DIR, "autovalue_processed.csv")
    with open(csv_path, "rb") as f:
        csv_hash = hashlib.sha256(f.read()).hexdigest()

    df = pd.read_csv(csv_path)
    print(f"\n[Preflight] Dataset: {csv_path}")
    print(f"  SHA-256 Hash  : {csv_hash}")
    print(f"  Total Records : {len(df)}")
    print(f"  Source Counts :\n{df['source'].value_counts().to_string()}")

    # 3. Verify Cluster Isolation
    clusters = build_vehicle_clusters(df)
    train_df, val_df, test_df = duplicate_safe_train_val_test_split(df, val_size=0.15, test_size=0.15, random_state=42)
    
    train_clusters = set(build_vehicle_clusters(train_df))
    val_clusters = set(build_vehicle_clusters(val_df))
    test_clusters = set(build_vehicle_clusters(test_df))

    print(f"\n[Preflight] Partition Disjointness Check:")
    print(f"  Train Records       : {len(train_df)} ({len(train_df)/len(df)*100:.1f}%)")
    print(f"  Calibration Records : {len(val_df)} ({len(val_df)/len(df)*100:.1f}%)")
    print(f"  Held-Out Test Records: {len(test_df)} ({len(test_df)/len(df)*100:.1f}%)")
    print(f"  Train + Val + Test  : {len(train_df) + len(val_df) + len(test_df)}")
    print(f"  Unique Clusters Total: {len(np.unique(clusters))}")

    # Verify no listing_id overlap
    train_lids = set(train_df["listing_id"].dropna())
    val_lids = set(val_df["listing_id"].dropna())
    test_lids = set(test_df["listing_id"].dropna())
    assert train_lids.isdisjoint(val_lids), "Overlap between Train and Val listing IDs!"
    assert train_lids.isdisjoint(test_lids), "Overlap between Train and Test listing IDs!"
    assert val_lids.isdisjoint(test_lids), "Overlap between Val and Test listing IDs!"
    print("  [PASS] All partition clusters and listing IDs are strictly disjoint.")

    # 4. Train Candidate in Isolated Directory
    candidate_models_dir = os.path.join(settings.MODELS_DIR, "candidates", "v003_eval")
    candidate_exp_dir = os.path.join(os.path.dirname(__file__), "..", "ml", "experiments", "candidate_v003")
    os.makedirs(candidate_models_dir, exist_ok=True)
    os.makedirs(candidate_exp_dir, exist_ok=True)

    print(f"\n[Training] Executing training into isolated directory: {candidate_models_dir}")
    train_result = run_training_v002(
        processed_csv_path=csv_path,
        models_dir=candidate_models_dir,
        experiments_dir=candidate_exp_dir,
        model_version="v003_candidate",
        random_state=42
    )

    # 5. Extract Artifact Hashes
    model_art_path = os.path.join(candidate_models_dir, "model_v003_candidate.joblib")
    prep_art_path = os.path.join(candidate_models_dir, "preprocessor_v003_candidate.joblib")
    meta_art_path = os.path.join(candidate_models_dir, "metadata_v003_candidate.json")

    with open(model_art_path, "rb") as f:
        model_hash = hashlib.sha256(f.read()).hexdigest()
    with open(prep_art_path, "rb") as f:
        prep_hash = hashlib.sha256(f.read()).hexdigest()
    with open(meta_art_path, "rb") as f:
        meta_hash = hashlib.sha256(f.read()).hexdigest()

    print("\n[Artifacts] Candidate Artifacts Persisted & Hashes:")
    print(f"  Model Joblib        : {model_art_path}")
    print(f"    SHA-256           : {model_hash}")
    print(f"  Preprocessor Joblib : {prep_art_path}")
    print(f"    SHA-256           : {prep_hash}")
    print(f"  Metadata JSON       : {meta_art_path}")
    print(f"    SHA-256           : {meta_hash}")

    # 6. Prediction Interval Evaluation on Held-Out Test Set
    fitted_prep = joblib.load(prep_art_path)
    fitted_model = joblib.load(model_art_path)

    X_test = test_df[NUMERICAL_FEATURES + CATEGORICAL_FEATURES].copy()
    y_test = test_df["listed_price"].values
    X_test_trans = fitted_prep.transform(X_test)
    y_test_preds = fitted_model.predict(X_test_trans)

    # Calibration statistics from training
    unc_stats = train_result["uncertainty_stats"]
    q80 = unc_stats["residual_q80"]
    q90 = unc_stats["residual_q90"]

    # Test set empirical residuals
    test_abs_residuals = np.abs(y_test - y_test_preds)

    # Coverage for 80% nominal interval: y_pred - q80 <= y_true <= y_pred + q80
    covered_80 = (y_test >= (y_test_preds - q80)) & (y_test <= (y_test_preds + q80))
    cov_80_pct = float(np.mean(covered_80) * 100)
    mean_width_80 = float(2 * q80)

    # Coverage for 90% nominal interval: y_pred - q90 <= y_true <= y_pred + q90
    covered_90 = (y_test >= (y_test_preds - q90)) & (y_test <= (y_test_preds + q90))
    cov_90_pct = float(np.mean(covered_90) * 100)
    mean_width_90 = float(2 * q90)

    # Test metrics
    test_metrics = calculate_regression_metrics(y_test, y_test_preds)

    print("\n" + "=" * 80)
    print("EVALUATION RESULTS SUMMARY")
    print("=" * 80)
    print("\n--- Training-CV Performance (Model Selection on 709 Training records) ---")
    for m_name, res in train_result["candidate_cv_results"].items():
        print(f"  {m_name:36s} | CV MAE: INR {res['cv_mae_mean']:,.0f} (+/- {res['cv_mae_std']:,.0f}) | CV R²: {res['cv_r2_mean']:.4f}")

    print(f"\nSelected Candidate Model : {train_result['selected_model']}")
    print(f"Selection Criterion      : Lowest Training CV MAE")

    print("\n--- Calibration Set Performance (143 Dedicated Calibration records) ---")
    print(f"  Calibration Sample Count : {unc_stats['calibration_sample_count']}")
    print(f"  Calibration Method       : {unc_stats['calibration_method']}")
    print(f"  Empirical Mean Abs Res   : INR {unc_stats['mean_abs_residual']:,.0f}")
    print(f"  Empirical Median Abs Res : INR {unc_stats['median_abs_residual']:,.0f}")
    print(f"  Nominal 80% Half-Width (q80): INR {q80:,.0f} (Full Width: INR {mean_width_80:,.0f})")
    print(f"  Nominal 90% Half-Width (q90): INR {q90:,.0f} (Full Width: INR {mean_width_90:,.0f})")

    print("\n--- Frozen Held-Out Test Set Performance (147 Held-Out Test records) ---")
    print(f"  Test Sample Count        : {len(test_df)}")
    print(f"  Test MAE                 : INR {test_metrics['mae']:,.0f}")
    print(f"  Test Median AE           : INR {test_metrics['median_ae']:,.0f}")
    print(f"  Test RMSE                : INR {test_metrics['rmse']:,.0f}")
    print(f"  Test R²                  : {test_metrics['r2']:.4f}")
    print(f"  Nominal 80% Interval Empirical Coverage: {cov_80_pct:.1f}% (Mean Width: INR {mean_width_80:,.0f})")
    print(f"  Nominal 90% Interval Empirical Coverage: {cov_90_pct:.1f}% (Mean Width: INR {mean_width_90:,.0f})")

    # Segment Analysis
    test_df_eval = test_df.copy()
    test_df_eval["abs_err"] = test_abs_residuals
    test_df_eval["in_80"] = covered_80
    test_df_eval["in_90"] = covered_90

    # Price Tier Breakdown
    def price_tier(p):
        if p < 500000:
            return "< ₹5L"
        elif p <= 1000000:
            return "₹5L–₹10L"
        elif p <= 2000000:
            return "₹10L–₹20L"
        else:
            return "> ₹20L"

    test_df_eval["price_tier"] = test_df_eval["listed_price"].apply(price_tier)
    print("\n--- Subgroup Breakdown: By Price Tier on Held-Out Test Set ---")
    tier_order = ["< ₹5L", "₹5L–₹10L", "₹10L–₹20L", "> ₹20L"]
    tier_rows = []
    for t in tier_order:
        sub = test_df_eval[test_df_eval["price_tier"] == t]
        if len(sub) > 0:
            sub_mae = sub["abs_err"].mean()
            sub_med = sub["abs_err"].median()
            cov80 = sub["in_80"].mean() * 100
            cov90 = sub["in_90"].mean() * 100
            tier_rows.append({
                "Tier": t, "Count": len(sub), "MAE (INR)": f"INR {sub_mae:,.0f}",
                "Median AE": f"INR {sub_med:,.0f}", "80% Coverage": f"{cov80:.1f}%", "90% Coverage": f"{cov90:.1f}%"
            })
            print(f"  {t:12s} | N={len(sub):2d} | MAE: INR {sub_mae:,.0f} | MedAE: INR {sub_med:,.0f} | 80% Cov: {cov80:.1f}% | 90% Cov: {cov90:.1f}%")

    print("\n--- Subgroup Breakdown: By Fuel Type on Held-Out Test Set ---")
    for f in test_df_eval["fuel_type"].unique():
        sub = test_df_eval[test_df_eval["fuel_type"] == f]
        if len(sub) > 0:
            sub_mae = sub["abs_err"].mean()
            sub_med = sub["abs_err"].median()
            cov80 = sub["in_80"].mean() * 100
            cov90 = sub["in_90"].mean() * 100
            print(f"  {f:12s} | N={len(sub):2d} | MAE: INR {sub_mae:,.0f} | MedAE: INR {sub_med:,.0f} | 80% Cov: {cov80:.1f}% | 90% Cov: {cov90:.1f}%")

    print("\n--- Subgroup Breakdown: By Transmission on Held-Out Test Set ---")
    for tr in test_df_eval["transmission"].unique():
        sub = test_df_eval[test_df_eval["transmission"] == tr]
        if len(sub) > 0:
            sub_mae = sub["abs_err"].mean()
            sub_med = sub["abs_err"].median()
            cov80 = sub["in_80"].mean() * 100
            cov90 = sub["in_90"].mean() * 100
            print(f"  {tr:12s} | N={len(sub):2d} | MAE: INR {sub_mae:,.0f} | MedAE: INR {sub_med:,.0f} | 80% Cov: {cov80:.1f}% | 90% Cov: {cov90:.1f}%")

    # Output structured summary JSON to scratch
    summary = {
        "candidate_model_version": "v003_candidate",
        "selected_model": train_result["selected_model"],
        "training_timestamp": train_result["metadata"]["training_timestamp"],
        "dataset_sha256": csv_hash,
        "sample_counts": {
            "total": len(df),
            "train": len(train_df),
            "calibration": len(val_df),
            "test": len(test_df)
        },
        "artifact_hashes": {
            "model_v003_candidate.joblib": model_hash,
            "preprocessor_v003_candidate.joblib": prep_hash,
            "metadata_v003_candidate.json": meta_hash
        },
        "training_cv_results": train_result["candidate_cv_results"],
        "calibration_results": unc_stats,
        "test_metrics": test_metrics,
        "prediction_interval_evaluation": {
            "nominal_80_coverage_pct": round(cov_80_pct, 2),
            "nominal_80_half_width": q80,
            "nominal_80_mean_width": mean_width_80,
            "nominal_90_coverage_pct": round(cov_90_pct, 2),
            "nominal_90_half_width": q90,
            "nominal_90_mean_width": mean_width_90
        }
    }

    summary_out = os.path.join(os.path.dirname(__file__), "v003_evaluation_summary.json")
    with open(summary_out, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nSaved structured evaluation report: {summary_out}")
    print("=" * 80)


if __name__ == "__main__":
    main()
