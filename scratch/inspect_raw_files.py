import os
import glob
import json
import hashlib
import pandas as pd

def inspect_folder(folder):
    files = glob.glob(os.path.join(folder, "*.json"))
    print(f"\n--- Files in {folder} ({len(files)} files) ---")
    for fp in sorted(files):
        size = os.path.getsize(fp)
        with open(fp, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            count = len(data) if isinstance(data, list) else len(data.get("listings", data.get("vehicles", [])))
            # check first record url and id
            first_rec = data[0] if isinstance(data, list) and len(data) > 0 else {}
            sample_keys = list(first_rec.keys())[:5]
            sample_url = first_rec.get("url") or first_rec.get("permalink") or first_rec.get("link") or first_rec.get("source_url") or "none"
        except Exception as e:
            count = f"Error: {e}"
            sample_keys = []
            sample_url = "none"
        print(f"File: {os.path.basename(fp):45s} | Records: {str(count):>4s} | Size: {size:>7d} bytes | Sample URL: {sample_url}")

inspect_folder("data/sample")
inspect_folder("data/raw")
