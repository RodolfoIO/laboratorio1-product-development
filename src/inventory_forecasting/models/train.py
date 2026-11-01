"""Entrenamiento, validación temporal y promoción del modelo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from inventory_forecasting.config import load_business, load_params
from inventory_forecasting.data.features import build_training_features, load_inputs
from inventory_forecasting.models.baseline import seasonal_naive_forecast
from inventory_forecasting.models.global_model import GlobalQuantileModel
from inventory_forecasting.models.metrics import evaluate_predictions, select_model
from inventory_forecasting.product.forecast import recursive_forecast


def train_and_evaluate(
    input_dir: str | Path,
    model_dir: str | Path = "data/models",
    params_path: str | Path = "params.yaml",
    business_path: str | Path = "configs/business.yaml",
) -> dict:
    params = load_params(params_path)
    business = load_business(business_path)
    inputs = load_inputs(input_dir)
    train = inputs["train"].copy()
    train["date"] = pd.to_datetime(train["date"])
    max_date = train["date"].max()
    validation_days = int(params["forecast"]["validation_days"])
    validation_start = max_date - pd.Timedelta(validation_days - 1, unit="D")
    fit_end = validation_start - pd.Timedelta(1, unit="D")

    fit_frame, feature_columns = build_training_features(
        inputs,
        cutoff=fit_end,
        lags=tuple(params["features"]["lags"]),
        rolling_windows=tuple(params["features"]["rolling_windows"]),
    )
    max_rows = int(params["model"].get("max_training_rows", 0))
    if max_rows and len(fit_frame) > max_rows:
        fit_frame = fit_frame.sample(n=max_rows, random_state=int(params.get("seed", 42))).copy()
    model_params = {
        key: value
        for key, value in params["model"].items()
        if key in {"max_iter", "learning_rate", "max_leaf_nodes", "min_samples_leaf", "l2_regularization"}
    }
    model = GlobalQuantileModel(params["forecast"]["quantiles"], model_params).fit(fit_frame, feature_columns)
    model_dir = Path(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model.save(model_dir / "global_model.joblib")

    validation_dates = pd.date_range(validation_start, max_date, freq="D")
    history = train[train["date"] <= fit_end]
    actual = train[train["date"] >= validation_start][["date", "store_nbr", "family", "sales"]].copy()
    baseline = seasonal_naive_forecast(history, validation_dates)
    ml = recursive_forecast(
        inputs,
        fit_end,
        validation_days,
        model=model,
        lags=tuple(params["features"]["lags"]),
        rolling_windows=tuple(params["features"]["rolling_windows"]),
    )
    join_keys = ["target_date", "store_nbr", "family"]
    baseline = baseline.rename(columns={"date": "target_date"})
    actual = actual.rename(columns={"date": "target_date"})
    baseline_eval = actual.merge(baseline, on=join_keys, how="inner")
    ml_eval = actual.merge(ml, on=join_keys, how="inner")
    stockout = float(business["business"]["stockout_cost"])
    waste = float(business["business"]["waste_cost"])
    baseline_metrics = evaluate_predictions(baseline_eval["sales"], baseline_eval, stockout, waste)
    ml_metrics = evaluate_predictions(ml_eval["sales"], ml_eval, stockout, waste)
    selected = select_model(
        baseline_metrics,
        ml_metrics,
        float(params["selection"]["min_business_improvement"]),
        float(params["selection"]["max_wape_regression"]),
    )
    result = {
        "validation_start": validation_start.date().isoformat(),
        "validation_end": max_date.date().isoformat(),
        "baseline": baseline_metrics,
        "global_ml": ml_metrics,
        "selected_model": selected,
        "model_path": str(model_path),
        "training_rows": len(fit_frame),
        "validation_rows": len(actual),
    }
    (model_dir / "metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    comparison = pd.DataFrame(
        [
            {"model": "baseline", **baseline_metrics},
            {"model": "global_ml", **ml_metrics},
        ]
    )
    comparison.to_csv(model_dir / "model_comparison.csv", index=False)
    (model_dir / "current_model.json").write_text(
        json.dumps(
            {
                "model": selected,
                "model_path": str(model_path),
                "selection": {
                    "min_business_improvement": float(params["selection"]["min_business_improvement"]),
                    "max_wape_regression": float(params["selection"]["max_wape_regression"]),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="store-sales-time-series-forecasting")
    parser.add_argument("--model-dir", default="data/models")
    args = parser.parse_args()
    print(json.dumps(train_and_evaluate(args.input_dir, args.model_dir), indent=2))


if __name__ == "__main__":
    main()
