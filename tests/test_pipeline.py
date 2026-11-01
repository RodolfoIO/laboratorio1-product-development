from __future__ import annotations

import json

from inventory_forecasting.models.train import train_and_evaluate
from inventory_forecasting.product.forecast import publish_forecast
from inventory_forecasting.product.monitor import monitor_forecasts


def test_train_publish_monitor_smoke(source_dir, tmp_path, monkeypatch):
    params = tmp_path / "params.yaml"
    params.write_text(
        """forecast:\n  horizon_days: 7\n  quantiles: [0.1, 0.5, 0.9]\n  validation_days: 7\nfeatures:\n  lags: [1, 7, 14, 28]\n  rolling_windows: [7, 28]\nmodel:\n  max_iter: 10\n  learning_rate: 0.1\n  max_leaf_nodes: 7\n  min_samples_leaf: 2\n  l2_regularization: 0.1\nselection:\n  min_business_improvement: 0.0\n  max_wape_regression: 1.0\n""",
        encoding="utf-8",
    )
    business = tmp_path / "business.yaml"
    business.write_text("business:\n  stockout_cost: 1.0\n  waste_cost: 0.25\n", encoding="utf-8")
    result = train_and_evaluate(source_dir, tmp_path / "models", params, business)
    assert result["selected_model"] in {"baseline", "global_ml"}
    forecast_path, order_path = publish_forecast(
        source_dir,
        "2024-03-10",
        tmp_path / "forecasts",
        tmp_path / "models" / "global_model.joblib",
        params,
        business,
    )
    assert forecast_path.exists() and order_path.exists()
    report = monitor_forecasts(source_dir, tmp_path / "forecasts", tmp_path / "reports", business)
    assert report["published_rows"] == 28
    assert (tmp_path / "reports" / "performance.json").exists()

