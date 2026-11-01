# Laboratorio 1 — Motor de reposición de inventario

Producto reproducible de pronóstico semanal para Corporación Favorita. A partir de ventas diarias, promociones, transacciones, petróleo, feriados y tiendas, publica un pronóstico de 7 días por tienda y familia, un pedido sugerido y el seguimiento de resultados.

## Estado del producto

- Frecuencia de publicación: semanal.
- Horizonte: 7 días.
- Cuantiles: p10, p50 y p90.
- Baseline: rezago estacional de 7 días.
- Modelo ML: modelo global tabular con regresión cuantílica.
- Pedido: requerimiento bruto; no se descuenta inventario porque las fuentes no contienen stock disponible.
- Las fuentes de entrada se consideran externas e inmutables.

## Datos

Coloca los archivos originales de Kaggle en:

```text
store-sales-time-series-forecasting/
├── train.csv
├── stores.csv
├── holidays_events.csv
├── oil.csv
└── transactions.csv
```

`test.csv` y `sample_submission.csv` se excluyen del laboratorio.

La validación se ejecuta con:

```bash
python -m inventory_forecasting.data.validate --input-dir store-sales-time-series-forecasting
```

Para construir la bandeja lógica y su manifest:

```bash
python -m inventory_forecasting.data.validate \
  --input-dir store-sales-time-series-forecasting \
  --landing-dir data/landing \
  --stage
```

La bandeja no modifica la carpeta original. `data/landing/manifest.parquet` registra una entrega lógica por fuente y fecha, fecha de disponibilidad, ruta y hash SHA-256.

## Instalación y pruebas

Se requiere Python 3.10 o superior:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=src
python -m pytest
```

También están disponibles:

```bash
make validate
make prepare CUTOFF=2017-07-31
make train
make forecast CUTOFF=2017-07-31
make monitor
```

## DVC

Los datos, modelos, pronósticos y reportes no deben confirmarse directamente en Git. Configura un remoto accesible para el equipo docente, por ejemplo un bucket S3-compatible:

```bash
dvc remote add -d storage s3://BUCKET/lab1
dvc remote modify storage endpointurl https://ENDPOINT
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
dvc push
```

Las credenciales se inyectan por variables de entorno o secretos; nunca se escriben en el repositorio.

Si el entorno restringe la escritura en `/var/tmp`, usa una caché local temporal antes de ejecutar DVC:

```bash
export DVC_SITE_CACHE_DIR=/tmp/lab1-dvc-site
```

Para reproducir las etapas declaradas:

```bash
dvc repro
dvc status
dvc push
```

Para demostrar la reproducción de un pronóstico pasado, se debe conservar el commit/tag del código, recuperar los objetos con `dvc pull`, restaurar la configuración de negocio y comparar el hash del archivo publicado:

```bash
git checkout entrega-lab1
dvc pull
PYTHONPATH=src python -m inventory_forecasting.product.forecast \
  --input-dir store-sales-time-series-forecasting \
  --cutoff 2017-07-31 \
  --model data/models/global_model.joblib
sha256sum data/forecasts/forecast_2017-07-31.parquet
```

## Entrenamiento y publicación

El entrenamiento realiza una validación temporal sobre los últimos 28 días disponibles:

```bash
PYTHONPATH=src python -m inventory_forecasting.models.train \
  --input-dir store-sales-time-series-forecasting
```

Para mantener un tiempo de ejecución controlado, el modelo global usa una muestra determinista de hasta 500,000 filas, configurada en `params.yaml`; la validación conserva todas las series del periodo de evaluación.

El modelo solo reemplaza al baseline si reduce al menos 5% la pérdida de negocio y no empeora el WAPE en más de 2%. El resultado queda en `data/models/metrics.json` y la decisión en `data/models/current_model.json`.

Para publicar:

```bash
PYTHONPATH=src python -m inventory_forecasting.product.forecast \
  --input-dir store-sales-time-series-forecasting \
  --cutoff 2017-07-31
```

El cuantil crítico del pedido se calcula como:

```text
stockout_cost / (stockout_cost + waste_cost)
```

Por ello, cambiar `configs/business.yaml` modifica la recomendación sin modificar el código.

## Airflow 3 con Docker Compose

El host debe tener Docker y Docker Compose:

```bash
docker compose build
docker compose up airflow-init
docker compose up -d airflow-apiserver airflow-scheduler airflow-dag-processor airflow-triggerer
```

La interfaz queda en <http://localhost:8080> con usuario `admin` y contraseña `admin` para una instalación local.

Los DAGs son:

- `lab1_ingest_validate`: valida y registra la bandeja.
- `lab1_prepare_features`: construye snapshots point-in-time.
- `lab1_forecast_and_order`: publica pronóstico y pedido semanal.
- `lab1_monitor_performance`: compara pronósticos con ventas disponibles.

Los DAGs tienen `catchup=True`, aceptan backfill y escriben resultados deterministas por fecha de corte. Las tareas esperan que la entrada esté montada en `/opt/project/store-sales-time-series-forecasting`.

## Estructura

```text
src/inventory_forecasting/
  data/        contratos, validación, bandeja y features
  models/      baseline, modelo global, métricas y entrenamiento
  product/     pronósticos, pedidos y seguimiento
dags/          orquestación Airflow
configs/       costos y contratos de fuentes
tests/         pruebas unitarias e integración
data/          artefactos locales versionados con DVC
```

## CI y entrega

GitHub Actions ejecuta pytest en cada Pull Request y en cada push a `main`. El flujo de entrega recomendado es:

1. Crear rama de trabajo.
2. Ejecutar `python -m pytest`.
3. Ejecutar el smoke test con `make smoke`.
4. Abrir Pull Request y revisar CI.
5. Proteger `main` contra pushes directos.
6. Confirmar que `dvc status` esté limpio y que `dvc push` haya terminado.
7. Crear el tag `entrega-lab1` sobre el último commit evaluable.
