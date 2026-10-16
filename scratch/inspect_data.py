import hashlib
import os
import json
import pandas as pd
import numpy as np

p = "data/processed/autovalue_processed.csv"
with open(p, "rb") as f:
    h = hashlib.sha256(f.read()).hexdigest()

df = pd.read_csv(p)
print(f"Path: {p}")
print(f"SHA-256: {h}")
print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")
print("\nSource distribution:")
print(df["source"].value_counts())
print("\nSource distribution (percentage):")
print((df["source"].value_counts(normalize=True) * 100).round(2))

# Check date_collected range
if "date_collected" in df.columns:
    print(f"\nDate collected min: {df['date_collected'].min()}, max: {df['date_collected'].max()}")

# Check if there are any indicator columns or synthetic patterns
print("\nUnique brands count:", df["brand"].nunique())
print("Brands:", sorted(df["brand"].dropna().unique()))
