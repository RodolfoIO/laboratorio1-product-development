"""Construcción de la bandeja lógica de entregas.

La entrada de Kaggle se trata como sistema externo: se lee y se copia a una
zona de trabajo, pero ningún flujo modifica el archivo original.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from inventory_forecasting.data.contracts import CONTRACTS, EXCLUDED_FILES, ValidationResult, validate_file


def sha256_file(path: str | Path, block_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_sources(input_dir: str | Path) -> list[ValidationResult]:
    input_dir = Path(input_dir)
    return [validate_file(input_dir / name, contract) for name, contract in CONTRACTS.items()]


def build_manifest(input_dir: str | Path) -> pd.DataFrame:
    """Crea una fila lógica por fuente y fecha de entrega."""

    input_dir = Path(input_dir)
    rows: list[dict[str, Any]] = []
    for name, contract in CONTRACTS.items():
        path = input_dir / name
        if not path.exists():
            continue
        checksum = sha256_file(path)
        if contract.date_column:
            dates = pd.read_csv(path, usecols=[contract.date_column], parse_dates=[contract.date_column])
            unique_dates = dates[contract.date_column].dropna().dt.date.astype(str).drop_duplicates().sort_values()
        else:
            unique_dates = pd.Series(["1970-01-01"])
        for observed_date in unique_dates:
            available_date = pd.Timestamp(observed_date) + timedelta(days=contract.availability_lag_days)
            rows.append(
                {
                    "source": name,
                    "observed_date": str(observed_date),
                    "available_date": available_date.date().isoformat(),
                    "delivery_path": str(path),
                    "sha256": checksum,
                }
            )
    return pd.DataFrame(rows).sort_values(["source", "observed_date"]).reset_index(drop=True)


def stage_sources(input_dir: str | Path, landing_dir: str | Path) -> dict[str, Any]:
    """Valida y materializa snapshots sin tocar la entrada externa."""

    input_dir = Path(input_dir)
    landing_dir = Path(landing_dir)
    landing_dir.mkdir(parents=True, exist_ok=True)
    results = validate_sources(input_dir)
    invalid = [result for result in results if not result.valid]
    if invalid:
        raise ValueError({result.source: result.errors for result in invalid})

    raw_dir = landing_dir / "raw"
    raw_dir.mkdir(exist_ok=True)
    hashes = {}
    for name in CONTRACTS:
        source = input_dir / name
        target = raw_dir / name
        if not target.exists() or sha256_file(target) != sha256_file(source):
            shutil.copy2(source, target)
        hashes[name] = sha256_file(target)

    manifest = build_manifest(input_dir)
    manifest_path = landing_dir / "manifest.parquet"
    manifest.to_parquet(manifest_path, index=False)
    metadata = {
        "input_dir": str(input_dir),
        "landing_dir": str(landing_dir),
        "sources": [result.as_dict() for result in results],
        "hashes": hashes,
        "excluded_files": sorted(EXCLUDED_FILES),
        "manifest": str(manifest_path),
    }
    (landing_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return metadata

