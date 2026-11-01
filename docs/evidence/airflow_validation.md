# Evidencia de validación de Airflow

Fecha de validación: 2026-11-01.

## Stack

- `docker compose build`: completado correctamente.
- `docker compose up airflow-init`: base PostgreSQL/Airflow inicializada.
- Servicios activos: `airflow-apiserver`, `airflow-scheduler`, `airflow-dag-processor`, `airflow-triggerer` y `postgres`.
- Interfaz publicada en `http://localhost:8080`.

## DAGs

`airflow dags list --output json` registró los cuatro DAG esperados:

- `lab1_ingest_validate`
- `lab1_prepare_features`
- `lab1_forecast_and_order`
- `lab1_monitor_performance`

`airflow dags list-import-errors --output json` devolvió `[]`.

## Ejecución controlada

Se ejecutó:

```bash
docker compose exec airflow-scheduler \
  airflow dags test lab1_monitor_performance 2017-07-31
```

Resultado: `DagRun Finished ... state=success`. La tarea reprodujo el reporte histórico con `12,474` observaciones publicadas, `0` pendientes y generó la sensibilidad de costos.

Los DAG están configurados con `catchup=False` para que el arranque no dispare backfills históricos. Cuando se necesita reprocesar un intervalo, se ejecuta de forma explícita:

```bash
docker compose exec airflow-scheduler airflow backfill create \
  --dag-id lab1_forecast_and_order \
  --from-date 2017-07-24 --to-date 2017-07-31
```
