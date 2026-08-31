"""
Hazard level calculator module.

Determines hazard level (HL1-HL5) from GHS classification data using the
CREATE-SIMPLE v3.0.2-v3.2.1 ``CalculateACRMax`` rules.
"""

from typing import Literal
from .substance_db import SubstanceData

HazardLevel = Literal["HL1", "HL2", "HL3", "HL4", "HL5"]


def _get_category(ghs_value: str | None) -> str | None:
    """Extract category from GHS value (e.g., '1A', '1B', '1', '2')."""
    if ghs_value is None:
        return None
    # Clean the value
    value = ghs_value.strip().upper()
    if not value:
        return None
    return value


def is_carcinogen(substance: SubstanceData) -> bool:
    """
    Check if substance is a carcinogen.

    Returns True if:
    - GHS carcinogenicity category is set (1A, 1B, or 2)
    - is_carcinogen flag is True

    Args:
        substance: SubstanceData from database

    Returns:
        True if carcinogen, False otherwise
    """
    if substance.is_carcinogen:
        return True

    category = _get_category(substance.ghs_carcinogenicity)
    if category is not None:
        return True

    return False


def is_mutagen(substance: SubstanceData) -> bool:
    """
    Check if substance is a mutagen.

    Returns True if GHS mutagenicity category is set (1A, 1B, or 2).

    Args:
        substance: SubstanceData from database

    Returns:
        True if mutagen, False otherwise
    """
    category = _get_category(substance.ghs_mutagenicity)
    return category is not None


def is_reproductive_toxicant(substance: SubstanceData) -> bool:
    """
    Check if substance is a reproductive toxicant.

    Returns True if GHS reproductive toxicity category is set (1A, 1B, or 2).

    Args:
        substance: SubstanceData from database

    Returns:
        True if reproductive toxicant, False otherwise
    """
    category = _get_category(substance.ghs_reproductive)
    return category is not None


def is_stot_re(substance: SubstanceData) -> bool:
    """
    Check if substance has STOT-RE (specific target organ toxicity - repeated exposure).

    Returns True if GHS STOT-RE category is set (1 or 2).

    Args:
        substance: SubstanceData from database

    Returns:
        True if has STOT-RE, False otherwise
    """
    category = _get_category(substance.ghs_stot_re)
    return category is not None


def is_respiratory_sensitizer(substance: SubstanceData) -> bool:
    """
    Check if substance is a respiratory sensitizer.

    Returns True if GHS respiratory sensitization category is set (1, 1A, or 1B).

    Args:
        substance: SubstanceData from database

    Returns:
        True if respiratory sensitizer, False otherwise
    """
    category = _get_category(substance.ghs_resp_sens)
    return category is not None


def has_health_hazards(substance: SubstanceData) -> bool:
    """
    Check if substance has any health hazards (HL2 level).

    Includes:
    - Acute toxicity (oral, dermal, inhalation)
    - Skin corrosion/irritation
    - Eye damage
    - Skin sensitization
    - STOT-SE
    - Aspiration hazard

    Args:
        substance: SubstanceData from database

    Returns:
        True if has any HL2 health hazards, False otherwise
    """
    # Check acute toxicity
    if _get_category(substance.ghs_acute_oral) is not None:
        return True
    if _get_category(substance.ghs_acute_dermal) is not None:
        return True
    if _get_category(substance.ghs_acute_inhal_gas) is not None:
        return True
    if _get_category(substance.ghs_acute_inhal_vapor) is not None:
        return True
    if _get_category(substance.ghs_acute_inhal_dust) is not None:
        return True

    # Check skin/eye hazards
    if _get_category(substance.ghs_skin_corr) is not None:
        return True
    if _get_category(substance.ghs_eye_damage) is not None:
        return True
    if _get_category(substance.ghs_skin_sens) is not None:
        return True

    # Check STOT-SE and aspiration
    if _get_category(substance.ghs_stot_se) is not None:
        return True
    if _get_category(substance.ghs_aspiration) is not None:
        return True

    return False


def _is_category_1(category: str | None) -> bool:
    """Check if category is 1, 1A, or 1B."""
    if category is None:
        return False
    return category in ("1", "1A", "1B")


def _is_category_2(category: str | None) -> bool:
    """Check if category is 2."""
    if category is None:
        return False
    return category == "2"


def get_hazard_level(substance: SubstanceData) -> HazardLevel:
    """
    Determine the hazard level for a substance.

    This raw-database API delegates to the same classification model used by
    the assessment calculator so database lookups and actual calculations
    cannot drift apart.

    Args:
        substance: SubstanceData from database

    Returns:
        Hazard level string ("HL1" to "HL5")
    """
    from .converter import to_ghs_classification

    return to_ghs_classification(substance).get_hazard_level()  # type: ignore[return-value]


def get_hazard_level_numeric(substance: SubstanceData) -> int:
    """
    Get hazard level as numeric value (1-5).

    Args:
        substance: SubstanceData from database

    Returns:
        Hazard level as integer (1-5)
    """
    hl = get_hazard_level(substance)
    return int(hl[2])  # Extract number from "HL1" -> 1


def should_apply_acrmax(substance: SubstanceData) -> bool:
    """
    Determine if ACRmax should be applied for this substance.

    CREATE-SIMPLE always derives an ACRmax from HL1-HL5.  It becomes the
    assessment standard when an occupational exposure limit is unavailable.

    Args:
        substance: SubstanceData from database

    Returns:
        True if ACRmax should be applied, False otherwise
    """
    return True


def get_acrmax_hazard_level(substance: SubstanceData) -> HazardLevel | None:
    """
    Get the hazard level to use for ACRmax lookup, if applicable.

    Compatibility alias for the full CREATE-SIMPLE GHS hazard level.

    Args:
        substance: SubstanceData from database

    Returns:
        Hazard level string ("HL1" through "HL5") for ACRmax lookup
    """
    return get_hazard_level(substance)
