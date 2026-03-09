"""
Exposure concentration calculation.

Implements the CREATE-SIMPLE exposure estimation methodology.

References:
- CREATE-SIMPLE Design Document v3.1.1, Section 3
- VBA: modCalc.bas
"""

from typing import Optional, Tuple

from ..models.assessment import (
    AssessmentInput,
    PropertyType,
    VentilationLevel,
)
from ..models.explanation import CalculationStep, CalculationExplanation, FactorContribution
from ..references.catalog import REFERENCES
from .constants import (
    MIN_EXPOSURE_LIQUID,
    MIN_EXPOSURE_SOLID,
    EXPOSURE_BANDS_LIQUID,
    EXPOSURE_BANDS_SOLID,
    CONTENT_COEFFICIENTS,
    VENTILATION_COEFFICIENTS,
    SPRAY_COEFFICIENT,
    DURATION_COEFFICIENTS_WEEKLY,
    DURATION_COEFFICIENTS_MONTHLY,
    WORK_AREA_SIZE_COEFFICIENTS,
    EXPOSURE_VARIATION_COEFFICIENTS,
)
from .utils import round_down_significant


def get_exposure_band(
    property_type: str,
    volatility_or_dustiness: str,
    amount_level: str,
) -> float:
    """
    Get base exposure band from lookup table.

    Reference: CREATE-SIMPLE Design v3.1.1, Figure 10 (liquid), Figure 11 (solid)
    VBA: modCalc.bas lines 326-394

    Args:
        property_type: "liquid" or "solid"
        volatility_or_dustiness: Volatility level (liquid) or dustiness level (solid)
        amount_level: Amount level (large, medium, small, minute, trace)

    Returns:
        Base exposure band value (ppm for liquid, mg/m³ for solid)
    """
    key = (volatility_or_dustiness, amount_level)

    if property_type == "liquid":
        if key in EXPOSURE_BANDS_LIQUID:
            return EXPOSURE_BANDS_LIQUID[key]
        # Fallback for very_high volatility (same as high for most)
        if volatility_or_dustiness == "very_high":
            high_key = ("high", amount_level)
            if high_key in EXPOSURE_BANDS_LIQUID:
                return EXPOSURE_BANDS_LIQUID[high_key]
    else:  # solid
        if key in EXPOSURE_BANDS_SOLID:
            return EXPOSURE_BANDS_SOLID[key]

    raise ValueError(f"No exposure band found for {property_type}, {key}")


def apply_content_coefficient(content_percent: float) -> float:
    """
    Get content percentage coefficient.

    Reference: CREATE-SIMPLE Design v3.1.1, Figure 15
    VBA: modCalc.bas lines 399-408

    Based on ECETOC TRA / Raoult's law:
    - ≥25%: 1.0 (full volatility)
    - 5-25%: 0.6 (reduced vapor pressure)
    - 1-5%: 0.2 (significantly reduced)
    - <1%: 0.1 (minimal contribution)

    Args:
        content_percent: Content percentage (0-100)

    Returns:
        Content coefficient
    """
    for threshold, coefficient in CONTENT_COEFFICIENTS:
        if content_percent >= threshold:
            return coefficient
    return 0.1  # Default for very low content


def apply_ventilation_coefficient(
    ventilation: str,
    control_velocity_verified: bool = False,
    volatility_or_dustiness: Optional[str] = None,
) -> float:
    """
    Get ventilation coefficient.

    Reference: CREATE-SIMPLE Design v3.1.1, Figure 17
    VBA: modCalc.bas lines 410-425, 403-405

    For very low volatility (saturated vapor), ventilation coefficient > 1.0
    is capped at 1.0 since poor ventilation cannot increase exposure
    beyond saturation.

    Args:
        ventilation: Ventilation level
        control_velocity_verified: Whether control velocity is verified
        volatility_or_dustiness: Volatility level (for very_low handling)

    Returns:
        Ventilation coefficient
    """
    key = (ventilation, control_velocity_verified)
    if key in VENTILATION_COEFFICIENTS:
        coeff = VENTILATION_COEFFICIENTS[key]
    else:
        # Try without verification flag
        key_unverified = (ventilation, False)
        if key_unverified in VENTILATION_COEFFICIENTS:
            coeff = VENTILATION_COEFFICIENTS[key_unverified]
        else:
            raise ValueError(f"Unknown ventilation level: {ventilation}")

    # VBA: modCalc.bas lines 403-405
    # For very low volatility, cap coefficient at 1.0
    # (poor ventilation can't increase exposure beyond saturation)
    if volatility_or_dustiness == "very_low" and coeff > 1.0:
        coeff = 1.0

    return coeff


def calculate_time_coefficient(
    frequency_type: str,
    frequency_value: int,
    working_hours: float,
    has_short_term_effect: bool = False,
) -> float:
    """
    Calculate time coefficient per CREATE-SIMPLE methodology.

    VBA Reference: modCalc.bas lines 408-432

    Args:
        frequency_type: "weekly" or "monthly"
        frequency_value: days per week or days per month
        working_hours: hours worked per day
        has_short_term_effect: whether substance has short-term effect

    Returns:
        Time coefficient
    """
    if has_short_term_effect:
        return 1.0

    if frequency_type == "weekly":
        frequency = min(frequency_value, 7)  # Cap at 7 days
        weekly_hours = working_hours * frequency

        if weekly_hours > 40:
            return 10.0
        elif working_hours > 8 and frequency >= 3:
            return 10.0
        elif weekly_hours <= 4:
            return 0.1
        else:
            return 1.0

    else:  # monthly (less than weekly)
        frequency = min(frequency_value, 31)
        yearly_hours = working_hours * frequency * 12

        if yearly_hours > 192:
            return 1.0
        else:
            return 0.1


def apply_exposure_caps(
    exposure_8hr: float,
    exposure_stel: float,
) -> tuple[float, float]:
    """
    Apply maximum exposure caps.

    VBA Reference: modCalc.bas lines 474-480
    Maximum exposure: 5000 ppm or mg/m³

    Args:
        exposure_8hr: 8-hour TWA exposure
        exposure_stel: Short-term exposure

    Returns:
        Tuple of (capped_8hr, capped_stel)
    """
    MAX_EXPOSURE = 5000.0

    capped_8hr = min(exposure_8hr, MAX_EXPOSURE)
    capped_stel = min(exposure_stel, MAX_EXPOSURE)

    return capped_8hr, capped_stel


def apply_minimum_floor(exposure: float, property_type: str) -> float:
    """
    Apply minimum exposure floor.

    Reference: CREATE-SIMPLE Design v3.1.1, Section 3.3 footnote 11
    VBA: modCalc.bas lines 441-448

    CREATE-SIMPLE cannot estimate below these floors:
    - Liquid: 0.005 ppm
    - Solid: 0.001 mg/m³

    Args:
        exposure: Calculated exposure
        property_type: "liquid" or "solid"

    Returns:
        Exposure with floor applied
    """
    if property_type == "liquid":
        return max(exposure, MIN_EXPOSURE_LIQUID)
    else:
        return max(exposure, MIN_EXPOSURE_SOLID)


def apply_spray_coefficient(is_spray: bool) -> float:
    """
    Get spray operation coefficient.

    Reference: CREATE-SIMPLE Design v3.1.1, Section 3.3

    Args:
        is_spray: Whether spray operation

    Returns:
        Spray coefficient (10.0 for spray, 1.0 otherwise)
    """
    return SPRAY_COEFFICIENT if is_spray else 1.0


def apply_work_area_size_coefficient(
    work_area_size: Optional[str],
    property_type: str,
) -> float:
    """
    Get work area size coefficient.

    Reference: CREATE-SIMPLE Design v3.1.1, Section 3.4.6

    This coefficient only applies to liquids. For solids, work area size
    has less effect on particle dispersion.

    Args:
        work_area_size: Work area size ("small", "medium", "large") or None
        property_type: "liquid" or "solid"

    Returns:
        Work area size coefficient (only applies to liquids)
    """
    # Only apply to liquids
    if property_type != "liquid":
        return 1.0

    if work_area_size is None:
        return 1.0  # Default to medium

    return WORK_AREA_SIZE_COEFFICIENTS.get(work_area_size, 1.0)


def apply_duration_coefficient(
    working_hours: float,
    frequency_type: str,
    frequency_value: int,
) -> float:
    """
    Calculate duration/frequency coefficient.

    Reference: CREATE-SIMPLE Design v3.1.1, Figure 18, 19

    Args:
        working_hours: Hours worked per day
        frequency_type: "weekly" or "less_than_weekly"
        frequency_value: Days per week or days per month

    Returns:
        Duration coefficient
    """
    # Hours coefficient (based on 8-hour baseline)
    hours_coeff = working_hours / 8.0

    # Frequency coefficient
    if frequency_type == "weekly":
        freq_coeff = DURATION_COEFFICIENTS_WEEKLY.get(frequency_value, 1.0)
    else:  # less_than_weekly (monthly)
        freq_coeff = DURATION_COEFFICIENTS_MONTHLY.get(frequency_value, 0.1)

    return hours_coeff * freq_coeff


def apply_exposure_variation_coefficient(variation: str) -> float:
    """
    Get exposure variation coefficient.

    .. deprecated:: 2.0
        This function is deprecated. STEL calculation now uses
        ExposureVariation.get_stel_multiplier() per CREATE-SIMPLE v3.1 spec.
        STEL = 8-hour TWA × multiplier (4 for small variation, 6 for large).

    Args:
        variation: "constant", "intermittent", or "brief"

    Returns:
        Variation coefficient (legacy values, not used in current STEL calculation)
    """
    import warnings

    warnings.warn(
        "apply_exposure_variation_coefficient is deprecated. "
        "Use ExposureVariation.get_stel_multiplier() for STEL calculation.",
        DeprecationWarning,
        stacklevel=2,
    )
    from .constants import EXPOSURE_VARIATION_COEFFICIENTS

    return EXPOSURE_VARIATION_COEFFICIENTS.get(variation, 1.0)


def calculate_exposure(
    assessment_input: AssessmentInput,
    volatility_or_dustiness: str,
    content_percent: float = 100.0,
    verbose: bool = True,
    use_vba_stel_method: bool = True,
) -> Tuple[float, Optional[float], Optional[CalculationExplanation]]:
    """
    Calculate estimated exposure concentration.

    This is the main exposure calculation function that applies all
    coefficients in sequence.

    Reference: CREATE-SIMPLE Design v3.1.1, Section 3

    STEL Calculation Methods:
    - VBA Method (default): STEL = Base × Content × Spray × WorkArea × Vent × VariationCoeff × APF
    - v3.1 Spec: STEL = 8-hour TWA × multiplier (4 or 6)
      (The VBA method does NOT include time coefficient in STEL)

    Args:
        assessment_input: Assessment input parameters
        volatility_or_dustiness: Volatility (liquid) or dustiness (solid) level
        content_percent: Content percentage of the substance
        verbose: Whether to generate detailed explanation
        use_vba_stel_method: If True, use VBA's STEL calculation method
            (variation coefficient) instead of v3.1 spec (STEL multiplier)

    Returns:
        Tuple of (8hr_exposure, short_term_exposure, explanation)
    """
    property_type = (
        "liquid" if assessment_input.product_property == PropertyType.LIQUID else "solid"
    )
    amount_level = assessment_input.amount_level.value

    steps = []
    factors = []
    step_num = 1

    # Step 1: Get base exposure band
    base_band = get_exposure_band(property_type, volatility_or_dustiness, amount_level)
    unit = "ppm" if property_type == "liquid" else "mg/m³"

    if verbose:
        steps.append(
            CalculationStep(
                step_number=step_num,
                description="Get base exposure band",
                description_ja="基本暴露バンドを取得",
                formula=f"Lookup({volatility_or_dustiness}, {amount_level})",
                input_values={
                    "property_type": property_type,
                    "volatility_dustiness": volatility_or_dustiness,
                    "amount_level": amount_level,
                },
                output_value=base_band,
                output_unit=unit,
                explanation=f"Base exposure band from Figure {'10' if property_type == 'liquid' else '11'}",
                explanation_ja=f"図{'10' if property_type == 'liquid' else '11'}から基本暴露バンドを取得",
                reference=REFERENCES["create_simple_design_3_3_band"],
            )
        )
        step_num += 1

    current_exposure = base_band

    # Step 2: Apply content coefficient
    content_coeff = apply_content_coefficient(content_percent)
    after_content = current_exposure * content_coeff

    if verbose:
        steps.append(
            CalculationStep(
                step_number=step_num,
                description="Apply content percentage coefficient",
                description_ja="含有率係数を適用",
                formula=f"{current_exposure} × {content_coeff}",
                input_values={"content_percent": content_percent, "coefficient": content_coeff},
                output_value=after_content,
                output_unit=unit,
                explanation=_explain_content_coefficient(content_percent, content_coeff),
                explanation_ja=_explain_content_coefficient_ja(content_percent, content_coeff),
                reference=REFERENCES["create_simple_design_3_3_content"],
            )
        )
        factors.append(
            FactorContribution(
                factor_name="Content percentage",
                factor_name_ja="含有率",
                factor_value=f"{content_percent}%",
                coefficient=content_coeff,
                contribution_percent=0,  # Calculated later
                is_beneficial=content_coeff < 1.0,
                can_be_improved=False,
            )
        )
        step_num += 1

    current_exposure = after_content

    # Step 3: Apply spray coefficient
    spray_coeff = apply_spray_coefficient(assessment_input.is_spray_operation)
    after_spray = current_exposure * spray_coeff

    if verbose and spray_coeff != 1.0:
        steps.append(
            CalculationStep(
                step_number=step_num,
                description="Apply spray operation coefficient",
                description_ja="スプレー作業係数を適用",
                formula=f"{current_exposure:.4f} × {spray_coeff}",
                input_values={
                    "is_spray": assessment_input.is_spray_operation,
                    "coefficient": spray_coeff,
                },
                output_value=after_spray,
                output_unit=unit,
                explanation="Spray operations increase airborne concentration 10×",
                explanation_ja="スプレー作業により空気中濃度が10倍増加",
                reference=REFERENCES["create_simple_design_3_3_spray"],
            )
        )
        step_num += 1

    current_exposure = after_spray

    # Step 3b: Apply work area size coefficient (liquids only)
    work_area_coeff = apply_work_area_size_coefficient(
        assessment_input.work_area_size,
        property_type,
    )
    after_work_area = current_exposure * work_area_coeff

    if verbose and work_area_coeff != 1.0:
        steps.append(
            CalculationStep(
                step_number=step_num,
                description="Apply work area size coefficient",
                description_ja="作業場の広さ係数を適用",
                formula=f"{current_exposure:.4f} × {work_area_coeff}",
                input_values={
                    "work_area_size": assessment_input.work_area_size or "medium",
                    "coefficient": work_area_coeff,
                },
                output_value=after_work_area,
                output_unit=unit,
                explanation=_explain_work_area_coefficient(
                    assessment_input.work_area_size, work_area_coeff
                ),
                explanation_ja=_explain_work_area_coefficient_ja(
                    assessment_input.work_area_size, work_area_coeff
                ),
            )
        )
        factors.append(
            FactorContribution(
                factor_name="Work area size",
                factor_name_ja="作業場の広さ",
                factor_value=assessment_input.work_area_size or "medium",
                coefficient=work_area_coeff,
                contribution_percent=0,
                is_beneficial=work_area_coeff < 1.0,
                can_be_improved=work_area_coeff > 0.5,
            )
        )
        step_num += 1

    current_exposure = after_work_area

    # Step 4: Apply ventilation coefficient
    vent_coeff = apply_ventilation_coefficient(
        assessment_input.ventilation.value,
        assessment_input.control_velocity_verified,
    )
    after_vent = current_exposure * vent_coeff

    if verbose:
        steps.append(
            CalculationStep(
                step_number=step_num,
                description="Apply ventilation coefficient",
                description_ja="換気係数を適用",
                formula=f"{current_exposure:.4f} × {vent_coeff}",
                input_values={
                    "ventilation": assessment_input.ventilation.value,
                    "control_verified": assessment_input.control_velocity_verified,
                    "coefficient": vent_coeff,
                },
                output_value=after_vent,
                output_unit=unit,
                explanation=_explain_ventilation_coefficient(
                    assessment_input.ventilation.value,
                    assessment_input.control_velocity_verified,
                    vent_coeff,
                ),
                reference=REFERENCES["create_simple_design_3_3_vent"],
            )
        )
        factors.append(
            FactorContribution(
                factor_name="Ventilation",
                factor_name_ja="換気",
                factor_value=assessment_input.ventilation.value,
                coefficient=vent_coeff,
                contribution_percent=0,
                is_beneficial=vent_coeff < 1.0,
                can_be_improved=True,
                improvement_options=_get_ventilation_improvements(assessment_input.ventilation),
            )
        )
        step_num += 1

    current_exposure = after_vent

    # Step 5: Apply time coefficient (VBA threshold-based logic)
    # VBA Reference: modCalc.bas lines 408-432
    # Note: VBA uses threshold-based logic, NOT linear scaling
    time_coeff = calculate_time_coefficient(
        frequency_type=assessment_input.frequency_type,
        frequency_value=assessment_input.frequency_value,
        working_hours=assessment_input.working_hours_per_day,
        has_short_term_effect=False,  # TODO: Add to AssessmentInput if needed
    )
    after_time = current_exposure * time_coeff

    if verbose:
        # Explain the time coefficient logic
        weekly_hours = assessment_input.working_hours_per_day * min(assessment_input.frequency_value, 7)
        time_explanation = _explain_time_coefficient(
            assessment_input.frequency_type,
            assessment_input.frequency_value,
            assessment_input.working_hours_per_day,
            time_coeff,
        )
        steps.append(
            CalculationStep(
                step_number=step_num,
                description="Apply time coefficient",
                description_ja="時間係数を適用",
                formula=f"{current_exposure:.4f} × {time_coeff}",
                input_values={
                    "hours": assessment_input.working_hours_per_day,
                    "frequency_type": assessment_input.frequency_type,
                    "frequency_value": assessment_input.frequency_value,
                    "coefficient": time_coeff,
                },
                output_value=after_time,
                output_unit=unit,
                explanation=time_explanation,
                reference=REFERENCES["create_simple_design_3_3_duration"],
            )
        )
        step_num += 1

    current_exposure = after_time
    calculated_exposure = current_exposure

    # Step 6: Apply minimum floor (unless ignored)
    if assessment_input.ignore_minimum_floor:
        floor_applied_exposure = calculated_exposure
    else:
        floor_applied_exposure = apply_minimum_floor(calculated_exposure, property_type)

    if verbose and calculated_exposure < floor_applied_exposure:
        steps.append(
            CalculationStep(
                step_number=step_num,
                description="Apply minimum exposure floor",
                description_ja="最小暴露フロアを適用",
                formula=f"max({calculated_exposure:.6f}, {floor_applied_exposure})",
                input_values={"calculated": calculated_exposure, "floor": floor_applied_exposure},
                output_value=floor_applied_exposure,
                output_unit=unit,
                explanation=(
                    f"CREATE-SIMPLE cannot estimate below {floor_applied_exposure} {unit}. "
                    "This is a methodological limitation, not a physical limit. "
                    "For more precise estimates, actual measurements are needed."
                ),
                explanation_ja=(
                    f"CREATE-SIMPLEでは{floor_applied_exposure} {unit}未満の推定はできません。"
                    "これは手法上の限界であり、物理的な限界ではありません。"
                    "より正確な推定には実測が必要です。"
                ),
                reference=REFERENCES["create_simple_design_3_3_floor"],
            )
        )
        step_num += 1

    # Step 7: Apply maximum cap (VBA: modCalc.bas lines 474-476)
    final_exposure, _ = apply_exposure_caps(floor_applied_exposure, floor_applied_exposure)

    # Apply VBA-style significant digits rounding (VBA: modCalc.bas line 438)
    final_exposure = round_down_significant(final_exposure, 2)

    # Calculate STEL
    # Special case: very_low volatility AND no spray → STEL = 8-hour TWA
    spray_coeff = apply_spray_coefficient(assessment_input.is_spray_operation)
    if volatility_or_dustiness == "very_low" and spray_coeff == 1.0:
        stel_exposure = final_exposure
    elif use_vba_stel_method:
        # VBA Method (modCalc.bas line 456):
        # STEL = Base × Content × Spray × WorkArea × Vent × VariationCoeff × APF
        # NOTE: VBA does NOT include time coefficient in STEL calculation
        variation_coeff = EXPOSURE_VARIATION_COEFFICIENTS.get(
            assessment_input.exposure_variation.value, 1.0
        )
        stel_before_floor = (
            base_band
            * content_coeff
            * spray_coeff
            * work_area_coeff
            * vent_coeff
            * variation_coeff
        )
        stel_exposure = apply_minimum_floor(stel_before_floor, property_type)
        stel_exposure = round_down_significant(stel_exposure, 2)
    else:
        # v3.1 Spec Method (CREATE-SIMPLE Design v3.1, Figure 23):
        # STEL = 8-hour TWA × multiplier based on exposure variation (GSD)
        # - Small variation (GSD = 3.0): multiplier = 4
        # - Large variation (GSD = 6.0): multiplier = 6
        stel_multiplier = assessment_input.exposure_variation.get_stel_multiplier()
        stel_before_floor = final_exposure * stel_multiplier
        stel_exposure = apply_minimum_floor(stel_before_floor, property_type)
        stel_exposure = round_down_significant(stel_exposure, 2)

    # Apply maximum cap to STEL
    _, stel_exposure = apply_exposure_caps(final_exposure, stel_exposure)

    # Build explanation
    explanation = None
    if verbose:
        explanation = CalculationExplanation(
            steps=steps,
            factors=factors,
            summary=f"Estimated 8-hour TWA exposure: {final_exposure:.4f} {unit}",
            summary_ja=f"8時間TWA暴露推定値: {final_exposure:.4f} {unit}",
            main_formula="Exposure = Band × Content × Spray × WorkArea × Ventilation × TimeCoeff",
        )

    return final_exposure, stel_exposure, explanation


def _explain_time_coefficient(
    frequency_type: str,
    frequency_value: int,
    working_hours: float,
    time_coeff: float,
) -> str:
    """Generate explanation for time coefficient based on VBA threshold logic."""
    if frequency_type == "weekly":
        frequency = min(frequency_value, 7)
        weekly_hours = working_hours * frequency

        if time_coeff == 10.0:
            if weekly_hours > 40:
                return f"Weekly hours ({weekly_hours:.1f}h) > 40h → coefficient = 10 (increased exposure)"
            else:
                return f"Daily hours ({working_hours}h) > 8h AND ≥3 days/week → coefficient = 10"
        elif time_coeff == 0.1:
            return f"Weekly hours ({weekly_hours:.1f}h) ≤ 4h → coefficient = 0.1 (reduced exposure)"
        else:
            return f"Weekly hours ({weekly_hours:.1f}h) within normal range → coefficient = 1"
    else:  # monthly
        frequency = min(frequency_value, 31)
        yearly_hours = working_hours * frequency * 12

        if time_coeff == 1.0:
            return f"Yearly hours ({yearly_hours:.1f}h) > 192h → coefficient = 1"
        else:
            return f"Yearly hours ({yearly_hours:.1f}h) ≤ 192h → coefficient = 0.1 (reduced exposure)"


def _explain_content_coefficient(content: float, coeff: float) -> str:
    """Generate explanation for content coefficient."""
    if coeff == 1.0:
        return f"Content ≥25% ({content}%): Full volatility/dustiness assumed"
    elif coeff == 0.6:
        return f"Content 5-25% ({content}%): Reduced vapor pressure per Raoult's law"
    elif coeff == 0.2:
        return f"Content 1-5% ({content}%): Significantly reduced emission"
    else:
        return f"Content <1% ({content}%): Minimal contribution to exposure"


def _explain_content_coefficient_ja(content: float, coeff: float) -> str:
    """Generate Japanese explanation for content coefficient."""
    if coeff == 1.0:
        return f"含有率≥25% ({content}%): 完全な揮発性/飛散性を仮定"
    elif coeff == 0.6:
        return f"含有率5-25% ({content}%): ラウールの法則により蒸気圧低下"
    elif coeff == 0.2:
        return f"含有率1-5% ({content}%): 放出量が大幅に減少"
    else:
        return f"含有率<1% ({content}%): 暴露への寄与は最小限"


def _explain_ventilation_coefficient(
    ventilation: str,
    verified: bool,
    coeff: float,
) -> str:
    """Generate explanation for ventilation coefficient."""
    vent_names = {
        "none": "No ventilation",
        "basic": "Basic/general ventilation",
        "industrial": "Industrial ventilation",
        "local_ext": "Local exhaust (external)",
        "local_enc": "Local exhaust (enclosed)",
        "sealed": "Sealed/enclosed system",
    }
    name = vent_names.get(ventilation, ventilation)
    verified_text = " with verified control velocity" if verified else ""
    reduction = (1 - coeff) * 100
    return f"{name}{verified_text}: {reduction:.0f}% reduction in exposure"


def _get_ventilation_improvements(current: VentilationLevel) -> list[str]:
    """Get possible ventilation improvements from current level."""
    improvements = {
        VentilationLevel.NONE: [
            "Add basic ventilation",
            "Install local exhaust ventilation",
        ],
        VentilationLevel.BASIC: [
            "Upgrade to industrial ventilation",
            "Install local exhaust ventilation",
        ],
        VentilationLevel.INDUSTRIAL: [
            "Install local exhaust (external type)",
            "Install local exhaust (enclosed type)",
        ],
        VentilationLevel.LOCAL_EXTERNAL: [
            "Verify control velocity",
            "Upgrade to enclosed local exhaust",
        ],
        VentilationLevel.LOCAL_ENCLOSED: [
            "Verify control velocity",
            "Consider sealed system",
        ],
        VentilationLevel.SEALED: [],
    }
    return improvements.get(current, [])


def _explain_work_area_coefficient(work_area_size: Optional[str], coeff: float) -> str:
    """Generate explanation for work area size coefficient."""
    names = {
        "small": "Small/confined work area",
        "medium": "Standard work area",
        "large": "Large/open work area",
    }
    name = names.get(work_area_size or "medium", "Standard work area")
    if coeff > 1.0:
        change = (coeff - 1) * 100
        return f"{name}: {change:.0f}% increase due to confined space"
    elif coeff < 1.0:
        reduction = (1 - coeff) * 100
        return f"{name}: {reduction:.0f}% reduction due to air dilution"
    else:
        return f"{name}: baseline exposure"


def _explain_work_area_coefficient_ja(work_area_size: Optional[str], coeff: float) -> str:
    """Generate Japanese explanation for work area size coefficient."""
    names = {
        "small": "狭い作業場",
        "medium": "標準的な作業場",
        "large": "広い作業場",
    }
    name = names.get(work_area_size or "medium", "標準的な作業場")
    if coeff > 1.0:
        change = (coeff - 1) * 100
        return f"{name}: 狭い空間により{change:.0f}%増加"
    elif coeff < 1.0:
        reduction = (1 - coeff) * 100
        return f"{name}: 空気希釈により{reduction:.0f}%低減"
    else:
        return f"{name}: 基準暴露"
