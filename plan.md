# Plan de implementación — Laboratorio 1

Este documento refleja el estado del repositorio respecto al plan aprobado. Estados: **Hecho**, **Parcial** y **Pendiente**.

## Fase 0 — Diagnóstico y línea base

**Hecho.** Se identificaron las fuentes Kaggle y se documentó el alcance: `train.csv` como histórico principal, 54 tiendas y 33 familias. `test.csv` y `sample_submission.csv` quedan fuera del laboratorio. La ruta de entrada está documentada en [README.md](README.md).

## Fase 1 — Estructura y calidad

**Hecho.** Existe estructura para `src/`, `tests/`, `dags/`, `configs/`, `scripts/`, Docker, CI y documentación. Están creados `README.md`, `DECISIONES.md`, `CLAUDE.md`, `AGENTS.md`, `.gitignore`, `pyproject.toml` y la configuración de pytest. Las pruebas locales pasan: **9 passed**.

## Fase 2 — Carga, bandeja y DVC

**Hecho.** La definición del pipeline incluye las cinco etapas, `dvc.lock` contiene los hashes de bandeja, datos procesados, modelo, pronóstico y reportes, `dvc status` está limpio y `dvc push` publicó 12 archivos en el remoto S3-compatible. Un clon limpio recuperó los artefactos con `AWS_PROFILE=laboratorio1 dvc pull` y quedó con `dvc status` limpio.

## Fase 3 — Validación y preparación temporal

**Hecho.** Están implementadas validaciones de esquema, duplicados, fechas, claves, valores inválidos, entregas por fecha, historial de hashes y features temporales. Las pruebas cubren una corrección y la idempotencia de la bandeja; Airflow ejecuta la misma lógica mediante el DAG de ingesta.

## Fase 4 — Baseline, ML y selección

**Hecho localmente.** El entrenamiento final generó métricas, tabla comparativa, decisión de selección y artefacto de modelo. El baseline fue seleccionado porque el modelo ML no mejoró la pérdida de negocio; los resultados están versionados mediante DVC.

## Fase 5 — Pronóstico y pedido

**Hecho localmente.** Se generaron p10, p50 y p90, pedido sugerido por costos, metadatos, sensibilidad a costos y salidas deterministas en `data/forecasts/`.

## Fase 6 — Airflow

**Hecho.** Se construyó la imagen, se inicializó PostgreSQL/Airflow, se levantaron los cuatro servicios, los cuatro DAGs cargaron sin errores de importación y la interfaz quedó publicada en el puerto 8080. Los DAGs usan `catchup=False`; el backfill se ejecuta explícitamente con `airflow backfill create` para evitar ejecuciones históricas masivas al levantar el entorno.

## Fase 7 — Seguimiento

**Hecho para datos históricos.** El reporte contiene 12,474 pronósticos observados, métricas por horizonte y sensibilidad a costos. Falta ejecutar el flujo equivalente en Airflow con datos pendientes, tardíos y corregidos.

## Fase 8 — CI, documentación y entrega

**Parcial.** GitHub Actions, README, decisiones, artefactos DVC, `dvc status` limpio, `dvc push` exitoso y evidencia de Airflow están listos. Falta publicar los commits y el tag final en GitHub.

## Verificación local final

- `pytest`: **9 passed**.
- `make smoke`: aprobado.
- `docker compose config`: aprobado.
- `dvc repro`: completado con las cinco etapas.
- `dvc status --no-updates --json`: `{}`.
- `dvc push`: **12 archivos publicados**.
- Seguimiento histórico: **12,474 pronósticos observados**, cero pendientes.
- Comparación de modelos: se seleccionó `baseline` porque el modelo ML no cumplió el criterio de pérdida de negocio.
- Docker/Airflow: imagen construida, base inicializada, cuatro servicios activos y `airflow dags list-import-errors` vacío.

## Orden recomendado para finalizar

1. Publicar los commits y el tag `entrega-lab1` en GitHub.
2. Si se requiere evidencia visual, abrir `http://localhost:8080` y capturar la vista de los DAGs activos.
