"""
Risk curve data providers.

Generates data for charts showing how risk level changes
as individual parameters vary across their full range.

Reference: CREATE-SIMPLE Design v3.1.1
"""

from typing import Optional
from pydantic import BaseModel, Field

from ..models.assessment import (
    AssessmentInput,
    AssessmentMode,
    VentilationLevel,
    AmountLevel,
    RPEType,
    RPE_APF_VALUES,
)
from ..models.substance import Substance
from ..models.risk import RiskLevel
from ..calculators.constants import VENTILATION_COEFFICIENTS


class RiskCurvePoint(BaseModel):
    """A single point on a risk curve."""

    parameter_value: float  # X-axis: coefficient value
    parameter_label: str  # Human-readable label
    parameter_label_ja: str = ""  # Japanese label
    exposure: float  # Calculated exposure
    rcr: float  # Risk Characterization Ratio
    risk_level: int  # 1-4
    is_current: bool = False  # Is this the current state?
    is_achievable: bool = True  # Can this be achieved?


class RiskCurve(BaseModel):
    """
    Risk curve data for a single parameter.

    Use this to render a chart showing how risk changes
    as one parameter varies across its full range.
    """

    parameter_name: str  # "ventilation", "amount", "rpe", etc.
    parameter_label: str  # "Ventilation"
    parameter_label_ja: str = ""  # "換気"
    points: list[RiskCurvePoint] = Field(default_factory=list)
    current_value_index: int = 0  # Index of current state in points
    min_achievable_rcr: float = 0  # Best possible with this parameter
    best_risk_level: int = 1  # Best achievable level
    level_boundaries: dict[int, float] = Field(default_factory=lambda: {1: 0.1, 2: 1.0, 3: 10.0})


class RiskCurvesData(BaseModel):
    """Complete risk curves data for all parameters."""

    current_rcr: float
    current_risk_level: int
    min_achievable_rcr: float
    min_achievable_risk_level: int

    ventilation_curve: RiskCurve
    amount_curve: Optional[RiskCurve] = None
    duration_curve: Optional[RiskCurve] = None
    rpe_curve: Optional[RiskCurve] = None  # Only in Report mode


def generate_risk_curves(
    assessment_input: AssessmentInput,
    substance: Substance,
    current_exposure: float,
    effective_oel: float,
    language: str = "en",
) -> RiskCurvesData:
    """
    Generate all risk curve data for an assessment.

    Args:
        assessment_input: Current assessment input
        substance: Substance being assessed
        current_exposure: Current calculated exposure
        effective_oel: Effective OEL (or ACRmax)
        language: "en" or "ja"

    Returns:
        RiskCurvesData with all chart data
    """
    current_rcr = current_exposure / effective_oel
    current_level = RiskLevel.from_rcr(current_rcr).value

    # Generate ventilation curve
    vent_curve = generate_ventilation_curve(
        assessment_input, current_exposure, effective_oel, language
    )

    # Generate amount curve
    amount_curve = generate_amount_curve(
        assessment_input, current_exposure, effective_oel, language
    )

    # Generate RPE curve (Report mode only)
    rpe_curve = None
    if assessment_input.mode == AssessmentMode.REPORT:
        rpe_curve = generate_rpe_curve(assessment_input, current_exposure, effective_oel, language)

    # Find minimum achievable
    min_rcr = min(vent_curve.min_achievable_rcr, amount_curve.min_achievable_rcr)
    if rpe_curve:
        min_rcr = min(min_rcr, rpe_curve.min_achievable_rcr)

    return RiskCurvesData(
        current_rcr=current_rcr,
        current_risk_level=current_level,
        min_achievable_rcr=min_rcr,
        min_achievable_risk_level=RiskLevel.from_rcr(min_rcr).value,
        ventilation_curve=vent_curve,
        amount_curve=amount_curve,
        rpe_curve=rpe_curve,
    )


def generate_ventilation_curve(
    assessment_input: AssessmentInput,
    current_exposure: float,
    effective_oel: float,
    language: str = "en",
) -> RiskCurve:
    """
    Generate risk curve for ventilation parameter.

    Sweeps through all ventilation levels and calculates
    RCR at each level.
    """
    current_vent = assessment_input.ventilation
    current_verified = assessment_input.control_velocity_verified
    current_coeff = VENTILATION_COEFFICIENTS.get((current_vent.value, current_verified), 1.0)

    # Define all ventilation options
    if language == "ja":
        vent_options = [
            (VentilationLevel.NONE, False, 4.0, "換気なし"),
            (VentilationLevel.BASIC, False, 3.0, "一般換気"),
            (VentilationLevel.INDUSTRIAL, False, 1.0, "工業的換気"),
            (VentilationLevel.LOCAL_EXTERNAL, False, 0.7, "局所排気(外付け)"),
            (VentilationLevel.LOCAL_EXTERNAL, True, 0.1, "局所排気(外付け・確認済)"),
            (VentilationLevel.LOCAL_ENCLOSED, False, 0.3, "局所排気(囲い式)"),
            (VentilationLevel.LOCAL_ENCLOSED, True, 0.01, "局所排気(囲い式・確認済)"),
            (VentilationLevel.SEALED, False, 0.001, "密閉系"),
        ]
    else:
        vent_options = [
            (VentilationLevel.NONE, False, 4.0, "No ventilation"),
            (VentilationLevel.BASIC, False, 3.0, "Basic ventilation"),
            (VentilationLevel.INDUSTRIAL, False, 1.0, "Industrial ventilation"),
            (VentilationLevel.LOCAL_EXTERNAL, False, 0.7, "Local exhaust (external)"),
            (VentilationLevel.LOCAL_EXTERNAL, True, 0.1, "Local exhaust (verified)"),
            (VentilationLevel.LOCAL_ENCLOSED, False, 0.3, "Local exhaust (enclosed)"),
            (VentilationLevel.LOCAL_ENCLOSED, True, 0.01, "Enclosed (verified)"),
            (VentilationLevel.SEALED, False, 0.001, "Sealed system"),
        ]

    points = []
    current_index = 0
    min_rcr = float("inf")

    for i, (vent, verified, coeff, label) in enumerate(vent_options):
        # Calculate exposure at this ventilation level
        ratio = coeff / current_coeff
        exposure = current_exposure * ratio
        rcr = exposure / effective_oel
        level = RiskLevel.from_rcr(rcr).value

        # Check if current
        is_current = vent == current_vent and verified == current_verified
        if is_current:
            current_index = i

        min_rcr = min(min_rcr, rcr)

        points.append(
            RiskCurvePoint(
                parameter_value=coeff,
                parameter_label=label,
                exposure=exposure,
                rcr=rcr,
                risk_level=level,
                is_current=is_current,
            )
        )

    return RiskCurve(
        parameter_name="ventilation",
        parameter_label="Ventilation" if language == "en" else "換気",
        parameter_label_ja="換気",
        points=points,
        current_value_index=current_index,
        min_achievable_rcr=min_rcr,
        best_risk_level=RiskLevel.from_rcr(min_rcr).value,
    )


def generate_amount_curve(
    assessment_input: AssessmentInput,
    current_exposure: float,
    effective_oel: float,
    language: str = "en",
) -> RiskCurve:
    """Generate risk curve for amount parameter."""
    current_amount = assessment_input.amount_level

    # Amount factors (relative to LARGE)
    if language == "ja":
        amount_options = [
            (AmountLevel.LARGE, 1.0, "大量"),
            (AmountLevel.MEDIUM, 0.1, "中量"),
            (AmountLevel.SMALL, 0.01, "少量"),
            (AmountLevel.MINUTE, 0.001, "微量"),
            (AmountLevel.TRACE, 0.0001, "極微量"),
        ]
    else:
        amount_options = [
            (AmountLevel.LARGE, 1.0, "Large"),
            (AmountLevel.MEDIUM, 0.1, "Medium"),
            (AmountLevel.SMALL, 0.01, "Small"),
            (AmountLevel.MINUTE, 0.01, "Minute"),
            (AmountLevel.TRACE, 0.001, "Trace"),
        ]

    # Get current factor
    current_factors = {a: f for a, f, _ in amount_options}
    current_factor = current_factors.get(current_amount, 1.0)

    points = []
    current_index = 0
    min_rcr = float("inf")

    for i, (amount, factor, label) in enumerate(amount_options):
        ratio = factor / current_factor
        exposure = current_exposure * ratio
        rcr = exposure / effective_oel
        level = RiskLevel.from_rcr(rcr).value

        is_current = amount == current_amount
        if is_current:
            current_index = i

        min_rcr = min(min_rcr, rcr)

        points.append(
            RiskCurvePoint(
                parameter_value=factor,
                parameter_label=label,
                exposure=exposure,
                rcr=rcr,
                risk_level=level,
                is_current=is_current,
            )
        )

    return RiskCurve(
        parameter_name="amount",
        parameter_label="Amount" if language == "en" else "取り扱い量",
        parameter_label_ja="取り扱い量",
        points=points,
        current_value_index=current_index,
        min_achievable_rcr=min_rcr,
        best_risk_level=RiskLevel.from_rcr(min_rcr).value,
    )


def generate_rpe_curve(
    assessment_input: AssessmentInput,
    current_exposure: float,
    effective_oel: float,
    language: str = "en",
) -> RiskCurve:
    """Generate risk curve for RPE parameter (Report mode only)."""
    current_rpe = assessment_input.rpe_type or RPEType.NONE
    current_apf = RPE_APF_VALUES.get(current_rpe, 1)

    if language == "ja":
        rpe_options = [
            (RPEType.NONE, 1, "なし"),
            (RPEType.TIGHT_FIT_10, 10, "タイトフィット APF 10"),
            (RPEType.LOOSE_FIT_11, 11, "ルーズフィット APF 11"),
            (RPEType.LOOSE_FIT_20, 20, "ルーズフィット APF 20"),
            (RPEType.LOOSE_FIT_25, 25, "ルーズフィット APF 25"),
            (RPEType.TIGHT_FIT_50, 50, "タイトフィット APF 50"),
            (RPEType.TIGHT_FIT_100, 100, "タイトフィット APF 100"),
            (RPEType.TIGHT_FIT_1000, 1000, "タイトフィット APF 1000"),
        ]
    else:
        rpe_options = [
            (RPEType.NONE, 1, "None"),
            (RPEType.TIGHT_FIT_10, 10, "Tight-fit APF 10"),
            (RPEType.LOOSE_FIT_11, 11, "Loose-fit APF 11"),
            (RPEType.LOOSE_FIT_20, 20, "Loose-fit APF 20"),
            (RPEType.LOOSE_FIT_25, 25, "Loose-fit APF 25"),
            (RPEType.TIGHT_FIT_50, 50, "Tight-fit APF 50"),
            (RPEType.TIGHT_FIT_100, 100, "Tight-fit APF 100"),
            (RPEType.TIGHT_FIT_1000, 1000, "Tight-fit APF 1000"),
        ]

    points = []
    current_index = 0
    min_rcr = float("inf")

    for i, (rpe, apf, label) in enumerate(rpe_options):
        # RPE reduces exposure by 1/APF
        ratio = current_apf / apf
        exposure = current_exposure * ratio
        rcr = exposure / effective_oel
        level = RiskLevel.from_rcr(rcr).value

        is_current = rpe == current_rpe
        if is_current:
            current_index = i

        min_rcr = min(min_rcr, rcr)

        points.append(
            RiskCurvePoint(
                parameter_value=1.0 / apf,  # Coefficient
                parameter_label=label,
                exposure=exposure,
                rcr=rcr,
                risk_level=level,
                is_current=is_current,
            )
        )

    return RiskCurve(
        parameter_name="rpe",
        parameter_label="Respirator" if language == "en" else "呼吸用保護具",
        parameter_label_ja="呼吸用保護具",
        points=points,
        current_value_index=current_index,
        min_achievable_rcr=min_rcr,
        best_risk_level=RiskLevel.from_rcr(min_rcr).value,
    )
