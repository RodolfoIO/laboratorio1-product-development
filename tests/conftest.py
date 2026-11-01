from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def source_dir(tmp_path):
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    dates = pd.date_range("2024-01-01", periods=70, freq="D")
    train_rows = []
    row_id = 0
    for date in dates:
        for store in (1, 2):
            for family in ("A", "B"):
                train_rows.append(
                    {
                        "id": row_id,
                        "date": date,
                        "store_nbr": store,
                        "family": family,
                        "sales": float(10 + store + (date.dayofyear % 7)),
                        "onpromotion": int(date.dayofyear % 3),
                    }
                )
                row_id += 1
    pd.DataFrame(train_rows).to_csv(source_dir / "train.csv", index=False)
    pd.DataFrame(
        [
            {"store_nbr": 1, "city": "Quito", "state": "Pichincha", "type": "A", "cluster": 1},
            {"store_nbr": 2, "city": "Guayaquil", "state": "Guayas", "type": "B", "cluster": 2},
        ]
    ).to_csv(source_dir / "stores.csv", index=False)
    pd.DataFrame(
        [{"date": "2024-01-15", "type": "Holiday", "locale": "National", "locale_name": "Ecuador", "description": "Test", "transferred": False}]
    ).to_csv(source_dir / "holidays_events.csv", index=False)
    pd.DataFrame({"date": dates, "dcoilwtico": 75.0}).to_csv(source_dir / "oil.csv", index=False)
    transaction_rows = [{"date": date, "store_nbr": store, "transactions": 100} for date in dates for store in (1, 2)]
    pd.DataFrame(transaction_rows).to_csv(source_dir / "transactions.csv", index=False)
    return source_dir

