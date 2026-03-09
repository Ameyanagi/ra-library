"""
Physical hazard risk reduction recommendations.

Generates prioritized recommendations for reducing physical hazard risk.

Reference: CREATE-SIMPLE Design v3.1.1, Section 7
"""

from typing import Optional

from ..models.assessment import AssessmentInput
from ..models.constraints import AssessmentConstraints
from ..models.substance import Substance
from ..models.risk import PhysicalRisk
from ..models.recommendation import (
    Recommendation,
    RecommendationSet,
    ActionCategory,
    EffectivenessLevel,
    Feasibility,
)
from ..references.catalog import get_reference


def get_physical_recommendations(
    assessment_input: AssessmentInput,
    substance: Substance,
    risk: PhysicalRisk,
    language: str = "en",
    constraints: Optional[AssessmentConstraints] = None,
) -> RecommendationSet:
    """
    Generate physical hazard risk reduction recommendations.

    Args:
        assessment_input: Current assessment input
        substance: Substance being assessed
        risk: Current physical risk result
        language: "en" or "ja"
        constraints: Optional constraints to filter recommendations (unused for physical)

    Returns:
        RecommendationSet with prioritized recommendations
    """
    recommendations = []

    # Fixed Level IV hazards cannot be controlled
    if risk.is_fixed_level_iv:
        recommendations.append(_recommend_fixed_level_iv(substance, risk, language))
        return RecommendationSet(
            current_risk_level=risk.risk_level.name,
            target_risk_level="IV",  # Cannot improve
            achievable=False,
            limitation_explanation="Fixed Level IV hazards cannot be reduced by control measures"
            if language == "en"
            else "固定レベルIVハザードは管理措置では低減できません",
            best_achievable_level="IV",
            recommendations=recommendations,
        )

    # Flammability recommendations
    if risk.hazard_type == "flammability":
        recommendations.extend(_recommend_flammability_controls(assessment_input, risk, language))

    # Oxidizer recommendations
    if risk.hazard_type == "oxidizer":
        recommendations.extend(_recommend_oxidizer_controls(assessment_input, risk, language))

    # General physical hazard recommendations
    recommendations.extend(_recommend_general_controls(assessment_input, risk, language))

    # Sort by effectiveness
    recommendations.sort(key=lambda r: -r.rcr_reduction_percent)

    return RecommendationSet(
        current_risk_level=risk.risk_level.name,
        target_risk_level="I",
        achievable=True,
        recommendations=recommendations,
    )


def _recommend_fixed_level_iv(
    substance: Substance,
    risk: PhysicalRisk,
    language: str,
) -> Recommendation:
    """Recommendation for fixed Level IV hazards."""
    if language == "ja":
        hazard_names = {
            "explosives": "爆発物",
            "pyrophoric_liquids": "自然発火性液体",
            "pyrophoric_solids": "自然発火性固体",
            "self_reactive": "自己反応性物質",
            "organic_peroxides": "有機過酸化物",
        }
        return Recommendation(
            action="物質の代替または工程の根本的見直し",
            action_ja="物質の代替または工程の根本的見直し",
            category=ActionCategory.ELIMINATION,
            effectiveness=EffectivenessLevel.HIGH,
            feasibility=Feasibility.VERY_DIFFICULT,
            current_risk_level="IV",
            predicted_risk_level="I",
            rcr_reduction_percent=100.0,
            parameter_affected="substance",
            current_value=hazard_names.get(risk.hazard_type, risk.hazard_type),
            new_value="代替物質/工程",
            coefficient_change="N/A",
            description=f"{hazard_names.get(risk.hazard_type, risk.hazard_type)}は本質的にレベルIVであり、管理措置では低減できません",
            description_ja=f"{hazard_names.get(risk.hazard_type, risk.hazard_type)}は本質的にレベルIVであり、管理措置では低減できません",
            implementation_notes="専門家との相談、代替物質の調査、工程変更の検討が必要",
            implementation_notes_ja="専門家との相談、代替物質の調査、工程変更の検討が必要",
            references=[get_reference("create_simple_design_7")],
        )
    else:
        hazard_names = {
            "explosives": "Explosives",
            "pyrophoric_liquids": "Pyrophoric liquids",
            "pyrophoric_solids": "Pyrophoric solids",
            "self_reactive": "Self-reactive substances",
            "organic_peroxides": "Organic peroxides",
        }
        return Recommendation(
            action="Substitute substance or fundamental process redesign",
            action_ja="物質の代替または工程の根本的見直し",
            category=ActionCategory.ELIMINATION,
            effectiveness=EffectivenessLevel.HIGH,
            feasibility=Feasibility.VERY_DIFFICULT,
            current_risk_level="IV",
            predicted_risk_level="I",
            rcr_reduction_percent=100.0,
            parameter_affected="substance",
            current_value=hazard_names.get(risk.hazard_type, risk.hazard_type),
            new_value="Alternative substance/process",
            coefficient_change="N/A",
            description=f"{hazard_names.get(risk.hazard_type, risk.hazard_type)} is inherently Level IV and cannot be reduced by controls",
            description_ja=f"{risk.hazard_type}は本質的にレベルIVであり、管理措置では低減できません",
            implementation_notes="Consult experts, investigate alternatives, consider process changes",
            implementation_notes_ja="専門家との相談、代替物質の調査、工程変更の検討が必要",
            references=[get_reference("create_simple_design_7")],
        )


def _recommend_flammability_controls(
    assessment_input: AssessmentInput,
    risk: PhysicalRisk,
    language: str,
) -> list[Recommendation]:
    """Generate flammability control recommendations."""
    recommendations = []

    # Temperature control if process temp is close to flash point
    if risk.temperature_margin is not None and risk.temperature_margin < 30:
        if language == "ja":
            recommendations.append(
                Recommendation(
                    action="作業温度の低下",
                    action_ja="作業温度の低下",
                    category=ActionCategory.ENGINEERING,
                    effectiveness=EffectivenessLevel.HIGH,
                    feasibility=Feasibility.MODERATE,
                    current_risk_level=risk.risk_level.name,
                    predicted_risk_level="II",
                    rcr_reduction_percent=50.0,
                    parameter_affected="process_temperature",
                    current_value=f"{risk.process_temperature}°C",
                    new_value=f"{risk.flash_point - 30}°C以下" if risk.flash_point else "低温",
                    coefficient_change="N/A",
                    description=f"引火点({risk.flash_point}°C)との温度マージンを確保",
                    description_ja=f"引火点({risk.flash_point}°C)との温度マージンを確保",
                    implementation_notes="冷却システムの導入、低温工程への変更",
                    implementation_notes_ja="冷却システムの導入、低温工程への変更",
                    references=[get_reference("create_simple_design_7")],
                )
            )
        else:
            recommendations.append(
                Recommendation(
                    action="Reduce process temperature",
                    action_ja="作業温度の低下",
                    category=ActionCategory.ENGINEERING,
                    effectiveness=EffectivenessLevel.HIGH,
                    feasibility=Feasibility.MODERATE,
                    current_risk_level=risk.risk_level.name,
                    predicted_risk_level="II",
                    rcr_reduction_percent=50.0,
                    parameter_affected="process_temperature",
                    current_value=f"{risk.process_temperature}°C",
                    new_value=f"Below {risk.flash_point - 30}°C" if risk.flash_point else "Lower",
                    coefficient_change="N/A",
                    description=f"Maintain adequate margin from flash point ({risk.flash_point}°C)",
                    description_ja=f"引火点({risk.flash_point}°C)との温度マージンを確保",
                    implementation_notes="Implement cooling system, switch to lower temperature process",
                    implementation_notes_ja="冷却システムの導入、低温工程への変更",
                    references=[get_reference("create_simple_design_7")],
                )
            )

    # Ignition source elimination
    if assessment_input.has_ignition_sources:
        if language == "ja":
            recommendations.append(
                Recommendation(
                    action="着火源の除去",
                    action_ja="着火源の除去",
                    category=ActionCategory.ENGINEERING,
                    effectiveness=EffectivenessLevel.HIGH,
                    feasibility=Feasibility.MODERATE,
                    current_risk_level=risk.risk_level.name,
                    predicted_risk_level="II",
                    rcr_reduction_percent=40.0,
                    parameter_affected="ignition_sources",
                    current_value="あり",
                    new_value="なし",
                    coefficient_change="N/A",
                    description="静電気、火花、高温表面などの着火源を排除",
                    description_ja="静電気、火花、高温表面などの着火源を排除",
                    implementation_notes="接地、防爆機器、火気厳禁エリアの設定",
                    implementation_notes_ja="接地、防爆機器、火気厳禁エリアの設定",
                    references=[get_reference("create_simple_design_7")],
                )
            )
        else:
            recommendations.append(
                Recommendation(
                    action="Eliminate ignition sources",
                    action_ja="着火源の除去",
                    category=ActionCategory.ENGINEERING,
                    effectiveness=EffectivenessLevel.HIGH,
                    feasibility=Feasibility.MODERATE,
                    current_risk_level=risk.risk_level.name,
                    predicted_risk_level="II",
                    rcr_reduction_percent=40.0,
                    parameter_affected="ignition_sources",
                    current_value="Present",
                    new_value="Eliminated",
                    coefficient_change="N/A",
                    description="Remove static, sparks, hot surfaces and other ignition sources",
                    description_ja="静電気、火花、高温表面などの着火源を排除",
                    implementation_notes="Grounding, explosion-proof equipment, no-flame zones",
                    implementation_notes_ja="接地、防爆機器、火気厳禁エリアの設定",
                    references=[get_reference("create_simple_design_7")],
                )
            )

    # Ventilation for vapor control
    if language == "ja":
        recommendations.append(
            Recommendation(
                action="換気による可燃性蒸気濃度の低減",
                action_ja="換気による可燃性蒸気濃度の低減",
                category=ActionCategory.ENGINEERING,
                effectiveness=EffectivenessLevel.MEDIUM,
                feasibility=Feasibility.EASY,
                current_risk_level=risk.risk_level.name,
                predicted_risk_level="II",
                rcr_reduction_percent=30.0,
                parameter_affected="ventilation",
                current_value="現状",
                new_value="防爆換気",
                coefficient_change="N/A",
                description="蒸気濃度をLEL以下に維持",
                description_ja="蒸気濃度をLEL以下に維持",
                implementation_notes="防爆型換気設備、濃度監視装置の設置",
                implementation_notes_ja="防爆型換気設備、濃度監視装置の設置",
                references=[get_reference("create_simple_design_7")],
            )
        )
    else:
        recommendations.append(
            Recommendation(
                action="Reduce flammable vapor concentration through ventilation",
                action_ja="換気による可燃性蒸気濃度の低減",
                category=ActionCategory.ENGINEERING,
                effectiveness=EffectivenessLevel.MEDIUM,
                feasibility=Feasibility.EASY,
                current_risk_level=risk.risk_level.name,
                predicted_risk_level="II",
                rcr_reduction_percent=30.0,
                parameter_affected="ventilation",
                current_value="Current",
                new_value="Explosion-proof ventilation",
                coefficient_change="N/A",
                description="Maintain vapor concentration below LEL",
                description_ja="蒸気濃度をLEL以下に維持",
                implementation_notes="Install explosion-proof ventilation, concentration monitoring",
                implementation_notes_ja="防爆型換気設備、濃度監視装置の設置",
                references=[get_reference("create_simple_design_7")],
            )
        )

    return recommendations


def _recommend_oxidizer_controls(
    assessment_input: AssessmentInput,
    risk: PhysicalRisk,
    language: str,
) -> list[Recommendation]:
    """Generate oxidizer control recommendations."""
    recommendations = []

    if language == "ja":
        recommendations.append(
            Recommendation(
                action="可燃物との分離保管",
                action_ja="可燃物との分離保管",
                category=ActionCategory.ADMINISTRATIVE,
                effectiveness=EffectivenessLevel.HIGH,
                feasibility=Feasibility.EASY,
                current_risk_level=risk.risk_level.name,
                predicted_risk_level="II",
                rcr_reduction_percent=50.0,
                parameter_affected="storage",
                current_value="現状",
                new_value="分離保管",
                coefficient_change="N/A",
                description="酸化性物質と可燃物を分離して保管",
                description_ja="酸化性物質と可燃物を分離して保管",
                implementation_notes="専用保管場所の設定、表示の明確化",
                implementation_notes_ja="専用保管場所の設定、表示の明確化",
                references=[get_reference("create_simple_design_7")],
            )
        )

        recommendations.append(
            Recommendation(
                action="有機物との接触防止",
                action_ja="有機物との接触防止",
                category=ActionCategory.ADMINISTRATIVE,
                effectiveness=EffectivenessLevel.HIGH,
                feasibility=Feasibility.MODERATE,
                current_risk_level=risk.risk_level.name,
                predicted_risk_level="II",
                rcr_reduction_percent=40.0,
                parameter_affected="contamination",
                current_value="リスクあり",
                new_value="管理済",
                coefficient_change="N/A",
                description="汚染防止と清掃手順の確立",
                description_ja="汚染防止と清掃手順の確立",
                implementation_notes="専用器具の使用、清掃手順の文書化",
                implementation_notes_ja="専用器具の使用、清掃手順の文書化",
                references=[get_reference("create_simple_design_7")],
            )
        )
    else:
        recommendations.append(
            Recommendation(
                action="Separate storage from combustibles",
                action_ja="可燃物との分離保管",
                category=ActionCategory.ADMINISTRATIVE,
                effectiveness=EffectivenessLevel.HIGH,
                feasibility=Feasibility.EASY,
                current_risk_level=risk.risk_level.name,
                predicted_risk_level="II",
                rcr_reduction_percent=50.0,
                parameter_affected="storage",
                current_value="Current",
                new_value="Segregated",
                coefficient_change="N/A",
                description="Store oxidizers separately from combustible materials",
                description_ja="酸化性物質と可燃物を分離して保管",
                implementation_notes="Dedicated storage area, clear labeling",
                implementation_notes_ja="専用保管場所の設定、表示の明確化",
                references=[get_reference("create_simple_design_7")],
            )
        )

        recommendations.append(
            Recommendation(
                action="Prevent contact with organic materials",
                action_ja="有機物との接触防止",
                category=ActionCategory.ADMINISTRATIVE,
                effectiveness=EffectivenessLevel.HIGH,
                feasibility=Feasibility.MODERATE,
                current_risk_level=risk.risk_level.name,
                predicted_risk_level="II",
                rcr_reduction_percent=40.0,
                parameter_affected="contamination",
                current_value="At risk",
                new_value="Controlled",
                coefficient_change="N/A",
                description="Establish contamination prevention and cleaning procedures",
                description_ja="汚染防止と清掃手順の確立",
                implementation_notes="Use dedicated equipment, document cleaning procedures",
                implementation_notes_ja="専用器具の使用、清掃手順の文書化",
                references=[get_reference("create_simple_design_7")],
            )
        )

    return recommendations


def _recommend_general_controls(
    assessment_input: AssessmentInput,
    risk: PhysicalRisk,
    language: str,
) -> list[Recommendation]:
    """Generate general physical hazard control recommendations."""
    recommendations = []

    if language == "ja":
        recommendations.append(
            Recommendation(
                action="取り扱い量の削減",
                action_ja="取り扱い量の削減",
                category=ActionCategory.ADMINISTRATIVE,
                effectiveness=EffectivenessLevel.MEDIUM,
                feasibility=Feasibility.MODERATE,
                current_risk_level=risk.risk_level.name,
                predicted_risk_level="II",
                rcr_reduction_percent=30.0,
                parameter_affected="amount",
                current_value="現状量",
                new_value="最小限",
                coefficient_change="N/A",
                description="作業場の保管量を必要最小限に抑える",
                description_ja="作業場の保管量を必要最小限に抑える",
                implementation_notes="ジャストインタイム供給、小分け作業",
                implementation_notes_ja="ジャストインタイム供給、小分け作業",
                references=[get_reference("create_simple_design_7")],
            )
        )

        recommendations.append(
            Recommendation(
                action="緊急時対応体制の整備",
                action_ja="緊急時対応体制の整備",
                category=ActionCategory.ADMINISTRATIVE,
                effectiveness=EffectivenessLevel.LOW,
                feasibility=Feasibility.EASY,
                current_risk_level=risk.risk_level.name,
                predicted_risk_level=risk.risk_level.name,
                rcr_reduction_percent=10.0,
                parameter_affected="emergency_response",
                current_value="未整備",
                new_value="整備済",
                coefficient_change="N/A",
                description="消火設備、避難経路、緊急連絡体制の整備",
                description_ja="消火設備、避難経路、緊急連絡体制の整備",
                implementation_notes="定期訓練、SDS確認、適切な消火剤の配備",
                implementation_notes_ja="定期訓練、SDS確認、適切な消火剤の配備",
                references=[get_reference("create_simple_design_7")],
            )
        )
    else:
        recommendations.append(
            Recommendation(
                action="Reduce quantity handled",
                action_ja="取り扱い量の削減",
                category=ActionCategory.ADMINISTRATIVE,
                effectiveness=EffectivenessLevel.MEDIUM,
                feasibility=Feasibility.MODERATE,
                current_risk_level=risk.risk_level.name,
                predicted_risk_level="II",
                rcr_reduction_percent=30.0,
                parameter_affected="amount",
                current_value="Current amount",
                new_value="Minimum",
                coefficient_change="N/A",
                description="Limit workplace storage to minimum necessary",
                description_ja="作業場の保管量を必要最小限に抑える",
                implementation_notes="Just-in-time supply, portioning",
                implementation_notes_ja="ジャストインタイム供給、小分け作業",
                references=[get_reference("create_simple_design_7")],
            )
        )

        recommendations.append(
            Recommendation(
                action="Establish emergency response procedures",
                action_ja="緊急時対応体制の整備",
                category=ActionCategory.ADMINISTRATIVE,
                effectiveness=EffectivenessLevel.LOW,
                feasibility=Feasibility.EASY,
                current_risk_level=risk.risk_level.name,
                predicted_risk_level=risk.risk_level.name,
                rcr_reduction_percent=10.0,
                parameter_affected="emergency_response",
                current_value="Not established",
                new_value="Established",
                coefficient_change="N/A",
                description="Fire suppression, evacuation routes, emergency contacts",
                description_ja="消火設備、避難経路、緊急連絡体制の整備",
                implementation_notes="Regular drills, SDS review, appropriate extinguishers",
                implementation_notes_ja="定期訓練、SDS確認、適切な消火剤の配備",
                references=[get_reference("create_simple_design_7")],
            )
        )

    return recommendations
