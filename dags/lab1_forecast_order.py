"""DAG semanal de pronóstico y pedido sugerido."""

from __future__ import annotations

import os
from pathlib import Path

from airflow.sdk import DAG, task
from pendulum import datetime

from inventory_forecasting.product.forecast import publish_forecast


INPUT_DIR = os.environ.get("LAB1_INPUT_DIR", "/opt/project/store-sales-time-series-forecasting")
OUTPUT_DIR = Path(os.environ.get("LAB1_FORECAST_DIR", "/opt/project/data/forecasts"))
MODEL_PATH = os.environ.get("LAB1_MODEL_PATH", "/opt/project/data/models/global_model.joblib")
PARAMS_PATH = os.environ.get("LAB1_PARAMS_PATH", "/opt/project/params.yaml")
BUSINESS_PATH = os.environ.get("LAB1_BUSINESS_PATH", "/opt/project/configs/business.yaml")


with DAG(
    dag_id="lab1_forecast_and_order",
    schedule="0 6 * * 1",
    start_date=datetime(2017, 7, 3, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    tags=["lab1", "forecast", "order"],
) as dag:

    @task
    def publish(logical_date=None) -> list[str]:
        forecast, order = publish_forecast(
            INPUT_DIR,
            logical_date.date().isoformat(),
            OUTPUT_DIR,
            MODEL_PATH,
            PARAMS_PATH,
            BUSINESS_PATH,
        )
        return [str(forecast), str(order)]

    publish()
