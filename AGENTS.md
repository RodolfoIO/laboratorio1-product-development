# Repository Guidelines

## Project Structure

- `src/inventory_forecasting/` contains the Python package, split into `data`, `models`, and `product` modules.
- `tests/` contains pytest tests for validation, feature generation, models, and pipeline behavior.
- `dags/` contains Airflow DAGs; DAGs should orchestrate Python modules rather than duplicate business logic.
- `configs/`, `params.yaml`, and `dvc.yaml` hold versioned configuration and pipeline definitions.
- `store-sales-time-series-forecasting/` is the source-data area managed by DVC. Do not commit raw data directly to Git.
- `reports/`, `artifacts/`, and model outputs are generated outputs and should remain DVC-managed.

## Build, Test, and Development Commands

Use Python 3.10 or newer and install dependencies with `make install`. Common commands are:

```bash
make test       # Run the full pytest suite
make validate   # Validate source schemas and data quality
make prepare    # Build deterministic features for a cutoff date
make train      # Train and persist model artifacts
make forecast   # Generate forecasts and suggested orders
make monitor    # Calculate monitoring metrics
make smoke      # Run the end-to-end local smoke test
make dags       # Validate Docker Compose syntax
```

Set `INPUT_DIR` and `CUTOFF` when testing alternate inputs, for example `CUTOFF=2017-07-31 make forecast`.

## Coding Style and Naming

Use four-space indentation, type hints where practical, small deterministic functions, and `snake_case` for Python files, functions, and variables. Keep dates and cutoff values explicit; never introduce features that use data after the forecast cutoff. Configuration belongs in YAML, not hard-coded constants.

## Testing Guidelines

Tests use pytest and are discovered under `tests/`. Name files `test_*.py` and test functions `test_*`. Add regression tests for temporal leakage, duplicate keys, invalid data, correction reprocessing, and idempotency. Run `make test` before every pull request.

## Commits and Pull Requests

Use short, imperative commit subjects such as `Add temporal validation` or `Track product artifacts with DVC`. Keep commits focused. Pull requests should explain the change, identify affected pipeline stages, include test results, and document any data, configuration, DVC, or Airflow implications. Never include credentials, raw datasets, or generated secrets.

## Data, DVC, and Airflow

Use DVC for data, models, forecasts, and reports; verify `dvc status` before delivery. Keep DVC remote credentials outside Git. Changes to DAGs must preserve retries, catchup/backfill behavior, deterministic paths, and idempotent reruns.
