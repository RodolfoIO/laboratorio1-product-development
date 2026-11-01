from __future__ import annotations

import pandas as pd

from inventory_forecasting.data.contracts import CONTRACTS, validate_file
from inventory_forecasting.data.landing import build_manifest, stage_sources


def test_validation_rejects_negative_sales(tmp_path):
    path = tmp_path / "train.csv"
    pd.DataFrame(
        [{"id": 1, "date": "2024-01-01", "store_nbr": 1, "family": "A", "sales": -1, "onpromotion": 0}]
    ).to_csv(path, index=False)
    result = validate_file(path, CONTRACTS["train.csv"])
    assert not result.valid
    assert any("negativos" in error for error in result.errors)


def test_stage_sources_creates_hash_manifest_without_modifying_input(source_dir, tmp_path):
    original = (source_dir / "train.csv").read_bytes()
    metadata = stage_sources(source_dir, tmp_path / "landing")
    assert metadata["excluded_files"] == ["sample_submission.csv", "test.csv"]
    assert (tmp_path / "landing" / "manifest.parquet").exists()
    assert (source_dir / "train.csv").read_bytes() == original
    manifest = build_manifest(source_dir)
    assert set(manifest["source"]) == {"train.csv", "stores.csv", "holidays_events.csv", "oil.csv", "transactions.csv"}

