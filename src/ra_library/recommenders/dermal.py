"""
Dermal risk reduction recommendations.

Generates prioritized recommendations for reducing dermal exposure risk.

Reference: CREATE-SIMPLE Design v3.1.1, Section 4.3
"""

from typing import Optional

from ..models.assessment import AssessmentInput, GloveType
from ..models.constraints import AssessmentConstraints
from ..models.substance import Substance
from ..models.risk import RiskLevel, DermalRisk
from ..models.recommendation import (
    Recommendation,
    RecommendationSet,
    ActionCategory,
    EffectivenessLevel,
    Feasibility,
)
from ..references.catalog import get_reference


def get_dermal_recommendations(
    assessment_input: AssessmentInput,
    substance: Substance,
    risk: DermalRisk,
    target_level: RiskLevel = RiskLevel.I,
    language: str = "en",
    constraints: Optional[AssessmentConstraints] = None,
) -> RecommendationSet:
    """
    Generate dermal risk reduction recommendations.

    Args:
        assessment_input: Current assessment input
        substance: Substance being assessed
        risk: Current dermal risk result
        target_level: Target risk level to achieve
        language: "en" or "ja"
        constraints: Optional constraints to filter recommendations

    Returns:
        RecommendationSet with prioritized recommendations
    """
    recommendations = []

    # Check if PPE controls are allowed for glove recommendations
    if constraints is None or constraints.allows_ppe_controls():
        # Glove recommendations
        recommendations.extend(_recommend_gloves(assessment_input, risk, language))

        # Skin area reduction (also PPE-related)
        recommendations.extend(_recommend_skin_protection(assessment_input, risk, language))

    # Substitution for high-risk substances
    if risk.risk_level >= RiskLevel.III:
        recommendations.append(_recommend_substitution(substance, risk, language))

    # Sort by effectiveness
    recommendations.sort(key=lambda r: -r.rcr_reduction_percent)

    return RecommendationSet(
        current_risk_level=risk.risk_level.name,
        target_risk_level=target_level.name,
        achievable=True,  # Dermal risk can usually be controlled with gloves
        recommendations=recommendations,
    )


def _recommend_gloves(
    assessment_input: AssessmentInput,
    risk: DermalRisk,
    language: str,
) -> list[Recommendation]:
    """Generate glove recommendations."""
    recommendations = []
    current_glove = assessment_input.glove_type or GloveType.NONE

    if current_glove == GloveType.NONE:
        # Recommend resistant gloves
        reduction = 80.0  # 1.0 -> 0.2 coefficient
        new_level = RiskLevel.from_rcr(risk.rcr * 0.2) if risk.rcr else risk.risk_level

        if language == "ja":
            recommendations.append(
                Recommendation(
                    action="耐透過性手袋の着用",
                    action_ja="耐透過性手袋の着用",
                    category=ActionCategory.PPE,
                    effectiveness=EffectivenessLevel.HIGH,
                    feasibility=Feasibility.EASY,
                    current_risk_level=risk.risk_level.name,
                    predicted_risk_level=new_level.name,
                    rcr_reduction_percent=reduction,
                    parameter_affected="glove_type",
                    current_value="なし",
                    new_value="耐透過性手袋",
                    coefficient_change="1.0 → 0.2",
                    description="適切な耐透過性手袋で経皮吸収を80%削減",
                    description_ja="適切な耐透過性手袋で経皮吸収を80%削減",
                    implementation_notes="物質に適した手袋材質を選定（製造元に確認）",
                    implementation_notes_ja="物質に適した手袋材質を選定（製造元に確認）",
                    references=[get_reference("create_simple_design_4_3")],
                )
            )
        else:
            recommendations.append(
                Recommendation(
                    action="Use chemical-resistant gloves",
                    action_ja="耐透過性手袋の着用",
                    category=ActionCategory.PPE,
                    effectiveness=EffectivenessLevel.HIGH,
                    feasibility=Feasibility.EASY,
                    current_risk_level=risk.risk_level.name,
                    predicted_risk_level=new_level.name,
                    rcr_reduction_percent=reduction,
                    parameter_affected="glove_type",
                    current_value="None",
                    new_value="Chemical-resistant gloves",
                    coefficient_change="1.0 → 0.2",
                    description="Appropriate chemical-resistant gloves reduce dermal absorption by 80%",
                    description_ja="適切な耐透過性手袋で経皮吸収を80%削減",
                    implementation_notes="Select glove material appropriate for the substance (consult manufacturer)",
                    implementation_notes_ja="物質に適した手袋材質を選定（製造元に確認）",
                    references=[get_reference("create_simple_design_4_3")],
                )
            )

    elif current_glove == GloveType.NON_RESISTANT:
        # Upgrade to resistant gloves
        reduction = 80.0
        new_level = RiskLevel.from_rcr(risk.rcr * 0.2) if risk.rcr else risk.risk_level

        if language == "ja":
            recommendations.append(
                Recommendation(
                    action="耐透過性手袋への変更",
                    action_ja="耐透過性手袋への変更",
                    category=ActionCategory.PPE,
                    effectiveness=EffectivenessLevel.HIGH,
                    feasibility=Feasibility.EASY,
                    current_risk_level=risk.risk_level.name,
                    predicted_risk_level=new_level.name,
                    rcr_reduction_percent=reduction,
                    parameter_affected="glove_type",
                    current_value="非耐透過性手袋",
                    new_value="耐透過性手袋",
                    coefficient_change="1.0 → 0.2",
                    description="現在の手袋は化学物質に対する保護効果がありません",
                    description_ja="現在の手袋は化学物質に対する保護効果がありません",
                    implementation_notes="物質に適した手袋材質を選定",
                    implementation_notes_ja="物質に適した手袋材質を選定",
                    references=[get_reference("create_simple_design_4_3")],
                )
            )
        else:
            recommendations.append(
                Recommendation(
                    action="Switch to chemical-resistant gloves",
                    action_ja="耐透過性手袋への変更",
                    category=ActionCategory.PPE,
                    effectiveness=EffectivenessLevel.HIGH,
                    feasibility=Feasibility.EASY,
                    current_risk_level=risk.risk_level.name,
                    predicted_risk_level=new_level.name,
                    rcr_reduction_percent=reduction,
                    parameter_affected="glove_type",
                    current_value="Non-resistant gloves",
                    new_value="Chemical-resistant gloves",
                    coefficient_change="1.0 → 0.2",
                    description="Current gloves provide no chemical protection",
                    description_ja="現在の手袋は化学物質に対する保護効果がありません",
                    implementation_notes="Select appropriate glove material for the substance",
                    implementation_notes_ja="物質に適した手袋材質を選定",
                    references=[get_reference("create_simple_design_4_3")],
                )
            )

    # Glove training recommendation
    if current_glove != GloveType.NONE and not assessment_input.glove_training:
        reduction = 20.0  # Estimated improvement from proper training

        if language == "ja":
            recommendations.append(
                Recommendation(
                    action="手袋使用教育の実施",
                    action_ja="手袋使用教育の実施",
                    category=ActionCategory.ADMINISTRATIVE,
                    effectiveness=EffectivenessLevel.MEDIUM,
                    feasibility=Feasibility.EASY,
                    current_risk_level=risk.risk_level.name,
                    predicted_risk_level=risk.risk_level.name,  # May not change level
                    rcr_reduction_percent=reduction,
                    parameter_affected="glove_training",
                    current_value="未実施",
                    new_value="実施済",
                    coefficient_change="N/A",
                    description="適切な着脱方法と交換時期の教育",
                    description_ja="適切な着脱方法と交換時期の教育",
                    implementation_notes="定期的な教育と記録の保管",
                    implementation_notes_ja="定期的な教育と記録の保管",
                    references=[get_reference("create_simple_design_4_3")],
                )
            )
        else:
            recommendations.append(
                Recommendation(
                    action="Implement glove use training",
                    action_ja="手袋使用教育の実施",
                    category=ActionCategory.ADMINISTRATIVE,
                    effectiveness=EffectivenessLevel.MEDIUM,
                    feasibility=Feasibility.EASY,
                    current_risk_level=risk.risk_level.name,
                    predicted_risk_level=risk.risk_level.name,
                    rcr_reduction_percent=reduction,
                    parameter_affected="glove_training",
                    current_value="Not conducted",
                    new_value="Conducted",
                    coefficient_change="N/A",
                    description="Train workers on proper donning/doffing and replacement schedule",
                    description_ja="適切な着脱方法と交換時期の教育",
                    implementation_notes="Regular training and documentation",
                    implementation_notes_ja="定期的な教育と記録の保管",
                    references=[get_reference("create_simple_design_4_3")],
                )
            )

    return recommendations


def _recommend_skin_protection(
    assessment_input: AssessmentInput,
    risk: DermalRisk,
    language: str,
) -> list[Recommendation]:
    """Generate skin area protection recommendations."""
    recommendations = []

    # If exposed skin area is large, recommend protection
    # This is a simplified recommendation
    if language == "ja":
        recommendations.append(
            Recommendation(
                action="保護衣の着用",
                action_ja="保護衣の着用",
                category=ActionCategory.PPE,
                effectiveness=EffectivenessLevel.MEDIUM,
                feasibility=Feasibility.EASY,
                current_risk_level=risk.risk_level.name,
                predicted_risk_level=risk.risk_level.name,
                rcr_reduction_percent=30.0,
                parameter_affected="skin_protection",
                current_value="腕部露出",
                new_value="保護衣着用",
                coefficient_change="N/A",
                description="長袖の保護衣で露出面積を削減",
                description_ja="長袖の保護衣で露出面積を削減",
                implementation_notes="物質に適した素材を選定",
                implementation_notes_ja="物質に適した素材を選定",
                references=[get_reference("create_simple_design_4_3")],
            )
        )
    else:
        recommendations.append(
            Recommendation(
                action="Use protective clothing",
                action_ja="保護衣の着用",
                category=ActionCategory.PPE,
                effectiveness=EffectivenessLevel.MEDIUM,
                feasibility=Feasibility.EASY,
                current_risk_level=risk.risk_level.name,
                predicted_risk_level=risk.risk_level.name,
                rcr_reduction_percent=30.0,
                parameter_affected="skin_protection",
                current_value="Arms exposed",
                new_value="Protective clothing",
                coefficient_change="N/A",
                description="Long-sleeve protective clothing reduces exposed area",
                description_ja="長袖の保護衣で露出面積を削減",
                implementation_notes="Select appropriate material for the substance",
                implementation_notes_ja="物質に適した素材を選定",
                references=[get_reference("create_simple_design_4_3")],
            )
        )

    return recommendations


def _recommend_substitution(
    substance: Substance,
    risk: DermalRisk,
    language: str,
) -> Recommendation:
    """Recommend substance substitution for high dermal risk."""
    if language == "ja":
        return Recommendation(
            action="経皮吸収性の低い代替物質への変更",
            action_ja="経皮吸収性の低い代替物質への変更",
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
            description="分子量が大きくlog Kowが低い物質は経皮吸収が少ない",
            description_ja="分子量が大きくlog Kowが低い物質は経皮吸収が少ない",
            implementation_notes="専門家との相談が必要",
            implementation_notes_ja="専門家との相談が必要",
            references=[get_reference("potts_guy")],
        )
    else:
        return Recommendation(
            action="Substitute with lower dermal absorption substance",
            action_ja="経皮吸収性の低い代替物質への変更",
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
            description="Higher MW and lower log Kow reduces dermal absorption",
            description_ja="分子量が大きくlog Kowが低い物質は経皮吸収が少ない",
            implementation_notes="Consult with chemical safety experts",
            implementation_notes_ja="専門家との相談が必要",
            references=[get_reference("potts_guy")],
        )
