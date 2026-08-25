"""Verified control-scenario recalculation for CREATE-SIMPLE assessments."""

from __future__ import annotations

import hashlib
import itertools
import json
from typing import Any

from ..assessment.result import AssessmentResult
from ..models.risk import RiskLevel
from .common import ServiceError


SCENARIO_SCOPE_KEYS = {
    "amount": "conditions",
    "ventilation": "conditions",
    "control_velocity_verified": "conditions",
    "is_spray": "conditions",
    "exposure_variation": "conditions",
    "work_area_size": "conditions",
    "dustiness": "conditions",
    "hours": "duration",
    "days_per_week": "duration",
    "days_per_month": "duration",
    "rpe": "protection",
    "rpe_fit_tested": "protection",
    "gloves": "protection",
    "glove_training": "protection",
    "skin_area": "protection",
    "process_temperature": "physical_conditions",
    "has_ignition_sources": "physical_conditions",
    "has_explosive_atmosphere": "physical_conditions",
    "has_organic_matter": "physical_conditions",
    "has_air_water_contact": "physical_conditions",
    "ignore_minimum_floor": "methodology_sensitivity",
}

_AMOUNTS = ["large", "medium", "small", "minute", "trace"]
_VENTILATION = ["none", "basic", "industrial", "local_ext", "local_enc", "sealed"]
_HOURS = [8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0, 0.5]
_TARGET_HEALTH_THRESHOLDS = {"I": 0.1, "II-A": 0.5, "II-B": 1.0, "III": 10.0, "IV": float("inf")}
_TARGET_SIMPLE_LEVELS = {"I": 1, "II-A": 2, "II-B": 2, "II": 2, "III": 3, "IV": 4}


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _canonical_ventilation(value: Any) -> Any:
    aliases = {"local_external": "local_ext", "local_enclosed": "local_enc"}
    return aliases.get(str(_enum_value(value)), _enum_value(value))


def _baseline_fingerprint(result: AssessmentResult) -> str:
    payload = {
        "assessment_input": result.assessment_input.model_dump(mode="json"),
        "substances": [
            {"cas_number": cas, "content_percent": component.content_percent}
            for cas, component in sorted(result.components.items())
        ],
        "preset": getattr(result.builder, "_preset_name", None),
        "targets": {
            "inhalation": result.target_inhalation.get_label(),
            "dermal": result.target_dermal.get_label(),
            "physical": result.target_physical.get_label(),
        },
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(encoded.encode('utf-8')).hexdigest()}"


def _default_scope(result: AssessmentResult) -> dict[str, Any]:
    inp = result.assessment_input
    amount = _enum_value(inp.amount_level)
    amount_index = _AMOUNTS.index(amount)
    ventilation = _canonical_ventilation(inp.ventilation)
    ventilation_index = _VENTILATION.index(ventilation)
    scope: dict[str, Any] = {
        "amount": _AMOUNTS[amount_index + 1 :],
        "ventilation": _VENTILATION[ventilation_index + 1 :],
        "hours": [value for value in _HOURS if value < inp.working_hours_per_day],
        "rpe": ["half_mask", "full_mask", "papr"],
        "max_combination_size": 2,
        "max_scenarios": 50,
    }
    if inp.frequency_type == "weekly":
        scope["days_per_week"] = [
            value for value in (3, 1) if value < inp.frequency_value
        ]
    return scope


def _normalize_scope(result: AssessmentResult, scope: dict[str, Any] | None) -> dict[str, Any]:
    normalized = _default_scope(result) if scope is None else dict(scope)
    normalized.setdefault("max_combination_size", 2)
    normalized.setdefault("max_scenarios", 50)
    unknown = set(normalized) - set(SCENARIO_SCOPE_KEYS) - {
        "max_combination_size",
        "max_scenarios",
        "scenarios",
    }
    if unknown:
        raise ServiceError(
            "INVALID_RECOMMENDATION_SCOPE",
            f"Unsupported recommendation_scope keys: {sorted(unknown)}",
            details={"supported_keys": sorted(SCENARIO_SCOPE_KEYS)},
        )
    max_combination = normalized.get("max_combination_size", 2)
    max_scenarios = normalized.get("max_scenarios", 50)
    if not isinstance(max_combination, int) or not 1 <= max_combination <= 4:
        raise ServiceError(
            "INVALID_RECOMMENDATION_SCOPE",
            "max_combination_size must be an integer from 1 to 4",
        )
    if not isinstance(max_scenarios, int) or not 1 <= max_scenarios <= 200:
        raise ServiceError(
            "INVALID_RECOMMENDATION_SCOPE",
            "max_scenarios must be an integer from 1 to 200",
        )
    for key in SCENARIO_SCOPE_KEYS:
        if key in normalized and not isinstance(normalized[key], list):
            raise ServiceError(
                "INVALID_RECOMMENDATION_SCOPE",
                f"recommendation_scope.{key} must be an array",
            )
    return normalized


def _current_value(result: AssessmentResult, key: str) -> Any:
    inp = result.assessment_input
    mapping = {
        "amount": inp.amount_level,
        "ventilation": inp.ventilation,
        "control_velocity_verified": inp.control_velocity_verified,
        "is_spray": inp.is_spray_operation,
        "exposure_variation": inp.exposure_variation,
        "work_area_size": inp.work_area_size,
        "dustiness": getattr(inp, "volatility_or_dustiness", None),
        "hours": inp.working_hours_per_day,
        "rpe": inp.rpe_type,
        "rpe_fit_tested": inp.rpe_fit_tested,
        "gloves": inp.glove_type,
        "glove_training": inp.glove_training,
        "skin_area": inp.exposed_skin_area,
        "process_temperature": inp.process_temperature,
        "has_ignition_sources": inp.has_ignition_sources,
        "has_explosive_atmosphere": inp.has_explosive_atmosphere,
        "has_organic_matter": inp.has_organic_matter,
        "has_air_water_contact": inp.has_air_water_contact,
        "ignore_minimum_floor": inp.ignore_minimum_floor,
    }
    if key == "days_per_week":
        return inp.frequency_value if inp.frequency_type == "weekly" else None
    if key == "days_per_month":
        return inp.frequency_value if inp.frequency_type != "weekly" else None
    value = _enum_value(mapping[key])
    return _canonical_ventilation(value) if key == "ventilation" else value


def _nest_changes(changes: dict[str, Any]) -> dict[str, Any]:
    nested: dict[str, Any] = {}
    for key, value in changes.items():
        group = SCENARIO_SCOPE_KEYS[key]
        nested.setdefault(group, {})[key] = value
    return nested


def _flatten_changes(changes: dict[str, Any]) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in changes.items():
        if key in SCENARIO_SCOPE_KEYS:
            flat[key] = value
        elif key in {"conditions", "duration", "protection", "physical_conditions", "methodology_sensitivity"}:
            if not isinstance(value, dict):
                raise ServiceError("INVALID_SCENARIO", f"scenario.{key} must be an object")
            for nested_key, nested_value in value.items():
                if nested_key not in SCENARIO_SCOPE_KEYS:
                    raise ServiceError("INVALID_SCENARIO", f"Unsupported scenario key: {nested_key}")
                flat[nested_key] = nested_value
        else:
            raise ServiceError("INVALID_SCENARIO", f"Unsupported scenario key: {key}")
    return flat


def _generated_change_sets(result: AssessmentResult, scope: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    factors: list[tuple[str, list[Any]]] = []
    for key in SCENARIO_SCOPE_KEYS:
        values = []
        current = _current_value(result, key)
        for value in scope.get(key, []):
            canonical = _canonical_ventilation(value) if key == "ventilation" else value
            if canonical != current and canonical not in values:
                values.append(canonical)
        if values:
            factors.append((key, values))

    requested_count = 0
    generated: list[dict[str, Any]] = []
    limit = scope["max_scenarios"]
    max_size = min(scope["max_combination_size"], len(factors))
    for size in range(1, max_size + 1):
        for selected in itertools.combinations(factors, size):
            option_lists = [options for _, options in selected]
            for option_values in itertools.product(*option_lists):
                requested_count += 1
                if len(generated) < limit:
                    generated.append(
                        {key: value for (key, _), value in zip(selected, option_values)}
                    )
    return generated, requested_count


def _explicit_change_sets(scenarios: list[dict[str, Any]], max_scenarios: int) -> tuple[list[dict[str, Any]], int]:
    if not isinstance(scenarios, list):
        raise ServiceError("INVALID_SCENARIO", "scenarios must be an array")
    generated: list[dict[str, Any]] = []
    for index, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict):
            raise ServiceError("INVALID_SCENARIO", f"scenarios[{index}] must be an object")
        raw_changes = scenario.get("changes", scenario)
        generated.append(_flatten_changes(raw_changes))
    return generated[:max_scenarios], len(generated)


def _component_payload(result: AssessmentResult) -> tuple[dict[str, Any], set[str], set[str]]:
    components: dict[str, Any] = {}
    calculated: set[str] = set()
    incomplete: set[str] = set()
    for cas, component in result.components.items():
        item: dict[str, Any] = {
            "cas_number": cas,
            "name": component.name,
            "content_percent": component.content_percent,
            "overall_risk_label": component.risk_label,
        }
        if component.inhalation:
            calculated.add("inhalation_8h")
            inhalation: dict[str, Any] = {
                "rcr": round(component.inhalation.rcr, 6),
                "risk_label": RiskLevel.get_detailed_label(component.inhalation.rcr),
            }
            if component.inhalation.stel_rcr is not None:
                calculated.add("inhalation_stel")
                inhalation["stel_rcr"] = round(component.inhalation.stel_rcr, 6)
                inhalation["stel_risk_label"] = RiskLevel.get_simple_label(
                    component.inhalation.stel_rcr
                )
            item["inhalation"] = inhalation
        if component.dermal:
            calculated.add("dermal")
            item["dermal"] = {
                "rcr": round(component.dermal.rcr, 6),
                "risk_label": RiskLevel.get_simple_label(component.dermal.rcr),
            }
        if component.physical:
            calculated.add("physical")
            item["physical"] = {
                "risk_level": int(component.physical.risk_level),
                "risk_label": {1: "I", 2: "II", 3: "III", 4: "IV"}.get(
                    int(component.physical.risk_level), "IV"
                ),
                "hazard_type": component.physical.hazard_type,
            }
        for skipped in component.skipped_assessments:
            incomplete.add(skipped.get("risk_type", "unknown"))
        for error in component.calculation_errors:
            incomplete.add(error.get("risk_type", "unknown"))
        if component.skipped_assessments:
            item["skipped_assessments"] = component.skipped_assessments
        if component.calculation_errors:
            item["calculation_errors"] = component.calculation_errors
        components[cas] = item
    return components, calculated, incomplete


def _target_status(result: AssessmentResult, target_level: str) -> str:
    health_threshold = _TARGET_HEALTH_THRESHOLDS[target_level]
    simple_target = _TARGET_SIMPLE_LEVELS[target_level]
    observed = False
    incomplete = bool(result.errors)
    for component in result.components.values():
        if component.skipped_assessments:
            incomplete = True
        if component.inhalation:
            observed = True
            if component.inhalation.rcr > health_threshold:
                return "not_achieved"
            if component.inhalation.stel_rcr is not None:
                stel_level = int(RiskLevel.from_rcr(component.inhalation.stel_rcr))
                if stel_level > simple_target:
                    return "not_achieved"
        if component.dermal:
            observed = True
            if int(component.dermal.risk_level) > simple_target:
                return "not_achieved"
        if component.physical:
            observed = True
            if int(component.physical.risk_level) > simple_target:
                return "not_achieved"
    if result.mixed_inhalation_rcr is not None:
        observed = True
        if result.mixed_inhalation_rcr > health_threshold:
            return "not_achieved"
    if result.mixed_dermal_rcr is not None:
        observed = True
        mixed_dermal_level = int(RiskLevel.from_rcr(result.mixed_dermal_rcr))
        if mixed_dermal_level > simple_target:
            return "not_achieved"
    if incomplete or not observed:
        return "indeterminate"
    return "achieved"


def _compact_result(result: AssessmentResult, target_level: str) -> dict[str, Any]:
    components, calculated, incomplete = _component_payload(result)
    payload: dict[str, Any] = {
        "overall_risk": {
            "level": result.overall_risk_level,
            "label": result.overall_risk_label,
        },
        "components": components,
        "covered_risk_types": sorted(calculated),
        "incomplete_risk_types": sorted(incomplete),
    }
    if len(result.components) > 1:
        payload["mixed_exposure"] = {
            "inhalation_rcr": round(result.mixed_inhalation_rcr, 6)
            if result.mixed_inhalation_rcr is not None
            else None,
            "inhalation_risk_label": RiskLevel.get_detailed_label(
                result.mixed_inhalation_rcr
            )
            if result.mixed_inhalation_rcr is not None
            else None,
            "dermal_rcr": round(result.mixed_dermal_rcr, 6)
            if result.mixed_dermal_rcr is not None
            else None,
        }
    if result.warnings:
        payload["warnings"] = result.warnings
    if result.errors:
        payload["errors"] = result.errors
    status = _target_status(result, target_level)
    payload["target_status"] = status
    payload["achieves_target"] = True if status == "achieved" else False if status == "not_achieved" else None
    return payload


def _scenario_id(changes: dict[str, Any]) -> str:
    encoded = json.dumps(changes, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:12]
    return f"scenario_{digest}"


def _requested_risk_types(result: AssessmentResult) -> list[str]:
    inp = result.assessment_input
    requested: list[str] = []
    if inp.assess_inhalation:
        requested.extend(["inhalation_8h", "inhalation_stel"])
    if inp.assess_dermal:
        requested.append("dermal")
    if inp.assess_physical:
        requested.append("physical")
    return requested


def calculate_scenarios_from_result(
    result: AssessmentResult,
    *,
    target_level: str = "II-A",
    recommendation_scope: dict[str, Any] | None = None,
    scenarios: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Recalculate a bounded range or an explicit batch from one baseline result."""
    target = target_level.upper()
    if target not in _TARGET_HEALTH_THRESHOLDS:
        raise ServiceError("INVALID_TARGET_LEVEL", f"Unsupported target level: {target_level}")
    scope = _normalize_scope(result, recommendation_scope)
    if scenarios is not None:
        changes_to_run, requested_count = _explicit_change_sets(
            scenarios, scope["max_scenarios"]
        )
        generation_mode = "explicit"
    elif "scenarios" in scope:
        changes_to_run, requested_count = _explicit_change_sets(
            scope["scenarios"], scope["max_scenarios"]
        )
        generation_mode = "explicit"
    else:
        changes_to_run, requested_count = _generated_change_sets(result, scope)
        generation_mode = "range"

    fingerprint = _baseline_fingerprint(result)
    scenario_results: list[dict[str, Any]] = []
    for flat_changes in changes_to_run:
        nested = _nest_changes(flat_changes)
        entry: dict[str, Any] = {
            "scenario_id": _scenario_id(nested),
            "changes": nested,
            "calculation_status": "recalculated",
            "methodology_version": result.assessment_input.methodology_version,
            "baseline_fingerprint": fingerprint,
        }
        try:
            recalculated = result.what_if(**flat_changes)
            entry["result"] = _compact_result(recalculated, target)
            entry["achieves_target"] = entry["result"]["achieves_target"]
            entry["target_status"] = entry["result"]["target_status"]
            entry["covered_risk_types"] = entry["result"]["covered_risk_types"]
            if entry["result"].get("errors"):
                entry["calculation_status"] = "not_calculable"
        except Exception as exc:
            entry.update(
                {
                    "calculation_status": "not_calculable",
                    "achieves_target": None,
                    "target_status": "indeterminate",
                    "covered_risk_types": [],
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                }
            )
        scenario_results.append(entry)

    scenario_results.sort(
        key=lambda item: (
            0 if item.get("target_status") == "achieved" else 1,
            item.get("result", {}).get("overall_risk", {}).get("level", 99),
            len(item["changes"]),
            item["scenario_id"],
        )
    )
    scope_values = {key: scope[key] for key in SCENARIO_SCOPE_KEYS if key in scope}
    return {
        "schema_version": "1.0",
        "calculation_basis": "full_recalculation",
        "calculation_status_values": ["recalculated", "estimated", "not_calculable"],
        "methodology_version": result.assessment_input.methodology_version,
        "baseline_fingerprint": fingerprint,
        "target_level": target,
        "baseline": _compact_result(result, target),
        "coverage": {
            "generation_mode": generation_mode,
            "requested_risk_types": _requested_risk_types(result),
            "requested_scope": scope_values,
            "max_combination_size": scope["max_combination_size"],
            "max_scenarios": scope["max_scenarios"],
            "requested_scenario_count": requested_count,
            "recalculated_scenario_count": len(scenario_results),
            "truncated": requested_count > len(scenario_results),
            "reuse_rule": "Reuse only when baseline_fingerprint, methodology_version, and exact changes match.",
        },
        "scenarios": scenario_results,
    }


def verified_recommendations(analysis: dict[str, Any], *, language: str) -> list[dict[str, Any]]:
    """Create concise recommendation rows that retain recalculation provenance."""
    rows: list[dict[str, Any]] = []
    for scenario in analysis["scenarios"]:
        if scenario["calculation_status"] != "recalculated":
            continue
        result = scenario.get("result", {})
        rows.append(
            {
                "scenario_id": scenario["scenario_id"],
                "changes": scenario["changes"],
                "calculation_status": scenario["calculation_status"],
                "baseline_fingerprint": scenario["baseline_fingerprint"],
                "methodology_version": scenario["methodology_version"],
                "covered_risk_types": scenario["covered_risk_types"],
                "predicted_level": result.get("overall_risk", {}).get("label"),
                "target_status": scenario["target_status"],
                "achieves_target": scenario["achieves_target"],
                "summary": (
                    "指定した管理条件で実際に再計算した結果です"
                    if language == "ja"
                    else "Result fully recalculated with the specified controls"
                ),
            }
        )
    return rows
