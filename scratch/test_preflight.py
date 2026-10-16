import os
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath("."))

from ml.training.split import duplicate_safe_train_val_test_split, build_vehicle_clusters
from data_pipeline.feature_engineering.features import CarFeatureEngineer

df = pd.read_csv("data/processed/autovalue_processed.csv")
engineer = CarFeatureEngineer()
engineered_df = engineer.transform(df)

# Compute clusters
clusters = build_vehicle_clusters(engineered_df)
engineered_df["_cluster_id"] = clusters
print(f"Total rows: {len(engineered_df)}")
print(f"Unique vehicle clusters: {len(np.unique(clusters))}")

train_df, val_df, test_df = duplicate_safe_train_val_test_split(
    engineered_df, val_size=0.15, test_size=0.15, random_state=42
)

# Re-attach cluster IDs to verify partitions
train_clusters = set(engineered_df.loc[train_df.index, "_cluster_id"])
val_clusters = set(engineered_df.loc[val_df.index, "_cluster_id"])
test_clusters = set(engineered_df.loc[test_df.index, "_cluster_id"])

print(f"Train records: {len(train_df)}, unique clusters: {len(train_clusters)}")
print(f"Calibration records: {len(val_df)}, unique clusters: {len(val_clusters)}")
print(f"Test records: {len(test_df)}, unique clusters: {len(test_clusters)}")

# Check disjointness
train_val_overlap = train_clusters.intersection(val_clusters)
train_test_overlap = train_clusters.intersection(test_clusters)
val_test_overlap = val_clusters.intersection(test_clusters)

print(f"Train-Val cluster overlap: {len(train_val_overlap)}")
print(f"Train-Test cluster overlap: {len(train_test_overlap)}")
print(f"Val-Test cluster overlap: {len(val_test_overlap)}")

assert len(train_val_overlap) == 0, "Train and Val clusters overlap!"
assert len(train_test_overlap) == 0, "Train and Test clusters overlap!"
assert len(val_test_overlap) == 0, "Val and Test clusters overlap!"

# Index intersection check
train_idx = set(train_df.index)
val_idx = set(val_df.index)
test_idx = set(test_df.index)

print(f"Train-Val index overlap: {len(train_idx.intersection(val_idx))}")
print(f"Train-Test index overlap: {len(train_idx.intersection(test_idx))}")
print(f"Val-Test index overlap: {len(val_idx.intersection(test_idx))}")

print("Preflight cluster-isolation checks PASSED completely!")
