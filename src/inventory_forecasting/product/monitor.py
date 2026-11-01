"""Seguimiento de pronósticos publicados contra ventas observadas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from inventory_forecasting.config import load_business
from inventory_forecasting.data.features import load_inputs
from inventory_forecasting.models.metrics import evaluate_predictions


def monitor_forecasts(
    input_dir: str | Path,
    forecast_dir: str | Path = "data/forecasts",
    reports_dir: str | Path = "data/reports",
    business_path: str | Path = "configs/business.yaml",
) -> dict:
    inputs = load_inputs(input_dir)
    actual = inputs["train"][["date", "store_nbr", "family", "sales"]].copy()
    actual["date"] = pd.to_datetime(actual["date"])
    forecast_dir = Path(forecast_dir)
    paths = sorted(forecast_dir.glob("forecast_*.parquet"))
    if not paths:
        raise FileNotFoundError(f"no hay pronósticos en {forecast_dir}")
    forecasts = pd.concat([pd.read_parquet(path) for path in paths], ignore_index=True)
    joined = forecasts.merge(
        actual,
        left_on=["target_date", "store_nbr", "family"],
        right_on=["date", "store_nbr", "family"],
        how="left",
    ).drop(columns=["date"])
    observed = joined[joined["sales"].notna()].copy()
    pending = joined[joined["sales"].isna()].copy()
    business = load_business(business_path)["business"]
    metrics = evaluate_predictions(
        observed["sales"],
        observed,
        float(business["stockout_cost"]),
        float(business["waste_cost"]),
    ) if not observed.empty else {}
    by_horizon = []
    if not observed.empty:
        observed["horizon_day"] = (observed["target_date"] - observed["cutoff_date"]).dt.days
        for horizon, group in observed.groupby("horizon_day"):
            values = evaluate_predictions(group["sales"], group, float(business["stockout_cost"]), float(business["waste_cost"]))
            values["horizon_day"] = int(horizon)
            by_horizon.append(values)
    report = {
        "published_rows": len(joined),
        "observed_rows": len(observed),
        "pending_rows": len(pending),
        "metrics": metrics,
        "metrics_by_horizon": by_horizon,
    }
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "performance.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    joined.to_parquet(reports_dir / "performance_detail.parquet", index=False)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="store-sales-time-series-forecasting")
    parser.add_argument("--forecast-dir", default="data/forecasts")
    parser.add_argument("--reports-dir", default="data/reports")
    args = parser.parse_args()
    print(json.dumps(monitor_forecasts(args.input_dir, args.forecast_dir, args.reports_dir), indent=2))


if __name__ == "__main__":
    main()

