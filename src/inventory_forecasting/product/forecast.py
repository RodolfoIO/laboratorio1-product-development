"""Generación y publicación de pronósticos y pedidos."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd

from inventory_forecasting.config import load_business, load_params
from inventory_forecasting.data.features import build_forecast_rows, load_inputs
from inventory_forecasting.models.baseline import seasonal_naive_forecast
from inventory_forecasting.models.global_model import GlobalQuantileModel
from inventory_forecasting.product.order import build_order


def code_version() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "working-tree"


def recursive_forecast(
    inputs: dict[str, pd.DataFrame],
    cutoff: str | pd.Timestamp,
    horizon_days: int,
    model: GlobalQuantileModel | None = None,
    lags: tuple[int, ...] = (1, 7, 14, 28),
    rolling_windows: tuple[int, ...] = (7, 28),
) -> pd.DataFrame:
    cutoff_ts = pd.Timestamp(cutoff)
    history = inputs["train"].copy()
    history["date"] = pd.to_datetime(history["date"])
    history = history[history["date"] <= cutoff_ts][["date", "store_nbr", "family", "sales"]].copy()
    future_dates = pd.date_range(cutoff_ts + pd.Timedelta(1, unit="D"), periods=horizon_days, freq="D")
    outputs: list[pd.DataFrame] = []
    for target_date in future_dates:
        if model is None:
            prediction = seasonal_naive_forecast(history, [target_date])
            rows = prediction[["store_nbr", "family"]].copy()
        else:
            rows, _ = build_forecast_rows(history, inputs, target_date, cutoff_ts, lags, rolling_windows)
            prediction = model.predict(rows)
            prediction = pd.concat(
                [rows[["store_nbr", "family"]].reset_index(drop=True), prediction.reset_index(drop=True)], axis=1
            )
        prediction = prediction.rename(columns={"date": "target_date"})
        prediction["target_date"] = target_date
        prediction["cutoff_date"] = cutoff_ts
        prediction["prediction"] = prediction["q50"]
        outputs.append(prediction)
        appended = prediction[["target_date", "store_nbr", "family", "prediction"]].rename(columns={"target_date": "date", "prediction": "sales"})
        history = pd.concat([history, appended], ignore_index=True)
    return pd.concat(outputs, ignore_index=True)


def publish_forecast(
    input_dir: str | Path,
    cutoff: str | pd.Timestamp,
    output_dir: str | Path,
    model_path: str | Path | None = None,
    params_path: str | Path = "params.yaml",
    business_path: str | Path = "configs/business.yaml",
) -> tuple[Path, Path]:
    params = load_params(params_path)
    business = load_business(business_path)
    inputs = load_inputs(input_dir)
    model = GlobalQuantileModel.load(model_path) if model_path and Path(model_path).exists() else None
    predictions = recursive_forecast(
        inputs,
        cutoff,
        int(params["forecast"]["horizon_days"]),
        model=model,
        lags=tuple(params["features"]["lags"]),
        rolling_windows=tuple(params["features"]["rolling_windows"]),
    )
    predictions["model_name"] = "global_ml" if model is not None else "baseline"
    predictions["model_version"] = Path(model_path).name if model_path and model is not None else "baseline-v1"
    predictions["code_version"] = code_version()
    predictions["data_version"] = hashlib.sha256(
        inputs["train"].to_csv(index=False).encode("utf-8")
    ).hexdigest()[:16]
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cutoff_label = pd.Timestamp(cutoff).date().isoformat()
    forecast_path = output_dir / f"forecast_{cutoff_label}.parquet"
    predictions.to_parquet(forecast_path, index=False)
    orders = build_order(
        predictions,
        float(business["business"]["stockout_cost"]),
        float(business["business"]["waste_cost"]),
        float(business["business"].get("minimum_order", 0.0)),
    )
    orders["model_name"] = predictions["model_name"].iloc[0]
    orders["model_version"] = predictions["model_version"].iloc[0]
    orders["code_version"] = predictions["code_version"].iloc[0]
    orders["data_version"] = predictions["data_version"].iloc[0]
    order_path = output_dir / f"order_{cutoff_label}.parquet"
    orders.to_parquet(order_path, index=False)
    return forecast_path, order_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="store-sales-time-series-forecasting")
    parser.add_argument("--cutoff", required=True)
    parser.add_argument("--output-dir", default="data/forecasts")
    parser.add_argument("--model", default="data/models/global_model.joblib")
    args = parser.parse_args()
    paths = publish_forecast(args.input_dir, args.cutoff, args.output_dir, args.model)
    print("\n".join(map(str, paths)))


if __name__ == "__main__":
    main()
