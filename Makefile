PYTHON ?= python3
export PYTHONPATH := src

.PHONY: install test validate prepare train forecast monitor smoke dags

install:
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTHON) -m pytest

validate:
	$(PYTHON) -m inventory_forecasting.data.validate --input-dir $${INPUT_DIR:-store-sales-time-series-forecasting}

prepare:
	$(PYTHON) -m inventory_forecasting.data.features --input-dir $${INPUT_DIR:-store-sales-time-series-forecasting} --cutoff $${CUTOFF:-2017-07-31}

train:
	$(PYTHON) -m inventory_forecasting.models.train --input-dir $${INPUT_DIR:-store-sales-time-series-forecasting}

forecast:
	$(PYTHON) -m inventory_forecasting.product.forecast --input-dir $${INPUT_DIR:-store-sales-time-series-forecasting} --cutoff $${CUTOFF:-2017-07-31}

monitor:
	$(PYTHON) -m inventory_forecasting.product.monitor --input-dir $${INPUT_DIR:-store-sales-time-series-forecasting}

smoke:
	$(PYTHON) scripts/smoke_test.py

dags:
	docker compose config --quiet

