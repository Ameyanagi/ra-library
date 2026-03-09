"""
Volatility and dustiness calculation module.

Based on VBA modFunction.bas lines 307-359.

Determines volatility level for liquids and dustiness for solids
based on physical properties (boiling point, vapor pressure).
"""

from typing import Optional, Literal
from .substance_db import SubstanceData

VolatilityLevel = Literal["high", "medium", "low", "very_low"]
DustinessLevel = Literal["high", "medium", "low"]


def calculate_volatility_from_boiling_point(
    bp: Optional[float],
) -> Optional[VolatilityLevel]:
    """
    Calculate volatility level from boiling point.

    Based on VBA logic:
    - BP < 50°C → high (1)
    - BP 50-149°C → medium (2)
    - BP ≥ 150°C → low (3)

    Args:
        bp: Boiling point in °C

    Returns:
        Volatility level string or None if BP not available
    """
    if bp is None:
        return None

    if bp < 50:
        return "high"
    elif bp < 150:
        return "medium"
    else:
        return "low"


def calculate_volatility_from_vapor_pressure(
    vp_pa: Optional[float],
) -> Optional[VolatilityLevel]:
    """
    Calculate volatility level from vapor pressure.

    Based on VBA logic:
    - VP < 0.5 Pa → very_low (4) - for liquids
    - VP 0.5-500 Pa → low
    - VP 500-25000 Pa → medium
    - VP ≥ 25000 Pa → high

    Args:
        vp_pa: Vapor pressure in Pa

    Returns:
        Volatility level string or None if VP not available
    """
    if vp_pa is None:
        return None

    if vp_pa < 0.5:
        return "very_low"
    elif vp_pa < 500:
        return "low"
    elif vp_pa < 25000:
        return "medium"
    else:
        return "high"


def determine_volatility_level(
    substance: SubstanceData,
) -> Optional[VolatilityLevel]:
    """
    Determine overall volatility level for a substance.

    Logic:
    - Gas (property_type=3): Always "high"
    - Solid (property_type=2): Returns None (use dustiness instead)
    - Liquid (property_type=1):
      - If VP < 0.5 Pa: "very_low" (overrides BP)
      - Otherwise: Based on boiling point

    Args:
        substance: SubstanceData from database

    Returns:
        Volatility level or None for solids
    """
    # Gas always has high volatility
    if substance.property_type == 3:
        return "high"

    # Solids don't have volatility (use dustiness instead)
    if substance.property_type == 2:
        return None

    # For liquids, check vapor pressure first
    if substance.vapor_pressure is not None:
        vp = substance.vapor_pressure
        # Very low VP overrides BP calculation
        if vp < 0.5:
            return "very_low"

    # Use boiling point for volatility
    return calculate_volatility_from_boiling_point(substance.boiling_point)


def should_treat_solid_as_vapor(substance: SubstanceData) -> bool:
    """
    Determine if a solid should be treated as vapor for exposure calculation.

    A solid with significant vapor pressure (≥ 0.5 Pa) should be treated
    as a vapor source, meaning OEL should use ppm units.

    Based on VBA modFunction.bas logic for subliming solids.

    Args:
        substance: SubstanceData from database

    Returns:
        True if solid should be treated as vapor, False otherwise
    """
    # Only applies to solids
    if substance.property_type != 2:
        return False

    # Check if vapor pressure is significant
    if substance.vapor_pressure is not None and substance.vapor_pressure >= 0.5:
        return True

    return False


def get_dustiness_level(
    substance: SubstanceData,
    default: DustinessLevel = "medium",
) -> Optional[DustinessLevel]:
    """
    Get dustiness level for a solid substance.

    Dustiness depends on the physical form of the solid:
    - Fine powder: high
    - Coarse particles/granules: medium
    - Pellets/large pieces: low

    Since we don't have form data, we use vapor pressure as a proxy:
    - High VP (subliming): high dustiness
    - Otherwise: default to medium

    Args:
        substance: SubstanceData from database
        default: Default dustiness level if not determinable

    Returns:
        Dustiness level or None for non-solids
    """
    # Only solids have dustiness
    if substance.property_type != 2:
        return None

    # If solid has significant vapor pressure, it's likely fine/volatile
    if substance.vapor_pressure is not None and substance.vapor_pressure >= 0.5:
        return "high"

    return default


def get_volatility_for_assessment(
    substance: SubstanceData,
) -> tuple[Optional[VolatilityLevel], Optional[DustinessLevel]]:
    """
    Get both volatility and dustiness for a substance.

    This is the main entry point for risk assessment.

    Args:
        substance: SubstanceData from database

    Returns:
        Tuple of (volatility, dustiness). One will be None based on property type.
    """
    volatility = determine_volatility_level(substance)
    dustiness = get_dustiness_level(substance)

    return volatility, dustiness
