# Plan de implementación — Laboratorio 1

Este documento refleja el estado del repositorio respecto al plan aprobado. Estados: **Hecho**, **Parcial** y **Pendiente**.

## Fase 0 — Diagnóstico y línea base

**Hecho.** Se identificaron las fuentes Kaggle y se documentó el alcance: `train.csv` como histórico principal, 54 tiendas y 33 familias. `test.csv` y `sample_submission.csv` quedan fuera del laboratorio. La ruta de entrada está documentada en [README.md](README.md).

## Fase 1 — Estructura y calidad

**Hecho.** Existe estructura para `src/`, `tests/`, `dags/`, `configs/`, `scripts/`, Docker, CI y documentación. Están creados `README.md`, `DECISIONES.md`, `CLAUDE.md`, `AGENTS.md`, `.gitignore`, `pyproject.toml` y la configuración de pytest. Las pruebas locales pasan: **8 passed**.

## Fase 2 — Carga, bandeja y DVC

**Parcial.** Hay archivos `.dvc`, `dvc.yaml`, `dvc.lock` y datos procesados. Falta instalar DVC, configurar el remoto de Google Drive, ejecutar `dvc push` y comprobar `dvc pull` desde un clon limpio. El remoto todavía no está configurado en `.dvc/config`.

## Fase 3 — Validación y preparación temporal

**Hecho a nivel de código; validación operativa pendiente.** Están implementadas validaciones de esquema, duplicados, fechas, claves, valores inválidos, features temporales y ejecución determinista. Falta ejecutar y conservar evidencia de correcciones, reprocesamiento y hashes idénticos en una segunda ejecución.

## Fase 4 — Baseline, ML y selección

**Parcial.** Existen baseline, modelo global, métricas y artefactos de entrenamiento. Falta generar la tabla comparativa reproducible entre modelos, documentar la selección y versionar el resultado mediante DVC.

## Fase 5 — Pronóstico y pedido

**Hecho a nivel de código.** Se generan p10, p50 y p90, pedido sugerido por costos, metadatos y salidas deterministas en `data/forecasts/`. Falta demostrar formalmente que cambiar `stockout_cost` y `waste_cost` modifica el pedido.

## Fase 6 — Airflow

**Parcial.** Existen los cuatro DAGs y `docker compose config` es válido. Falta levantar los servicios, verificar la interfaz, ejecutar DAGs, realizar backfill, reprocesar una corrección y confirmar que una segunda ejecución no duplica resultados. Actualmente el entorno no permite acceder al daemon Docker.

## Fase 7 — Seguimiento

**Parcial.** Existe el módulo de monitorización y el reporte en `data/reports/`. Falta validar un periodo completo con ventas reales, incluyendo datos pendientes, tardíos y corregidos, y conservar evidencia de actualización.

## Fase 8 — CI, documentación y entrega

**Parcial.** GitHub Actions ejecuta pytest; README y decisiones están documentados; el tag `entrega-lab1` existe. Faltan la prueba desde clon limpio, evidencias finales, `dvc status` limpio, `dvc push` exitoso y la verificación integral Docker + Airflow + DVC.

## Orden recomendado para finalizar

1. Instalar `dvc[gdrive]` y configurar el remoto de Google Drive.
2. Ejecutar `dvc push` y validar recuperación con `dvc pull`.
3. Habilitar Docker y ejecutar los DAGs, backfill y reprocesamiento.
4. Generar y guardar las evidencias de modelo, costos y monitorización.
5. Repetir la entrega desde un clon limpio y actualizar el tag final si corresponde.
