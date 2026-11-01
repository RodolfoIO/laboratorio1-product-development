"""DAG de seguimiento de pronósticos publicados."""

from __future__ import annotations

import os
from pathlib import Path

from airflow.sdk import DAG, task
from pendulum import datetime

from inventory_forecasting.product.monitor import monitor_forecasts


INPUT_DIR = os.environ.get("LAB1_INPUT_DIR", "/opt/project/store-sales-time-series-forecasting")
FORECAST_DIR = Path(os.environ.get("LAB1_FORECAST_DIR", "/opt/project/data/forecasts"))
REPORT_DIR = Path(os.environ.get("LAB1_REPORT_DIR", "/opt/project/data/reports"))
BUSINESS_PATH = os.environ.get("LAB1_BUSINESS_PATH", "/opt/project/configs/business.yaml")


with DAG(
    dag_id="lab1_monitor_performance",
    schedule="@daily",
    start_date=datetime(2017, 7, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    tags=["lab1", "monitoring"],
) as dag:

    @task
    def monitor() -> dict:
        try:
            return monitor_forecasts(INPUT_DIR, FORECAST_DIR, REPORT_DIR, BUSINESS_PATH)
        except FileNotFoundError:
            # No tener pronósticos publicados todavía es un estado esperado.
            return {"status": "pending", "reason": "no forecasts published yet"}

    monitor()
