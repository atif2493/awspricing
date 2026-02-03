# mapping.py - v1.0
# Load service definitions from YAML; query by scenario or id. Deps: PyYAML (optional).
# Port: N/A.

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

def _data_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data" / "services"


def _load_yaml() -> list[dict[str, Any]]:
    """Load all AWS services from YAML. Returns list of service dicts."""
    try:
        import yaml
    except ImportError:
        return []
    path = _data_dir() / "aws_services.yaml"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, list) else []


_SERVICES: list[dict[str, Any]] | None = None


def _get_services() -> list[dict[str, Any]]:
    global _SERVICES
    if _SERVICES is None:
        _SERVICES = _load_yaml()
    return _SERVICES


def list_services_by_scenario(scenario: str) -> list[dict[str, Any]]:
    """Return services that support the given scenario (e.g. web_app, api_backend)."""
    out = []
    for s in _get_services():
        scenarios = s.get("scenarios") or []
        if scenario in scenarios:
            out.append(s)
    return out


def get_service(service_id: str) -> dict[str, Any] | None:
    """Return a single service by id, or None."""
    for s in _get_services():
        if s.get("id") == service_id:
            return s
    return None
