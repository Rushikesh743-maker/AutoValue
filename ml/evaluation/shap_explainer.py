"""
SHAP (SHapley Additive exPlanations) foundation module for AutoValue tree-based models.
Computes genuine feature-level price contributions (depreciation, brand premium, usage penalty)
strictly derived from trained models without fabricating explanation values.
"""
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger("autovalue.ml.shap")

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False


class AutoValueSHAPExplainer:
    """
    Computes local feature attributions for vehicle valuations using SHAP TreeExplainer.
    """

    def __init__(self, model: Any, preprocessor: Any, feature_names: Optional[List[str]] = None):
        self.model = model
        self.preprocessor = preprocessor
        self.feature_names = feature_names
        if not self.feature_names and self.preprocessor is not None:
            try:
                from ml.features.preprocessor import get_feature_names_out
                self.feature_names = get_feature_names_out(self.preprocessor)
            except Exception as e:
                logger.warning(f"Could not extract feature names from preprocessor: {e}")
                self.feature_names = None
        self.explainer = None
        self._init_explainer()

    def _init_explainer(self):
        if not SHAP_AVAILABLE:
            logger.info("SHAP package not installed. Attribution explainer is disabled.")
            return

        try:
            # TreeExplainer is supported for RandomForest, GradientBoosting, XGBoost, etc.
            self.explainer = shap.TreeExplainer(self.model)
        except Exception as e:
            logger.warning(f"Failed to initialize SHAP TreeExplainer: {e}")
            self.explainer = None

    @property
    def is_available(self) -> bool:
        return SHAP_AVAILABLE and self.explainer is not None

    def explain_prediction(self, X_input: pd.DataFrame) -> Dict[str, Any]:
        """
        Computes SHAP feature attribution values for a transformed input sample.
        Returns baseline value and top positive/negative feature contributions in INR.
        """
        if not self.is_available:
            return {
                "available": False,
                "reason": "SHAP library or TreeExplainer is not initialized for this model.",
                "attributions": []
            }

        try:
            X_trans = self.preprocessor.transform(X_input)
            shap_values = self.explainer.shap_values(X_trans)
            
            # Base value (expected value over training set)
            base_val = 0.0
            if hasattr(self.explainer, "expected_value"):
                ev = self.explainer.expected_value
                if isinstance(ev, (list, np.ndarray)) and len(ev) > 0:
                    base_val = float(ev[0])
                else:
                    base_val = float(ev)

            # Map attributions to feature names
            features = self.feature_names or [f"Feature_{i}" for i in range(X_trans.shape[1])]
            if isinstance(shap_values, list):
                values = np.asarray(shap_values[0]).flatten()
            else:
                values = np.asarray(shap_values).flatten()

            attributions = []
            for i, f_name in enumerate(features):
                if i < len(values):
                    val = float(values[i])
                    if abs(val) > 10.0:  # Include meaningful non-zero contributions
                        attributions.append({
                            "feature": f_name,
                            "impact_inr": round(val, 2),
                            "direction": "increases_price" if val > 0 else "decreases_price"
                        })

            # Sort by absolute impact
            attributions = sorted(attributions, key=lambda x: abs(x["impact_inr"]), reverse=True)

            return {
                "available": True,
                "base_value_inr": round(base_val, 2),
                "attributions": attributions
            }
        except Exception as e:
            logger.error(f"Error computing SHAP values: {e}")
            return {
                "available": False,
                "reason": str(e),
                "attributions": []
            }
