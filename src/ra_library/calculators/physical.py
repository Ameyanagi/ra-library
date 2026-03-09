"""
Physical hazard risk assessment calculation.

Reference: CREATE-SIMPLE Design v3.1.1, Section 7
VBA Reference: modCalc.bas CalculateExplosivesRisk through CalculateInertExplosivesRisk

This module implements comprehensive physical hazard assessment following
the CREATE-SIMPLE methodology:
1. Determine provisional risk level (暫定RL) from GHS category + amount level
2. Adjust for work conditions (ignition sources, explosive atmosphere, etc.)
3. Convert provisional level (1-5) to final risk level (I-IV)
"""

from dataclasses import dataclass
from typing import Optional

from ..models.substance import Substance, GHSClassification
from ..models.assessment import AssessmentInput, AmountLevel
from ..models.risk import RiskLevel, PhysicalRisk
from ..models.explanation import CalculationExplanation, CalculationStep, Limitation


# Amount level to index mapping (for lookup tables)
AMOUNT_LEVEL_INDEX = {
    AmountLevel.LARGE: 0,   # kL, ton
    AmountLevel.MEDIUM: 1,  # ≥1L, ≥1kg
    AmountLevel.SMALL: 2,   # 100mL-1L, 100g-1kg
    AmountLevel.MINUTE: 3,  # 10mL-100mL, 10g-100g
    AmountLevel.TRACE: 4,   # <10mL, <10g
}


def _provisional_to_risk_level(provisional: int) -> RiskLevel:
    """
    Convert provisional risk level (1-5) to final RiskLevel (I-IV).

    Reference: CREATE-SIMPLE Design v3.1.1, Section 7.2
    """
    if provisional >= 4:
        return RiskLevel.IV
    elif provisional == 3:
        return RiskLevel.III
    elif provisional == 2:
        return RiskLevel.II
    else:
        return RiskLevel.I


def _parse_ghs_category(value: Optional[str]) -> Optional[str]:
    """Parse GHS category value, handling various formats."""
    if value is None or value == "" or value == "-9999":
        return None
    # Strip "Category " prefix if present
    return str(value).replace("Category ", "").replace("Type ", "").strip()


@dataclass
class PhysicalHazardResult:
    """Result from individual hazard assessment."""
    hazard_type: str
    hazard_type_ja: str
    provisional_level: int
    risk_level: RiskLevel
    description: str
    description_ja: str
    is_fixed_level_iv: bool = False


# =============================================================================
# Individual Hazard Assessment Functions (following VBA modCalc.bas)
# =============================================================================

def assess_explosives(ghs: GHSClassification) -> Optional[PhysicalHazardResult]:
    """
    Assess explosives risk.

    VBA Reference: CalculateExplosivesRisk (lines 837-845)
    All explosives (Div 1.1-1.6) are Level IV regardless of amount.
    """
    cat = _parse_ghs_category(ghs.explosives)
    if cat is None:
        return None

    return PhysicalHazardResult(
        hazard_type="explosives",
        hazard_type_ja="爆発物",
        provisional_level=5,
        risk_level=RiskLevel.IV,
        description="Explosives - consult specialist. Handle according to SDS.",
        description_ja="専門家または購入元に取り扱い方等を確認・相談のうえSDS等に従い取り扱うこと。",
        is_fixed_level_iv=True,
    )


def assess_flammable_gas(
    ghs: GHSClassification,
    amount_level: AmountLevel,
    ignition_removed: bool,
    explosive_atmosphere_prevented: bool,
) -> Optional[PhysicalHazardResult]:
    """
    Assess flammable/combustible gas risk.

    VBA Reference: CalculateFlamGasRisk (lines 848-906)
    """
    cat = _parse_ghs_category(ghs.flammable_gases)
    if cat is None:
        return None

    idx = AMOUNT_LEVEL_INDEX[amount_level]

    # Provisional RL table: [Category 1, Category 2] x [amount levels]
    # Category 1: [5, 5, 5, 4, 3]
    # Category 2: [5, 5, 4, 3, 2]
    if cat == "1":
        provisional = [5, 5, 5, 4, 3][idx]
    elif cat == "2":
        provisional = [5, 5, 4, 3, 2][idx]
    else:
        return None

    # Adjustments
    if ignition_removed:
        provisional -= 1
    if explosive_atmosphere_prevented:
        provisional -= 1

    provisional = max(1, provisional)

    return PhysicalHazardResult(
        hazard_type="flammable_gas",
        hazard_type_ja="可燃性ガス",
        provisional_level=provisional,
        risk_level=_provisional_to_risk_level(provisional),
        description=f"Flammable gas Category {cat}",
        description_ja=f"可燃性ガス 区分{cat}",
    )


def assess_aerosol(
    ghs: GHSClassification,
    amount_level: AmountLevel,
    ignition_removed: bool,
    explosive_atmosphere_prevented: bool,
) -> Optional[PhysicalHazardResult]:
    """
    Assess aerosol risk.

    VBA Reference: CalculateAerosolRisk (lines 908-976)
    """
    cat = _parse_ghs_category(ghs.flammable_aerosols)
    if cat is None:
        return None

    idx = AMOUNT_LEVEL_INDEX[amount_level]

    # Provisional RL table: [Cat 1, Cat 2, Cat 3] x [amount levels]
    # Category 1: [5, 5, 5, 4, 3]
    # Category 2: [5, 5, 4, 4, 3]
    # Category 3: [2, 2, 2, 1, 1]
    if cat == "1":
        provisional = [5, 5, 5, 4, 3][idx]
    elif cat == "2":
        provisional = [5, 5, 4, 4, 3][idx]
    elif cat == "3":
        provisional = [2, 2, 2, 1, 1][idx]
    else:
        return None

    # Adjustments apply to ALL categories per VBA
    if ignition_removed:
        provisional -= 1
    if explosive_atmosphere_prevented:
        provisional -= 1

    provisional = max(1, provisional)

    return PhysicalHazardResult(
        hazard_type="aerosol",
        hazard_type_ja="エアゾール",
        provisional_level=provisional,
        risk_level=_provisional_to_risk_level(provisional),
        description=f"Aerosol Category {cat}",
        description_ja=f"エアゾール 区分{cat}",
    )


def assess_oxidizing_gas(
    ghs: GHSClassification,
    amount_level: AmountLevel,
) -> Optional[PhysicalHazardResult]:
    """
    Assess oxidizing gas risk.

    VBA Reference: CalculateOxGasRisk (lines 977-1011)
    """
    cat = _parse_ghs_category(ghs.oxidizing_gases)
    if cat is None:
        return None

    idx = AMOUNT_LEVEL_INDEX[amount_level]

    # Provisional RL: [5, 4, 3, 2, 2]
    provisional = [5, 4, 3, 2, 2][idx]

    return PhysicalHazardResult(
        hazard_type="oxidizing_gas",
        hazard_type_ja="酸化性ガス",
        provisional_level=provisional,
        risk_level=_provisional_to_risk_level(provisional),
        description=f"Oxidizing gas Category {cat}",
        description_ja=f"酸化性ガス 区分{cat}",
    )


def assess_gases_under_pressure(
    ghs: GHSClassification,
    amount_level: AmountLevel,
) -> Optional[PhysicalHazardResult]:
    """
    Assess gases under pressure risk.

    VBA Reference: CalculateGasesUnderPressureRisk (lines 1013-1048)
    """
    cat = _parse_ghs_category(ghs.gases_under_pressure)
    if cat is None:
        return None

    idx = AMOUNT_LEVEL_INDEX[amount_level]

    # Provisional RL: [2, 2, 2, 1, 1]
    provisional = [2, 2, 2, 1, 1][idx]

    return PhysicalHazardResult(
        hazard_type="gases_under_pressure",
        hazard_type_ja="高圧ガス",
        provisional_level=provisional,
        risk_level=_provisional_to_risk_level(provisional),
        description="Pressurized gas - refer to High Pressure Gas Safety Act",
        description_ja="圧力に応じて法令（高圧ガス保安法等）を参照のうえ対応すること。",
    )


def assess_flammable_liquid(
    ghs: GHSClassification,
    amount_level: AmountLevel,
    flash_point: Optional[float],
    process_temperature: Optional[float],
    ignition_removed: bool,
    explosive_atmosphere_prevented: bool,
) -> Optional[PhysicalHazardResult]:
    """
    Assess flammable liquid risk.

    VBA Reference: CalculateFlamLiqRisk (lines 1050-1138)

    Key logic:
    1. If process_temp + 10°C safety margin > flash_point → use highest risk row
    2. Otherwise use GHS category-based assessment
    3. Adjust for ignition sources and explosive atmosphere
    """
    cat = _parse_ghs_category(ghs.flammable_liquids)

    # Need either GHS category or flash point
    if cat is None and flash_point is None:
        return None

    idx = AMOUNT_LEVEL_INDEX[amount_level]

    # Check if process temperature exceeds flash point (with 10°C safety margin)
    process_temp_exceeds_flash = False
    effective_flash_point = flash_point

    # If no flash point data, estimate from category (conservative)
    if flash_point is None and cat is not None:
        if cat in ["1", "2", "3"]:
            effective_flash_point = 23.0  # Conservative for Cat 1-3
        elif cat == "4":
            effective_flash_point = 60.0  # Cat 4: 60°C

    if process_temperature is not None and effective_flash_point is not None:
        # VBA: direct comparison without safety margin
        # Note: Design doc mentions 10°C margin but VBA doesn't implement it
        if process_temperature > effective_flash_point:
            process_temp_exceeds_flash = True

    # Provisional RL tables
    # ProcessTemp > FlashPoint or Category 1,2: [5, 5, 4, 3, 2]
    # Category 3: [4, 3, 2, 2, 2]
    # Category 4: [3, 2, 2, 2, 1]

    if process_temp_exceeds_flash or cat in ["1", "2"]:
        provisional = [5, 5, 4, 3, 2][idx]
        desc = "Process temp ≥ flash point" if process_temp_exceeds_flash else f"Flammable liquid Category {cat}"
        desc_ja = "取扱温度≧引火点" if process_temp_exceeds_flash else f"引火性液体 区分{cat}"
    elif cat == "3":
        provisional = [4, 3, 2, 2, 2][idx]
        desc = f"Flammable liquid Category {cat}"
        desc_ja = f"引火性液体 区分{cat}"
    elif cat == "4":
        provisional = [3, 2, 2, 2, 1][idx]
        desc = f"Flammable liquid Category {cat}"
        desc_ja = f"引火性液体 区分{cat}"
    else:
        return None

    # Adjustments
    if ignition_removed:
        provisional -= 1
    if explosive_atmosphere_prevented:
        provisional -= 1

    provisional = max(1, provisional)

    return PhysicalHazardResult(
        hazard_type="flammable_liquid",
        hazard_type_ja="引火性液体",
        provisional_level=provisional,
        risk_level=_provisional_to_risk_level(provisional),
        description=desc,
        description_ja=desc_ja,
    )


def assess_flammable_solid(
    ghs: GHSClassification,
    amount_level: AmountLevel,
    dustiness_low: bool,
    ignition_removed: bool,
    explosive_atmosphere_prevented: bool,
) -> Optional[PhysicalHazardResult]:
    """
    Assess flammable solid risk.

    VBA Reference: CalculateFlamSolRisk (lines 1140-1205)
    """
    cat = _parse_ghs_category(ghs.flammable_solids)
    if cat is None:
        return None

    idx = AMOUNT_LEVEL_INDEX[amount_level]

    # Provisional RL: [5, 5, 4, 3, 2] for both categories
    provisional = [5, 5, 4, 3, 2][idx]

    # Adjustments
    if cat == "1":
        # Category 1: ignition + atmosphere
        if ignition_removed:
            provisional -= 1
        if explosive_atmosphere_prevented:
            provisional -= 1
    elif cat == "2":
        # Category 2: ignition + atmosphere + dustiness
        adjustments = sum([ignition_removed, explosive_atmosphere_prevented, dustiness_low])
        provisional -= adjustments

    provisional = max(1, provisional)

    return PhysicalHazardResult(
        hazard_type="flammable_solid",
        hazard_type_ja="可燃性固体",
        provisional_level=provisional,
        risk_level=_provisional_to_risk_level(provisional),
        description=f"Flammable solid Category {cat}",
        description_ja=f"可燃性固体 区分{cat}",
    )


def assess_self_reactive(
    ghs: GHSClassification,
    amount_level: AmountLevel,
) -> Optional[PhysicalHazardResult]:
    """
    Assess self-reactive substance risk.

    VBA Reference: CalculateSelfReactRisk (lines 1207-1246)
    """
    cat = _parse_ghs_category(ghs.self_reactive)
    if cat is None:
        return None

    idx = AMOUNT_LEVEL_INDEX[amount_level]

    # Type A-E: Always Level IV (provisional 5)
    # Note: VBA doesn't handle Type F, but per GHS it should be amount-dependent like G
    if cat in ["A", "B", "C", "D", "E"]:
        return PhysicalHazardResult(
            hazard_type="self_reactive",
            hazard_type_ja="自己反応性化学品",
            provisional_level=5,
            risk_level=RiskLevel.IV,
            description=f"Self-reactive Type {cat} - consult specialist",
            description_ja="専門家または購入元に取り扱い方等を確認・相談のうえSDS等に従い取り扱うこと。",
            is_fixed_level_iv=True,
        )
    elif cat in ["F", "G"]:
        # Type F and G: Amount-dependent
        provisional = [5, 4, 3, 2, 1][idx]
        return PhysicalHazardResult(
            hazard_type="self_reactive",
            hazard_type_ja="自己反応性化学品",
            provisional_level=provisional,
            risk_level=_provisional_to_risk_level(provisional),
            description=f"Self-reactive Type {cat}",
            description_ja=f"自己反応性化学品 タイプ{cat}",
        )

    return None


def assess_pyrophoric_liquid(ghs: GHSClassification) -> Optional[PhysicalHazardResult]:
    """
    Assess pyrophoric liquid risk.

    VBA Reference: CalculatePyrLiqRisk (lines 1248-1259)
    Always Level IV regardless of amount.
    """
    cat = _parse_ghs_category(ghs.pyrophoric_liquids)
    if cat is None:
        return None

    return PhysicalHazardResult(
        hazard_type="pyrophoric_liquid",
        hazard_type_ja="自然発火性液体",
        provisional_level=5,
        risk_level=RiskLevel.IV,
        description="Pyrophoric liquid - consult specialist",
        description_ja="専門家または購入元に取り扱い方等を確認・相談のうえSDS等に従い取り扱うこと。",
        is_fixed_level_iv=True,
    )


def assess_pyrophoric_solid(ghs: GHSClassification) -> Optional[PhysicalHazardResult]:
    """
    Assess pyrophoric solid risk.

    VBA Reference: CalculatePyrSolRisk (lines 1261-1271)
    Always Level IV regardless of amount.
    """
    cat = _parse_ghs_category(ghs.pyrophoric_solids)
    if cat is None:
        return None

    return PhysicalHazardResult(
        hazard_type="pyrophoric_solid",
        hazard_type_ja="自然発火性固体",
        provisional_level=5,
        risk_level=RiskLevel.IV,
        description="Pyrophoric solid - consult specialist",
        description_ja="専門家または購入元に取り扱い方等を確認・相談のうえSDS等に従い取り扱うこと。",
        is_fixed_level_iv=True,
    )


def assess_self_heating(
    ghs: GHSClassification,
    amount_level: AmountLevel,
    air_water_contact_prevented: bool,
) -> Optional[PhysicalHazardResult]:
    """
    Assess self-heating substance risk.

    VBA Reference: CalculateselfHeatRisk (lines 1272-1310)
    """
    cat = _parse_ghs_category(ghs.self_heating)
    if cat is None:
        return None

    idx = AMOUNT_LEVEL_INDEX[amount_level]

    # Provisional RL: [5, 4, 3, 2, 2]
    provisional = [5, 4, 3, 2, 2][idx]

    # Adjustment
    if air_water_contact_prevented:
        provisional -= 1

    provisional = max(1, provisional)

    return PhysicalHazardResult(
        hazard_type="self_heating",
        hazard_type_ja="自己発熱性化学品",
        provisional_level=provisional,
        risk_level=_provisional_to_risk_level(provisional),
        description=f"Self-heating substance Category {cat}",
        description_ja=f"自己発熱性化学品 区分{cat}",
    )


def assess_water_reactive(
    ghs: GHSClassification,
    amount_level: AmountLevel,
    ignition_removed: bool,
    air_water_contact_prevented: bool,
) -> Optional[PhysicalHazardResult]:
    """
    Assess water-reactive substance risk.

    VBA Reference: CalculatewaterReactRisk (lines 1312-1378)
    """
    cat = _parse_ghs_category(ghs.water_reactive)
    if cat is None:
        return None

    idx = AMOUNT_LEVEL_INDEX[amount_level]

    # Category 1: Always Level IV (provisional 5)
    if cat == "1":
        return PhysicalHazardResult(
            hazard_type="water_reactive",
            hazard_type_ja="水反応可燃性化学品",
            provisional_level=5,
            risk_level=RiskLevel.IV,
            description="Water-reactive Category 1 - consult specialist",
            description_ja="専門家または購入元に取り扱い方等を確認・相談のうえSDS等に従い取り扱うこと。",
            is_fixed_level_iv=True,
        )

    # Category 2: [5, 5, 4, 4, 3]
    # Category 3: [5, 4, 3, 3, 2]
    if cat == "2":
        provisional = [5, 5, 4, 4, 3][idx]
    elif cat == "3":
        provisional = [5, 4, 3, 3, 2][idx]
    else:
        return None

    # Adjustments
    if ignition_removed:
        provisional -= 1
    if air_water_contact_prevented:
        provisional -= 1

    provisional = max(1, provisional)

    return PhysicalHazardResult(
        hazard_type="water_reactive",
        hazard_type_ja="水反応可燃性化学品",
        provisional_level=provisional,
        risk_level=_provisional_to_risk_level(provisional),
        description=f"Water-reactive Category {cat}",
        description_ja=f"水反応可燃性化学品 区分{cat}",
    )


def assess_oxidizing_liquid(
    ghs: GHSClassification,
    amount_level: AmountLevel,
    no_organic_matter_nearby: bool,
) -> Optional[PhysicalHazardResult]:
    """
    Assess oxidizing liquid risk.

    VBA Reference: CalculateOxLiqRisk (lines 1380-1443)
    """
    cat = _parse_ghs_category(ghs.oxidizing_liquids)
    if cat is None:
        return None

    idx = AMOUNT_LEVEL_INDEX[amount_level]

    # Provisional RL tables by category
    # Category 1: [5, 4, 3, 2, 2]
    # Category 2: [4, 3, 2, 2, 2]
    # Category 3: [3, 2, 2, 2, 1]
    if cat == "1":
        provisional = [5, 4, 3, 2, 2][idx]
    elif cat == "2":
        provisional = [4, 3, 2, 2, 2][idx]
    elif cat == "3":
        provisional = [3, 2, 2, 2, 1][idx]
    else:
        return None

    # Adjustment
    if no_organic_matter_nearby:
        provisional -= 1

    provisional = max(1, provisional)

    return PhysicalHazardResult(
        hazard_type="oxidizing_liquid",
        hazard_type_ja="酸化性液体",
        provisional_level=provisional,
        risk_level=_provisional_to_risk_level(provisional),
        description=f"Oxidizing liquid Category {cat}",
        description_ja=f"酸化性液体 区分{cat}",
    )


def assess_oxidizing_solid(
    ghs: GHSClassification,
    amount_level: AmountLevel,
    no_organic_matter_nearby: bool,
) -> Optional[PhysicalHazardResult]:
    """
    Assess oxidizing solid risk.

    VBA Reference: CalculateOxSolRisk (lines 1444-1507)
    """
    cat = _parse_ghs_category(ghs.oxidizing_solids)
    if cat is None:
        return None

    idx = AMOUNT_LEVEL_INDEX[amount_level]

    # Same as oxidizing liquid
    if cat == "1":
        provisional = [5, 4, 3, 2, 2][idx]
    elif cat == "2":
        provisional = [4, 3, 2, 2, 2][idx]
    elif cat == "3":
        provisional = [3, 2, 2, 2, 1][idx]
    else:
        return None

    # Adjustment
    if no_organic_matter_nearby:
        provisional -= 1

    provisional = max(1, provisional)

    return PhysicalHazardResult(
        hazard_type="oxidizing_solid",
        hazard_type_ja="酸化性固体",
        provisional_level=provisional,
        risk_level=_provisional_to_risk_level(provisional),
        description=f"Oxidizing solid Category {cat}",
        description_ja=f"酸化性固体 区分{cat}",
    )


def assess_organic_peroxide(
    ghs: GHSClassification,
    amount_level: AmountLevel,
) -> Optional[PhysicalHazardResult]:
    """
    Assess organic peroxide risk.

    VBA Reference: CalculateOrgPerox (lines 1509-1551)
    """
    cat = _parse_ghs_category(ghs.organic_peroxides)
    if cat is None:
        return None

    idx = AMOUNT_LEVEL_INDEX[amount_level]

    # Type A-E: Always Level IV (provisional 5)
    # Note: VBA doesn't handle Type F, but per GHS it should be amount-dependent like G
    if cat in ["A", "B", "C", "D", "E"]:
        return PhysicalHazardResult(
            hazard_type="organic_peroxide",
            hazard_type_ja="有機過酸化物",
            provisional_level=5,
            risk_level=RiskLevel.IV,
            description=f"Organic peroxide Type {cat} - consult specialist",
            description_ja="専門家または購入元に取り扱い方等を確認・相談のうえSDS等に従い取り扱うこと。",
            is_fixed_level_iv=True,
        )
    elif cat in ["F", "G"]:
        # Type F and G: Amount-dependent
        provisional = [5, 4, 3, 2, 1][idx]
        return PhysicalHazardResult(
            hazard_type="organic_peroxide",
            hazard_type_ja="有機過酸化物",
            provisional_level=provisional,
            risk_level=_provisional_to_risk_level(provisional),
            description=f"Organic peroxide Type {cat}",
            description_ja=f"有機過酸化物 タイプ{cat}",
        )

    return None


def assess_corrosive_to_metals(ghs: GHSClassification) -> Optional[PhysicalHazardResult]:
    """
    Assess metal corrosive risk.

    VBA Reference: CalculateInertMetCorrRisk (lines 1553-1565)
    Always Level II (provisional 2).
    """
    cat = _parse_ghs_category(ghs.corrosive_to_metals)
    if cat is None:
        return None

    return PhysicalHazardResult(
        hazard_type="corrosive_to_metals",
        hazard_type_ja="金属腐食性物質",
        provisional_level=2,
        risk_level=RiskLevel.II,
        description="Metal corrosive - store in appropriate containers",
        description_ja="貯蔵、使用時に容器や配管などを腐食し破損、割れのおそれがあるため、SDS等を確認し適切に取り扱うこと。",
    )


# Note: Desensitized explosives (鈍性化爆発物) would be assessed similarly to explosives
# but this GHS category may not be in our current model. Can be added if needed.


# =============================================================================
# Main Physical Risk Calculator
# =============================================================================

def calculate_physical_risk(
    assessment_input: AssessmentInput,
    substance: Substance,
    verbose: bool = True,
) -> Optional[PhysicalRisk]:
    """
    Calculate physical hazard risk following CREATE-SIMPLE methodology.

    Evaluates all 17+ physical hazard types and returns the highest risk.

    Reference: CREATE-SIMPLE Design v3.1.1, Section 7
    VBA Reference: modCalc.bas

    Args:
        assessment_input: Assessment input parameters
        substance: Substance data
        verbose: Whether to generate detailed explanation

    Returns:
        PhysicalRisk result, or None if physical assessment not requested
    """
    if not assessment_input.assess_physical:
        return None

    ghs = substance.ghs
    props = substance.properties
    amount_level = assessment_input.amount_level

    # Work condition flags (inverted where needed)
    ignition_removed = not assessment_input.has_ignition_sources
    explosive_atmosphere_prevented = not assessment_input.has_explosive_atmosphere
    air_water_contact_prevented = not assessment_input.has_air_water_contact
    no_organic_matter_nearby = not assessment_input.has_organic_matter

    # Dustiness check for solids
    dustiness_low = False
    if substance.property_type.value == "solid":
        # TODO: Could add dustiness level to substance model
        dustiness_low = False  # Conservative default

    # Collect all hazard assessments
    hazard_results: list[PhysicalHazardResult] = []

    # 1. Explosives
    result = assess_explosives(ghs)
    if result:
        hazard_results.append(result)

    # 2. Flammable gas
    result = assess_flammable_gas(ghs, amount_level, ignition_removed, explosive_atmosphere_prevented)
    if result:
        hazard_results.append(result)

    # 3. Aerosol
    result = assess_aerosol(ghs, amount_level, ignition_removed, explosive_atmosphere_prevented)
    if result:
        hazard_results.append(result)

    # 4. Oxidizing gas
    result = assess_oxidizing_gas(ghs, amount_level)
    if result:
        hazard_results.append(result)

    # 5. Gases under pressure
    result = assess_gases_under_pressure(ghs, amount_level)
    if result:
        hazard_results.append(result)

    # 6. Flammable liquid
    result = assess_flammable_liquid(
        ghs, amount_level, props.flash_point,
        assessment_input.process_temperature,
        ignition_removed, explosive_atmosphere_prevented,
    )
    if result:
        hazard_results.append(result)

    # 7. Flammable solid
    result = assess_flammable_solid(
        ghs, amount_level, dustiness_low,
        ignition_removed, explosive_atmosphere_prevented,
    )
    if result:
        hazard_results.append(result)

    # 8. Self-reactive
    result = assess_self_reactive(ghs, amount_level)
    if result:
        hazard_results.append(result)

    # 9. Pyrophoric liquid
    result = assess_pyrophoric_liquid(ghs)
    if result:
        hazard_results.append(result)

    # 10. Pyrophoric solid
    result = assess_pyrophoric_solid(ghs)
    if result:
        hazard_results.append(result)

    # 11. Self-heating
    result = assess_self_heating(ghs, amount_level, air_water_contact_prevented)
    if result:
        hazard_results.append(result)

    # 12. Water-reactive
    result = assess_water_reactive(ghs, amount_level, ignition_removed, air_water_contact_prevented)
    if result:
        hazard_results.append(result)

    # 13. Oxidizing liquid
    result = assess_oxidizing_liquid(ghs, amount_level, no_organic_matter_nearby)
    if result:
        hazard_results.append(result)

    # 14. Oxidizing solid
    result = assess_oxidizing_solid(ghs, amount_level, no_organic_matter_nearby)
    if result:
        hazard_results.append(result)

    # 15. Organic peroxide
    result = assess_organic_peroxide(ghs, amount_level)
    if result:
        hazard_results.append(result)

    # 16. Corrosive to metals
    result = assess_corrosive_to_metals(ghs)
    if result:
        hazard_results.append(result)

    # No physical hazards identified
    if not hazard_results:
        return None

    # Find the highest risk hazard
    highest_hazard = max(hazard_results, key=lambda x: (x.risk_level.value, x.provisional_level))

    # Build explanation
    steps = []
    step_num = 1

    for hr in hazard_results:
        if verbose:
            steps.append(
                CalculationStep(
                    step_number=step_num,
                    description=f"Assess {hr.hazard_type}",
                    description_ja=f"{hr.hazard_type_ja}の評価",
                    formula=f"GHS category + amount level → provisional RL",
                    input_values={
                        "hazard_type": hr.hazard_type,
                        "amount_level": amount_level.value,
                        "ignition_removed": ignition_removed,
                        "explosive_atmosphere_prevented": explosive_atmosphere_prevented,
                    },
                    output_value=hr.risk_level.value,
                    output_unit="",
                    explanation=hr.description,
                    explanation_ja=hr.description_ja,
                )
            )
            step_num += 1

    # Build limitations
    limitations = []
    if highest_hazard.is_fixed_level_iv:
        limitations.append(
            Limitation(
                factor_name="Fixed Level IV hazard",
                factor_name_ja="固定レベルIVハザード",
                description=f"{highest_hazard.hazard_type} is inherently Level IV - no controls can reduce risk",
                description_ja=f"{highest_hazard.hazard_type_ja}は本質的にレベルIVに分類され、管理措置でリスクを低減できません",
                current_value=4,
                limiting_value=4,
                impact="Level I is not achievable",
                impact_ja="レベルIは達成不可能",
            )
        )

    explanation = (
        CalculationExplanation(
            steps=steps,
            summary=f"Physical hazard: Level {highest_hazard.risk_level.name} ({highest_hazard.hazard_type_ja})",
            summary_ja=f"物理的危険性: レベル{highest_hazard.risk_level.name} ({highest_hazard.hazard_type_ja})",
        )
        if verbose
        else None
    )

    return PhysicalRisk(
        hazard_type=highest_hazard.hazard_type,
        is_fixed_level_iv=highest_hazard.is_fixed_level_iv,
        flash_point=props.flash_point,
        process_temperature=assessment_input.process_temperature,
        temperature_margin=(
            props.flash_point - assessment_input.process_temperature
            if props.flash_point and assessment_input.process_temperature
            else None
        ),
        risk_level=highest_hazard.risk_level,
        explanation=explanation,
        min_achievable_level=RiskLevel.IV if highest_hazard.is_fixed_level_iv else None,
        limitations=limitations,
        level_one_achievable=not highest_hazard.is_fixed_level_iv,
    )
