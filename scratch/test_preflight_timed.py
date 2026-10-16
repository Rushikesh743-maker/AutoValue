import os
import sys
import time
import pandas as pd
import numpy as np

print("Starting preflight test...", flush=True)
t0 = time.time()

sys.path.insert(0, os.path.abspath("."))

from ml.training.split import duplicate_safe_train_val_test_split, build_vehicle_clusters
from data_pipeline.feature_engineering.features import CarFeatureEngineer

df = pd.read_csv("data/processed/autovalue_processed.csv")
print(f"Loaded csv with {len(df)} rows in {time.time()-t0:.2f}s", flush=True)

engineer = CarFeatureEngineer()
engineered_df = engineer.transform(df)
print(f"Feature engineering completed in {time.time()-t0:.2f}s", flush=True)

t1 = time.time()
clusters = build_vehicle_clusters(engineered_df)
print(f"build_vehicle_clusters completed in {time.time()-t1:.2f}s; {len(np.unique(clusters))} unique clusters", flush=True)

working_df = engineered_df.copy().reset_index(drop=True)
working_df["_cluster_id"] = clusters

unique_clusters = np.sort(working_df["_cluster_id"].unique())
rng = np.random.RandomState(42)
shuffled_clusters = rng.permutation(unique_clusters)

n_test_clusters = max(1, int(len(shuffled_clusters) * 0.15))
n_val_clusters = max(1, int(len(shuffled_clusters) * 0.15))

test_cluster_ids = set(shuffled_clusters[:n_test_clusters])
val_cluster_ids = set(shuffled_clusters[n_test_clusters:n_test_clusters + n_val_clusters])

test_mask = working_df["_cluster_id"].isin(test_cluster_ids)
val_mask = working_df["_cluster_id"].isin(val_cluster_ids)
train_mask = ~(test_mask | val_mask)

train_clusters = set(working_df.loc[train_mask, "_cluster_id"])
val_clusters = set(working_df.loc[val_mask, "_cluster_id"])
test_clusters = set(working_df.loc[test_mask, "_cluster_id"])

print(f"Train records: {train_mask.sum()}, unique clusters: {len(train_clusters)}", flush=True)
print(f"Val records: {val_mask.sum()}, unique clusters: {len(val_clusters)}", flush=True)
print(f"Test records: {test_mask.sum()}, unique clusters: {len(test_clusters)}", flush=True)

train_val_overlap = train_clusters.intersection(val_clusters)
train_test_overlap = train_clusters.intersection(test_clusters)
val_test_overlap = val_clusters.intersection(test_clusters)

print(f"Train-Val cluster overlap: {len(train_val_overlap)}", flush=True)
print(f"Train-Test cluster overlap: {len(train_test_overlap)}", flush=True)
print(f"Val-Test cluster overlap: {len(val_test_overlap)}", flush=True)

assert len(train_val_overlap) == 0
assert len(train_test_overlap) == 0
assert len(val_test_overlap) == 0

print(f"ALL PREFLIGHT CHECKS PASSED in {time.time()-t0:.2f}s total!", flush=True)
