"""
Inhalation risk assessment calculation.

Reference: CREATE-SIMPLE Design v3.1.1, Sections 3 and 5
"""

from typing import Optional

from ..models.substance import Substance, PropertyType, OccupationalExposureLimits
from ..models.assessment import AssessmentInput
from ..models.risk import RiskLevel, InhalationRisk
from ..models.explanation import CalculationStep, Limitation
from ..references.catalog import REFERENCES
from .exposure import calculate_exposure
from .oel import select_oel
from .acr import get_acrmax, calculate_rcr, calculate_engineering_limit
from .rpe import calculate_apf_coefficient_for_mode


def select_stel_oel(oel: OccupationalExposureLimits) -> tuple[Optional[float], Optional[str], Optional[str]]:
    """
    Select the appropriate STEL OEL value following priority order.

    Priority order:
    1. 濃度基準値 STEL (Concentration Standard - Japan)
    2. TLV-STEL (ACGIH)
    3. Other STEL

    Returns:
        Tuple of (value, unit, source) or (None, None, None) if no STEL available
    """
    # Priority 1: Concentration Standard STEL
    if oel.concentration_standard_stel is not None:
        return (
            oel.concentration_standard_stel,
            oel.concentration_standard_stel_unit or "ppm",
            "濃度基準値 短時間",
        )

    # Priority 2: ACGIH TLV-STEL
    if oel.acgih_tlv_stel is not None:
        return (
            oel.acgih_tlv_stel,
            oel.acgih_tlv_stel_unit or "ppm",
            "TLV-STEL (ACGIH)",
        )

    # Priority 3: Other STEL
    if oel.other_stel is not None:
        return (
            oel.other_stel,
            oel.other_stel_unit or "ppm",
            "Other STEL",
        )

    return (None, None, None)


def calculate_inhalation_risk(
    assessment_input: AssessmentInput,
    substance: Substance,
    content_percent: float = 100.0,
    verbose: bool = True,
) -> InhalationRisk:
    """
    Calculate inhalation risk for a substance.

    This function:
    1. Calculates exposure concentration
    2. Selects appropriate OEL
    3. Applies ACRmax if applicable (carcinogens)
    4. Applies RPE coefficient (Report mode only)
    5. Calculates RCR and determines risk level
    6. Identifies limitations (why Level I may not be achievable)

    Reference: CREATE-SIMPLE Design v3.1.1, Sections 3 and 5

    Args:
        assessment_input: Assessment input parameters
        substance: Substance data
        content_percent: Content percentage of the substance
        verbose: Whether to generate detailed explanation

    Returns:
        InhalationRisk result with all calculations and explanations
    """
    # Determine volatility or dustiness
    if substance.property_type == PropertyType.LIQUID:
        volatility = substance.properties.get_volatility_level().value
        property_type = "liquid"
        unit = "ppm"
    else:
        volatility = "medium"  # Default dustiness if not specified
        property_type = "solid"
        unit = "mg/m³"

    # Step 1: Calculate base exposure
    exposure_8hr, exposure_stel, exposure_explanation = calculate_exposure(
        assessment_input=assessment_input,
        volatility_or_dustiness=volatility,
        content_percent=content_percent,
        verbose=verbose,
    )

    # Step 2: Select OEL
    oel_value, oel_unit, oel_source = select_oel(substance.oel)

    if oel_value is None:
        raise ValueError(f"No OEL available for substance {substance.cas_number}")

    # Step 3: Get ACRmax if applicable (carcinogens/mutagens ONLY, not reproductive toxicity)
    # Note: hazard_level is used for display/reporting, but ACRmax uses a separate check
    hazard_level = substance.get_hazard_level()
    acrmax_hazard_level = substance.ghs.get_acrmax_hazard_level()
    acrmax = get_acrmax(acrmax_hazard_level, property_type)

    # Step 4: Apply RPE coefficient (Report mode only)
    rpe_coeff = calculate_apf_coefficient_for_mode(
        mode=assessment_input.mode.value,
        rpe_type=assessment_input.rpe_type,
        fit_tested=assessment_input.rpe_fit_tested,
        fit_test_multiplier=assessment_input.rpe_fit_test_multiplier,
    )
    exposure_after_rpe = exposure_8hr * rpe_coeff

    # Step 5: Calculate RCR
    rcr = calculate_rcr(exposure_after_rpe, oel_value, acrmax)
    risk_level = RiskLevel.from_rcr(rcr)

    # Step 6: Calculate engineering control limit (minimum achievable RCR without RPE)
    min_rcr, min_level, min_reason, min_explanation, min_reason_ja = calculate_engineering_limit(
        property_type=property_type,
        oel=oel_value,
        acrmax=acrmax,
        # Note: constraints are applied at the display level, not here
        # This gives the theoretical minimum; practical minimum is calculated in paths.py
    )

    # Build limitations list
    limitations = []

    # Check if minimum floor limits Level I
    if min_level > RiskLevel.I:
        from .constants import MIN_EXPOSURE_LIQUID, MIN_EXPOSURE_SOLID

        min_floor = MIN_EXPOSURE_LIQUID if property_type == "liquid" else MIN_EXPOSURE_SOLID

        limitations.append(
            Limitation(
                factor_name="Minimum exposure floor",
                factor_name_ja="最小暴露推定値",
                description=(
                    f"CREATE-SIMPLE cannot estimate exposure below {min_floor} {unit}. "
                    "This is a methodological limitation."
                ),
                description_ja=(
                    f"CREATE-SIMPLEでは{min_floor} {unit}未満の暴露推定はできません。"
                    "これは手法上の限界です。"
                ),
                current_value=exposure_after_rpe,
                limiting_value=min_floor,
                impact=f"Minimum RCR = {min_rcr:.4f}, Level {min_level.name} is best achievable",
                impact_ja=f"最小RCR = {min_rcr:.4f}、到達可能な最良レベルは{min_level.name}",
                reference=REFERENCES["create_simple_design_3_3_floor"],
                alternatives=[
                    "Use actual exposure measurements",
                    "Consider substance substitution",
                ],
            )
        )

    if acrmax is not None:
        limitations.append(
            Limitation(
                factor_name="ACRmax (Management target)",
                factor_name_ja="ACRmax（管理目標濃度）",
                description=(
                    f"This substance has hazard level {hazard_level}. "
                    f"ACRmax = {acrmax} {unit} is used instead of OEL."
                ),
                description_ja=(
                    f"この物質はハザードレベル{hazard_level}です。"
                    f"OELの代わりにACRmax = {acrmax} {unit}が使用されます。"
                ),
                current_value=acrmax,
                limiting_value=acrmax,
                impact="More stringent target for carcinogens/mutagens",
                impact_ja="発がん性・変異原性物質に対するより厳しい目標",
                reference=REFERENCES["create_simple_design_5_3_acrmax"],
            )
        )

    # Add RPE explanation if used
    if verbose and rpe_coeff < 1.0:
        exposure_explanation.steps.append(
            CalculationStep(
                step_number=len(exposure_explanation.steps) + 1,
                description="Apply RPE protection factor",
                description_ja="呼吸用保護具の防護係数を適用",
                formula=f"{exposure_8hr:.6f} × {rpe_coeff:.6f}",
                input_values={
                    "rpe_type": assessment_input.rpe_type.value
                    if assessment_input.rpe_type
                    else "none",
                    "coefficient": rpe_coeff,
                },
                output_value=exposure_after_rpe,
                output_unit=unit,
                explanation=f"RPE reduces exposure by {(1 - rpe_coeff) * 100:.1f}%",
                explanation_ja=f"呼吸用保護具により暴露が{(1 - rpe_coeff) * 100:.1f}%低減",
            )
        )

    # Calculate min exposure (10% of max per CREATE-SIMPLE methodology)
    exposure_8hr_min = exposure_after_rpe * 0.1
    exposure_stel_after_rpe = exposure_stel * rpe_coeff if exposure_stel else None
    exposure_stel_min = (exposure_stel_after_rpe * 0.1) if exposure_stel_after_rpe else None

    # Calculate exposure without floor for tracking "would achieve target without floor"
    exposure_without_floor = None
    rcr_without_floor = None
    would_achieve_target_without_floor = False

    if not assessment_input.ignore_minimum_floor:
        # Calculate what exposure/RCR would be without the floor
        input_without_floor = assessment_input.model_copy(update={"ignore_minimum_floor": True})
        exp_no_floor, _, _ = calculate_exposure(
            assessment_input=input_without_floor,
            volatility_or_dustiness=volatility,
            content_percent=content_percent,
            verbose=False,
        )
        exposure_without_floor = exp_no_floor * rpe_coeff
        rcr_without_floor = calculate_rcr(exposure_without_floor, oel_value, acrmax)

        # Check if target would be achieved without floor (target is Level I by default)
        from ..models.risk import DetailedRiskLevel
        level_without_floor = DetailedRiskLevel.from_rcr(rcr_without_floor)
        current_level = DetailedRiskLevel.from_rcr(rcr)
        # Would achieve target if floor-less level is better than current level
        would_achieve_target_without_floor = level_without_floor < current_level

    # Step 7: Calculate STEL RCR if both STEL exposure and STEL OEL are available
    stel_oel_value, stel_oel_unit, stel_oel_source = select_stel_oel(substance.oel)

    # Fallback: If no specific STEL OEL, use 8-hour OEL × 3
    # Reference: VBA modCalc.bas lines 193-194, 218-221
    if stel_oel_value is None:
        if oel_value and oel_value > 0:
            stel_oel_value = oel_value * 3.0
            stel_oel_unit = oel_unit
            stel_oel_source = f"{oel_source} ×3"
        elif acrmax and acrmax > 0:
            stel_oel_value = acrmax * 3.0
            stel_oel_unit = unit
            stel_oel_source = "ACRmax ×3"

    stel_rcr = None
    stel_risk_level = None

    if exposure_stel_after_rpe and stel_oel_value:
        # STEL uses STEL OEL directly, without ACRmax adjustment
        # ACRmax is for chronic (8-hour TWA) risk management, not acute (STEL) risk
        # Reference: CREATE-SIMPLE separates acute vs chronic risk assessment
        stel_rcr = calculate_rcr(exposure_stel_after_rpe, stel_oel_value, None)
        stel_risk_level = RiskLevel.from_rcr(stel_rcr)

    return InhalationRisk(
        exposure_8hr=exposure_after_rpe,
        exposure_8hr_min=exposure_8hr_min,
        exposure_8hr_unit=unit,
        exposure_stel=exposure_stel_after_rpe,
        exposure_stel_min=exposure_stel_min,
        exposure_stel_unit=unit,
        oel=oel_value,
        oel_unit=oel_unit,
        oel_source=oel_source,
        acrmax=acrmax,
        acrmax_unit=unit if acrmax else None,
        rcr=rcr,
        risk_level=risk_level,
        stel_oel=stel_oel_value,
        stel_oel_unit=stel_oel_unit,
        stel_oel_source=stel_oel_source,
        stel_rcr=stel_rcr,
        stel_risk_level=stel_risk_level,
        explanation=exposure_explanation,
        min_achievable_rcr=min_rcr,
        min_achievable_level=min_level,
        min_achievable_reason=min_reason,
        min_achievable_reason_ja=min_reason_ja,
        limitations=limitations,
        exposure_without_floor=exposure_without_floor,
        rcr_without_floor=rcr_without_floor,
        would_achieve_target_without_floor=would_achieve_target_without_floor,
    )
