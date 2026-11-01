from __future__ import annotations

import pandas as pd

from inventory_forecasting.models.global_model import GlobalQuantileModel
from inventory_forecasting.models.metrics import select_model
from inventory_forecasting.product.order import build_order, critical_quantile


def test_order_changes_when_costs_change():
    forecasts = pd.DataFrame(
        [
            {"cutoff_date": "2024-01-01", "target_date": "2024-01-02", "store_nbr": 1, "family": "A", "q10": 10, "q50": 20, "q90": 40},
            {"cutoff_date": "2024-01-01", "target_date": "2024-01-03", "store_nbr": 1, "family": "A", "q10": 10, "q50": 20, "q90": 40},
        ]
    )
    low = build_order(forecasts, 1.0, 1.0).iloc[0]["suggested_order"]
    high = build_order(forecasts, 9.0, 1.0).iloc[0]["suggested_order"]
    assert critical_quantile(9.0, 1.0) > critical_quantile(1.0, 1.0)
    assert high > low


def test_model_selection_requires_business_improvement():
    baseline = {"business_loss": 10.0, "wape": 0.20}
    candidate = {"business_loss": 9.0, "wape": 0.20}
    assert select_model(baseline, candidate) == "global_ml"
    assert select_model(baseline, {"business_loss": 9.8, "wape": 0.20}) == "baseline"


def test_global_model_preserves_quantile_order():
    frame = pd.DataFrame(
        {
            "feature": range(20),
            "sales": [float(value + 1) for value in range(20)],
        }
    )
    model = GlobalQuantileModel((0.1, 0.5, 0.9), {"max_iter": 10, "max_leaf_nodes": 7, "min_samples_leaf": 2})
    model.fit(frame, ["feature"])
    prediction = model.predict(frame)
    assert (prediction["q10"] <= prediction["q50"]).all()
    assert (prediction["q50"] <= prediction["q90"]).all()

