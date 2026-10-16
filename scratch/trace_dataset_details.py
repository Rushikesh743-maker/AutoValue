import json
import pandas as pd
import numpy as np

df = pd.read_csv("data/processed/autovalue_processed.csv")
with open("data/processed/dataset_metadata.json", "r") as f:
    meta = json.load(f)

print(f"Dataset shape: {df.shape}")
print(f"Metadata processed count: {meta['processed_record_count']}")

# Check outliers
if "is_outlier" in df.columns:
    print(f"Outliers in CSV: {df['is_outlier'].sum()}")

# Check duplicates
if "is_duplicate_candidate" in df.columns:
    print(f"Duplicates in CSV: {df['is_duplicate_candidate'].sum()}")

# Check missing values
print("\nMissing values in CSV vs Metadata:")
for col in df.columns:
    actual_nulls = df[col].isnull().sum()
    meta_nulls = meta["missing_value_summary"]["counts"].get(col, "N/A")
    print(f"  {col:25s}: actual={actual_nulls:3d} | metadata={str(meta_nulls):>3s}")

# Check car_age vs year
print("\nCar age vs Year distribution:")
print(df[["year", "car_age"]].head(10))
print("Year min/max:", df["year"].min(), df["year"].max())
print("Car age min/max:", df["car_age"].min(), df["car_age"].max())

# Check target price rounding
price_mod_5000 = (df["listed_price"] % 5000 == 0).mean() * 100
print(f"\nPercentage of listed prices exactly divisible by 5,000 INR: {price_mod_5000:.2f}%")

# Check model catalog consistency
models_per_brand = df.groupby("brand")["model"].nunique()
print("\nUnique models per brand:")
print(models_per_brand)

# Check engine_cc uniqueness per model
engine_std_per_model = df.groupby(["brand", "model"])["engine_cc"].std().dropna()
print(f"Number of (brand, model) with non-zero std in engine_cc: {(engine_std_per_model > 0).sum()} of {len(engine_std_per_model)}")
mileage_std_per_model = df.groupby(["brand", "model"])["mileage"].std().dropna()
print(f"Number of (brand, model) with non-zero std in mileage: {(mileage_std_per_model > 0).sum()} of {len(mileage_std_per_model)}")

# Check date_collected
print("\nDate collected summary:")
print("Min:", df["date_collected"].min())
print("Max:", df["date_collected"].max())
print("Unique dates:", df["date_collected"].nunique())
