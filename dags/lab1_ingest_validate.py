"""DAG diario de ingesta y validación de fuentes."""

from __future__ import annotations

import os

from airflow.sdk import DAG, task
from pendulum import datetime

from inventory_forecasting.data.landing import stage_sources


INPUT_DIR = os.environ.get("LAB1_INPUT_DIR", "/opt/project/store-sales-time-series-forecasting")
LANDING_DIR = os.environ.get("LAB1_LANDING_DIR", "/opt/project/data/landing")


with DAG(
    dag_id="lab1_ingest_validate",
    schedule="@daily",
    start_date=datetime(2017, 7, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    tags=["lab1", "ingesta", "validacion"],
) as dag:

    @task
    def ingest_and_validate() -> dict:
        return stage_sources(INPUT_DIR, LANDING_DIR)

    ingest_and_validate()
