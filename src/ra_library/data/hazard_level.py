"""
Hazard level calculator module.

Determines hazard level (HL1-HL5) from GHS classification data.

Based on CREATE-SIMPLE hazard level determination:
- HL5: Carcinogenicity 1A/1B, Mutagenicity 1A/1B, Reproductive 1A/1B
- HL4: Carcinogenicity 2, Mutagenicity 2, Reproductive 2
- HL3: STOT-RE 1/2, Respiratory sensitization 1
- HL2: Other health hazards (acute toxicity, skin irritation, etc.)
- HL1: No significant health hazards
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

    Priority (highest wins):
    - HL5: Carcinogenicity 1A/1B, Mutagenicity 1A/1B, Reproductive 1A/1B
    - HL4: Carcinogenicity 2, Mutagenicity 2, Reproductive 2
    - HL3: STOT-RE 1/2, Respiratory sensitization 1
    - HL2: Other health hazards
    - HL1: No significant health hazards

    Args:
        substance: SubstanceData from database

    Returns:
        Hazard level string ("HL1" to "HL5")
    """
    # Check HL5 conditions (Category 1A/1B for CMR)
    carc_cat = _get_category(substance.ghs_carcinogenicity)
    muta_cat = _get_category(substance.ghs_mutagenicity)
    repr_cat = _get_category(substance.ghs_reproductive)

    if _is_category_1(carc_cat) or _is_category_1(muta_cat) or _is_category_1(repr_cat):
        return "HL5"

    # Also check is_carcinogen flag (may indicate cat 1 even if GHS not specified)
    # Only elevate to HL5 if no category is specified (flag might be more conservative)
    if substance.is_carcinogen and carc_cat is None:
        # If flag is set but category unknown, assume worst case (HL5)
        return "HL5"

    # Check HL4 conditions (Category 2 for CMR)
    if _is_category_2(carc_cat) or _is_category_2(muta_cat) or _is_category_2(repr_cat):
        return "HL4"

    # Check HL3 conditions (STOT-RE 1/2, Respiratory sensitization)
    if is_stot_re(substance) or is_respiratory_sensitizer(substance):
        return "HL3"

    # Check HL2 conditions (other health hazards)
    if has_health_hazards(substance):
        return "HL2"

    # Default to HL1 (no significant health hazards)
    return "HL1"


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

    ACRmax (Management Target Concentration) should ONLY apply to:
    - Carcinogens (Category 1A, 1B, or 2)
    - Mutagens (Category 1A, 1B, or 2)

    ACRmax should NOT apply to:
    - Reproductive toxicants (even though they contribute to HL4/HL5)
    - Other health hazards

    Reference: CREATE-SIMPLE Design v3.1.1, Section 5.3.3
    The ACRmax table specifies values for "Carcinogen 1A/1B" (HL5)
    and "Carcinogen 2, Mutagen 1A/1B/2" (HL4), but does NOT include
    reproductive toxicity.

    Args:
        substance: SubstanceData from database

    Returns:
        True if ACRmax should be applied, False otherwise
    """
    carc_cat = _get_category(substance.ghs_carcinogenicity)
    muta_cat = _get_category(substance.ghs_mutagenicity)

    # Apply ACRmax for any carcinogen category (1A, 1B, or 2)
    if carc_cat is not None:
        return True

    # Apply ACRmax for any mutagen category (1A, 1B, or 2)
    if muta_cat is not None:
        return True

    # Check is_carcinogen flag (may indicate carcinogenicity even if GHS not specified)
    if substance.is_carcinogen:
        return True

    return False


def get_acrmax_hazard_level(substance: SubstanceData) -> HazardLevel | None:
    """
    Get the hazard level to use for ACRmax lookup, if applicable.

    This returns the hazard level ONLY based on carcinogenicity/mutagenicity,
    ignoring reproductive toxicity. This is used to determine the correct
    ACRmax value from the lookup table.

    Args:
        substance: SubstanceData from database

    Returns:
        Hazard level string ("HL4" or "HL5") for ACRmax lookup,
        or None if ACRmax should not be applied
    """
    if not should_apply_acrmax(substance):
        return None

    carc_cat = _get_category(substance.ghs_carcinogenicity)
    muta_cat = _get_category(substance.ghs_mutagenicity)

    # HL5: Carcinogen 1A/1B or Mutagen 1A/1B
    if _is_category_1(carc_cat) or _is_category_1(muta_cat):
        return "HL5"

    # Check is_carcinogen flag - assume worst case (HL5) if no category specified
    if substance.is_carcinogen and carc_cat is None:
        return "HL5"

    # HL4: Carcinogen 2 or Mutagen 2
    if _is_category_2(carc_cat) or _is_category_2(muta_cat):
        return "HL4"

    return None
