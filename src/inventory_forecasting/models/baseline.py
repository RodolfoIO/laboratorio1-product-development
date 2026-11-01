"""Baseline estacional semanal."""

from __future__ import annotations

import numpy as np
import pandas as pd

from inventory_forecasting.data.features import KEYS


def seasonal_naive_forecast(
    history: pd.DataFrame,
    future_dates: list[pd.Timestamp] | pd.DatetimeIndex,
    quantiles: tuple[float, ...] = (0.1, 0.5, 0.9),
) -> pd.DataFrame:
    """Pronostica con rezago de 7 días y fallback a la media reciente."""

    history = history.copy()
    history["date"] = pd.to_datetime(history["date"])
    history = history.sort_values(KEYS + ["date"])
    lookup = history.set_index(KEYS + ["date"])["sales"]
    lagged = history[KEYS + ["date", "sales"]].copy()
    lagged["date"] = lagged["date"] + pd.Timedelta(7, unit="D")
    lagged = lagged.rename(columns={"sales": "lag7"})
    residual_frame = history.merge(lagged, on=KEYS + ["date"], how="inner")
    residuals = (residual_frame["sales"] - residual_frame["lag7"]).to_numpy()
    residuals = np.asarray(residuals if len(residuals) else [0.0])
    recent_means = history.groupby(KEYS)["sales"].apply(lambda values: float(values.tail(28).mean())).to_dict()
    pairs = history[KEYS].drop_duplicates()
    outputs = []
    for date in pd.DatetimeIndex(future_dates):
        for _, pair in pairs.iterrows():
            key = (int(pair["store_nbr"]), pair["family"], date - pd.Timedelta(7, unit="D"))
            if key in lookup:
                point = float(lookup.loc[key])
            else:
                point = recent_means.get((pair["store_nbr"], pair["family"]), 0.0)
            row = {"date": date, "store_nbr": int(pair["store_nbr"]), "family": pair["family"]}
            for quantile in quantiles:
                offset = 0.0 if quantile == 0.5 else float(np.quantile(residuals, quantile))
                row[f"q{int(quantile * 100):02d}"] = max(0.0, point + offset)
            row["prediction"] = row.get("q50", point)
            outputs.append(row)
    return pd.DataFrame(outputs)
