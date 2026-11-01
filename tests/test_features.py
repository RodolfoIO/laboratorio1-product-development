from __future__ import annotations

import pandas as pd

from inventory_forecasting.data.features import build_forecast_rows, build_training_features, load_inputs


def test_training_features_respect_cutoff(source_dir):
    inputs = load_inputs(source_dir)
    frame, feature_columns = build_training_features(inputs, cutoff="2024-02-20")
    assert frame["date"].max() <= pd.Timestamp("2024-02-20")
    assert {"lag_1", "lag_7", "rolling_mean_7"}.issubset(feature_columns)
    assert frame[feature_columns].isna().sum().sum() == 0


def test_forecast_rows_do_not_use_future_sales(source_dir):
    inputs = load_inputs(source_dir)
    history = inputs["train"].query("date <= '2024-02-20'")[['date', 'store_nbr', 'family', 'sales']]
    rows, columns = build_forecast_rows(history, inputs, "2024-02-21", "2024-02-20")
    assert len(rows) == 4
    assert rows[columns].isna().sum().sum() == 0
    assert rows["date"].eq(pd.Timestamp("2024-02-21")).all()

