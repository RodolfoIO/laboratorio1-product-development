"""Modelo global tabular con regresión cuantílica."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor


class GlobalQuantileModel:
    def __init__(self, quantiles=(0.1, 0.5, 0.9), model_params: dict[str, Any] | None = None):
        self.quantiles = tuple(float(value) for value in quantiles)
        self.model_params = model_params or {}
        self.feature_columns: list[str] = []
        self.models: dict[float, HistGradientBoostingRegressor] = {}

    def fit(self, frame: pd.DataFrame, feature_columns: list[str], target: str = "sales") -> "GlobalQuantileModel":
        self.feature_columns = list(feature_columns)
        X = frame[self.feature_columns].astype(float).fillna(0.0)
        y = pd.to_numeric(frame[target], errors="coerce").fillna(0.0).clip(lower=0.0)
        for quantile in self.quantiles:
            estimator = HistGradientBoostingRegressor(
                loss="quantile",
                quantile=quantile,
                random_state=42,
                **self.model_params,
            )
            estimator.fit(X, y)
            self.models[quantile] = estimator
        return self

    def predict(self, frame: pd.DataFrame) -> pd.DataFrame:
        if not self.models:
            raise RuntimeError("el modelo no está entrenado")
        X = frame[self.feature_columns].astype(float).fillna(0.0)
        result = {}
        for quantile, model in self.models.items():
            result[f"q{int(quantile * 100):02d}"] = np.maximum(0.0, model.predict(X))
        prediction = pd.DataFrame(result, index=frame.index)
        q_columns = sorted(result)
        for left, right in zip(q_columns, q_columns[1:]):
            prediction[right] = np.maximum(prediction[right], prediction[left])
        prediction["prediction"] = prediction.get("q50", prediction[q_columns[len(q_columns) // 2]])
        return prediction

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        return path

    @classmethod
    def load(cls, path: str | Path) -> "GlobalQuantileModel":
        return joblib.load(path)

