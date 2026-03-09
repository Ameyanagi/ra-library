"""
Regulatory threshold checker module.

Based on VBA modFunction.bas lines 562-574.

Checks content percentage against regulatory thresholds for:
- 特定化学物質 (Specified Chemical Substances - Tokka)
- 皮膚等障害化学物質 (Skin Hazard Substances)
- Organic solvents
- Lead regulations
- Carcinogens
"""

from typing import TypedDict
from .substance_db import SubstanceData


class TokkaResult(TypedDict):
    """Result of Tokka regulation check."""

    applies: bool
    class_: int | None  # 1, 2, or 3
    threshold: float | None
    exceeds_threshold: bool


class OrganicSolventResult(TypedDict):
    """Result of organic solvent regulation check."""

    applies: bool
    class_: int | None  # 1, 2, or 3


class RegulationsResult(TypedDict):
    """Result of all regulations check."""

    tokka: dict
    organic_solvent: dict
    skin_hazard: bool
    lead: bool
    tetraalkyl_lead: bool
    carcinogen: bool
    concentration_standard: bool


def check_tokka_regulation(
    substance: SubstanceData,
    content_pct: float,
) -> dict:
    """
    Check 特定化学物質 (Tokka) regulation for a substance.

    Tokka classes:
    - Class 1 (第一類): Most hazardous, strict regulations
    - Class 2 (第二類): Moderate hazards
    - Class 3 (第三類): Handled as industrial waste

    Args:
        substance: SubstanceData from database
        content_pct: Content percentage of substance in product (0-100)

    Returns:
        Dict with applies, class, threshold, and exceeds_threshold
    """
    # Determine class
    tokka_class = None
    if substance.tokka_class1:
        tokka_class = 1
    elif substance.tokka_class2:
        tokka_class = 2
    elif substance.tokka_class3:
        tokka_class = 3

    if tokka_class is None:
        return {
            "applies": False,
            "class": None,
            "threshold": None,
            "exceeds_threshold": False,
        }

    # Check threshold
    threshold = substance.tokka_threshold
    if threshold is None:
        # No threshold = always exceeds
        exceeds = True
    else:
        exceeds = content_pct >= threshold

    return {
        "applies": True,
        "class": tokka_class,
        "threshold": threshold,
        "exceeds_threshold": exceeds,
    }


def check_organic_solvent_regulation(substance: SubstanceData) -> dict:
    """
    Check organic solvent regulation for a substance.

    Organic solvent classes:
    - Class 1 (第一種): Most hazardous (e.g., carbon tetrachloride)
    - Class 2 (第二種): Common solvents (e.g., toluene, xylene)
    - Class 3 (第三種): Less hazardous (e.g., petroleum solvents)

    Args:
        substance: SubstanceData from database

    Returns:
        Dict with applies and class
    """
    organic_class = None
    if substance.organic_class1:
        organic_class = 1
    elif substance.organic_class2:
        organic_class = 2
    elif substance.organic_class3:
        organic_class = 3

    if organic_class is None:
        return {"applies": False, "class": None}

    return {"applies": True, "class": organic_class}


def check_skin_hazard_regulation(
    substance: SubstanceData,
    content_pct: float,
) -> bool:
    """
    Check 皮膚等障害化学物質 (Skin Hazard) regulation for a substance.

    Args:
        substance: SubstanceData from database
        content_pct: Content percentage of substance in product (0-100)

    Returns:
        True if skin hazard regulation applies and exceeds threshold
    """
    if not substance.is_skin_hazard:
        return False

    threshold = substance.skin_hazard_threshold
    if threshold is None:
        # No threshold = always applies
        return True

    return content_pct >= threshold


def get_applicable_regulations(
    substance: SubstanceData,
    content_pct: float,
) -> dict:
    """
    Get all applicable regulations for a substance.

    Args:
        substance: SubstanceData from database
        content_pct: Content percentage of substance in product (0-100)

    Returns:
        Dict with all regulation check results
    """
    return {
        "tokka": check_tokka_regulation(substance, content_pct),
        "organic_solvent": check_organic_solvent_regulation(substance),
        "skin_hazard": check_skin_hazard_regulation(substance, content_pct),
        "lead": substance.lead_regulation,
        "tetraalkyl_lead": substance.tetraalkyl_lead,
        "carcinogen": substance.is_carcinogen,
        "concentration_standard": substance.is_conc_standard,
    }


def get_regulatory_summary(
    substance: SubstanceData,
    content_pct: float,
) -> list[str]:
    """
    Get a human-readable summary of applicable regulations.

    Args:
        substance: SubstanceData from database
        content_pct: Content percentage of substance in product (0-100)

    Returns:
        List of regulation names that apply
    """
    regulations = []

    tokka = check_tokka_regulation(substance, content_pct)
    if tokka["applies"]:
        class_name = f"第{tokka['class']}類"
        regulations.append(f"特定化学物質 {class_name}")

    organic = check_organic_solvent_regulation(substance)
    if organic["applies"]:
        class_name = f"第{organic['class']}種"
        regulations.append(f"有機溶剤 {class_name}")

    if check_skin_hazard_regulation(substance, content_pct):
        regulations.append("皮膚等障害化学物質")

    if substance.lead_regulation:
        regulations.append("鉛則対象")

    if substance.tetraalkyl_lead:
        regulations.append("四アルキル鉛")

    if substance.is_carcinogen:
        regulations.append("がん原性物質")

    if substance.is_conc_standard:
        regulations.append("濃度基準値設定物質")

    return regulations
