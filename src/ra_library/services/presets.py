"""Canonical transport-ready work-preset service."""

from __future__ import annotations

from typing import Any

from ..presets import PRESETS
from .common import ServiceError, ServiceResult

_CATEGORY_PREFIXES = {
    "laboratory": "lab_",
    "production": "production_",
    "maintenance": "maintenance_",
    "spray": "spray_",
}


def _serialize_preset(name: str, language: str) -> dict[str, Any]:
    preset = PRESETS[name]
    conditions: dict[str, Any] = {
        "property_type": preset.property_type,
        "amount": preset.amount,
        "ventilation": preset.ventilation,
        "control_velocity_verified": preset.control_velocity_verified,
        "is_spray": preset.is_spray,
    }
    if preset.dustiness:
        conditions["dustiness"] = preset.dustiness
    if preset.work_area_size:
        conditions["work_area_size"] = preset.work_area_size
    if preset.process_temperature is not None:
        conditions["process_temperature"] = preset.process_temperature

    return {
        "name": name,
        "description": preset.description if language == "ja" else preset.description_en,
        "conditions": conditions,
        "duration": {
            "hours": preset.hours,
            "days_per_week": preset.days_per_week,
            "days_per_month": preset.days_per_month,
        },
        "protection": {
            "gloves": preset.gloves,
            "glove_training": preset.glove_training,
            "rpe": preset.rpe,
        },
        "constraints": {
            "max_ventilation": preset.max_ventilation,
            "excluded_rpe": list(preset.excluded_rpe),
            "no_admin": preset.no_admin,
        },
    }


def list_preset_profiles(category: str | None = None, language: str = "en") -> ServiceResult:
    """Return the complete, stable preset payload used by MCP and local providers."""
    normalized_language = "ja" if language == "ja" else "en"
    categories = {
        name: [preset_name for preset_name in PRESETS if preset_name.startswith(prefix)]
        for name, prefix in _CATEGORY_PREFIXES.items()
    }
    if category:
        normalized_category = category.lower()
        if normalized_category not in categories:
            raise ServiceError(
                "UNKNOWN_PRESET_CATEGORY",
                f"Unknown category: {category}",
                {"valid_categories": sorted(categories)},
            )
        names = categories[normalized_category]
        selected_categories = [normalized_category]
    else:
        names = list(PRESETS)
        selected_categories = [name for name, values in categories.items() if values]

    return ServiceResult(
        data={
            "count": len(names),
            "categories": selected_categories,
            "presets": [_serialize_preset(name, normalized_language) for name in names],
            "counts": {
                "total": len(PRESETS),
                "filtered": len(names),
                "by_category": {name: len(values) for name, values in categories.items()},
            },
        }
    )

