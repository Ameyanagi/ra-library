"""Auditable CREATE-SIMPLE v3.2.1 display terminology.

The bundled JSON is extracted directly from the official unlocked workbook's
Open XML parts.  Every value retains its originating worksheet and cell.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from typing import Any


TERMINOLOGY_RESOURCE = "create_simple_terminology_v3_2_1.json"


@lru_cache(maxsize=1)
def get_official_terminology() -> dict[str, Any]:
    """Return the complete versioned terminology payload."""
    resource = files("ra_library.data").joinpath(TERMINOLOGY_RESOURCE)
    return json.loads(resource.read_text(encoding="utf-8"))


def get_terminology_source() -> dict[str, str]:
    """Return workbook version, filename, and SHA-256 provenance."""
    return dict(get_official_terminology()["source"])


def get_official_option_list(name: str, *, values_only: bool = False) -> list[Any]:
    """Return one workbook-defined option list, preserving cell provenance."""
    records = get_official_terminology()["option_lists"].get(name, [])
    if values_only:
        return [record["value"] for record in records]
    return [dict(record) for record in records]


def get_official_named_text(name: str, *, values_only: bool = False) -> list[Any]:
    """Return a named risk description or display string from the workbook."""
    payload = get_official_terminology()
    records = payload["risk_descriptions"].get(name)
    if records is None:
        records = payload["labels_and_messages"].get(name, [])
    if values_only:
        return [record["value"] for record in records]
    return [dict(record) for record in records]

