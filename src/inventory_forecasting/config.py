"""Carga centralizada de configuración versionada."""

from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def load_params(path: str | Path = "params.yaml") -> dict[str, Any]:
    return load_yaml(path)


def load_business(path: str | Path = "configs/business.yaml") -> dict[str, Any]:
    return load_yaml(path)


def project_path(path: str | Path, root: str | Path = ".") -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else Path(root) / candidate

