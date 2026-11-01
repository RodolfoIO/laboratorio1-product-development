"""Contratos de las fuentes externas."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class SourceContract:
    name: str
    required_columns: tuple[str, ...]
    date_column: str | None
    availability_lag_days: int = 0
    key_columns: tuple[str, ...] = ()
    non_negative_columns: tuple[str, ...] = ()


CONTRACTS: dict[str, SourceContract] = {
    "train.csv": SourceContract(
        "train.csv",
        ("id", "date", "store_nbr", "family", "sales", "onpromotion"),
        "date",
        1,
        ("date", "store_nbr", "family"),
        ("sales", "onpromotion"),
    ),
    "stores.csv": SourceContract(
        "stores.csv",
        ("store_nbr", "city", "state", "type", "cluster"),
        None,
        0,
        ("store_nbr",),
        ("store_nbr", "cluster"),
    ),
    "holidays_events.csv": SourceContract(
        "holidays_events.csv",
        ("date", "type", "locale", "locale_name", "description", "transferred"),
        "date",
        7,
        (),
        (),
    ),
    "oil.csv": SourceContract(
        "oil.csv", ("date", "dcoilwtico"), "date", 1, ("date",), ()
    ),
    "transactions.csv": SourceContract(
        "transactions.csv", ("date", "store_nbr", "transactions"), "date", 1, ("date", "store_nbr"), ("transactions",)
    ),
}

EXCLUDED_FILES = {"test.csv", "sample_submission.csv"}


@dataclass
class ValidationResult:
    source: str
    path: str
    rows: int = 0
    min_date: str | None = None
    max_date: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "path": self.path,
            "rows": self.rows,
            "min_date": self.min_date,
            "max_date": self.max_date,
            "errors": self.errors,
            "warnings": self.warnings,
            "valid": self.valid,
        }


def _date_range(df: pd.DataFrame, column: str | None) -> tuple[str | None, str | None]:
    if not column or column not in df.columns:
        return None, None
    dates = pd.to_datetime(df[column], errors="coerce")
    if dates.dropna().empty:
        return None, None
    return dates.min().date().isoformat(), dates.max().date().isoformat()


def validate_file(path: str | Path, contract: SourceContract, chunksize: int = 200_000) -> ValidationResult:
    """Valida una fuente por bloques sin modificarla."""

    path = Path(path)
    result = ValidationResult(contract.name, str(path))
    if not path.exists():
        result.errors.append("archivo inexistente")
        return result

    try:
        header = pd.read_csv(path, nrows=0).columns.tolist()
    except Exception as exc:  # pragma: no cover - depende del archivo externo
        result.errors.append(f"no se pudo leer el encabezado: {exc}")
        return result

    missing = sorted(set(contract.required_columns) - set(header))
    if missing:
        result.errors.append(f"faltan columnas: {missing}")
        return result

    min_date = None
    max_date = None
    duplicate_keys: set[tuple[Any, ...]] = set()
    try:
        for chunk in pd.read_csv(path, chunksize=chunksize):
            result.rows += len(chunk)
            if contract.date_column:
                parsed = pd.to_datetime(chunk[contract.date_column], errors="coerce")
                if parsed.isna().any():
                    result.errors.append(f"fechas inválidas en {contract.date_column}")
                if not parsed.dropna().empty:
                    current_min = parsed.min().date().isoformat()
                    current_max = parsed.max().date().isoformat()
                    min_date = min(min_date, current_min) if min_date else current_min
                    max_date = max(max_date, current_max) if max_date else current_max

            for column in contract.non_negative_columns:
                numeric = pd.to_numeric(chunk[column], errors="coerce")
                if numeric.isna().any() and column not in {"dcoilwtico"}:
                    result.errors.append(f"valores no numéricos en {column}")
                if (numeric.dropna() < 0).any():
                    result.errors.append(f"valores negativos en {column}")

            if contract.key_columns:
                keys = chunk.loc[:, list(contract.key_columns)].astype(str).agg("|".join, axis=1)
                duplicates = keys[keys.duplicated()].tolist()
                if duplicates:
                    result.errors.append(f"claves duplicadas en {contract.key_columns}")
                # Solo retenemos claves de cada bloque para detectar duplicados entre bloques.
                for key in keys:
                    if key in duplicate_keys:
                        result.errors.append(f"claves duplicadas entre bloques en {contract.key_columns}")
                        break
                    duplicate_keys.add(key)
    except Exception as exc:  # pragma: no cover - depende del archivo externo
        result.errors.append(f"error leyendo datos: {exc}")

    result.min_date = min_date
    result.max_date = max_date
    if result.rows == 0:
        result.errors.append("fuente vacía")
    return result

