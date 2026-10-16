"""
AutoValue Hyperparameter Tuning Module.
Explores reproducible parameter configurations for tree regression models
using 5-Fold Cross Validation.
"""
from typing import Dict, Any, Tuple, Optional, List
import logging
import numpy as np
import pandas as pd
from sklearn.model_selection import KFold, RandomizedSearchCV
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.pipeline import Pipeline

from ml.features.preprocessor import create_preprocessor_pipeline

logger = logging.getLogger("autovalue.ml.tuning")


class HyperparameterTuner:
    """
    Performs bounded hyperparameter tuning across candidate regression models.
    """

    def __init__(self, cv_folds: int = 5, n_iter: int = 15, random_state: int = 42):
        self.cv_folds = cv_folds
        self.n_iter = n_iter
        self.random_state = random_state

    def tune_random_forest(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series
    ) -> Tuple[RandomForestRegressor, Dict[str, Any], float]:
        """
        Tunes Random Forest Regressor hyperparameters.
        """
        param_distributions = {
            "regressor__n_estimators": [100, 150, 200, 250],
            "regressor__max_depth": [8, 12, 16, 20, None],
            "regressor__min_samples_split": [2, 4, 6],
            "regressor__min_samples_leaf": [1, 2, 4],
            "regressor__max_features": ["sqrt", 0.7, 0.9, 1.0]
        }

        pipeline = Pipeline(steps=[
            ("preprocessor", create_preprocessor_pipeline()),
            ("regressor", RandomForestRegressor(random_state=self.random_state))
        ])

        cv = KFold(n_splits=self.cv_folds, shuffle=True, random_state=self.random_state)
        search = RandomizedSearchCV(
            pipeline,
            param_distributions=param_distributions,
            n_iter=self.n_iter,
            cv=cv,
            scoring="neg_mean_absolute_error",
            random_state=self.random_state,
            n_jobs=1
        )

        search.fit(X_train, y_train)
        best_pipe = search.best_estimator_
        best_params = search.best_params_
        best_score = float(-search.best_score_)

        clean_params = {k.replace("regressor__", ""): v for k, v in best_params.items()}
        logger.info(f"Tuned Random Forest - Best CV MAE: {best_score:,.0f}, Params: {clean_params}")

        return best_pipe.named_steps["regressor"], clean_params, best_score

    def tune_hist_gradient_boosting(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series
    ) -> Tuple[HistGradientBoostingRegressor, Dict[str, Any], float]:
        """
        Tunes HistGradientBoostingRegressor hyperparameters.
        """
        param_distributions = {
            "regressor__max_iter": [100, 150, 200],
            "regressor__learning_rate": [0.03, 0.05, 0.08, 0.12],
            "regressor__max_depth": [4, 6, 8, None],
            "regressor__min_samples_leaf": [10, 20, 30],
            "regressor__l2_regularization": [0.0, 0.1, 1.0]
        }

        pipeline = Pipeline(steps=[
            ("preprocessor", create_preprocessor_pipeline()),
            ("regressor", HistGradientBoostingRegressor(random_state=self.random_state))
        ])

        cv = KFold(n_splits=self.cv_folds, shuffle=True, random_state=self.random_state)
        search = RandomizedSearchCV(
            pipeline,
            param_distributions=param_distributions,
            n_iter=min(12, self.n_iter),
            cv=cv,
            scoring="neg_mean_absolute_error",
            random_state=self.random_state,
            n_jobs=1
        )

        search.fit(X_train, y_train)
        best_pipe = search.best_estimator_
        best_params = search.best_params_
        best_score = float(-search.best_score_)

        clean_params = {k.replace("regressor__", ""): v for k, v in best_params.items()}
        logger.info(f"Tuned HistGB - Best CV MAE: {best_score:,.0f}, Params: {clean_params}")

        return best_pipe.named_steps["regressor"], clean_params, best_score
