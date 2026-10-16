"""
Dataset Partitioning Strategies.
Provides standard, duplicate-safe (group-aware), 3-way (train/val/test), and temporal split utilities
to eliminate information leakage across physical vehicles and evaluate time generalization.
"""
from typing import Tuple, Optional, List, Dict, Any, Set
from collections import defaultdict
import pandas as pd
import numpy as np


class _UnionFind:
    """Disjoint-set data structure for fast vehicle cluster tracking."""
    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, i: int) -> int:
        if self.parent[i] == i:
            return i
        self.parent[i] = self.find(self.parent[i])
        return self.parent[i]

    def union(self, i: int, j: int) -> None:
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            self.parent[root_i] = root_j


def build_vehicle_clusters(df: pd.DataFrame) -> np.ndarray:
    """
    Constructs connected vehicle cluster IDs for each row in the DataFrame.
    Identifies duplicate listings, re-listings across platforms, and near-duplicate physical vehicles
    using listing identifiers, explicit duplicate links, exact specifications, and defensible similarity rules.

    Does not rely solely on `duplicate_of_id` (which may be null after pipeline filtering),
    and avoids grouping unrelated vehicles together.
    """
    n = len(df)
    if n == 0:
        return np.array([], dtype=int)
    if n == 1:
        return np.array([0], dtype=int)

    uf = _UnionFind(n)
    records = df.to_dict("records")

    # 1. Group by explicit listing_id
    if "listing_id" in df.columns:
        lid_map: Dict[str, List[int]] = defaultdict(list)
        for idx, val in enumerate(df["listing_id"]):
            if pd.notnull(val) and str(val).strip():
                lid_map[str(val).strip()].append(idx)
        for indices in lid_map.values():
            for i in indices[1:]:
                uf.union(indices[0], i)

    # 2. Group by exact non-generic listing_url
    if "listing_url" in df.columns:
        url_map: Dict[str, List[int]] = defaultdict(list)
        for idx, val in enumerate(df["listing_url"]):
            v = str(val).strip() if pd.notnull(val) else ""
            if v and v != "https://example.com":
                url_map[v].append(idx)
        for indices in url_map.values():
            for i in indices[1:]:
                uf.union(indices[0], i)

    # 3. Explicit duplicate_of_id references
    if "id" in df.columns and "duplicate_of_id" in df.columns:
        id_to_idx = {row["id"]: idx for idx, row in enumerate(records) if pd.notnull(row.get("id"))}
        for idx, row in enumerate(records):
            dup_of = row.get("duplicate_of_id")
            if pd.notnull(dup_of) and dup_of in id_to_idx:
                uf.union(idx, id_to_idx[dup_of])

    # 4. Physical specification matching within (brand, model) buckets
    bm_groups: Dict[Tuple[str, str], List[int]] = defaultdict(list)
    for idx, r in enumerate(records):
        b = str(r.get("brand") or "").strip().lower()
        m = str(r.get("model") or "").strip().lower()
        bm_groups[(b, m)].append(idx)

    for (b, m), indices in bm_groups.items():
        if len(indices) <= 1:
            continue
        for i_pos in range(len(indices)):
            idx_i = indices[i_pos]
            r_i = records[idx_i]
            for j_pos in range(i_pos + 1, len(indices)):
                idx_j = indices[j_pos]
                if uf.find(idx_i) == uf.find(idx_j):
                    continue
                r_j = records[idx_j]

                # Year check (exact or registration tolerance <= 1)
                y_i, y_j = r_i.get("year"), r_j.get("year")
                if y_i is not None and y_j is not None and abs(int(y_i) - int(y_j)) > 1:
                    continue

                # Fuel type
                f_i = str(r_i.get("fuel_type") or "").strip().lower()
                f_j = str(r_j.get("fuel_type") or "").strip().lower()
                if f_i and f_j and f_i != f_j:
                    continue

                # Transmission
                t_i = str(r_i.get("transmission") or "").strip().lower()
                t_j = str(r_j.get("transmission") or "").strip().lower()
                if t_i and t_j and t_i != t_j:
                    continue

                # City
                c_i = str(r_i.get("city") or "").strip().lower()
                c_j = str(r_j.get("city") or "").strip().lower()
                if c_i and c_j and c_i != c_j:
                    continue

                # Odometer km_driven (within 15% tolerance)
                km_i, km_j = r_i.get("km_driven"), r_j.get("km_driven")
                if km_i is not None and km_j is not None and km_i > 0 and km_j > 0:
                    max_km = max(km_i, km_j)
                    if abs(km_i - km_j) / max_km > 0.15:
                        continue

                # Listed price (within 20% tolerance)
                p_i, p_j = r_i.get("listed_price"), r_j.get("listed_price")
                if p_i is not None and p_j is not None and p_i > 0 and p_j > 0:
                    max_p = max(p_i, p_j)
                    if abs(p_i - p_j) / max_p > 0.20:
                        continue

                # All physical attributes match within tolerance -> same vehicle cluster
                uf.union(idx_i, idx_j)

    return np.array([uf.find(i) for i in range(n)], dtype=int)


def duplicate_safe_train_val_test_split(
    df: pd.DataFrame,
    val_size: float = 0.15,
    test_size: float = 0.15,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Partitions DataFrame into 3 disjoint sets: train, validation/calibration, and final test,
    guaranteeing that duplicate candidates and listings of the same physical vehicle remain
    strictly within the same partition.

    Returns:
        (train_df, val_df, test_df)
    """
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    if len(df) <= 2:
        return df.copy(), pd.DataFrame(), pd.DataFrame()

    working_df = df.copy().reset_index(drop=True)
    working_df["_cluster_id"] = build_vehicle_clusters(working_df)

    # Sort unique cluster IDs deterministically before shuffling with seeded RNG
    unique_clusters = np.sort(working_df["_cluster_id"].unique())
    rng = np.random.RandomState(random_state)
    shuffled_clusters = rng.permutation(unique_clusters)

    n_test_clusters = max(1, int(len(shuffled_clusters) * test_size))
    n_val_clusters = max(1, int(len(shuffled_clusters) * val_size))

    test_cluster_ids: Set[int] = set(shuffled_clusters[:n_test_clusters])
    val_cluster_ids: Set[int] = set(shuffled_clusters[n_test_clusters:n_test_clusters + n_val_clusters])

    test_mask = working_df["_cluster_id"].isin(test_cluster_ids)
    val_mask = working_df["_cluster_id"].isin(val_cluster_ids)
    train_mask = ~(test_mask | val_mask)

    test_df = working_df[test_mask].drop(columns=["_cluster_id"]).copy()
    val_df = working_df[val_mask].drop(columns=["_cluster_id"]).copy()
    train_df = working_df[train_mask].drop(columns=["_cluster_id"]).copy()

    return train_df, val_df, test_df


def duplicate_safe_train_test_split(
    df: pd.DataFrame,
    test_size: float = 0.2,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Partitions DataFrame into train and test splits while guaranteeing that related
    duplicate candidates and listings of the same physical vehicle remain in the same partition.
    """
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    if len(df) <= 1:
        return df.copy(), pd.DataFrame()

    working_df = df.copy().reset_index(drop=True)
    working_df["_cluster_id"] = build_vehicle_clusters(working_df)

    # Sort unique cluster IDs deterministically before shuffling with seeded RNG
    unique_clusters = np.sort(working_df["_cluster_id"].unique())
    rng = np.random.RandomState(random_state)
    shuffled_clusters = rng.permutation(unique_clusters)

    n_test_clusters = max(1, int(len(shuffled_clusters) * test_size))
    test_cluster_ids = set(shuffled_clusters[:n_test_clusters])

    test_mask = working_df["_cluster_id"].isin(test_cluster_ids)
    test_df = working_df[test_mask].drop(columns=["_cluster_id"]).copy()
    train_df = working_df[~test_mask].drop(columns=["_cluster_id"]).copy()

    return train_df, test_df


def standard_train_test_split(
    df: pd.DataFrame,
    test_size: float = 0.2,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Standard random train/test split.
    """
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    if len(df) <= 1:
        return df.copy(), pd.DataFrame()

    shuffled = df.sample(frac=1.0, random_state=random_state).reset_index(drop=True)
    n_test = max(1, int(len(df) * test_size))
    test_df = shuffled.iloc[:n_test].copy()
    train_df = shuffled.iloc[n_test:].copy()
    return train_df, test_df


def temporal_train_test_split(
    df: pd.DataFrame,
    test_size: float = 0.2,
    date_col: str = "date_collected"
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Temporal train/test split.
    Earlier collected listings go into training, later listings into test set.
    """
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    if len(df) <= 1:
        return df.copy(), pd.DataFrame()

    working_df = df.copy()
    if date_col in working_df.columns and working_df[date_col].notnull().any():
        working_df[date_col] = pd.to_datetime(working_df[date_col], errors="coerce")
        working_df = working_df.sort_values(by=date_col).reset_index(drop=True)
    elif "year" in working_df.columns:
        working_df = working_df.sort_values(by="year").reset_index(drop=True)
    else:
        return standard_train_test_split(df, test_size=test_size)

    n_test = max(1, int(len(working_df) * test_size))
    split_idx = len(working_df) - n_test
    train_df = working_df.iloc[:split_idx].copy()
    test_df = working_df.iloc[split_idx:].copy()

    return train_df, test_df
