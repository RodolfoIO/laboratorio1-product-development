"""Features point-in-time para entrenamiento y pronóstico recursivo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

KEYS = ["store_nbr", "family"]
BASE_FEATURES = [
    "store_nbr",
    "family_code",
    "cluster",
    "type_code",
    "onpromotion",
    "transactions",
    "oil",
    "is_holiday",
    "day_of_week",
    "day_of_month",
    "month",
    "week_of_year",
]


def load_inputs(input_dir: str | Path) -> dict[str, pd.DataFrame]:
    input_dir = Path(input_dir)
    return {
        "train": pd.read_csv(input_dir / "train.csv", parse_dates=["date"]),
        "stores": pd.read_csv(input_dir / "stores.csv"),
        "holidays": pd.read_csv(input_dir / "holidays_events.csv", parse_dates=["date"]),
        "oil": pd.read_csv(input_dir / "oil.csv", parse_dates=["date"]),
        "transactions": pd.read_csv(input_dir / "transactions.csv", parse_dates=["date"]),
    }


def _holiday_table(holidays: pd.DataFrame, cutoff: pd.Timestamp | None = None) -> pd.DataFrame:
    frame = holidays.copy()
    if cutoff is not None:
        frame = frame[frame["date"] + pd.Timedelta(7, unit="D") <= cutoff]
    frame["is_holiday"] = (~frame["transferred"].astype(str).str.lower().eq("true")).astype(int)
    return frame.groupby("date", as_index=False)["is_holiday"].max()


def _attach_known_metadata(
    frame: pd.DataFrame,
    inputs: dict[str, pd.DataFrame],
    cutoff: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Agrega solamente información disponible al corte indicado."""

    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"]).astype("datetime64[ns]")
    stores = inputs["stores"].copy()
    stores["type_code"] = pd.Categorical(stores["type"]).codes
    frame = frame.merge(stores[["store_nbr", "cluster", "type_code"]], on="store_nbr", how="left", validate="many_to_one")

    transactions = inputs["transactions"].copy()
    if cutoff is not None:
        transactions = transactions[transactions["date"] + pd.Timedelta(1, unit="D") <= cutoff]
    frame = frame.merge(transactions, on=["date", "store_nbr"], how="left", suffixes=("", "_source"))
    frame["transactions"] = frame["transactions"].fillna(0.0)

    oil = inputs["oil"].sort_values("date")[["date", "dcoilwtico"]].rename(columns={"dcoilwtico": "oil"})
    oil["date"] = pd.to_datetime(oil["date"]).astype("datetime64[ns]")
    if cutoff is not None:
        oil = oil[oil["date"] + pd.Timedelta(1, unit="D") <= cutoff]
    frame = pd.merge_asof(frame.sort_values("date"), oil, on="date", direction="backward")
    frame["oil"] = frame["oil"].ffill().fillna(0.0)

    holiday = _holiday_table(inputs["holidays"], cutoff)
    frame = frame.merge(holiday, on="date", how="left")
    frame["is_holiday"] = frame["is_holiday"].fillna(0).astype(int)

    family_order = {name: i for i, name in enumerate(sorted(inputs["train"]["family"].dropna().unique()))}
    frame["family_code"] = frame["family"].map(family_order).fillna(-1).astype(int)
    frame["cluster"] = frame["cluster"].fillna(-1).astype(float)
    frame["type_code"] = frame["type_code"].fillna(-1).astype(float)
    frame["onpromotion"] = pd.to_numeric(frame["onpromotion"], errors="coerce").fillna(0.0)
    frame["day_of_week"] = frame["date"].dt.dayofweek
    frame["day_of_month"] = frame["date"].dt.day
    frame["month"] = frame["date"].dt.month
    frame["week_of_year"] = frame["date"].dt.isocalendar().week.astype(int)
    return frame


def build_training_features(
    inputs: dict[str, pd.DataFrame],
    cutoff: str | pd.Timestamp | None = None,
    lags: tuple[int, ...] = (1, 7, 14, 28),
    rolling_windows: tuple[int, ...] = (7, 28),
) -> tuple[pd.DataFrame, list[str]]:
    """Construye filas cuyo target y features respetan la información disponible."""

    cutoff_ts = pd.Timestamp(cutoff) if cutoff is not None else None
    frame = inputs["train"].copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values(KEYS + ["date"]).reset_index(drop=True)
    if cutoff_ts is not None:
        frame = frame[frame["date"] <= cutoff_ts].copy()
    frame = _attach_known_metadata(frame, inputs, cutoff_ts)
    grouped = frame.groupby(KEYS, sort=False)["sales"]
    for lag in lags:
        frame[f"lag_{lag}"] = grouped.shift(lag)
    for window in rolling_windows:
        frame[f"rolling_mean_{window}"] = grouped.transform(
            lambda values: values.shift(1).rolling(window, min_periods=window).mean()
        )
    feature_columns = BASE_FEATURES + [f"lag_{lag}" for lag in lags] + [f"rolling_mean_{window}" for window in rolling_windows]
    frame = frame.dropna(subset=feature_columns + ["sales"]).reset_index(drop=True)
    frame[feature_columns] = frame[feature_columns].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return frame, feature_columns


def build_forecast_rows(
    history: pd.DataFrame,
    inputs: dict[str, pd.DataFrame],
    target_date: str | pd.Timestamp,
    cutoff: str | pd.Timestamp,
    lags: tuple[int, ...] = (1, 7, 14, 28),
    rolling_windows: tuple[int, ...] = (7, 28),
) -> tuple[pd.DataFrame, list[str]]:
    """Construye filas futuras usando history, sin consultar ventas posteriores al corte."""

    cutoff_ts = pd.Timestamp(cutoff)
    target_ts = pd.Timestamp(target_date)
    max_lookback = max(max(lags), max(rolling_windows)) + 1
    history = history.copy()
    history["date"] = pd.to_datetime(history["date"]).astype("datetime64[ns]")
    history = history[history["date"] >= target_ts - pd.Timedelta(max_lookback, unit="D")]
    pairs = history[KEYS].drop_duplicates().copy()
    pairs["date"] = target_ts
    pairs["onpromotion"] = 0.0
    frame = _attach_known_metadata(pairs, inputs, cutoff_ts)
    base = history[KEYS + ["date", "sales"]].sort_values(KEYS + ["date"])
    for lag in lags:
        shifted = base.copy()
        shifted["date"] = shifted["date"] + pd.Timedelta(lag, unit="D")
        shifted = shifted.rename(columns={"sales": f"lag_{lag}"})
        frame = frame.merge(shifted[KEYS + ["date", f"lag_{lag}"]], on=KEYS + ["date"], how="left")
    for window in rolling_windows:
        rolling = base.copy()
        rolling[f"rolling_mean_{window}"] = rolling.groupby(KEYS, sort=False)["sales"].transform(
            lambda values: values.shift(1).rolling(window, min_periods=1).mean()
        )
        frame = frame.merge(
            rolling[KEYS + ["date", f"rolling_mean_{window}"]],
            on=KEYS + ["date"],
            how="left",
        )
    feature_columns = BASE_FEATURES + [f"lag_{lag}" for lag in lags] + [f"rolling_mean_{window}" for window in rolling_windows]
    frame[feature_columns] = frame[feature_columns].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return frame, feature_columns


def save_training_features(
    input_dir: str | Path,
    output_path: str | Path,
    cutoff: str | None = None,
    params_path: str | Path = "params.yaml",
) -> Path:
    from inventory_forecasting.config import load_params

    params = load_params(params_path)
    inputs = load_inputs(input_dir)
    feature_frame, feature_columns = build_training_features(
        inputs,
        cutoff=cutoff,
        lags=tuple(params["features"]["lags"]),
        rolling_windows=tuple(params["features"]["rolling_windows"]),
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    feature_frame.to_parquet(output_path, index=False)
    output_path.with_suffix(".json").write_text(json.dumps({"feature_columns": feature_columns}, indent=2), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="store-sales-time-series-forecasting")
    parser.add_argument("--cutoff", default=None)
    parser.add_argument("--output", default="data/processed/training_features.parquet")
    args = parser.parse_args()
    output = save_training_features(args.input_dir, args.output, args.cutoff)
    print(f"features: {output}")


if __name__ == "__main__":
    main()
