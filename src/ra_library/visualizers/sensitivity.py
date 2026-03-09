"""
Sensitivity analysis for risk assessment.

Calculates how much each parameter contributes to the overall risk
and ranks parameters by their impact.

Reference: CREATE-SIMPLE Design v3.1.1
"""

from pydantic import BaseModel, Field

from ..models.assessment import (
    AssessmentInput,
    AssessmentMode,
    VentilationLevel,
    AmountLevel,
)
from ..models.substance import Substance
from ..calculators.constants import VENTILATION_COEFFICIENTS


class SensitivityBar(BaseModel):
    """
    Sensitivity analysis for a single parameter.

    Shows how much changing this parameter affects the result.
    Used for horizontal bar charts showing parameter importance.
    """

    parameter_name: str  # "ventilation"
    parameter_label: str  # "Ventilation"
    parameter_label_ja: str = ""  # "換気"
    current_value: str  # "Industrial"
    current_coefficient: float  # 1.0

    # How much this contributes to current RCR
    contribution_percent: float

    # How much improvement is possible
    max_reduction_percent: float

    # Best coefficient achievable
    best_coefficient: float

    # Is this controllable by the user?
    is_controllable: bool = True


class SensitivityAnalysis(BaseModel):
    """Complete sensitivity analysis for all parameters."""

    current_rcr: float
    current_risk_level: int

    # Parameters sorted by contribution
    parameters: list[SensitivityBar] = Field(default_factory=list)

    # Summary
    dominant_factor: str = ""
    highest_improvement_potential: str = ""
    total_improvement_possible: float = 0.0


def calculate_sensitivity(
    assessment_input: AssessmentInput,
    substance: Substance,
    current_exposure: float,
    effective_oel: float,
    language: str = "en",
) -> SensitivityAnalysis:
    """
    Calculate sensitivity analysis for all parameters.

    Args:
        assessment_input: Current assessment input
        substance: Substance being assessed
        current_exposure: Current calculated exposure
        effective_oel: Effective OEL
        language: "en" or "ja"

    Returns:
        SensitivityAnalysis with ranked parameters
    """
    from ..models.risk import RiskLevel

    current_rcr = current_exposure / effective_oel
    current_level = RiskLevel.from_rcr(current_rcr).value

    parameters = []

    # Analyze ventilation
    vent_bar = _analyze_ventilation_sensitivity(
        assessment_input, current_exposure, effective_oel, language
    )
    parameters.append(vent_bar)

    # Analyze amount
    amount_bar = _analyze_amount_sensitivity(
        assessment_input, current_exposure, effective_oel, language
    )
    parameters.append(amount_bar)

    # Analyze duration
    duration_bar = _analyze_duration_sensitivity(
        assessment_input, current_exposure, effective_oel, language
    )
    parameters.append(duration_bar)

    # Analyze spray (if applicable)
    if assessment_input.is_spray_operation:
        spray_bar = _analyze_spray_sensitivity(
            assessment_input, current_exposure, effective_oel, language
        )
        parameters.append(spray_bar)

    # Analyze RPE (Report mode only)
    if assessment_input.mode == AssessmentMode.REPORT:
        rpe_bar = _analyze_rpe_sensitivity(
            assessment_input, current_exposure, effective_oel, language
        )
        parameters.append(rpe_bar)

    # Sort by contribution
    parameters.sort(key=lambda p: p.contribution_percent, reverse=True)

    # Find dominant and highest potential
    dominant = parameters[0].parameter_name if parameters else ""
    highest_potential = (
        max(parameters, key=lambda p: p.max_reduction_percent) if parameters else None
    )
    highest_potential_name = highest_potential.parameter_name if highest_potential else ""

    # Calculate total improvement
    total_improvement = sum(p.max_reduction_percent for p in parameters)

    return SensitivityAnalysis(
        current_rcr=current_rcr,
        current_risk_level=current_level,
        parameters=parameters,
        dominant_factor=dominant,
        highest_improvement_potential=highest_potential_name,
        total_improvement_possible=min(total_improvement, 99.9),  # Cap at 99.9%
    )


def _analyze_ventilation_sensitivity(
    assessment_input: AssessmentInput,
    current_exposure: float,
    effective_oel: float,
    language: str,
) -> SensitivityBar:
    """Analyze ventilation parameter sensitivity."""
    current_vent = assessment_input.ventilation
    verified = assessment_input.control_velocity_verified
    current_coeff = VENTILATION_COEFFICIENTS.get((current_vent.value, verified), 1.0)

    # Best achievable ventilation coefficient
    best_coeff = VENTILATION_COEFFICIENTS[("sealed", False)]  # 0.001

    # Calculate contribution and improvement
    # Contribution = how much current coefficient increases RCR vs baseline (1.0)
    if current_coeff > 1.0:
        contribution = ((current_coeff - 1.0) / current_coeff) * 100
    else:
        contribution = 0.0

    # Improvement = how much reducing to best would help
    improvement = ((current_coeff - best_coeff) / current_coeff) * 100

    if language == "ja":
        vent_labels = {
            VentilationLevel.NONE: "換気なし",
            VentilationLevel.BASIC: "一般換気",
            VentilationLevel.INDUSTRIAL: "工業的換気",
            VentilationLevel.LOCAL_EXTERNAL: "局所排気(外付け)",
            VentilationLevel.LOCAL_ENCLOSED: "局所排気(囲い式)",
            VentilationLevel.SEALED: "密閉系",
        }
        suffix = "・確認済" if verified else ""
        current_value = vent_labels.get(current_vent, str(current_vent)) + suffix
    else:
        vent_labels = {
            VentilationLevel.NONE: "No ventilation",
            VentilationLevel.BASIC: "Basic",
            VentilationLevel.INDUSTRIAL: "Industrial",
            VentilationLevel.LOCAL_EXTERNAL: "Local exhaust (ext)",
            VentilationLevel.LOCAL_ENCLOSED: "Local exhaust (enc)",
            VentilationLevel.SEALED: "Sealed",
        }
        suffix = " - verified" if verified else ""
        current_value = vent_labels.get(current_vent, str(current_vent)) + suffix

    return SensitivityBar(
        parameter_name="ventilation",
        parameter_label="Ventilation" if language == "en" else "換気",
        parameter_label_ja="換気",
        current_value=current_value,
        current_coefficient=current_coeff,
        contribution_percent=contribution,
        max_reduction_percent=improvement,
        best_coefficient=best_coeff,
        is_controllable=True,
    )


def _analyze_amount_sensitivity(
    assessment_input: AssessmentInput,
    current_exposure: float,
    effective_oel: float,
    language: str,
) -> SensitivityBar:
    """Analyze amount parameter sensitivity."""
    current_amount = assessment_input.amount_level

    # Amount factors
    amount_factors = {
        AmountLevel.LARGE: 1.0,
        AmountLevel.MEDIUM: 0.1,
        AmountLevel.SMALL: 0.01,
        AmountLevel.MINUTE: 0.001,
        AmountLevel.TRACE: 0.0001,
    }

    current_factor = amount_factors.get(current_amount, 1.0)
    best_factor = 0.0001  # TRACE

    # Calculate improvement potential
    if current_factor > best_factor:
        improvement = ((current_factor - best_factor) / current_factor) * 100
    else:
        improvement = 0.0

    # Contribution is based on how far from minimum
    if current_factor > best_factor:
        contribution = ((current_factor - best_factor) / current_factor) * 100 * 0.5
    else:
        contribution = 0.0

    if language == "ja":
        amount_labels = {
            AmountLevel.LARGE: "大量",
            AmountLevel.MEDIUM: "中量",
            AmountLevel.SMALL: "少量",
            AmountLevel.MINUTE: "微量",
            AmountLevel.TRACE: "極微量",
        }
    else:
        amount_labels = {
            AmountLevel.LARGE: "Large",
            AmountLevel.MEDIUM: "Medium",
            AmountLevel.SMALL: "Small",
            AmountLevel.MINUTE: "Minute",
            AmountLevel.TRACE: "Trace",
        }

    return SensitivityBar(
        parameter_name="amount",
        parameter_label="Amount" if language == "en" else "取り扱い量",
        parameter_label_ja="取り扱い量",
        current_value=amount_labels.get(current_amount, str(current_amount)),
        current_coefficient=current_factor,
        contribution_percent=contribution,
        max_reduction_percent=improvement,
        best_coefficient=best_factor,
        is_controllable=True,
    )


def _analyze_duration_sensitivity(
    assessment_input: AssessmentInput,
    current_exposure: float,
    effective_oel: float,
    language: str,
) -> SensitivityBar:
    """Analyze duration parameter sensitivity."""
    current_hours = assessment_input.working_hours_per_day
    current_coeff = current_hours / 8.0
    best_coeff = 1.0 / 8.0  # 1 hour

    improvement = (
        ((current_coeff - best_coeff) / current_coeff) * 100 if current_coeff > best_coeff else 0.0
    )
    contribution = improvement * 0.3  # Duration typically contributes less

    if language == "ja":
        current_value = f"{current_hours}時間/日"
    else:
        current_value = f"{current_hours}h/day"

    return SensitivityBar(
        parameter_name="duration",
        parameter_label="Duration" if language == "en" else "作業時間",
        parameter_label_ja="作業時間",
        current_value=current_value,
        current_coefficient=current_coeff,
        contribution_percent=contribution,
        max_reduction_percent=improvement,
        best_coefficient=best_coeff,
        is_controllable=True,
    )


def _analyze_spray_sensitivity(
    assessment_input: AssessmentInput,
    current_exposure: float,
    effective_oel: float,
    language: str,
) -> SensitivityBar:
    """Analyze spray operation sensitivity."""
    # Spray coefficient is 10x
    current_coeff = 10.0
    best_coeff = 1.0  # No spray

    improvement = 90.0  # 10x -> 1x is 90% reduction

    return SensitivityBar(
        parameter_name="spray",
        parameter_label="Spray Operation" if language == "en" else "スプレー作業",
        parameter_label_ja="スプレー作業",
        current_value="Yes (×10)" if language == "en" else "あり (×10)",
        current_coefficient=current_coeff,
        contribution_percent=50.0,  # Major contribution
        max_reduction_percent=improvement,
        best_coefficient=best_coeff,
        is_controllable=True,
    )


def _analyze_rpe_sensitivity(
    assessment_input: AssessmentInput,
    current_exposure: float,
    effective_oel: float,
    language: str,
) -> SensitivityBar:
    """Analyze RPE sensitivity (Report mode only)."""
    from ..models.assessment import RPEType, RPE_APF_VALUES

    current_rpe = assessment_input.rpe_type or RPEType.NONE
    current_apf = RPE_APF_VALUES.get(current_rpe, 1)
    current_coeff = 1.0 / current_apf

    # Best RPE
    best_apf = 1000  # APF 1000
    best_coeff = 1.0 / best_apf

    if current_apf < best_apf:
        improvement = ((current_coeff - best_coeff) / current_coeff) * 100
    else:
        improvement = 0.0

    # Contribution is low if already using good RPE
    contribution = improvement * 0.4

    if current_rpe == RPEType.NONE:
        current_value = "None" if language == "en" else "なし"
    else:
        current_value = f"APF {current_apf}"

    return SensitivityBar(
        parameter_name="rpe",
        parameter_label="Respirator" if language == "en" else "呼吸用保護具",
        parameter_label_ja="呼吸用保護具",
        current_value=current_value,
        current_coefficient=current_coeff,
        contribution_percent=contribution,
        max_reduction_percent=improvement,
        best_coefficient=best_coeff,
        is_controllable=True,
    )
