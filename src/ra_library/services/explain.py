"""Service helpers for explanation workflows."""

from __future__ import annotations

from .. import RiskAssessment
from .common import ServiceError, ServiceResult


def explain_calculation(
    cas_number: str,
    content_percent: float = 100.0,
    preset: str | None = None,
    risk_type: str = "inhalation",
    language: str = "en",
) -> ServiceResult:
    """Build a detailed calculation breakdown for one substance."""
    assessment = RiskAssessment().verbose(True)

    if preset:
        try:
            assessment = assessment.use_preset(preset)
        except ValueError as exc:
            raise ServiceError("INVALID_PRESET", str(exc)) from exc

    try:
        assessment = assessment.add_substance(cas_number, content=content_percent)
    except ValueError as exc:
        raise ServiceError("SUBSTANCE_LOOKUP_FAILED", f"Substance lookup failed: {exc}") from exc

    if risk_type == "dermal":
        assessment = assessment.with_assessments(dermal=True)
    elif risk_type == "physical":
        assessment = assessment.with_assessments(physical=True)

    try:
        result = assessment.calculate()
    except ValueError as exc:
        raise ServiceError("CALCULATION_FAILED", f"Calculation failed: {exc}") from exc

    component = result.components.get(cas_number)
    if not component:
        raise ServiceError("MISSING_COMPONENT_RESULT", f"Failed to assess substance: {cas_number}")

    risk_result = None
    if risk_type == "inhalation" and component.inhalation:
        risk_result = component.inhalation
    elif risk_type == "dermal" and component.dermal:
        risk_result = component.dermal
    elif risk_type == "physical" and component.physical:
        risk_result = component.physical

    if not risk_result:
        raise ServiceError(
            "ASSESSMENT_NOT_AVAILABLE",
            f"No {risk_type} assessment available for this substance",
        )

    output = {
        "substance": {
            "cas_number": cas_number,
            "name": component.name,
        },
        "input_snapshot": {
            "content_percent": content_percent,
            "preset": preset,
            "risk_type": risk_type,
            "language": language,
        },
        "risk_type": risk_type,
        "result": {
            "rcr": round(risk_result.rcr, 4) if hasattr(risk_result, "rcr") else None,
            "risk_level": int(risk_result.risk_level),
            "risk_label": component.risk_label,
        },
        "calculation_steps": [],
        "contributing_factors": [],
        "limitations": [],
    }

    explanation = getattr(risk_result, "explanation", None)
    if explanation:
        steps = getattr(explanation, "steps", [])
        for step in steps:
            output["calculation_steps"].append(
                {
                    "step": getattr(step, "step_number", None),
                    "description": getattr(step, "description_ja", step.description)
                    if language == "ja"
                    else step.description,
                    "formula": getattr(step, "formula", None),
                    "inputs": getattr(step, "input_values", {}),
                    "output": f"{getattr(step, 'output_value', '')} {getattr(step, 'output_unit', '')}".strip(),
                    "explanation": getattr(step, "explanation_ja", getattr(step, "explanation", ""))
                    if language == "ja"
                    else getattr(step, "explanation", ""),
                }
            )

        factors = getattr(explanation, "factors", [])
        for factor in factors:
            factor_data = {
                "name": getattr(factor, "factor_name_ja", factor.factor_name)
                if language == "ja"
                else factor.factor_name,
                "value": getattr(factor, "factor_value", None),
                "coefficient": getattr(factor, "coefficient", None),
                "contribution_percent": round(getattr(factor, "contribution_percent", 0), 1),
                "is_beneficial": getattr(factor, "is_beneficial", False),
                "can_improve": getattr(factor, "can_be_improved", False),
            }
            improvement_options = getattr(factor, "improvement_options", None)
            if improvement_options:
                factor_data["improvement_options"] = improvement_options
            output["contributing_factors"].append(factor_data)

        limitations = getattr(explanation, "limitations", [])
        for limitation in limitations:
            limitation_data = {
                "factor": getattr(limitation, "factor_name_ja", limitation.factor_name)
                if language == "ja"
                else limitation.factor_name,
                "description": getattr(limitation, "description_ja", limitation.description)
                if language == "ja"
                else limitation.description,
                "impact": getattr(limitation, "impact_ja", getattr(limitation, "impact", ""))
                if language == "ja"
                else getattr(limitation, "impact", ""),
            }
            alternatives = getattr(limitation, "alternatives", None)
            if alternatives:
                limitation_data["alternatives"] = alternatives
            output["limitations"].append(limitation_data)

        output["summary"] = (
            getattr(explanation, "summary_ja", None) if language == "ja" else getattr(explanation, "summary", None)
        )
    else:
        output["summary"] = _generate_basic_explanation(risk_result, risk_type, language)

    return ServiceResult(data=output)


def _generate_basic_explanation(risk_result, risk_type: str, language: str) -> str:
    """Generate basic explanation when detailed explanation is unavailable."""
    if risk_type == "inhalation":
        if language == "ja":
            return (
                f"リスク計算式: RCR = ばく露濃度 ÷ ばく露限界値\n"
                f"RCR値: {round(risk_result.rcr, 4) if hasattr(risk_result, 'rcr') else 'N/A'}\n"
                f"リスクレベル: {int(risk_result.risk_level)}\n"
                "※詳細な説明を取得するにはverboseモードを有効にしてください"
            )
        return (
            "Risk calculation: RCR = Exposure / OEL\n"
            f"RCR value: {round(risk_result.rcr, 4) if hasattr(risk_result, 'rcr') else 'N/A'}\n"
            f"Risk level: {int(risk_result.risk_level)}\n"
            "Enable verbose mode for detailed calculation steps"
        )
    if risk_type == "dermal":
        if language == "ja":
            return (
                "経皮リスク計算\n"
                f"RCR値: {round(risk_result.rcr, 4) if hasattr(risk_result, 'rcr') else 'N/A'}\n"
                f"リスクレベル: {int(risk_result.risk_level)}"
            )
        return (
            "Dermal risk calculation\n"
            f"RCR value: {round(risk_result.rcr, 4) if hasattr(risk_result, 'rcr') else 'N/A'}\n"
            f"Risk level: {int(risk_result.risk_level)}"
        )
    if language == "ja":
        return f"物理的危険性評価\nリスクレベル: {int(risk_result.risk_level)}"
    return f"Physical hazard assessment\nRisk level: {int(risk_result.risk_level)}"
