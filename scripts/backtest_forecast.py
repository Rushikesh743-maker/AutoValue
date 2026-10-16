#!/usr/bin/env python
"""
AutoValue Phase 14 Market Forecast Backtesting Engine.
Evaluates temporal forecasting methodology against empirical historical data
using strict out-of-sample temporal train/test validation splits (70% train, 30% test).
Calculates MAE, MAPE, and directional movement accuracy across vehicle segments.
"""
import sys
import os
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import math
import numpy as np
import pandas as pd
from datetime import datetime

from backend.app.schemas.forecast import ForecastRequest, TrendDirection
from backend.app.services.market_forecast_service import MarketForecastService


def run_forecast_backtest():
    print("=" * 78)
    print(" AutoValue Phase 14 Market Forecast Backtesting Evaluation")
    print("=" * 78)

    csv_path = os.path.join(ROOT_DIR, "data", "processed", "autovalue_processed.csv")
    if not os.path.exists(csv_path):
        print(f"Error: Dataset not found at {csv_path}")
        return

    df = pd.read_csv(csv_path)
    if "date_collected" not in df.columns:
        df["date_collected"] = pd.Timestamp.now()
    else:
        df["date_collected"] = pd.to_datetime(df["date_collected"], errors="coerce")

    df = df.dropna(subset=["date_collected", "listed_price", "brand", "model"]).sort_values("date_collected")
    total_records = len(df)
    print(f"Total Verified Marketplace Records: {total_records}")
    print(f"Date Span: {df['date_collected'].min().strftime('%Y-%m-%d')} to {df['date_collected'].max().strftime('%Y-%m-%d')}")

    # 70% Train / 30% Validation Temporal Split
    split_idx = int(total_records * 0.70)
    cutoff_date = df["date_collected"].iloc[split_idx].strftime("%Y-%m-%d")
    print(f"Temporal Cutoff Date (Train Split): {cutoff_date}")
    print(f"Training Pool (<= {cutoff_date}): {split_idx} records")
    print(f"Validation Pool (> {cutoff_date}): {total_records - split_idx} records")
    print("-" * 78)

    train_service = MarketForecastService(processed_csv_path=csv_path)

    # Segments to evaluate
    segments = [
        {"brand": "Hyundai", "model": "Creta", "year": 2021, "city": "Bengaluru"},
        {"brand": "Honda", "model": "City", "year": 2020, "city": "Mumbai"},
        {"brand": "Maruti Suzuki", "model": "Swift", "year": 2019, "city": "Delhi Ncr"},
        {"brand": "Tata", "model": "Nexon", "year": 2022, "city": "Pune"},
        {"brand": "Toyota", "model": "Innova Crysta", "year": 2018, "city": "Hyderabad"},
        {"brand": "Mahindra", "model": "XUV700", "year": 2022, "city": "Bengaluru"},
        {"brand": "Kia", "model": "Seltos", "year": 2020, "city": "Mumbai"}
    ]

    results = []

    for seg in segments:
        req = ForecastRequest(
            brand=seg["brand"],
            model=seg["model"],
            year=seg["year"],
            city=seg["city"],
            cutoff_date=cutoff_date,
            horizon_days=365
        )

        fc_response = train_service.forecast_vehicle_market(req)

        # Evaluate against actual validation records
        val_subset = df[
            (df["date_collected"] > pd.to_datetime(cutoff_date)) &
            (df["brand"].str.lower() == seg["brand"].lower()) &
            (df["model"].str.lower() == seg["model"].lower())
        ]

        if len(val_subset) > 0 and fc_response.status == "AVAILABLE":
            actual_val_median = float(np.median(val_subset["listed_price"].values))
            base_projected = fc_response.forecast_points[-1].base_price  # 1Y horizon

            error_abs = abs(base_projected - actual_val_median)
            mape = (error_abs / actual_val_median) * 100.0

            # Directional accuracy
            actual_price_diff = actual_val_median - (fc_response.current_market_median or actual_val_median)
            predicted_price_diff = base_projected - (fc_response.current_market_median or base_projected)
            directional_match = (actual_price_diff * predicted_price_diff >= 0)

            results.append({
                "segment": f"{seg['brand']} {seg['model']} ({seg['year']})",
                "train_obs": fc_response.evidence.observation_count,
                "val_obs": len(val_subset),
                "forecast_1y": base_projected,
                "actual_val_median": actual_val_median,
                "mae_inr": error_abs,
                "mape_pct": mape,
                "directional_match": directional_match,
                "confidence": fc_response.forecast_confidence.value
            })
        else:
            # Insufficient validation observations or segment match
            results.append({
                "segment": f"{seg['brand']} {seg['model']} ({seg['year']})",
                "train_obs": fc_response.evidence.observation_count,
                "val_obs": len(val_subset),
                "forecast_1y": fc_response.forecast_points[-1].base_price if fc_response.forecast_points else None,
                "actual_val_median": float(np.median(val_subset["listed_price"].values)) if len(val_subset) > 0 else None,
                "mae_inr": None,
                "mape_pct": None,
                "directional_match": None,
                "confidence": fc_response.forecast_confidence.value
            })

    print(f"{'Segment':<32} | {'Train':<5} | {'Val':<5} | {'MAPE %':<8} | {'MAE (INR)':<12} | {'Direction':<10} | {'Confidence'}")
    print("-" * 105)

    valid_mapes = []
    valid_maes = []
    dir_matches = []

    for r in results:
        mape_str = f"{r['mape_pct']:.1f}%" if r['mape_pct'] is not None else "N/A"
        mae_str = f"₹{r['mae_inr']:,.0f}" if r['mae_inr'] is not None else "N/A"
        dir_str = "MATCH" if r['directional_match'] is True else ("DIVERGE" if r['directional_match'] is False else "N/A")
        print(f"{r['segment']:<32} | {r['train_obs']:<5} | {r['val_obs']:<5} | {mape_str:<8} | {mae_str:<12} | {dir_str:<10} | {r['confidence']}")

        if r['mape_pct'] is not None:
            valid_mapes.append(r['mape_pct'])
            valid_maes.append(r['mae_inr'])
        if r['directional_match'] is not None:
            dir_matches.append(1 if r['directional_match'] else 0)

    print("=" * 105)
    if valid_mapes:
        avg_mape = np.mean(valid_mapes)
        avg_mae = np.mean(valid_maes)
        dir_acc = (sum(dir_matches) / len(dir_matches)) * 100.0 if dir_matches else 0.0
        print(f"Overall Backtest Metrics Across Evaluated Segments:")
        print(f"  • Mean Absolute Percentage Error (MAPE): {avg_mape:.2f}%")
        print(f"  • Mean Absolute Error (MAE): ₹{avg_mae:,.0f} INR")
        print(f"  • Directional Trajectory Accuracy: {dir_acc:.1f}%")
    else:
        print("Backtest executed. Insufficient post-cutoff validation samples for complete MAPE metric.")
    print("=" * 105)
    print("Note: Backtest performance on past asking prices does not guarantee future valuation certitude.\n")


if __name__ == "__main__":
    run_forecast_backtest()
