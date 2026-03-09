"""
Limitation analysis for risk assessment.

Explains WHY a certain risk level cannot be achieved and what
factors limit the minimum achievable risk.

Reference: CREATE-SIMPLE Design v3.1.1, Section 3.3 (minimum floor) and 5.3.3 (ACRmax)
"""

from typing import Optional

from ..models.assessment import AssessmentInput, AssessmentMode, VentilationLevel
from ..models.substance import Substance, PropertyType
from ..models.risk import RiskLevel
from ..models.explanation import Limitation, MinimumAchievableResult
from ..calculators.constants import (
    MIN_EXPOSURE_LIQUID,
    MIN_EXPOSURE_SOLID,
    ACRMAX_VALUES,
)
from ..references.catalog import get_reference


def explain_limitations(
    assessment_input: AssessmentInput,
    substance: Substance,
    current_rcr: float,
    target_level: RiskLevel = RiskLevel.I,
    language: str = "en",
) -> list[Limitation]:
    """
    Identify and explain all factors that limit achieving a target risk level.

    Args:
        assessment_input: The assessment input parameters
        substance: The substance being assessed
        current_rcr: The current RCR value
        target_level: The desired risk level (default: Level I)
        language: "en" or "ja"

    Returns:
        List of Limitation objects explaining each limiting factor
    """
    limitations = []

    # Check minimum exposure floor limitation
    floor_limitation = _check_exposure_floor_limitation(
        assessment_input, substance, target_level, language
    )
    if floor_limitation:
        limitations.append(floor_limitation)

    # Check ACRmax limitation for carcinogens/mutagens
    acrmax_limitation = _check_acrmax_limitation(substance, target_level, language)
    if acrmax_limitation:
        limitations.append(acrmax_limitation)

    # Check fixed Level IV hazards (physical)
    fixed_limitation = _check_fixed_level_iv(substance, language)
    if fixed_limitation:
        limitations.append(fixed_limitation)

    # Check RPE availability limitation (RA Sheet mode)
    rpe_limitation = _check_rpe_availability(assessment_input, language)
    if rpe_limitation:
        limitations.append(rpe_limitation)

    return limitations


def _check_exposure_floor_limitation(
    assessment_input: AssessmentInput,
    substance: Substance,
    target_level: RiskLevel,
    language: str,
) -> Optional[Limitation]:
    """Check if minimum exposure floor prevents achieving target level."""
    is_liquid = substance.property_type == PropertyType.LIQUID
    min_floor = MIN_EXPOSURE_LIQUID if is_liquid else MIN_EXPOSURE_SOLID
    unit = "ppm" if is_liquid else "mg/m³"

    # Get the effective OEL
    oel = substance.oel.get_best_oel()
    if oel is None:
        return None

    # Calculate minimum RCR with floor
    min_rcr = min_floor / oel

    # Get target threshold
    target_threshold = {
        RiskLevel.I: 0.1,
        RiskLevel.II: 1.0,
        RiskLevel.III: 10.0,
        RiskLevel.IV: float("inf"),
    }[target_level]

    if min_rcr > target_threshold:
        if language == "ja":
            return Limitation(
                factor_name="最小ばく露濃度下限",
                factor_name_ja="最小ばく露濃度下限",
                description=f"CREATE-SIMPLEは{min_floor} {unit}未満のばく露を推定できません",
                description_ja=f"CREATE-SIMPLEは{min_floor} {unit}未満のばく露を推定できません",
                current_value=min_floor,
                limiting_value=oel * target_threshold,
                impact=f"最小RCRは{min_rcr:.4f}となり、レベル{target_level.name}({target_threshold}以下)は達成できません",
                impact_ja=f"最小RCRは{min_rcr:.4f}となり、レベル{target_level.name}({target_threshold}以下)は達成できません",
                reference=get_reference("create_simple_design_3_3_floor"),
                alternatives=[
                    "実測によるばく露評価",
                    "より毒性の低い代替物質の検討",
                    "工程の密閉化による発散抑制",
                ],
            )
        else:
            return Limitation(
                factor_name="Minimum Exposure Floor",
                factor_name_ja="最小ばく露濃度下限",
                description=f"CREATE-SIMPLE cannot estimate exposure below {min_floor} {unit}",
                description_ja=f"CREATE-SIMPLEは{min_floor} {unit}未満のばく露を推定できません",
                current_value=min_floor,
                limiting_value=oel * target_threshold,
                impact=f"Minimum RCR is {min_rcr:.4f}, so Level {target_level.name} (≤{target_threshold}) cannot be achieved",
                impact_ja=f"最小RCRは{min_rcr:.4f}となり、レベル{target_level.name}({target_threshold}以下)は達成できません",
                reference=get_reference("create_simple_design_3_3_floor"),
                alternatives=[
                    "Conduct actual exposure monitoring",
                    "Consider substitution with less toxic substances",
                    "Implement enclosed processing systems",
                ],
            )

    return None


def _check_acrmax_limitation(
    substance: Substance,
    target_level: RiskLevel,
    language: str,
) -> Optional[Limitation]:
    """Check if ACRmax for carcinogens limits achieving target level."""
    # Determine hazard level from GHS classification
    hazard_level = _get_hazard_level(substance)
    if hazard_level not in ACRMAX_VALUES:
        return None

    acrmax = ACRMAX_VALUES[hazard_level]
    is_liquid = substance.property_type == PropertyType.LIQUID
    min_floor = MIN_EXPOSURE_LIQUID if is_liquid else MIN_EXPOSURE_SOLID

    # Calculate minimum RCR with ACRmax
    min_rcr = min_floor / acrmax

    target_threshold = {
        RiskLevel.I: 0.1,
        RiskLevel.II: 1.0,
        RiskLevel.III: 10.0,
        RiskLevel.IV: float("inf"),
    }[target_level]

    if min_rcr > target_threshold:
        hazard_names = {
            "HL5": "Carcinogen 1A/1B",
            "HL4": "Carcinogen 2 / Mutagen 1A/1B/2",
            "HL3": "Respiratory sensitizer / STOT RE 1",
        }

        if language == "ja":
            hazard_names_ja = {
                "HL5": "発がん性1A/1B",
                "HL4": "発がん性2 / 変異原性1A/1B/2",
                "HL3": "呼吸器感作性 / 特定標的臓器毒性(反復)1",
            }
            return Limitation(
                factor_name="管理目標濃度 (ACRmax)",
                factor_name_ja="管理目標濃度 (ACRmax)",
                description=f"この物質は{hazard_names_ja.get(hazard_level, hazard_level)}に分類され、ACRmax={acrmax} ppmが適用されます",
                description_ja=f"この物質は{hazard_names_ja.get(hazard_level, hazard_level)}に分類され、ACRmax={acrmax} ppmが適用されます",
                current_value=acrmax,
                limiting_value=min_floor / target_threshold,
                impact=f"最小RCRは{min_rcr:.4f}となり、レベル{target_level.name}は達成できません",
                impact_ja=f"最小RCRは{min_rcr:.4f}となり、レベル{target_level.name}は達成できません",
                reference=get_reference("create_simple_design_2_2"),
                alternatives=[
                    "代替物質への置換",
                    "完全密閉系での取り扱い",
                    "自動化・遠隔操作の導入",
                ],
            )
        else:
            return Limitation(
                factor_name="Management Target Concentration (ACRmax)",
                factor_name_ja="管理目標濃度 (ACRmax)",
                description=f"Classified as {hazard_names.get(hazard_level, hazard_level)}, ACRmax of {acrmax} ppm applies",
                description_ja=f"この物質は{hazard_level}に分類され、ACRmax={acrmax} ppmが適用されます",
                current_value=acrmax,
                limiting_value=min_floor / target_threshold,
                impact=f"Minimum RCR is {min_rcr:.4f}, Level {target_level.name} cannot be achieved",
                impact_ja=f"最小RCRは{min_rcr:.4f}となり、レベル{target_level.name}は達成できません",
                reference=get_reference("create_simple_design_2_2"),
                alternatives=[
                    "Substitute with less hazardous substance",
                    "Handle only in completely enclosed systems",
                    "Implement automation and remote operation",
                ],
            )

    return None


def _check_fixed_level_iv(
    substance: Substance,
    language: str,
) -> Optional[Limitation]:
    """Check for fixed Level IV physical hazards."""
    ghs = substance.ghs

    # Check each fixed Level IV hazard type
    fixed_hazards = []

    if ghs.explosives in ["1.1", "1.2", "1.3", "Div 1.1", "Div 1.2", "Div 1.3"]:
        fixed_hazards.append(("explosives", ghs.explosives))
    if ghs.pyrophoric_liquids in ["1", "Category 1"]:
        fixed_hazards.append(("pyrophoric_liquids", ghs.pyrophoric_liquids))
    if ghs.pyrophoric_solids in ["1", "Category 1"]:
        fixed_hazards.append(("pyrophoric_solids", ghs.pyrophoric_solids))
    if ghs.self_reactive in ["A", "B", "Type A", "Type B"]:
        fixed_hazards.append(("self_reactive", ghs.self_reactive))
    if ghs.organic_peroxides in ["A", "B", "Type A", "Type B"]:
        fixed_hazards.append(("organic_peroxides", ghs.organic_peroxides))

    if not fixed_hazards:
        return None

    hazard_type, category = fixed_hazards[0]

    if language == "ja":
        hazard_names = {
            "explosives": "爆発物",
            "pyrophoric_liquids": "自然発火性液体",
            "pyrophoric_solids": "自然発火性固体",
            "self_reactive": "自己反応性物質",
            "organic_peroxides": "有機過酸化物",
        }
        return Limitation(
            factor_name="固定レベルIV危険性",
            factor_name_ja="固定レベルIV危険性",
            description=f"{hazard_names.get(hazard_type, hazard_type)}（区分{category}）は本質的にレベルIVです",
            description_ja=f"{hazard_names.get(hazard_type, hazard_type)}（区分{category}）は本質的にレベルIVです",
            current_value=4.0,
            limiting_value=4.0,
            impact="管理措置によるリスク低減は不可能です",
            impact_ja="管理措置によるリスク低減は不可能です",
            reference=get_reference("create_simple_design_7"),
            alternatives=[
                "物質の代替",
                "工程の根本的見直し",
                "取り扱いの中止",
            ],
        )
    else:
        hazard_names = {
            "explosives": "Explosives",
            "pyrophoric_liquids": "Pyrophoric liquids",
            "pyrophoric_solids": "Pyrophoric solids",
            "self_reactive": "Self-reactive substances",
            "organic_peroxides": "Organic peroxides",
        }
        return Limitation(
            factor_name="Fixed Level IV Hazard",
            factor_name_ja="固定レベルIV危険性",
            description=f"{hazard_names.get(hazard_type, hazard_type)} Category {category} is inherently Level IV",
            description_ja=f"{hazard_type}（区分{category}）は本質的にレベルIVです",
            current_value=4.0,
            limiting_value=4.0,
            impact="No control measures can reduce this risk",
            impact_ja="管理措置によるリスク低減は不可能です",
            reference=get_reference("create_simple_design_7"),
            alternatives=[
                "Substitute the substance",
                "Fundamental process redesign",
                "Discontinue handling",
            ],
        )


def _check_rpe_availability(
    assessment_input: AssessmentInput,
    language: str,
) -> Optional[Limitation]:
    """Check if RA Sheet mode limits RPE options."""
    if assessment_input.mode != AssessmentMode.RA_SHEET:
        return None

    if language == "ja":
        return Limitation(
            factor_name="呼吸用保護具の制限",
            factor_name_ja="呼吸用保護具の制限",
            description="リスクアセスメントシートモードでは呼吸用保護具を選択できません",
            description_ja="リスクアセスメントシートモードでは呼吸用保護具を選択できません",
            current_value=1.0,
            limiting_value=1.0,
            impact="保護具によるばく露低減を考慮できません",
            impact_ja="保護具によるばく露低減を考慮できません",
            reference=get_reference("create_simple_vba_ra_sheet"),
            alternatives=[
                "実施レポートモードに切り替える",
                "工学的対策を優先する",
            ],
        )
    else:
        return Limitation(
            factor_name="RPE Availability",
            factor_name_ja="呼吸用保護具の制限",
            description="RA Sheet mode does not allow RPE selection",
            description_ja="リスクアセスメントシートモードでは呼吸用保護具を選択できません",
            current_value=1.0,
            limiting_value=1.0,
            impact="Cannot account for RPE exposure reduction",
            impact_ja="保護具によるばく露低減を考慮できません",
            reference=get_reference("create_simple_vba_ra_sheet"),
            alternatives=[
                "Switch to Report mode",
                "Prioritize engineering controls",
            ],
        )


def _get_hazard_level(substance: Substance) -> Optional[str]:
    """Determine hazard level from GHS classification."""
    ghs = substance.ghs

    # HL5: Carcinogen 1A/1B
    if ghs.carcinogenicity in ["1A", "1B", "Category 1A", "Category 1B"]:
        return "HL5"

    # HL4: Carcinogen 2, Mutagen 1A/1B/2
    if ghs.carcinogenicity in ["2", "Category 2"]:
        return "HL4"
    if ghs.germ_cell_mutagenicity in ["1A", "1B", "2", "Category 1A", "Category 1B", "Category 2"]:
        return "HL4"

    # HL3: Respiratory sensitizer, STOT RE 1
    if ghs.respiratory_sensitization in [
        "1",
        "1A",
        "1B",
        "Category 1",
        "Category 1A",
        "Category 1B",
    ]:
        return "HL3"
    if ghs.stot_repeated in ["1", "Category 1"]:
        return "HL3"

    return None


def find_minimum_achievable(
    assessment_input: AssessmentInput,
    substance: Substance,
    language: str = "en",
) -> MinimumAchievableResult:
    """
    Calculate the minimum achievable risk level with maximum controls.

    This function determines the best possible outcome assuming all
    available control measures are applied to their maximum extent.

    Args:
        assessment_input: The assessment input parameters
        substance: The substance being assessed
        language: "en" or "ja"

    Returns:
        MinimumAchievableResult with best possible outcome
    """
    # Calculate minimum exposure with best controls
    is_liquid = substance.property_type == PropertyType.LIQUID
    min_floor = MIN_EXPOSURE_LIQUID if is_liquid else MIN_EXPOSURE_SOLID

    # Get effective OEL or ACRmax
    oel = substance.oel.get_best_oel()
    hazard_level = _get_hazard_level(substance)
    acrmax = ACRMAX_VALUES.get(hazard_level) if hazard_level else None
    effective_oel = min(oel, acrmax) if acrmax and oel else (oel or acrmax)

    if effective_oel is None:
        if language == "ja":
            return MinimumAchievableResult(
                best_possible_rcr=float("inf"),
                best_possible_level=4,
                explanation="ばく露限界値が設定されていないため、リスク評価ができません",
                explanation_ja="ばく露限界値が設定されていないため、リスク評価ができません",
                alternatives=["ばく露限界値の設定を確認してください"],
            )
        else:
            return MinimumAchievableResult(
                best_possible_rcr=float("inf"),
                best_possible_level=4,
                explanation="No OEL available, cannot assess risk",
                explanation_ja="ばく露限界値が設定されていないため、リスク評価ができません",
                alternatives=["Verify OEL settings"],
            )

    # Calculate minimum RCR
    min_rcr = min_floor / effective_oel
    best_level = RiskLevel.from_rcr(min_rcr).value

    # Get all limitations
    limitations = explain_limitations(assessment_input, substance, min_rcr, RiskLevel.I, language)

    # Required changes to achieve minimum
    required_changes = []
    if assessment_input.ventilation != VentilationLevel.SEALED:
        if language == "ja":
            required_changes.append("換気を密閉系に変更")
        else:
            required_changes.append("Change ventilation to sealed system")

    # Generate explanation
    if language == "ja":
        if best_level == 1:
            explanation = f"最大限の対策を講じることで、レベルI（RCR={min_rcr:.4f}）が達成可能です"
        else:
            explanation = f"最大限の対策を講じても、レベル{RiskLevel(best_level).name}（RCR={min_rcr:.4f}）までしか達成できません"
    else:
        if best_level == 1:
            explanation = f"With maximum controls, Level I (RCR={min_rcr:.4f}) is achievable"
        else:
            explanation = f"Even with maximum controls, only Level {RiskLevel(best_level).name} (RCR={min_rcr:.4f}) is achievable"

    return MinimumAchievableResult(
        best_possible_rcr=min_rcr,
        best_possible_level=best_level,
        limiting_factors=limitations,
        explanation=explanation,
        explanation_ja=explanation if language == "ja" else "",
        required_changes=required_changes,
        alternatives=[
            "Consider substance substitution" if language == "en" else "代替物質の検討",
            "Conduct actual exposure measurements" if language == "en" else "実測によるばく露評価",
        ],
    )
