"""Conversión de cuantiles a pedido sugerido."""

from __future__ import annotations

import math

import pandas as pd


def critical_quantile(stockout_cost: float, waste_cost: float) -> float:
    if stockout_cost < 0 or waste_cost < 0 or stockout_cost + waste_cost <= 0:
        raise ValueError("los costos deben ser no negativos y al menos uno debe ser positivo")
    return stockout_cost / (stockout_cost + waste_cost)


def interpolate_quantile(row: pd.Series, quantile: float) -> float:
    points = [(0.1, row.get("q10", 0.0)), (0.5, row.get("q50", 0.0)), (0.9, row.get("q90", 0.0))]
    if quantile <= points[0][0]:
        return float(points[0][1])
    if quantile >= points[-1][0]:
        return float(points[-1][1])
    for (left_q, left_value), (right_q, right_value) in zip(points, points[1:]):
        if left_q <= quantile <= right_q:
            fraction = (quantile - left_q) / (right_q - left_q)
            return float(left_value + fraction * (right_value - left_value))
    return float(row.get("q50", 0.0))


def build_order(
    forecasts: pd.DataFrame,
    stockout_cost: float,
    waste_cost: float,
    minimum_order: float = 0.0,
) -> pd.DataFrame:
    required = {"cutoff_date", "target_date", "store_nbr", "family", "q10", "q50", "q90"}
    missing = required - set(forecasts.columns)
    if missing:
        raise ValueError(f"faltan columnas en pronósticos: {sorted(missing)}")
    alpha = critical_quantile(stockout_cost, waste_cost)
    result = forecasts.copy()
    result["critical_quantile"] = alpha
    result["demand_at_critical_quantile"] = result.apply(lambda row: interpolate_quantile(row, alpha), axis=1)
    grouped = result.groupby(["cutoff_date", "store_nbr", "family"], as_index=False).agg(
        suggested_order=("demand_at_critical_quantile", "sum"),
        forecast_mean=("q50", "sum"),
        critical_quantile=("critical_quantile", "first"),
    )
    grouped["suggested_order"] = grouped["suggested_order"].map(lambda value: max(minimum_order, math.ceil(max(0.0, value))))
    grouped["stockout_cost"] = stockout_cost
    grouped["waste_cost"] = waste_cost
    return grouped

