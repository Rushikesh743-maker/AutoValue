"""
AutoValue Model Registry and Artifact Integrity Service.
Manages versioned ML artifacts, validates SHA-256 integrity checksums,
and safely serves model metadata and active predictors.
"""
import os
import json
import hashlib
import logging
from typing import Dict, Any, List, Optional, Tuple
import joblib

from backend.app.core.config import settings
from backend.app.core.exceptions import ModelNotFoundError, ModelIntegrityError

logger = logging.getLogger("autovalue.model_registry")


def compute_file_sha256(filepath: str) -> Optional[str]:
    """Computes SHA-256 cryptographic hash of a file on disk."""
    if not os.path.exists(filepath):
        return None
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


class ModelRegistry:
    """
    Centralized model registry service for managing, loading, and verifying versioned ML models.
    """

    def __init__(self, models_dir: Optional[str] = None):
        self.models_dir = models_dir or settings.MODELS_DIR
        self._loaded_models: Dict[str, Any] = {}
        self._loaded_preprocessors: Dict[str, Any] = {}
        self._loaded_metadata: Dict[str, Dict[str, Any]] = {}

    def get_artifact_paths(self, version: str) -> Dict[str, str]:
        """Returns expected paths for model, preprocessor, and metadata files."""
        return {
            "model_path": os.path.join(self.models_dir, f"model_{version}.joblib"),
            "preprocessor_path": os.path.join(self.models_dir, f"preprocessor_{version}.joblib"),
            "metadata_path": os.path.join(self.models_dir, f"metadata_{version}.json")
        }

    def verify_artifact_integrity(self, version: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Validates artifact existence and cryptographic SHA-256 checksums.
        """
        paths = self.get_artifact_paths(version)
        model_path = paths["model_path"]
        prep_path = paths["preprocessor_path"]
        meta_path = paths["metadata_path"]

        if not os.path.exists(model_path):
            raise ModelNotFoundError(version, f"Model artifact '{model_path}' not found.")
        if not os.path.exists(prep_path):
            raise ModelNotFoundError(version, f"Preprocessor artifact '{prep_path}' not found.")
        if not os.path.exists(meta_path):
            raise ModelNotFoundError(version, f"Metadata file '{meta_path}' not found.")

        # Compute actual checksums
        actual_model_sha = compute_file_sha256(model_path)
        actual_prep_sha = compute_file_sha256(prep_path)

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        integrity_info = meta.get("artifact_integrity", {})
        expected_model_sha = integrity_info.get("model_sha256")
        expected_prep_sha = integrity_info.get("preprocessor_sha256")

        model_checksum_match = True
        prep_checksum_match = True

        if expected_model_sha and expected_model_sha != actual_model_sha:
            model_checksum_match = False
            logger.error(f"Model {version} SHA256 mismatch! Expected {expected_model_sha}, got {actual_model_sha}")
            raise ModelIntegrityError(f"Model artifact {version} checksum verification failed. Possible file corruption.")

        if expected_prep_sha and expected_prep_sha != actual_prep_sha:
            prep_checksum_match = False
            logger.error(f"Preprocessor {version} SHA256 mismatch! Expected {expected_prep_sha}, got {actual_prep_sha}")
            raise ModelIntegrityError(f"Preprocessor artifact {version} checksum verification failed. Possible file corruption.")

        return True, {
            "model_version": version,
            "model_sha256": actual_model_sha,
            "preprocessor_sha256": actual_prep_sha,
            "model_checksum_verified": model_checksum_match,
            "preprocessor_checksum_verified": prep_checksum_match,
            "dataset_version": meta.get("dataset_version", "v0.3"),
            "selected_model": meta.get("selected_model", "Unknown")
        }

    def load_model_bundle(self, version: Optional[str] = None) -> Tuple[Any, Any, Dict[str, Any]]:
        """
        Loads and verifies model, preprocessor, and metadata for the specified or active model version.
        Caches in memory for instant subsequent lookups.
        """
        ver = version or settings.AUTOVALUE_MODEL_VERSION
        if ver in self._loaded_models and ver in self._loaded_preprocessors:
            return self._loaded_models[ver], self._loaded_preprocessors[ver], self._loaded_metadata[ver]

        # Verify integrity before loading
        self.verify_artifact_integrity(ver)

        paths = self.get_artifact_paths(ver)
        try:
            model = joblib.load(paths["model_path"])
            preprocessor = joblib.load(paths["preprocessor_path"])
            with open(paths["metadata_path"], "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load joblib model bundle for version {ver}: {e}")
            raise ModelNotFoundError(ver, f"Failed to load model bundle {ver}: {e}")

        self._loaded_models[ver] = model
        self._loaded_preprocessors[ver] = preprocessor
        self._loaded_metadata[ver] = metadata

        logger.info(f"Successfully loaded and verified model bundle '{ver}' ({metadata.get('selected_model')}).")
        return model, preprocessor, metadata

    def list_available_models(self) -> List[Dict[str, Any]]:
        """
        Discovers all available model versions in the models directory and returns sanitized metadata.
        """
        active_ver = settings.AUTOVALUE_MODEL_VERSION
        versions = []

        if not os.path.exists(self.models_dir):
            return []

        for fname in os.listdir(self.models_dir):
            if fname.startswith("metadata_") and fname.endswith(".json"):
                ver = fname.replace("metadata_", "").replace(".json", "")
                meta_path = os.path.join(self.models_dir, fname)
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        versions.append({
                            "model_version": ver,
                            "dataset_version": meta.get("dataset_version", "v0.2"),
                            "status": "active" if ver == active_ver else "available",
                            "selected_model": meta.get("selected_model"),
                            "metrics": meta.get("metrics_test") or meta.get("metrics"),
                            "training_timestamp": meta.get("training_timestamp"),
                            "evaluation_strategy": meta.get("evaluation_strategy", "standard"),
                            "has_integrity_record": "artifact_integrity" in meta
                        })
                except Exception:
                    pass

        return sorted(versions, key=lambda x: x["model_version"], reverse=True)


# Global singleton registry
model_registry = ModelRegistry()
