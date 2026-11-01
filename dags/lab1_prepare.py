"""DAG de preparación de snapshots point-in-time."""

from __future__ import annotations

import os
from pathlib import Path

from airflow.sdk import DAG, task
from pendulum import datetime

from inventory_forecasting.data.features import save_training_features


INPUT_DIR = os.environ.get("LAB1_INPUT_DIR", "/opt/project/store-sales-time-series-forecasting")
OUTPUT_DIR = Path(os.environ.get("LAB1_PROCESSED_DIR", "/opt/project/data/processed"))
PARAMS_PATH = os.environ.get("LAB1_PARAMS_PATH", "/opt/project/params.yaml")


with DAG(
    dag_id="lab1_prepare_features",
    schedule="@daily",
    start_date=datetime(2017, 7, 1, tz="UTC"),
    catchup=True,
    max_active_runs=1,
    tags=["lab1", "features", "point-in-time"],
) as dag:

    @task
    def prepare(logical_date=None) -> str:
        cutoff = logical_date.date().isoformat()
        destination = OUTPUT_DIR / f"training_features_{cutoff}.parquet"
        return str(save_training_features(INPUT_DIR, destination, cutoff, PARAMS_PATH))

    prepare()
