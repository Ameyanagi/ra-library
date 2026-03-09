"""
Inhalation risk reduction recommendations.

Generates prioritized recommendations for reducing inhalation exposure risk.

Reference: CREATE-SIMPLE Design v3.1.1, Control hierarchy
"""

from typing import Optional

from ..models.assessment import (
    AssessmentInput,
    AssessmentMode,
    PropertyType,
    VentilationLevel,
)
from ..models.constraints import AssessmentConstraints
from ..models.substance import Substance
from ..models.risk import RiskLevel, InhalationRisk
from ..models.recommendation import (
    Recommendation,
    RecommendationSet,
    ActionCategory,
    EffectivenessLevel,
    Feasibility,
)
from ..references.catalog import get_reference


def get_inhalation_recommendations(
    assessment_input: AssessmentInput,
    substance: Substance,
    risk: InhalationRisk,
    target_level: RiskLevel = RiskLevel.I,
    language: str = "en",
    constraints: Optional[AssessmentConstraints] = None,
) -> RecommendationSet:
    """
    Generate inhalation risk reduction recommendations.

    Args:
        assessment_input: Current assessment input
        substance: Substance being assessed
        risk: Current inhalation risk result
        target_level: Target risk level to achieve
        language: "en" or "ja"
        constraints: Optional constraints to filter recommendations

    Returns:
        RecommendationSet with prioritized recommendations
    """
    recommendations = []

    # Hierarchy of controls (most to least effective):
    # 1. Elimination - not usually possible for chemicals
    # 2. Substitution - use less hazardous substance
    # 3. Engineering controls - ventilation, enclosure
    # 4. Administrative controls - time, procedures
    # 5. PPE - respiratory protection

    # Substitution recommendations
    if risk.risk_level >= RiskLevel.III:
        recommendations.append(_recommend_substitution(substance, risk, language))

    # Engineering recommendations
    recommendations.extend(
        _recommend_ventilation(assessment_input, risk, language, constraints)
    )

    # Administrative recommendations
    recommendations.extend(
        _recommend_administrative(assessment_input, risk, language, constraints)
    )

    # PPE recommendations
    # Note: Originally restricted to Report mode only per CREATE-SIMPLE VBA design,
    # but included by default for practical daily RA workflow.
    # RPE is the last line of defense but often the most practical immediate measure.
    recommendations.extend(_recommend_rpe(assessment_input, risk, language, constraints))

    # Sort by effectiveness and feasibility
    recommendations.sort(
        key=lambda r: (
            -_effectiveness_score(r.effectiveness),
            _feasibility_score(r.feasibility),
        )
    )

    # Calculate if target is achievable
    target_rcr = {
        RiskLevel.I: 0.1,
        RiskLevel.II: 1.0,
        RiskLevel.III: 10.0,
        RiskLevel.IV: float("inf"),
    }[target_level]

    best_achievable = _calculate_best_achievable(assessment_input, risk)

    return RecommendationSet(
        current_risk_level=risk.risk_level.name,
        target_risk_level=target_level.name,
        achievable=best_achievable <= target_rcr,
        limitation_explanation=None
        if best_achievable <= target_rcr
        else f"Best achievable RCR is {best_achievable:.4f}"
        if language == "en"
        else f"達成可能な最小RCRは{best_achievable:.4f}です",
        best_achievable_level=RiskLevel.from_rcr(best_achievable).name,
        recommendations=recommendations,
    )


def _recommend_substitution(
    substance: Substance,
    risk: InhalationRisk,
    language: str,
) -> Recommendation:
    """Recommend substance substitution."""
    if language == "ja":
        return Recommendation(
            action="より有害性の低い代替物質への変更",
            action_ja="より有害性の低い代替物質への変更",
            category=ActionCategory.SUBSTITUTION,
            effectiveness=EffectivenessLevel.HIGH,
            feasibility=Feasibility.DIFFICULT,
            current_risk_level=risk.risk_level.name,
            predicted_risk_level="I",
            rcr_reduction_percent=90.0,
            parameter_affected="substance",
            current_value=substance.name_ja or substance.cas_number,
            new_value="代替物質",
            coefficient_change="N/A",
            description="本質的にリスクを除去する最も効果的な方法です",
            description_ja="本質的にリスクを除去する最も効果的な方法です",
            implementation_notes="専門家との相談が必要です",
            implementation_notes_ja="専門家との相談が必要です",
            cost_estimate="要見積",
            references=[get_reference("create_simple_design")],
        )
    else:
        return Recommendation(
            action="Substitute with less hazardous substance",
            action_ja="より有害性の低い代替物質への変更",
            category=ActionCategory.SUBSTITUTION,
            effectiveness=EffectivenessLevel.HIGH,
            feasibility=Feasibility.DIFFICULT,
            current_risk_level=risk.risk_level.name,
            predicted_risk_level="I",
            rcr_reduction_percent=90.0,
            parameter_affected="substance",
            current_value=substance.name_en or substance.cas_number,
            new_value="Alternative substance",
            coefficient_change="N/A",
            description="Most effective way to eliminate risk at the source",
            description_ja="本質的にリスクを除去する最も効果的な方法です",
            implementation_notes="Consult with chemical safety experts",
            implementation_notes_ja="専門家との相談が必要です",
            cost_estimate="Variable",
            references=[get_reference("create_simple_design")],
        )


def _recommend_ventilation(
    assessment_input: AssessmentInput,
    risk: InhalationRisk,
    language: str,
    constraints: Optional[AssessmentConstraints] = None,
) -> list[Recommendation]:
    """Generate ventilation improvement recommendations."""
    from ..calculators.constants import MIN_EXPOSURE_LIQUID, MIN_EXPOSURE_SOLID

    recommendations = []
    current = assessment_input.ventilation
    verified = assessment_input.control_velocity_verified

    # Check if exposure is floor-limited (ventilation improvements won't help)
    is_solid = assessment_input.product_property == PropertyType.SOLID
    floor_value = MIN_EXPOSURE_SOLID if is_solid else MIN_EXPOSURE_LIQUID

    # If current exposure is at or very close to the floor, skip ventilation recs
    if risk.exposure_8hr <= floor_value * 1.01:  # 1% tolerance for floating point
        return recommendations

    def _is_allowed(target_level: VentilationLevel) -> bool:
        """Check if target ventilation level is allowed by constraints."""
        if constraints is None:
            return True
        return constraints.allows_ventilation(target_level)

    def _would_hit_floor(ratio: float) -> bool:
        """Check if applying this ratio would result in floor-limited exposure."""
        theoretical_exposure = risk.exposure_8hr * ratio
        return theoretical_exposure < floor_value

    # Define upgrade paths with constraint and floor checks
    if current == VentilationLevel.NONE:
        ratio = 0.7 / 4.0
        if _is_allowed(VentilationLevel.LOCAL_EXTERNAL) and not _would_hit_floor(ratio):
            recommendations.append(
                _create_vent_recommendation(
                    current, VentilationLevel.LOCAL_EXTERNAL, risk, ratio, language
                )
            )
        ratio = 0.3 / 4.0
        if _is_allowed(VentilationLevel.LOCAL_ENCLOSED) and not _would_hit_floor(ratio):
            recommendations.append(
                _create_vent_recommendation(
                    current, VentilationLevel.LOCAL_ENCLOSED, risk, ratio, language
                )
            )

    elif current == VentilationLevel.BASIC:
        ratio = 0.7 / 3.0
        if _is_allowed(VentilationLevel.LOCAL_EXTERNAL) and not _would_hit_floor(ratio):
            recommendations.append(
                _create_vent_recommendation(
                    current, VentilationLevel.LOCAL_EXTERNAL, risk, ratio, language
                )
            )
        ratio = 0.3 / 3.0
        if _is_allowed(VentilationLevel.LOCAL_ENCLOSED) and not _would_hit_floor(ratio):
            recommendations.append(
                _create_vent_recommendation(
                    current, VentilationLevel.LOCAL_ENCLOSED, risk, ratio, language
                )
            )

    elif current == VentilationLevel.INDUSTRIAL:
        ratio = 0.7
        if _is_allowed(VentilationLevel.LOCAL_EXTERNAL) and not _would_hit_floor(ratio):
            recommendations.append(
                _create_vent_recommendation(
                    current, VentilationLevel.LOCAL_EXTERNAL, risk, ratio, language
                )
            )
        ratio = 0.3
        if _is_allowed(VentilationLevel.LOCAL_ENCLOSED) and not _would_hit_floor(ratio):
            recommendations.append(
                _create_vent_recommendation(
                    current, VentilationLevel.LOCAL_ENCLOSED, risk, ratio, language
                )
            )

    elif current == VentilationLevel.LOCAL_EXTERNAL:
        if not verified:
            ratio = 0.1 / 0.7
            if not _would_hit_floor(ratio):
                recommendations.append(
                    _create_vent_verification_recommendation(current, risk, ratio, language)
                )
        ratio = 0.3 / 0.7
        if _is_allowed(VentilationLevel.LOCAL_ENCLOSED) and not _would_hit_floor(ratio):
            recommendations.append(
                _create_vent_recommendation(
                    current, VentilationLevel.LOCAL_ENCLOSED, risk, ratio, language
                )
            )

    elif current == VentilationLevel.LOCAL_ENCLOSED:
        if not verified:
            ratio = 0.01 / 0.3
            if not _would_hit_floor(ratio):
                recommendations.append(
                    _create_vent_verification_recommendation(current, risk, ratio, language)
                )
        ratio = 0.001 / 0.3
        # Check both constraint AND floor for sealed system
        if _is_allowed(VentilationLevel.SEALED) and not _would_hit_floor(ratio):
            recommendations.append(
                _create_vent_recommendation(
                    current, VentilationLevel.SEALED, risk, ratio, language
                )
            )

    return recommendations


def _create_vent_recommendation(
    current: VentilationLevel,
    target: VentilationLevel,
    risk: InhalationRisk,
    ratio: float,
    language: str,
) -> Recommendation:
    """Create a ventilation upgrade recommendation."""
    new_rcr = risk.rcr * ratio
    reduction = (1 - ratio) * 100
    new_level = RiskLevel.from_rcr(new_rcr)

    if language == "ja":
        vent_names = {
            VentilationLevel.LOCAL_EXTERNAL: "局所排気装置(外付け)の設置",
            VentilationLevel.LOCAL_ENCLOSED: "囲い式局所排気装置の設置",
            VentilationLevel.SEALED: "密閉系への変更",
        }
        current_names = {
            VentilationLevel.NONE: "換気なし",
            VentilationLevel.BASIC: "一般換気",
            VentilationLevel.INDUSTRIAL: "工業的換気",
            VentilationLevel.LOCAL_EXTERNAL: "局所排気(外付け)",
            VentilationLevel.LOCAL_ENCLOSED: "局所排気(囲い式)",
        }
    else:
        vent_names = {
            VentilationLevel.LOCAL_EXTERNAL: "Install local exhaust ventilation (external hood)",
            VentilationLevel.LOCAL_ENCLOSED: "Install enclosed local exhaust ventilation",
            VentilationLevel.SEALED: "Implement sealed/enclosed system",
        }
        current_names = {
            VentilationLevel.NONE: "No ventilation",
            VentilationLevel.BASIC: "Basic ventilation",
            VentilationLevel.INDUSTRIAL: "Industrial ventilation",
            VentilationLevel.LOCAL_EXTERNAL: "Local exhaust (external)",
            VentilationLevel.LOCAL_ENCLOSED: "Local exhaust (enclosed)",
        }

    # Determine feasibility
    if target == VentilationLevel.SEALED:
        feasibility = Feasibility.VERY_DIFFICULT
    elif target == VentilationLevel.LOCAL_ENCLOSED:
        feasibility = Feasibility.DIFFICULT
    else:
        feasibility = Feasibility.MODERATE

    return Recommendation(
        action=vent_names.get(target, str(target)),
        action_ja=vent_names.get(target, str(target)) if language == "ja" else "",
        category=ActionCategory.ENGINEERING,
        effectiveness=EffectivenessLevel.HIGH if reduction > 50 else EffectivenessLevel.MEDIUM,
        feasibility=feasibility,
        current_risk_level=risk.risk_level.name,
        predicted_risk_level=new_level.name,
        rcr_reduction_percent=reduction,
        parameter_affected="ventilation",
        current_value=current_names.get(current, str(current)),
        new_value=vent_names.get(target, str(target)),
        coefficient_change=f"→ {ratio:.3f}×",
        description=f"Reduces exposure by {reduction:.0f}%"
        if language == "en"
        else f"ばく露を{reduction:.0f}%削減",
        description_ja=f"ばく露を{reduction:.0f}%削減",
        implementation_notes="Design with industrial hygienist"
        if language == "en"
        else "産業衛生専門家と設計",
        implementation_notes_ja="産業衛生専門家と設計",
        references=[get_reference("create_simple_design_3_3_vent")],
    )


def _create_vent_verification_recommendation(
    current: VentilationLevel,
    risk: InhalationRisk,
    ratio: float,
    language: str,
) -> Recommendation:
    """Create a control velocity verification recommendation."""
    new_rcr = risk.rcr * ratio
    reduction = (1 - ratio) * 100
    new_level = RiskLevel.from_rcr(new_rcr)

    if language == "ja":
        return Recommendation(
            action="制御風速の確認・記録",
            action_ja="制御風速の確認・記録",
            category=ActionCategory.ENGINEERING,
            effectiveness=EffectivenessLevel.HIGH,
            feasibility=Feasibility.EASY,
            current_risk_level=risk.risk_level.name,
            predicted_risk_level=new_level.name,
            rcr_reduction_percent=reduction,
            parameter_affected="control_velocity_verified",
            current_value="未確認",
            new_value="確認済",
            coefficient_change=f"→ {ratio:.3f}×",
            description=f"制御風速を確認・記録することでばく露を{reduction:.0f}%削減",
            description_ja=f"制御風速を確認・記録することでばく露を{reduction:.0f}%削減",
            implementation_notes="風速計で測定し、記録を保管",
            implementation_notes_ja="風速計で測定し、記録を保管",
            references=[get_reference("create_simple_design_3_3_vent")],
        )
    else:
        return Recommendation(
            action="Verify and document control velocity",
            action_ja="制御風速の確認・記録",
            category=ActionCategory.ENGINEERING,
            effectiveness=EffectivenessLevel.HIGH,
            feasibility=Feasibility.EASY,
            current_risk_level=risk.risk_level.name,
            predicted_risk_level=new_level.name,
            rcr_reduction_percent=reduction,
            parameter_affected="control_velocity_verified",
            current_value="Not verified",
            new_value="Verified",
            coefficient_change=f"→ {ratio:.3f}×",
            description=f"Verify control velocity to reduce exposure by {reduction:.0f}%",
            description_ja=f"制御風速を確認することでばく露を{reduction:.0f}%削減",
            implementation_notes="Measure with anemometer and maintain records",
            implementation_notes_ja="風速計で測定し、記録を保管",
            references=[get_reference("create_simple_design_3_3_vent")],
        )


def _recommend_administrative(
    assessment_input: AssessmentInput,
    risk: InhalationRisk,
    language: str,
    constraints: Optional[AssessmentConstraints] = None,
) -> list[Recommendation]:
    """Generate administrative control recommendations."""
    recommendations = []

    # Check if admin controls are allowed
    if constraints and not constraints.allows_admin_controls():
        return recommendations

    # Duration reduction
    if assessment_input.working_hours_per_day > 4:
        half_hours = assessment_input.working_hours_per_day / 2
        reduction = 50.0
        new_rcr = risk.rcr * 0.5
        new_level = RiskLevel.from_rcr(new_rcr)

        if language == "ja":
            recommendations.append(
                Recommendation(
                    action=f"作業時間を{half_hours:.1f}時間/日に短縮",
                    action_ja=f"作業時間を{half_hours:.1f}時間/日に短縮",
                    category=ActionCategory.ADMINISTRATIVE,
                    effectiveness=EffectivenessLevel.MEDIUM,
                    feasibility=Feasibility.MODERATE,
                    current_risk_level=risk.risk_level.name,
                    predicted_risk_level=new_level.name,
                    rcr_reduction_percent=reduction,
                    parameter_affected="working_hours",
                    current_value=f"{assessment_input.working_hours_per_day}時間/日",
                    new_value=f"{half_hours:.1f}時間/日",
                    coefficient_change="→ 0.5×",
                    description="ジョブローテーションで作業時間を半減",
                    description_ja="ジョブローテーションで作業時間を半減",
                    implementation_notes="作業者の交代制を導入",
                    implementation_notes_ja="作業者の交代制を導入",
                    references=[get_reference("create_simple_design_3_3_duration")],
                )
            )
        else:
            recommendations.append(
                Recommendation(
                    action=f"Reduce work hours to {half_hours:.1f}h/day",
                    action_ja=f"作業時間を{half_hours:.1f}時間/日に短縮",
                    category=ActionCategory.ADMINISTRATIVE,
                    effectiveness=EffectivenessLevel.MEDIUM,
                    feasibility=Feasibility.MODERATE,
                    current_risk_level=risk.risk_level.name,
                    predicted_risk_level=new_level.name,
                    rcr_reduction_percent=reduction,
                    parameter_affected="working_hours",
                    current_value=f"{assessment_input.working_hours_per_day}h/day",
                    new_value=f"{half_hours:.1f}h/day",
                    coefficient_change="→ 0.5×",
                    description="Halve exposure duration through job rotation",
                    description_ja="ジョブローテーションで作業時間を半減",
                    implementation_notes="Implement worker rotation schedule",
                    implementation_notes_ja="作業者の交代制を導入",
                    references=[get_reference("create_simple_design_3_3_duration")],
                )
            )

    return recommendations


def _recommend_rpe(
    assessment_input: AssessmentInput,
    risk: InhalationRisk,
    language: str,
    constraints: Optional[AssessmentConstraints] = None,
) -> list[Recommendation]:
    """Generate RPE recommendations (Report mode only)."""
    from ..calculators.constants import MIN_EXPOSURE_LIQUID, MIN_EXPOSURE_SOLID

    recommendations = []

    # Check if PPE controls are allowed
    if constraints and not constraints.allows_ppe_controls():
        return recommendations

    # Determine floor value based on exposure unit
    is_solid = "mg" in risk.exposure_8hr_unit.lower()
    floor_value = MIN_EXPOSURE_SOLID if is_solid else MIN_EXPOSURE_LIQUID

    # If exposure is already at or very close to floor, RPE won't help
    # (the exposure cannot be reduced below the floor)
    if risk.exposure_8hr <= floor_value * 1.01:  # 1% tolerance for floating point
        return recommendations

    # Suggest appropriate APF based on current RCR
    target_rcr_for_level_i = 0.1
    required_apf = risk.rcr / target_rcr_for_level_i

    # Define RPE options with their APF values
    rpe_options = [
        (10, "tight_fit_10", "Tight-fit APF 10", "タイトフィット APF 10"),
        (25, "loose_fit_25", "Loose-fit APF 25", "ルーズフィット APF 25"),
        (50, "tight_fit_50", "Tight-fit APF 50", "タイトフィット APF 50"),
        (100, "tight_fit_100", "Tight-fit APF 100", "タイトフィット APF 100"),
        (1000, "tight_fit_1000", "Tight-fit APF 1000", "タイトフィット APF 1000"),
    ]

    # Find the smallest APF that achieves target, checking constraints
    apf = None
    rpe_name = None
    for apf_val, rpe_type, name_en, name_ja in rpe_options:
        if required_apf <= apf_val:
            # Check if this RPE is allowed by constraints
            if constraints and not constraints.allows_rpe(rpe_type, apf_val):
                continue
            apf = apf_val
            rpe_name = name_ja if language == "ja" else name_en
            break

    # If no suitable RPE found (all filtered by constraints), try highest
    if apf is None:
        for apf_val, rpe_type, name_en, name_ja in reversed(rpe_options):
            if constraints and not constraints.allows_rpe(rpe_type, apf_val):
                continue
            apf = apf_val
            rpe_name = name_ja if language == "ja" else name_en
            break

    # If still no RPE allowed, return empty
    if apf is None:
        return recommendations

    # Calculate actual achievable exposure considering the floor
    # RPE reduces exposure by 1/APF, but floor limits the minimum
    theoretical_exposure = risk.exposure_8hr / apf
    actual_exposure = max(theoretical_exposure, floor_value)
    new_rcr = actual_exposure / risk.oel
    reduction = (1 - (actual_exposure / risk.exposure_8hr)) * 100
    new_level = RiskLevel.from_rcr(new_rcr)

    # Skip recommendation if actual reduction is negligible (< 10%)
    if reduction < 10:
        return recommendations

    if language == "ja":
        recommendations.append(
            Recommendation(
                action=f"{rpe_name}の着用",
                action_ja=f"{rpe_name}の着用",
                category=ActionCategory.PPE,
                effectiveness=EffectivenessLevel.HIGH if apf >= 50 else EffectivenessLevel.MEDIUM,
                feasibility=Feasibility.MODERATE if "Tight" in rpe_name else Feasibility.EASY,
                current_risk_level=risk.risk_level.name,
                predicted_risk_level=new_level.name,
                rcr_reduction_percent=reduction,
                parameter_affected="rpe",
                current_value="なし",
                new_value=rpe_name,
                coefficient_change=f"→ 1/{apf}",
                description=f"APF {apf}の呼吸用保護具でばく露を{reduction:.0f}%削減",
                description_ja=f"APF {apf}の呼吸用保護具でばく露を{reduction:.0f}%削減",
                implementation_notes="フィットテストと教育が必要"
                if "Tight" in rpe_name
                else "使用者教育が必要",
                implementation_notes_ja="フィットテストと教育が必要"
                if "Tight" in rpe_name
                else "使用者教育が必要",
                references=[get_reference("create_simple_design")],
            )
        )
    else:
        recommendations.append(
            Recommendation(
                action=f"Use {rpe_name} respirator",
                action_ja=f"{rpe_name}の着用",
                category=ActionCategory.PPE,
                effectiveness=EffectivenessLevel.HIGH if apf >= 50 else EffectivenessLevel.MEDIUM,
                feasibility=Feasibility.MODERATE if "Tight" in rpe_name else Feasibility.EASY,
                current_risk_level=risk.risk_level.name,
                predicted_risk_level=new_level.name,
                rcr_reduction_percent=reduction,
                parameter_affected="rpe",
                current_value="None",
                new_value=rpe_name,
                coefficient_change=f"→ 1/{apf}",
                description=f"APF {apf} respirator reduces exposure by {reduction:.0f}%",
                description_ja=f"APF {apf}の呼吸用保護具でばく露を{reduction:.0f}%削減",
                implementation_notes="Fit test and training required"
                if "Tight" in rpe_name
                else "User training required",
                implementation_notes_ja="フィットテストと教育が必要"
                if "Tight" in rpe_name
                else "使用者教育が必要",
                references=[get_reference("create_simple_design")],
            )
        )

    return recommendations


def _effectiveness_score(effectiveness: EffectivenessLevel) -> int:
    """Convert effectiveness to numeric score for sorting."""
    return {
        EffectivenessLevel.HIGH: 3,
        EffectivenessLevel.MEDIUM: 2,
        EffectivenessLevel.LOW: 1,
    }[effectiveness]


def _feasibility_score(feasibility: Feasibility) -> int:
    """Convert feasibility to numeric score for sorting."""
    return {
        Feasibility.EASY: 1,
        Feasibility.MODERATE: 2,
        Feasibility.DIFFICULT: 3,
        Feasibility.VERY_DIFFICULT: 4,
    }[feasibility]


def _calculate_best_achievable(
    assessment_input: AssessmentInput,
    risk: InhalationRisk,
) -> float:
    """Calculate the best achievable RCR with maximum controls."""
    from ..calculators.constants import MIN_EXPOSURE_LIQUID, MIN_EXPOSURE_SOLID

    # Use appropriate minimum floor based on unit
    if "mg" in risk.exposure_8hr_unit.lower():
        min_floor = MIN_EXPOSURE_SOLID
    else:
        min_floor = MIN_EXPOSURE_LIQUID

    # If ACRmax applies, use it; otherwise use OEL
    if risk.acrmax:
        return min_floor / risk.acrmax
    else:
        return min_floor / risk.oel
