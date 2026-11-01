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


def _sha256_frame(frame: pd.DataFrame) -> str:
    """Hash estable de una entrega lógica, independiente del índice."""

    canonical = frame.sort_values(list(frame.columns)).to_csv(index=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


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
        if contract.date_column:
            source_frame = pd.read_csv(path, parse_dates=[contract.date_column])
            grouped = source_frame.dropna(subset=[contract.date_column]).groupby(contract.date_column)
            deliveries = [(str(pd.Timestamp(date).date()), group.copy()) for date, group in grouped]
        else:
            deliveries = [("1970-01-01", pd.read_csv(path))]
        for observed_date, delivery_frame in deliveries:
            available_date = pd.Timestamp(observed_date) + timedelta(days=contract.availability_lag_days)
            rows.append(
                {
                    "source": name,
                    "observed_date": str(observed_date),
                    "available_date": available_date.date().isoformat(),
                    "delivery_path": str(path),
                    "sha256": _sha256_frame(delivery_frame),
                }
            )
    return pd.DataFrame(rows).sort_values(["source", "observed_date"]).reset_index(drop=True)


def materialize_deliveries(
    input_dir: str | Path,
    landing_dir: str | Path,
    manifest: pd.DataFrame,
) -> pd.DataFrame:
    """Materializa una entrega por fuente y fecha sin modificar el origen."""

    input_dir = Path(input_dir)
    deliveries_dir = Path(landing_dir) / "deliveries"
    result = manifest.copy()
    loaded: dict[str, pd.DataFrame] = {}
    for source, source_manifest in result.groupby("source", sort=False):
        contract = CONTRACTS[source]
        source_frame = loaded.setdefault(source, pd.read_csv(input_dir / source, parse_dates=[contract.date_column] if contract.date_column else None))
        source_dir = deliveries_dir / Path(source).stem
        source_dir.mkdir(parents=True, exist_ok=True)
        for index, row in source_manifest.iterrows():
            if contract.date_column:
                observed_date = pd.Timestamp(row["observed_date"])
                delivery = source_frame[source_frame[contract.date_column] == observed_date].copy()
                filename = f"{observed_date.date().isoformat()}.csv"
            else:
                delivery = source_frame.copy()
                filename = "snapshot.csv"
            destination = source_dir / filename
            payload = delivery.to_csv(index=False).encode("utf-8")
            if not destination.exists() or destination.read_bytes() != payload:
                destination.write_bytes(payload)
            result.at[index, "delivery_path"] = str(destination)
    return result


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

    manifest = materialize_deliveries(input_dir, landing_dir, build_manifest(input_dir))
    manifest_path = landing_dir / "manifest.parquet"
    manifest.to_parquet(manifest_path, index=False)
    history_path = landing_dir / "manifest_history.parquet"
    history = pd.concat(
        [pd.read_parquet(history_path), manifest] if history_path.exists() else [manifest],
        ignore_index=True,
    ).drop_duplicates(subset=["source", "observed_date", "sha256"])
    history = history.sort_values(["source", "observed_date", "sha256"]).reset_index(drop=True)
    history.to_parquet(history_path, index=False)
    metadata = {
        "input_dir": str(input_dir),
        "landing_dir": str(landing_dir),
        "sources": [result.as_dict() for result in results],
        "hashes": hashes,
        "excluded_files": sorted(EXCLUDED_FILES),
        "manifest": str(manifest_path),
        "manifest_history": str(history_path),
    }
    (landing_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return metadata
