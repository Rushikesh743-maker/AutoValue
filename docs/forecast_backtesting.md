# AutoValue — Forecast Backtesting & Temporal Validation Methodology

## 1. Overview & Objective

The forecast backtesting suite (`scripts/backtest_forecast.py` and temporal tests in `tests/backend/test_forecast.py`) validates the empirical rigor of AutoValue's Phase 14 forecasting algorithms. The critical requirement is to guarantee **zero future-data leakage** and quantify prediction error across historical split points.

---

## 2. Temporal Partitioning Strategy

Backtesting strictly enforces chronological train/validation splits:
- **Cutoff Date ($T_0$)**: A point in time dividing the available marketplace history.
- **Training Set**: Listings collected on or before $T_0$ ($t \le T_0$).
- **Validation Set**: Listings observed strictly after $T_0$ ($t > T_0$).

```
Timeline: |================ Training Pool (<= T_0) ================|======= Validation Pool (> T_0) =======>
                                                                     ^
                                                             Cutoff Point (T_0)
```

### Future Data Leakage Prevention
The forecasting service accepts a `cutoff_date` parameter that filters dataset records prior to any aggregation, momentum calculation, volatility measurement, or forecast extrapolation.

Unit test `test_no_future_data_leakage` in `tests/backend/test_forecast.py` asserts that predictions made with cutoff $T_0$ produce identical results regardless of whether subsequent future records exist in the database.

---

## 3. Backtest Metrics

For segments with adequate post-cutoff validation samples, the backtest evaluates:
1. **Mean Absolute Percentage Error (MAPE)**:
   $$\text{MAPE} = \frac{1}{N} \sum_{i=1}^N \left| \frac{y_i - \hat{y}_i}{y_i} \right| \times 100\%$$
2. **Mean Absolute Error (MAE)**:
   $$\text{MAE} = \frac{1}{N} \sum_{i=1}^N \left| y_i - \hat{y}_i \right|$$
3. **Directional Accuracy**: Proportion of segments where forecasted direction (`RISING`, `STABLE`, `DECLINING`) matched observed post-cutoff trajectory.
4. **Coverage Rate**: Proportion of observed validation prices falling within the forecast's uncertainty corridor ($[\text{Lower Bound}, \text{Upper Bound}]$).

---

## 4. Benchmark Backtest Results

Running `python scripts/backtest_forecast.py` on the verified dataset (v0.3, N=999) yields:
- Total Verified Marketplace Records: 999
- Temporal Partition: 70% Train (699 records) / 30% Validation (300 records)
- Refusal Rate on Sparse History: 100% (Strictly returns `INSUFFICIENT_EVIDENCE` when temporal window is insufficient, avoiding hallucinated error metrics).

---

## 5. Methodological Disclaimer
Backtesting on past advertised asking prices evaluates statistical model stability but does not guarantee future valuation certainty. Marketplace conditions may fluctuate due to external macroeconomic shocks, supply-chain shifts, and regulatory changes.
