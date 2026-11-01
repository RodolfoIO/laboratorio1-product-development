"""Métricas técnicas, cuantílicas y de negocio."""

from __future__ import annotations

import numpy as np
import pandas as pd


def mae(actual: pd.Series, predicted: pd.Series) -> float:
    return float(np.mean(np.abs(actual.to_numpy() - predicted.to_numpy())))


def wape(actual: pd.Series, predicted: pd.Series) -> float:
    denominator = float(np.abs(actual.to_numpy()).sum())
    return float(np.abs(actual.to_numpy() - predicted.to_numpy()).sum() / denominator) if denominator else 0.0


def pinball_loss(actual: pd.Series, predicted: pd.Series, quantile: float) -> float:
    error = actual.to_numpy() - predicted.to_numpy()
    return float(np.mean(np.maximum(quantile * error, (quantile - 1) * error)))


def business_loss(
    actual: pd.Series,
    predicted: pd.Series,
    stockout_cost: float,
    waste_cost: float,
) -> float:
    error = actual.to_numpy() - predicted.to_numpy()
    return float(np.mean(stockout_cost * np.maximum(error, 0) + waste_cost * np.maximum(-error, 0)))


def evaluate_predictions(
    actual: pd.Series,
    predictions: pd.DataFrame,
    stockout_cost: float,
    waste_cost: float,
) -> dict[str, float]:
    result = {
        "mae": mae(actual, predictions["prediction"]),
        "wape": wape(actual, predictions["prediction"]),
        "business_loss": business_loss(actual, predictions["prediction"], stockout_cost, waste_cost),
    }
    for quantile in (0.1, 0.5, 0.9):
        column = f"q{int(quantile * 100):02d}"
        if column in predictions:
            result[f"pinball_{column}"] = pinball_loss(actual, predictions[column], quantile)
    return result


def select_model(
    baseline: dict[str, float],
    candidate: dict[str, float],
    min_business_improvement: float = 0.05,
    max_wape_regression: float = 0.02,
) -> str:
    baseline_loss = baseline["business_loss"]
    business_improvement = (baseline_loss - candidate["business_loss"]) / baseline_loss if baseline_loss else 0.0
    wape_ok = candidate["wape"] <= baseline["wape"] * (1 + max_wape_regression)
    return "global_ml" if business_improvement >= min_business_improvement and wape_ok else "baseline"

