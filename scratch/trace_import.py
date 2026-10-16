import sys, os, time
print("1. start", flush=True)
import pandas as pd
print("2. pandas imported", flush=True)
import numpy as np
print("3. numpy imported", flush=True)
from ml.training.split import duplicate_safe_train_val_test_split, build_vehicle_clusters
print("4. split imported", flush=True)
from data_pipeline.feature_engineering.features import CarFeatureEngineer
print("5. features imported", flush=True)
df = pd.read_csv("data/processed/autovalue_processed.csv")
print("6. read_csv done", flush=True)
