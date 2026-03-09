"""
ACRmax (Management Target Concentration) and RCR calculation.

Reference: CREATE-SIMPLE Design v3.1.1, Section 5.3.3
VBA Reference: modCalc.bas lines 231-277 (CalculateACRMax)
"""

from typing import Optional

from ..models.risk import RiskLevel
from .constants import ACRMAX_VALUES_LIQUID, ACRMAX_VALUES_SOLID


def get_acrmax(
    hazard_level: Optional[str],
    property_type: Optional[str] = "liquid",
) -> Optional[float]:
    """
    Get ACRmax value for a hazard level and property type.

    ACRmax is the management target concentration for highly hazardous
    substances (carcinogens, mutagens). When present, it is used instead
    of OEL as the denominator for RCR calculation.

    Reference: CREATE-SIMPLE Design v3.1.1, Section 5.3.3
    VBA Reference: modCalc.bas lines 231-277

    Args:
        hazard_level: Hazard level (HL1-HL5), or None
        property_type: "liquid" or "solid", or None

    Returns:
        ACRmax value (ppm for liquid, mg/m³ for solid), or None if not applicable
    """
    if hazard_level is None or property_type is None:
        return None

    if property_type == "liquid":
        return ACRMAX_VALUES_LIQUID.get(hazard_level)
    elif property_type == "solid":
        return ACRMAX_VALUES_SOLID.get(hazard_level)
    else:
        return None


def calculate_rcr(
    exposure: float,
    oel: Optional[float],
    acrmax: Optional[float] = None,
) -> float:
    """
    Calculate Risk Characterization Ratio (RCR).

    RCR = Exposure / evaluation_standard

    VBA Reference: modCalc.bas lines 496-503 (DetermineRiskLevelInhalation8Hour)
    - If OEL exists (> 0), use OEL as the evaluation standard
    - If OEL doesn't exist, use ACRmax as fallback

    Note: ACRmax is NOT used when OEL is available, even if ACRmax < OEL.
    ACRmax serves as a separate management target for carcinogens, displayed
    for information but not used in risk level calculation when OEL exists.

    Args:
        exposure: Estimated exposure concentration
        oel: Occupational Exposure Limit (can be None)
        acrmax: Management target concentration (fallback if no OEL)

    Returns:
        RCR value
    """
    # VBA logic: Use OEL if available, ACRmax only as fallback
    if oel is not None and oel > 0:
        denominator = oel
    elif acrmax is not None and acrmax > 0:
        denominator = acrmax
    else:
        raise ValueError("No valid OEL or ACRmax available")

    return exposure / denominator


def get_risk_level_from_rcr(rcr: float) -> RiskLevel:
    """
    Determine risk level from RCR value.

    Reference: CREATE-SIMPLE Design v3.1.1, Section 5.3

    Risk levels:
    - Level I: RCR ≤ 0.1
    - Level II: 0.1 < RCR ≤ 1.0
    - Level III: 1.0 < RCR ≤ 10.0
    - Level IV: RCR > 10.0

    Args:
        rcr: Risk Characterization Ratio

    Returns:
        Risk level (I-IV)
    """
    return RiskLevel.from_rcr(rcr)


def calculate_minimum_achievable_rcr(
    property_type: str,
    oel: float,
    acrmax: Optional[float] = None,
) -> tuple[float, RiskLevel, str]:
    """
    Calculate the minimum achievable RCR for a substance (theoretical minimum).

    This is limited by:
    1. Minimum exposure floor (0.005 ppm for liquids, 0.001 mg/m³ for solids)
    2. ACRmax for highly hazardous substances

    Args:
        property_type: "liquid" or "solid"
        oel: Occupational Exposure Limit
        acrmax: Management target concentration (optional)

    Returns:
        Tuple of (min_rcr, best_level, explanation)
    """
    min_rcr, best_level, _, explanation, _ = calculate_engineering_limit(
        property_type=property_type,
        oel=oel,
        acrmax=acrmax,
    )
    return min_rcr, best_level, explanation


def calculate_engineering_limit(
    property_type: str,
    oel: float,
    acrmax: Optional[float] = None,
    max_ventilation: Optional[str] = None,
) -> tuple[float, RiskLevel, str, str, str]:
    """
    Calculate the engineering control limit for a substance.

    This calculates the minimum RCR achievable with engineering controls only
    (without RPE/PPE), considering optional ventilation constraints.

    The limit is determined by:
    1. Minimum exposure floor (0.005 ppm for liquids, 0.001 mg/m³ for solids)
    2. ACRmax for highly hazardous substances
    3. Ventilation constraints (if specified)

    Args:
        property_type: "liquid" or "solid"
        oel: Occupational Exposure Limit
        acrmax: Management target concentration (optional)
        max_ventilation: Maximum allowed ventilation level (optional)
            If specified, limits cannot assume sealed system is available.
            Values: "none", "basic", "industrial", "local_ext", "local_enc", "sealed"

    Returns:
        Tuple of (min_rcr, best_level, reason_en, explanation_en, reason_ja)
    """
    from .constants import MIN_EXPOSURE_LIQUID, MIN_EXPOSURE_SOLID

    # Get minimum exposure floor
    if property_type == "liquid":
        min_exposure = MIN_EXPOSURE_LIQUID
        unit = "ppm"
    else:
        min_exposure = MIN_EXPOSURE_SOLID
        unit = "mg/m³"

    # Determine effective denominator (VBA: OEL if available, ACRmax as fallback)
    if oel is not None and oel > 0:
        effective_limit = oel
        limit_source = "OEL"
        limit_source_ja = "OEL"
    elif acrmax is not None and acrmax > 0:
        effective_limit = acrmax
        limit_source = "ACRmax"
        limit_source_ja = "ACRmax"
    else:
        raise ValueError("No valid OEL or ACRmax available")

    # Calculate minimum RCR (theoretical with sealed system)
    theoretical_min_rcr = min_exposure / effective_limit

    # Adjust for ventilation constraints if specified
    # Ventilation coefficients: sealed=0.001, local_enc(verified)=0.01, local_ext(verified)=0.1, etc.
    ventilation_factors = {
        "sealed": 1.0,  # baseline
        "local_enc": 10.0,  # 0.01 / 0.001 = 10x worse than sealed
        "local_ext": 100.0,  # 0.1 / 0.001 = 100x worse than sealed
        "industrial": 1000.0,  # 1.0 / 0.001 = 1000x worse than sealed
        "basic": 3000.0,  # 3.0 / 0.001
        "none": 4000.0,  # 4.0 / 0.001
    }

    if max_ventilation and max_ventilation in ventilation_factors:
        constraint_factor = ventilation_factors[max_ventilation]
        practical_min_rcr = theoretical_min_rcr * constraint_factor
        best_level = RiskLevel.from_rcr(practical_min_rcr)

        # Determine reason
        vent_names_ja = {
            "sealed": "密閉系",
            "local_enc": "局所排気・囲い式",
            "local_ext": "局所排気・外付け式",
            "industrial": "工業的換気",
            "basic": "一般換気",
            "none": "無換気",
        }
        vent_name_ja = vent_names_ja.get(max_ventilation, max_ventilation)

        if practical_min_rcr == theoretical_min_rcr:
            # Constraint doesn't affect the result (already using sealed or floor is the limit)
            reason_en = "model_floor"
            reason_ja = f"暴露推定モデル下限値（{min_exposure} {unit}）が{limit_source_ja}と同等のため"
        else:
            reason_en = "ventilation_constraint"
            reason_ja = f"制約条件（最大換気: {vent_name_ja}）による限界"

        min_rcr = practical_min_rcr
    else:
        # No constraint - use theoretical minimum
        min_rcr = theoretical_min_rcr
        best_level = RiskLevel.from_rcr(min_rcr)
        reason_en = "model_floor"
        reason_ja = f"暴露推定モデル下限値（{min_exposure} {unit}）が{limit_source_ja}と同等のため"

    # Generate explanation
    if best_level == RiskLevel.I:
        explanation = f"Level I is achievable. Minimum RCR = {min_exposure} / {effective_limit} = {min_rcr:.4f}"
    else:
        explanation = (
            f"Level I is NOT achievable for this substance. "
            f"Minimum exposure floor ({min_exposure} {unit}) divided by "
            f"{limit_source} ({effective_limit} {unit}) = {min_rcr:.4f}. "
            f"Best achievable: Level {best_level.name}"
        )

    return min_rcr, best_level, reason_en, explanation, reason_ja
