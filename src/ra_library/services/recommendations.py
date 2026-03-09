"""Service helpers for recommendation workflows."""

from __future__ import annotations

from typing import Any

from .. import RiskAssessment, get_database
from .common import ServiceError, ServiceResult, warning_item


def get_recommendations(
    cas_number: str,
    current_rcr: float | None = None,
    preset: str | None = None,
    target_level: str = "II-A",
    engineering_only: bool = False,
    language: str = "en",
) -> ServiceResult:
    """Get control measure suggestions for reducing risk."""
    db = get_database()
    substance_data = db.lookup(cas_number)
    if not substance_data:
        raise ServiceError(
            "SUBSTANCE_NOT_FOUND",
            f"Substance not found: {cas_number}",
            details={"cas_number": cas_number},
        )

    assessment = RiskAssessment()
    if preset:
        try:
            assessment = assessment.use_preset(preset)
        except ValueError as exc:
            raise ServiceError("INVALID_PRESET", str(exc)) from exc

    try:
        assessment = (
            assessment
            .add_substance(cas_number, content=100.0)
            .with_target_levels(inhalation=target_level)
            .with_language(language)
        )
    except ValueError as exc:
        raise ServiceError("ASSESSMENT_SETUP_FAILED", f"Assessment setup failed: {exc}") from exc

    if engineering_only:
        assessment = assessment.with_constraints(no_ppe=True)

    try:
        result = assessment.calculate()
    except ValueError as exc:
        raise ServiceError("CALCULATION_FAILED", f"Calculation failed: {exc}") from exc

    component = result.components.get(cas_number)
    if not component:
        raise ServiceError("MISSING_COMPONENT_RESULT", "Failed to calculate recommendations")

    warnings: list[dict[str, Any]] = []
    for warning in getattr(result, "warnings", []):
        warnings.append(warning_item("ASSESSMENT_PARTIAL_FAILURE", warning))

    current_level = component.risk_label
    computed_rcr = round(component.inhalation.rcr, 4) if component.inhalation else None
    current_rcr_value = current_rcr if current_rcr is not None else computed_rcr

    try:
        recommendations = result.get_recommendations_for_substance(cas_number)
        paths = [_recommendation_path(rec, idx, language) for idx, rec in enumerate(recommendations[:5], start=1)]
        target_level_int = _level_to_int(target_level)
        achievable = any(
            _level_to_int(path["predicted_level"]) <= target_level_int
            for path in paths
            if path.get("predicted_level")
        )

        data = {
            "mode": "analysis",
            "substance": {
                "cas_number": cas_number,
                "name": substance_data.name_en if language == "en" else substance_data.name_ja,
            },
            "current": {
                "rcr": current_rcr_value,
                "level": current_level,
            },
            "target": {
                "level": target_level,
            },
            "achievable": achievable,
            "summary": _summary_from_paths(paths, target_level, achievable, language),
            "paths": paths,
        }
        return ServiceResult(data=data, warnings=warnings)
    except Exception as exc:
        warnings.append(
            warning_item(
                "RECOMMENDATION_ANALYSIS_FALLBACK",
                "Detailed recommendation analysis unavailable; using basic fallback"
                if language == "en"
                else "詳細な推奨分析を生成できないため、基本推奨にフォールバックしました",
                details={"error_type": type(exc).__name__, "error": str(exc)},
            )
        )
        data = {
            "mode": "fallback",
            "substance": {
                "cas_number": cas_number,
                "name": substance_data.name_en if language == "en" else substance_data.name_ja,
            },
            "current": {
                "rcr": current_rcr_value,
                "level": current_level,
            },
            "target": {
                "level": target_level,
            },
            "achievable": _level_to_int(current_level) <= _level_to_int(target_level),
            "summary": _generate_basic_recommendations(component, target_level, language),
            "paths": [],
        }
        return ServiceResult(data=data, warnings=warnings)


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
        "description": rec.description_ja if language == "ja" and rec.description_ja else rec.description,
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


def _summary_from_paths(paths: list[dict[str, Any]], target_level: str, achievable: bool, language: str) -> str:
    if not paths:
        return "推奨対策は見つかりませんでした" if language == "ja" else "No recommendation paths were generated"

    if language == "ja":
        head = f"{len(paths)}件の推奨対策を提示しました。"
        tail = f"目標レベル{target_level}は到達可能です。" if achievable else f"目標レベル{target_level}への到達は追加対策が必要です。"
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

    return "現在のリスクレベルは目標を達成しています" if language == "ja" else "Current risk level meets target"
