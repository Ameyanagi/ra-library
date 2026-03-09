"""
Factor contribution analysis.

Explains how each controllable factor contributes to the overall risk
and which factors have the most impact.

Reference: CREATE-SIMPLE Design v3.1.1, Section 3.3
"""

from ..models.assessment import AssessmentInput, VentilationLevel, AmountLevel
from ..models.substance import Substance, PropertyType
from ..models.explanation import FactorContribution
from ..calculators.constants import (
    CONTENT_COEFFICIENTS,
    VENTILATION_COEFFICIENTS,
)


def explain_factors(
    assessment_input: AssessmentInput,
    substance: Substance,
    language: str = "en",
) -> list[FactorContribution]:
    """
    Analyze and explain how each factor contributes to the risk.

    Args:
        assessment_input: The assessment input parameters
        substance: The substance being assessed
        language: "en" or "ja"

    Returns:
        List of FactorContribution objects for each factor
    """
    factors = []

    # Volatility/Dustiness factor
    factors.append(_analyze_volatility_factor(assessment_input, substance, language))

    # Amount factor
    factors.append(_analyze_amount_factor(assessment_input, language))

    # Content factor
    factors.append(_analyze_content_factor(assessment_input, language))

    # Ventilation factor
    factors.append(_analyze_ventilation_factor(assessment_input, language))

    # Spray operation factor
    if assessment_input.is_spray_operation:
        factors.append(_analyze_spray_factor(assessment_input, language))

    # Duration factor
    factors.append(_analyze_duration_factor(assessment_input, language))

    # Sort by contribution (highest first)
    factors.sort(key=lambda f: f.contribution_percent, reverse=True)

    return factors


def get_factor_contributions(
    assessment_input: AssessmentInput,
    substance: Substance,
    base_exposure: float,
    final_exposure: float,
) -> dict[str, float]:
    """
    Calculate the contribution percentage of each factor.

    This shows how much each factor affects the final exposure
    relative to the base exposure.

    Args:
        assessment_input: The assessment input parameters
        substance: The substance being assessed
        base_exposure: Initial exposure band value
        final_exposure: Final calculated exposure

    Returns:
        Dictionary mapping factor names to contribution percentages
    """
    contributions = {}

    # Calculate log ratios for each factor
    total_log_reduction = _safe_log_ratio(base_exposure, final_exposure)

    if total_log_reduction == 0:
        return {"none": 100.0}

    # Content contribution
    content_coeff = _get_content_coefficient(assessment_input)
    content_contribution = _safe_log_ratio(1.0, content_coeff) / total_log_reduction * 100
    contributions["content"] = content_contribution

    # Ventilation contribution
    vent_coeff = _get_ventilation_coefficient(assessment_input)
    vent_contribution = _safe_log_ratio(1.0, vent_coeff) / total_log_reduction * 100
    contributions["ventilation"] = vent_contribution

    # Spray contribution
    spray_coeff = 10.0 if assessment_input.is_spray_operation else 1.0
    if spray_coeff != 1.0:
        spray_contribution = _safe_log_ratio(spray_coeff, 1.0) / total_log_reduction * 100
        contributions["spray"] = spray_contribution

    # Duration contribution
    duration_coeff = _get_duration_coefficient(assessment_input)
    duration_contribution = _safe_log_ratio(1.0, duration_coeff) / total_log_reduction * 100
    contributions["duration"] = duration_contribution

    return contributions


def _analyze_volatility_factor(
    assessment_input: AssessmentInput,
    substance: Substance,
    language: str,
) -> FactorContribution:
    """Analyze volatility/dustiness factor."""
    is_liquid = substance.property_type == PropertyType.LIQUID

    # Get volatility level
    volatility = _get_volatility_level(substance)

    if language == "ja":
        if is_liquid:
            factor_name = "揮発性"
            volatility_names = {
                "high": "高揮発性 (BP < 50°C)",
                "medium": "中揮発性 (50°C ≤ BP < 150°C)",
                "low": "低揮発性 (BP ≥ 150°C)",
                "very_low": "極低揮発性 (VP < 0.5 Pa)",
            }
            improvement_options = [
                "より揮発性の低い代替物質への変更",
                "プロセス温度の低下",
            ]
        else:
            factor_name = "飛散性"
            volatility_names = {
                "high": "高飛散性 (微粉末)",
                "medium": "中飛散性 (結晶・粒状)",
                "low": "低飛散性 (ペレット・ワックス状)",
            }
            improvement_options = [
                "より飛散性の低い形態への変更",
                "湿式作業への変更",
            ]
    else:
        if is_liquid:
            factor_name = "Volatility"
            volatility_names = {
                "high": "High volatility (BP < 50°C)",
                "medium": "Medium volatility (50°C ≤ BP < 150°C)",
                "low": "Low volatility (BP ≥ 150°C)",
                "very_low": "Very low volatility (VP < 0.5 Pa)",
            }
            improvement_options = [
                "Switch to less volatile substitute",
                "Reduce process temperature",
            ]
        else:
            factor_name = "Dustiness"
            volatility_names = {
                "high": "High dustiness (fine powders)",
                "medium": "Medium dustiness (crystalline/granular)",
                "low": "Low dustiness (pellets/waxy)",
            }
            improvement_options = [
                "Switch to less dusty form",
                "Use wet processing methods",
            ]

    return FactorContribution(
        factor_name=factor_name,
        factor_name_ja="揮発性" if is_liquid else "飛散性",
        factor_value=volatility_names.get(volatility, volatility),
        coefficient=1.0,  # Base factor, not a coefficient
        contribution_percent=30.0,  # Estimated contribution
        is_beneficial=volatility in ["low", "very_low"],
        can_be_improved=True,
        improvement_options=improvement_options,
    )


def _analyze_amount_factor(
    assessment_input: AssessmentInput,
    language: str,
) -> FactorContribution:
    """Analyze amount factor."""
    amount = assessment_input.amount_level

    if language == "ja":
        amount_names = {
            AmountLevel.LARGE: "大量 (≥1kL/1ton)",
            AmountLevel.MEDIUM: "中量 (1L-1kL / 1kg-1ton)",
            AmountLevel.SMALL: "少量 (100mL-1L / 100g-1kg)",
            AmountLevel.MINUTE: "微量 (10mL-100mL / 10g-100g)",
            AmountLevel.TRACE: "極微量 (<10mL / <10g)",
        }
        improvement_options = [
            "取り扱い量の削減",
            "小分け作業の導入",
            "バッチサイズの縮小",
        ]
    else:
        amount_names = {
            AmountLevel.LARGE: "Large (≥1kL/1ton)",
            AmountLevel.MEDIUM: "Medium (1L-1kL / 1kg-1ton)",
            AmountLevel.SMALL: "Small (100mL-1L / 100g-1kg)",
            AmountLevel.MINUTE: "Minute (10mL-100mL / 10g-100g)",
            AmountLevel.TRACE: "Trace (<10mL / <10g)",
        }
        improvement_options = [
            "Reduce handling amount",
            "Implement portioning",
            "Reduce batch size",
        ]

    # Estimate contribution (higher amounts = higher contribution)
    contribution = {
        AmountLevel.LARGE: 40.0,
        AmountLevel.MEDIUM: 30.0,
        AmountLevel.SMALL: 20.0,
        AmountLevel.MINUTE: 10.0,
        AmountLevel.TRACE: 5.0,
    }.get(amount, 25.0)

    return FactorContribution(
        factor_name="Amount" if language == "en" else "取り扱い量",
        factor_name_ja="取り扱い量",
        factor_value=amount_names.get(amount, str(amount)),
        coefficient=1.0,
        contribution_percent=contribution,
        is_beneficial=amount in [AmountLevel.MINUTE, AmountLevel.TRACE],
        can_be_improved=True,
        improvement_options=improvement_options,
    )


def _analyze_content_factor(
    assessment_input: AssessmentInput,
    language: str,
) -> FactorContribution:
    """Analyze content percentage factor."""
    # Get first component's content
    content = (
        assessment_input.components[0].content_percent if assessment_input.components else 100.0
    )

    if content >= 25:
        coeff = 1.0
        level = "high"
    elif content >= 5:
        coeff = 0.6
        level = "medium"
    elif content >= 1:
        coeff = 0.2
        level = "low"
    else:
        coeff = 0.1
        level = "very_low"

    if language == "ja":
        level_names = {
            "high": f"高濃度 ({content}% ≥25%)",
            "medium": f"中濃度 ({content}%: 5-25%)",
            "low": f"低濃度 ({content}%: 1-5%)",
            "very_low": f"極低濃度 ({content}% <1%)",
        }
        improvement_options = [
            "希釈による濃度低下",
            "低濃度製品への変更",
        ]
    else:
        level_names = {
            "high": f"High ({content}% ≥25%)",
            "medium": f"Medium ({content}%: 5-25%)",
            "low": f"Low ({content}%: 1-5%)",
            "very_low": f"Very low ({content}% <1%)",
        }
        improvement_options = [
            "Reduce concentration by dilution",
            "Switch to lower concentration product",
        ]

    contribution = (1.0 - coeff) / 1.0 * 20 if coeff < 1.0 else 0.0

    return FactorContribution(
        factor_name="Content %" if language == "en" else "含有率",
        factor_name_ja="含有率",
        factor_value=level_names.get(level, f"{content}%"),
        coefficient=coeff,
        contribution_percent=contribution,
        is_beneficial=level in ["low", "very_low"],
        can_be_improved=True,
        improvement_options=improvement_options,
    )


def _analyze_ventilation_factor(
    assessment_input: AssessmentInput,
    language: str,
) -> FactorContribution:
    """Analyze ventilation factor."""
    vent = assessment_input.ventilation
    verified = assessment_input.control_velocity_verified
    coeff = _get_ventilation_coefficient(assessment_input)

    if language == "ja":
        vent_names = {
            VentilationLevel.NONE: "換気なし",
            VentilationLevel.BASIC: "一般換気",
            VentilationLevel.INDUSTRIAL: "工業的換気",
            VentilationLevel.LOCAL_EXTERNAL: "局所排気(外付け)"
            + ("・制御風速確認済" if verified else ""),
            VentilationLevel.LOCAL_ENCLOSED: "局所排気(囲い式)"
            + ("・制御風速確認済" if verified else ""),
            VentilationLevel.SEALED: "密閉系",
        }
        improvement_options = [
            "局所排気装置の設置",
            "囲い式フードへの変更",
            "制御風速の確認・記録",
            "密閉系への変更",
        ]
    else:
        vent_names = {
            VentilationLevel.NONE: "No ventilation",
            VentilationLevel.BASIC: "Basic ventilation",
            VentilationLevel.INDUSTRIAL: "Industrial ventilation",
            VentilationLevel.LOCAL_EXTERNAL: "Local exhaust (external)"
            + (" - verified" if verified else ""),
            VentilationLevel.LOCAL_ENCLOSED: "Local exhaust (enclosed)"
            + (" - verified" if verified else ""),
            VentilationLevel.SEALED: "Sealed system",
        }
        improvement_options = [
            "Install local exhaust ventilation",
            "Upgrade to enclosed hood",
            "Verify and document control velocity",
            "Implement sealed system",
        ]

    # Higher coefficient = worse ventilation = higher contribution to risk
    contribution = min(coeff * 25, 100)

    return FactorContribution(
        factor_name="Ventilation" if language == "en" else "換気",
        factor_name_ja="換気",
        factor_value=vent_names.get(vent, str(vent)),
        coefficient=coeff,
        contribution_percent=contribution,
        is_beneficial=coeff <= 0.1,
        can_be_improved=vent != VentilationLevel.SEALED,
        improvement_options=improvement_options if vent != VentilationLevel.SEALED else [],
    )


def _analyze_spray_factor(
    assessment_input: AssessmentInput,
    language: str,
) -> FactorContribution:
    """Analyze spray operation factor."""
    if language == "ja":
        return FactorContribution(
            factor_name="スプレー作業",
            factor_name_ja="スプレー作業",
            factor_value="あり (×10)",
            coefficient=10.0,
            contribution_percent=40.0,
            is_beneficial=False,
            can_be_improved=True,
            improvement_options=[
                "刷毛塗りへの変更",
                "浸漬法への変更",
                "静電塗装への変更",
            ],
        )
    else:
        return FactorContribution(
            factor_name="Spray Operation",
            factor_name_ja="スプレー作業",
            factor_value="Yes (×10)",
            coefficient=10.0,
            contribution_percent=40.0,
            is_beneficial=False,
            can_be_improved=True,
            improvement_options=[
                "Switch to brush application",
                "Switch to dip coating",
                "Use electrostatic spraying",
            ],
        )


def _analyze_duration_factor(
    assessment_input: AssessmentInput,
    language: str,
) -> FactorContribution:
    """Analyze work duration factor."""
    hours = assessment_input.working_hours_per_day
    coeff = hours / 8.0

    if language == "ja":
        value = f"{hours}時間/日 (係数: {coeff:.2f})"
        improvement_options = [
            "作業時間の短縮",
            "交代制の導入",
            "作業の分散化",
        ]
    else:
        value = f"{hours} hours/day (coefficient: {coeff:.2f})"
        improvement_options = [
            "Reduce working hours",
            "Implement shift rotation",
            "Distribute work tasks",
        ]

    contribution = coeff * 15

    return FactorContribution(
        factor_name="Duration" if language == "en" else "作業時間",
        factor_name_ja="作業時間",
        factor_value=value,
        coefficient=coeff,
        contribution_percent=contribution,
        is_beneficial=coeff < 0.5,
        can_be_improved=True,
        improvement_options=improvement_options,
    )


def _get_content_coefficient(assessment_input: AssessmentInput) -> float:
    """Get content percentage coefficient."""
    content = (
        assessment_input.components[0].content_percent if assessment_input.components else 100.0
    )
    for threshold, coeff in sorted(CONTENT_COEFFICIENTS.items(), reverse=True):
        if content >= threshold:
            return coeff
    return 0.1


def _get_ventilation_coefficient(assessment_input: AssessmentInput) -> float:
    """Get ventilation coefficient."""
    vent_key = assessment_input.ventilation.value
    verified = assessment_input.control_velocity_verified
    return VENTILATION_COEFFICIENTS.get((vent_key, verified), 1.0)


def _get_duration_coefficient(assessment_input: AssessmentInput) -> float:
    """Get duration coefficient."""
    return assessment_input.working_hours_per_day / 8.0


def _get_volatility_level(substance: Substance) -> str:
    """Determine volatility/dustiness level from substance properties."""
    props = substance.properties

    if substance.property_type == PropertyType.LIQUID:
        # Determine from boiling point or vapor pressure
        if props.vapor_pressure and props.vapor_pressure < 0.5:
            return "very_low"
        if props.boiling_point:
            if props.boiling_point < 50:
                return "high"
            elif props.boiling_point < 150:
                return "medium"
            else:
                return "low"
        return "medium"  # Default for liquids
    else:
        # For solids, would need dustiness classification
        return "medium"  # Default for solids


def _safe_log_ratio(a: float, b: float) -> float:
    """Calculate log ratio safely."""
    import math

    if a <= 0 or b <= 0:
        return 0.0
    return math.log10(a / b)
