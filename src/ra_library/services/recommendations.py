"""Service helpers for recommendation workflows."""

from __future__ import annotations

from typing import Any

from .. import get_database
from .common import ServiceError, ServiceResult


def get_recommendations(
    cas_number: str | None = None,
    current_rcr: float | None = None,
    substances: list[dict[str, Any]] | None = None,
    preset: str | None = None,
    conditions: dict[str, Any] | None = None,
    duration: dict[str, Any] | None = None,
    protection: dict[str, Any] | None = None,
    assess_inhalation: bool = True,
    assess_dermal: bool = True,
    assess_physical: bool = True,
    target_level: str = "II-A",
    engineering_only: bool = False,
    recommendation_scope: dict[str, Any] | None = None,
    methodology_version: str = "v3.2.1",
    language: str = "en",
) -> ServiceResult:
    """Return controls whose numeric effects were fully recalculated.

    ``cas_number`` is retained for compatibility. New callers should provide the
    complete ``substances`` mixture and baseline conditions so scenario results
    cannot silently fall back to a 100% single-substance assessment.
    """
    from .calculate import calculate_risk

    if substances is None:
        if not cas_number:
            raise ServiceError(
                "MISSING_SUBSTANCES",
                "Provide substances or the legacy cas_number argument",
            )
        db = get_database()
        if not db.lookup(cas_number):
            raise ServiceError(
                "SUBSTANCE_NOT_FOUND",
                f"Substance not found: {cas_number}",
                details={"cas_number": cas_number},
            )
        substances = [{"cas_number": cas_number, "content_percent": 100.0}]

    scope = dict(recommendation_scope or {})
    if engineering_only and not recommendation_scope:
        scope = {
            "ventilation": ["local_external", "local_enclosed", "sealed"],
            "amount": ["small", "minute", "trace"],
            "hours": [4, 2, 1, 0.5],
            "days_per_week": [3, 1],
            "max_combination_size": 2,
            "max_scenarios": 50,
        }

    calculated = calculate_risk(
        substances=substances,
        preset=preset,
        conditions=conditions,
        duration=duration,
        protection=protection,
        assess_inhalation=assess_inhalation,
        assess_dermal=assess_dermal,
        assess_physical=assess_physical,
        target_level=target_level,
        include_recommendations="verified",
        recommendation_scope=scope or None,
        methodology_version=methodology_version,
        language=language,
    )
    analysis = calculated.data["recommendation_analysis"]
    paths = calculated.data.get("recommendations", [])
    achievable = any(path.get("achieves_target") is True for path in paths)
    baseline = analysis["baseline"]
    data = {
        "mode": "verified_recalculation",
        "substances": [
            {
                "cas_number": component["cas_number"],
                "name": component["name"],
                "content_percent": component["content_percent"],
            }
            for component in baseline["components"].values()
        ],
        "current": {
            "provided_rcr": current_rcr,
            "calculated": baseline,
        },
        "target": {"level": target_level},
        "achievable": achievable,
        "summary": _summary_from_paths(paths, target_level, achievable, language),
        "paths": paths,
        "recommendation_analysis": analysis,
    }
    return ServiceResult(data=data, warnings=calculated.warnings)


def _level_to_int(level: str) -> int:
    mapping = {"I": 1, "II-A": 2, "II-B": 3, "III": 4, "IV": 5}
    return mapping.get((level or "").upper(), 5)


def _recommendation_path(rec: Any, index: int, language: str) -> dict[str, Any]:
    """Map a recommendation model to API response path shape."""
    path: dict[str, Any] = {
        "id": f"rec_{index}",
        "priority": rec.priority,
        "category": rec.category.value,
        "action": rec.action_ja if language == "ja" and rec.action_ja else rec.action,
        "description": rec.description_ja
        if language == "ja" and rec.description_ja
        else rec.description,
        "effectiveness": rec.effectiveness.value,
        "feasibility": rec.feasibility.value,
        "current_level": rec.current_risk_level,
        "predicted_level": rec.predicted_risk_level,
        "current_rcr": rec.current_rcr,
        "predicted_rcr": rec.predicted_rcr,
        "rcr_reduction_percent": round(rec.rcr_reduction_percent, 1),
    }
    if rec.parameter_affected:
        path["parameter_change"] = {
            "parameter": rec.parameter_affected,
            "from": rec.current_value,
            "to": rec.new_value,
            "coefficient": rec.coefficient_change,
        }
    notes = rec.implementation_notes_ja if language == "ja" else rec.implementation_notes
    if notes:
        path["notes"] = notes
    return path


def _summary_from_paths(
    paths: list[dict[str, Any]], target_level: str, achievable: bool, language: str
) -> str:
    if not paths:
        return (
            "推奨対策は見つかりませんでした"
            if language == "ja"
            else "No recommendation paths were generated"
        )

    if language == "ja":
        head = f"{len(paths)}件の推奨対策を提示しました。"
        tail = (
            f"目標レベル{target_level}は到達可能です。"
            if achievable
            else f"目標レベル{target_level}への到達は追加対策が必要です。"
        )
        return f"{head}{tail}"

    head = f"{len(paths)} recommendation paths were generated."
    tail = (
        f"Target level {target_level} is achievable."
        if achievable
        else f"Reaching target level {target_level} requires additional controls."
    )
    return f"{head} {tail}"


def _generate_basic_recommendations(component: Any, target_level: str, language: str) -> str:
    recommendations: list[str] = []

    if _level_to_int(component.risk_label) > _level_to_int(target_level):
        if language == "ja":
            if component.inhalation and component.inhalation.rcr > 1.0:
                recommendations.append("- 換気の改善を検討してください(局所排気、囲い式など)")
                recommendations.append("- 作業時間または頻度の削減を検討してください")
                recommendations.append("- 呼吸用保護具の使用を検討してください")
            if component.dermal:
                recommendations.append("- 耐薬品性手袋の使用を検討してください")
            return "\n".join(recommendations) if recommendations else "対策が必要です"

        if component.inhalation and component.inhalation.rcr > 1.0:
            recommendations.append("- Consider improving ventilation (local exhaust, enclosure)")
            recommendations.append("- Consider reducing work duration or frequency")
            recommendations.append("- Consider using respiratory protection")
        if component.dermal:
            recommendations.append("- Consider using chemical-resistant gloves")
        return "\n".join(recommendations) if recommendations else "Controls needed"

    return (
        "現在のリスクレベルは目標を達成しています"
        if language == "ja"
        else "Current risk level meets target"
    )
