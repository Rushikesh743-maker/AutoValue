"""
Evaluation metrics for vehicle price regression models.
Calculates MAE (in INR), RMSE (in INR), R², and Median Absolute Error without fabricated metrics.
"""
from typing import Dict, Any, List, Union
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score, median_absolute_error


def calculate_regression_metrics(
    y_true: Union[pd.Series, np.ndarray, List[float]],
    y_pred: Union[pd.Series, np.ndarray, List[float]]
) -> Dict[str, float]:
    """
    Computes standard regression metrics comparing predicted prices against actual observed listing prices.
    All monetary errors are in Indian Rupees (INR).
    """
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)

    if len(y_t) == 0:
        return {"mae": 0.0, "rmse": 0.0, "r2": 0.0, "median_ae": 0.0}

    mae = float(mean_absolute_error(y_t, y_p))
    try:
        rmse = float(root_mean_squared_error(y_t, y_p))
    except (AttributeError, TypeError):
        # Fallback if root_mean_squared_error isn't available
        from sklearn.metrics import mean_squared_error
        rmse = float(np.sqrt(mean_squared_error(y_t, y_p)))
    
    r2 = float(r2_score(y_t, y_p)) if len(y_t) > 1 else 0.0
    med_ae = float(median_absolute_error(y_t, y_p))

    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "r2": round(r2, 4),
        "median_ae": round(med_ae, 2)
    }


def format_metrics_table(model_results: Dict[str, Dict[str, float]]) -> str:
    """
    Formats model comparison dictionary into a clean markdown table.
    """
    header = "| Model | MAE (INR) | RMSE (INR) | R² | Median AE (INR) |\n|---|---:|---:|---:|---:|"
    rows = []
    for model_name, metrics in model_results.items():
        mae_str = f"INR {metrics.get('mae', 0.0):,.0f}"
        rmse_str = f"INR {metrics.get('rmse', 0.0):,.0f}"
        r2_str = f"{metrics.get('r2', 0.0):.4f}"
        med_str = f"INR {metrics.get('median_ae', 0.0):,.0f}"
        rows.append(f"| {model_name} | {mae_str} | {rmse_str} | {r2_str} | {med_str} |")

    return "\n".join([header] + rows)
