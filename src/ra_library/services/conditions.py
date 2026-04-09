"""
Format assessment conditions with human-readable labels for LLM understanding.

Based on CREATE-SIMPLE Design v3.1.1 and VBA SelectList.csv.
"""

from math import isfinite
from typing import Any, Literal

from ra_library.i18n import get_labels
from ra_library.models.assessment import AssessmentInput

Language = Literal["ja", "en"]

STANDARD_GAS_MOLAR_VOLUME_L_PER_MOL = 24.47
GAS_AMOUNT_KG_RANGES = {
    "large": {"min_kg": 1000.0, "max_kg": None},
    "medium": {"min_kg": 1.0, "max_kg": 1000.0},
    "small": {"min_kg": 0.1, "max_kg": 1.0},
    "minute": {"min_kg": 0.01, "max_kg": 0.1},
    "trace": {"min_kg": None, "max_kg": 0.01},
}


def get_gas_amount_metadata(
    amount_key: str,
    molecular_weight: float | None = None,
) -> dict[str, Any]:
    """Return workbook-faithful gas amount metadata with optional volume estimates."""
    band = GAS_AMOUNT_KG_RANGES.get(amount_key)
    if band is None:
        return {}

    metadata: dict[str, Any] = {
        "band_basis": "workbook_q1_gas_mass_band",
        "mass_range_kg": {
            "min": band["min_kg"],
            "max": band["max_kg"],
        },
        "conversion_assumption": {
            "model": "ideal_gas",
            "temperature_celsius": 25.0,
            "pressure_atm": 1.0,
            "molar_volume_l_per_mol": STANDARD_GAS_MOLAR_VOLUME_L_PER_MOL,
        },
    }

    if molecular_weight is None or molecular_weight <= 0 or not isfinite(molecular_weight):
        return metadata

    liters_per_kg = (1000.0 / molecular_weight) * STANDARD_GAS_MOLAR_VOLUME_L_PER_MOL
    metadata["volume_equivalent_at_25c_1atm"] = {
        "molecular_weight_g_mol": round(molecular_weight, 4),
        "liters_per_kg": round(liters_per_kg, 4),
        "min_liters": round(band["min_kg"] * liters_per_kg, 2) if band["min_kg"] is not None else None,
        "max_liters": round(band["max_kg"] * liters_per_kg, 2) if band["max_kg"] is not None else None,
    }
    return metadata


def _augment_gas_amount_labels(
    amount_labels: dict[str, Any],
    language: Language,
    molecular_weight: float | None = None,
    component_count: int = 1,
) -> dict[str, Any]:
    """Attach gas mass-band and volume-estimate metadata to amount labels."""
    result = dict(amount_labels)
    result.update(get_gas_amount_metadata(result.get("key", ""), molecular_weight=molecular_weight))
    result["basis_note"] = (
        "CREATE-SIMPLE workbook gas bands are mass-based; volume is shown as an ideal-gas estimate."
        if language == "en"
        else "CREATE-SIMPLEワークブックの気体取扱量区分は質量基準です。体積は理想気体としての推定値を表示しています。"
    )
    if component_count > 1:
        result["volume_note"] = (
            "Equivalent gas volume depends on each component molecular weight; see component-level estimates."
            if language == "en"
            else "等価ガス体積は各成分の分子量に依存します。成分別の推定値を参照してください。"
        )
        result.pop("volume_equivalent_at_25c_1atm", None)
    return result


def format_conditions_used(
    assessment_input: AssessmentInput,
    language: Language = "ja",
    volatility: str | None = None,
    dustiness: str | None = None,
    volatility_source: str | None = None,
    flash_point: float | None = None,
    boiling_point: float | None = None,
    gas_molecular_weight: float | None = None,
    component_count: int = 1,
) -> dict[str, Any]:
    """
    Format assessment conditions with human-readable labels.

    Args:
        assessment_input: The assessment input containing conditions
        language: Output language (ja/en)
        volatility: Auto-calculated volatility level (for liquids)
        dustiness: Auto-calculated or specified dustiness level (for solids)
        volatility_source: How volatility was determined (e.g., "boiling_point: 110.6°C")
        flash_point: Flash point in °C (for physical hazard context)
        boiling_point: Boiling point in °C (for volatility context)

    Returns:
        Dict with formatted condition details for LLM understanding
    """
    inp = assessment_input
    prop_type = inp.product_property.value

    result: dict[str, Any] = {
        "property_type": {
            "key": prop_type,
            "label": (
                "液体"
                if prop_type == "liquid"
                else "粉体"
                if prop_type == "solid"
                else "気体"
                if language == "ja"
                else "Liquid"
                if prop_type == "liquid"
                else "Solid"
                if prop_type == "solid"
                else "Gas"
            ),
        },
    }

    # Amount
    amount_labels = get_labels("amount", inp.amount_level.value, language, prop_type)
    if prop_type == "gas":
        amount_labels = _augment_gas_amount_labels(
            amount_labels,
            language=language,
            molecular_weight=gas_molecular_weight,
            component_count=component_count,
        )
    result["amount"] = amount_labels

    # Volatility (liquids only)
    if prop_type == "liquid" and volatility:
        vol_labels = get_labels("volatility", volatility, language)
        vol_labels["auto_calculated"] = True
        if volatility_source:
            vol_labels["source"] = volatility_source
        result["volatility"] = vol_labels
    # Dustiness (solids only)
    elif prop_type == "solid":
        dust_level = dustiness or "medium"
        dust_labels = get_labels("dustiness", dust_level, language)
        result["dustiness"] = dust_labels

    # Ventilation
    vent_labels = get_labels("ventilation", inp.ventilation.value, language)
    # Adjust coefficient for control velocity verification
    if inp.ventilation.value in ("local_ext", "local_enc"):
        if inp.control_velocity_verified:
            vent_labels["coefficient"] = vent_labels.get("coefficient_verified")
            vent_labels["control_velocity_verified"] = True
        else:
            vent_labels["coefficient"] = vent_labels.get("coefficient_unverified")
            vent_labels["control_velocity_verified"] = False
    result["ventilation"] = vent_labels

    # Work area size (liquids only)
    if prop_type == "liquid" and inp.work_area_size:
        area_labels = get_labels("work_area", inp.work_area_size, language)
        result["work_area_size"] = area_labels

    # Spray operation
    if inp.is_spray_operation:
        result["spray_operation"] = {
            "key": "yes",
            "label": "スプレー作業あり（×10）" if language == "ja" else "Spray operation (×10)",
            "coefficient": 10.0,
        }

    # Duration
    duration_info = {
        "hours_per_day": inp.working_hours_per_day,
        "frequency_type": inp.frequency_type,
        "frequency_value": inp.frequency_value,
    }
    if inp.frequency_type == "weekly":
        freq_label = f"週{inp.frequency_value}日" if language == "ja" else f"{inp.frequency_value} days/week"
    else:
        freq_label = f"月{inp.frequency_value}日" if language == "ja" else f"{inp.frequency_value} days/month"

    hours_label = f"{inp.working_hours_per_day}時間/日" if language == "ja" else f"{inp.working_hours_per_day}h/day"
    duration_info["label"] = f"{hours_label}、{freq_label}"
    result["duration"] = duration_info

    # Protection measures (RPE)
    if inp.rpe_type and inp.rpe_type.value != "none":
        rpe_labels = get_labels("rpe", inp.rpe_type.value, language)
        rpe_labels["fit_tested"] = inp.rpe_fit_tested
        result["respiratory_protection"] = rpe_labels

    # Gloves
    if inp.glove_type:
        glove_labels = get_labels("gloves", inp.glove_type.value, language)
        glove_labels["training"] = inp.glove_training
        if inp.glove_training:
            glove_labels["training_coefficient"] = 0.5
        result["gloves"] = glove_labels

    # Skin area (dermal assessment)
    if inp.exposed_skin_area:
        skin_labels = get_labels("skin_area", inp.exposed_skin_area.value, language)
        result["exposed_skin_area"] = skin_labels

    # Exposure variation
    if inp.exposure_variation:
        var_labels = get_labels("exposure_variation", inp.exposure_variation.value, language)
        result["exposure_variation"] = var_labels

    # Special flags
    if inp.ignore_minimum_floor:
        result["minimum_floor_disabled"] = {
            "label": "最小フロア制限無効" if language == "ja" else "Minimum floor disabled",
            "description": (
                "液体: 0.005ppm、粉体: 0.001mg/m³ の最小値制限を無効化"
                if language == "ja"
                else "Liquid: 0.005ppm, Solid: 0.001mg/m³ floor disabled"
            ),
        }

    # Physical properties (for physical hazard context)
    if flash_point is not None or boiling_point is not None:
        phys_props: dict[str, Any] = {}
        if flash_point is not None:
            phys_props["flash_point"] = {
                "value_celsius": flash_point,
                "label": f"引火点: {flash_point}°C" if language == "ja" else f"Flash point: {flash_point}°C",
            }
        if boiling_point is not None:
            phys_props["boiling_point"] = {
                "value_celsius": boiling_point,
                "label": f"沸点: {boiling_point}°C" if language == "ja" else f"Boiling point: {boiling_point}°C",
            }
        result["physical_properties"] = phys_props

    return result


def format_substance_properties(
    cas_number: str,
    name: str,
    content_percent: float,
    boiling_point: float | None = None,
    vapor_pressure: float | None = None,
    language: Language = "ja",
) -> dict[str, Any]:
    """
    Format substance properties for output.

    Args:
        cas_number: CAS registry number
        name: Substance name
        content_percent: Content percentage
        boiling_point: Boiling point in °C
        vapor_pressure: Vapor pressure in Pa
        language: Output language

    Returns:
        Dict with formatted substance properties
    """
    result = {
        "cas_number": cas_number,
        "name": name,
        "content_percent": content_percent,
    }

    # Content coefficient
    if content_percent >= 25:
        content_key = "high"
    elif content_percent >= 5:
        content_key = "medium_high"
    elif content_percent >= 1:
        content_key = "medium_low"
    else:
        content_key = "low"

    content_labels = get_labels("content", content_key, language)
    result["content_coefficient"] = content_labels

    # Physical properties
    if boiling_point is not None:
        result["boiling_point"] = {
            "value": boiling_point,
            "unit": "°C",
        }

    if vapor_pressure is not None:
        result["vapor_pressure"] = {
            "value": vapor_pressure,
            "unit": "Pa",
        }

    return result
