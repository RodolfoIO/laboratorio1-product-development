# Laboratorio 1 — reglas del proyecto

## Objetivo

Motor reproducible de reposición de inventario para ventas de Corporación Favorita. Publica semanalmente un pronóstico de siete días por tienda y familia, un pedido bruto basado en costos y métricas de seguimiento.

## Comandos

- `python -m pytest`: pruebas unitarias e integración pequeña.
- `make validate`: valida las cinco fuentes de Kaggle.
- `make prepare CUTOFF=YYYY-MM-DD`: construye features point-in-time.
- `make train`: entrena y evalúa baseline y modelo global.
- `make forecast CUTOFF=YYYY-MM-DD`: publica pronóstico y pedido.
- `make monitor`: calcula seguimiento de resultados disponibles.
- `make smoke`: ejecuta el flujo sobre un subconjunto reproducible.

## Reglas de datos

- No modificar `store-sales-time-series-forecasting/`.
- No usar `test.csv` ni `sample_submission.csv`.
- No utilizar ventas posteriores a la fecha de corte.
- No usar columnas futuras sin documentar su disponibilidad.
- Datos, modelos, pronósticos y reportes van a DVC, no a Git.

## Reglas de implementación

- La lógica vive en `src/inventory_forecasting`; los DAGs solo orquestan.
- Toda tarea debe ser idempotente.
- Los cambios deben incluir pruebas.
- Los costos se leen desde `configs/business.yaml`; no duplicarlos en código.
- Usar fechas de corte y hashes para garantizar trazabilidad.

