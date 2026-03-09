"""
Physical hazard risk calculation functions.

VBA Reference: modCalc.bas

Each function calculates a risk level (1-4) based on:
- GHS hazard category
- Amount level (1=large to 5=small)
- Control measures

Risk level is capped at 4 (Level IV is maximum).
Returns None if no GHS classification exists.
"""

from typing import Optional


def _cap_risk_level(level: int) -> int:
    """Cap risk level at 4 (max) and 1 (min)."""
    if level >= 4:
        return 4
    elif level <= 1:
        return 1
    else:
        return level


def calculate_flam_gas_risk(
    ghs_category: Optional[str],
    amount_level: int,
    ignition_controlled: bool = False,
    explosive_atm_controlled: bool = False,
) -> Optional[int]:
    """
    Calculate flammable gas risk.

    VBA Reference: modCalc.bas lines 848-907 (CalculateFlamGasRisk)

    Args:
        ghs_category: GHS category ("1" or "2")
        amount_level: Amount level (1=large to 5=small)
        ignition_controlled: Whether ignition sources are controlled
        explosive_atm_controlled: Whether explosive atmosphere is controlled

    Returns:
        Risk level (1-4), or None if no classification
    """
    if ghs_category is None or ghs_category == "-9999":
        return None

    # Base risk by category and amount
    if ghs_category == "1":
        base_risks = {1: 5, 2: 5, 3: 5, 4: 4, 5: 3}
    elif ghs_category == "2":
        base_risks = {1: 5, 2: 5, 3: 4, 4: 3, 5: 2}
    else:
        return None

    temp_risk = base_risks.get(amount_level, 0)

    # Apply control reductions
    if ignition_controlled and explosive_atm_controlled:
        temp_risk -= 2
    elif ignition_controlled or explosive_atm_controlled:
        temp_risk -= 1

    return _cap_risk_level(temp_risk)


def calculate_flam_sol_risk(
    ghs_category: Optional[str],
    amount_level: int,
    ignition_controlled: bool = False,
    explosive_atm_controlled: bool = False,
    low_dustiness: bool = False,
) -> Optional[int]:
    """
    Calculate flammable solid risk.

    VBA Reference: modCalc.bas lines 1140-1206 (CalculateFlamSolRisk)

    Note: Category 2 has special dustiness consideration.

    Args:
        ghs_category: GHS category ("1" or "2")
        amount_level: Amount level (1=large to 5=small)
        ignition_controlled: Whether ignition sources are controlled
        explosive_atm_controlled: Whether explosive atmosphere is controlled
        low_dustiness: Whether dustiness is low (volatilityOrDustiness in VBA)

    Returns:
        Risk level (1-4), or None if no classification
    """
    if ghs_category is None or ghs_category == "-9999":
        return None

    # Base risk by category and amount
    if ghs_category == "1":
        base_risks = {1: 5, 2: 5, 3: 4, 4: 3, 5: 2}
        temp_risk = base_risks.get(amount_level, 0)

        # Category 1: standard control reduction
        if ignition_controlled and explosive_atm_controlled:
            temp_risk -= 2
        elif ignition_controlled or explosive_atm_controlled:
            temp_risk -= 1

    elif ghs_category == "2":
        base_risks = {1: 5, 2: 5, 3: 4, 4: 3, 5: 2}
        temp_risk = base_risks.get(amount_level, 0)

        # Category 2: dustiness is also considered
        controls = [ignition_controlled, explosive_atm_controlled, low_dustiness]
        num_controls = sum(controls)

        if num_controls == 3:
            temp_risk -= 3
        elif num_controls == 2:
            temp_risk -= 2
        elif num_controls == 1:
            temp_risk -= 1
    else:
        return None

    return _cap_risk_level(temp_risk)


def calculate_aerosol_risk(
    ghs_category: Optional[str],
    amount_level: int,
    ignition_controlled: bool = False,
    explosive_atm_controlled: bool = False,
) -> Optional[int]:
    """
    Calculate aerosol risk.

    VBA Reference: modCalc.bas lines 908-976 (CalculateAerosolRisk)

    Args:
        ghs_category: GHS category ("1", "2", or "3")
        amount_level: Amount level (1=large to 5=small)
        ignition_controlled: Whether ignition sources are controlled
        explosive_atm_controlled: Whether explosive atmosphere is controlled

    Returns:
        Risk level (1-4), or None if no classification
    """
    if ghs_category is None or ghs_category == "-9999":
        return None

    # Base risk by category and amount
    if ghs_category == "1":
        base_risks = {1: 5, 2: 5, 3: 5, 4: 4, 5: 3}
    elif ghs_category == "2":
        base_risks = {1: 5, 2: 5, 3: 4, 4: 4, 5: 3}
    elif ghs_category == "3":
        base_risks = {1: 2, 2: 2, 3: 2, 4: 1, 5: 1}
    else:
        return None

    temp_risk = base_risks.get(amount_level, 0)

    # Apply control reductions
    if ignition_controlled and explosive_atm_controlled:
        temp_risk -= 2
    elif ignition_controlled or explosive_atm_controlled:
        temp_risk -= 1

    return _cap_risk_level(temp_risk)


def calculate_ox_gas_risk(
    ghs_category: Optional[str],
    amount_level: int,
) -> Optional[int]:
    """
    Calculate oxidizing gas risk.

    VBA Reference: modCalc.bas lines 977-1012 (CalculateOxGasRisk)

    Note: No control measure reductions for oxidizing gases.

    Args:
        ghs_category: GHS category ("1")
        amount_level: Amount level (1=large to 5=small)

    Returns:
        Risk level (1-4), or None if no classification
    """
    if ghs_category is None or ghs_category == "-9999":
        return None

    # Risk by amount only (no category differentiation)
    base_risks = {1: 5, 2: 4, 3: 3, 4: 2, 5: 2}
    temp_risk = base_risks.get(amount_level, 0)

    return _cap_risk_level(temp_risk)


def calculate_ox_liq_risk(
    ghs_category: Optional[str],
    amount_level: int,
    organic_controlled: bool = False,
) -> Optional[int]:
    """
    Calculate oxidizing liquid risk.

    VBA Reference: modCalc.bas lines 1381-1443 (CalculateOxLiqRisk)

    Args:
        ghs_category: GHS category ("1", "2", or "3")
        amount_level: Amount level (1=large to 5=small)
        organic_controlled: Whether organic matter is controlled

    Returns:
        Risk level (1-4), or None if no classification
    """
    if ghs_category is None or ghs_category == "-9999":
        return None

    # Base risk by category and amount
    if ghs_category == "1":
        base_risks = {1: 5, 2: 4, 3: 3, 4: 2, 5: 2}
    elif ghs_category == "2":
        base_risks = {1: 4, 2: 3, 3: 2, 4: 2, 5: 2}
    elif ghs_category == "3":
        base_risks = {1: 3, 2: 2, 3: 2, 4: 2, 5: 1}
    else:
        return None

    temp_risk = base_risks.get(amount_level, 0)

    # Apply control reduction
    if organic_controlled:
        temp_risk -= 1

    return _cap_risk_level(temp_risk)


def calculate_ox_sol_risk(
    ghs_category: Optional[str],
    amount_level: int,
    organic_controlled: bool = False,
) -> Optional[int]:
    """
    Calculate oxidizing solid risk.

    VBA Reference: modCalc.bas lines 1445-1507 (CalculateOxSolRisk)

    Args:
        ghs_category: GHS category ("1", "2", or "3")
        amount_level: Amount level (1=large to 5=small)
        organic_controlled: Whether organic matter is controlled

    Returns:
        Risk level (1-4), or None if no classification
    """
    if ghs_category is None or ghs_category == "-9999":
        return None

    # Base risk by category and amount (same as liquid)
    if ghs_category == "1":
        base_risks = {1: 5, 2: 4, 3: 3, 4: 2, 5: 2}
    elif ghs_category == "2":
        base_risks = {1: 4, 2: 3, 3: 2, 4: 2, 5: 2}
    elif ghs_category == "3":
        base_risks = {1: 3, 2: 2, 3: 2, 4: 2, 5: 1}
    else:
        return None

    temp_risk = base_risks.get(amount_level, 0)

    # Apply control reduction
    if organic_controlled:
        temp_risk -= 1

    return _cap_risk_level(temp_risk)


def calculate_gases_under_pressure_risk(
    ghs_category: Optional[str],
    amount_level: int,
) -> Optional[int]:
    """
    Calculate gases under pressure risk.

    VBA Reference: modCalc.bas lines 1013-1048 (CalculateGasesUnderPressureRisk)

    Args:
        ghs_category: GHS category (e.g., "compressed", "liquefied", etc.)
        amount_level: Amount level (1=large to 5=small)

    Returns:
        Risk level (1-4), or None if no classification
    """
    if ghs_category is None or ghs_category == "-9999":
        return None

    # Risk by amount only
    base_risks = {1: 2, 2: 2, 3: 2, 4: 1, 5: 1}
    temp_risk = base_risks.get(amount_level, 0)

    return _cap_risk_level(temp_risk)


def calculate_self_react_risk(
    ghs_category: Optional[str],
    amount_level: int,
) -> Optional[int]:
    """
    Calculate self-reactive risk.

    VBA Reference: modCalc.bas lines 1207-1247 (CalculateSelfReactRisk)

    Args:
        ghs_category: GHS type ("A", "B", "C", "D", "E", "F", "G")
        amount_level: Amount level (1=large to 5=small)

    Returns:
        Risk level (1-4), or None if no classification
    """
    if ghs_category is None or ghs_category == "-9999":
        return None

    # Types A-E always have temp_risk = 5 (high risk)
    if ghs_category in ["A", "B", "C", "D", "E"]:
        temp_risk = 5
    elif ghs_category in ["F", "G"]:
        # Types F and G have variable risk by amount
        base_risks = {1: 5, 2: 4, 3: 3, 4: 2, 5: 1}
        temp_risk = base_risks.get(amount_level, 0)
    else:
        return None

    return _cap_risk_level(temp_risk)


def calculate_pyr_liq_risk(
    ghs_category: Optional[str],
) -> Optional[int]:
    """
    Calculate pyrophoric liquid risk.

    VBA Reference: modCalc.bas lines 1248-1260 (CalculatePyrLiqRisk)

    Args:
        ghs_category: GHS category ("1")

    Returns:
        Risk level 4 (always), or None if no classification
    """
    if ghs_category is None or ghs_category == "-9999":
        return None

    return 4


def calculate_pyr_sol_risk(
    ghs_category: Optional[str],
) -> Optional[int]:
    """
    Calculate pyrophoric solid risk.

    VBA Reference: modCalc.bas lines 1261-1271 (CalculatePyrSolRisk)

    Args:
        ghs_category: GHS category ("1")

    Returns:
        Risk level 4 (always), or None if no classification
    """
    if ghs_category is None or ghs_category == "-9999":
        return None

    return 4


def calculate_self_heat_risk(
    ghs_category: Optional[str],
    amount_level: int,
    contact_controlled: bool = False,
) -> Optional[int]:
    """
    Calculate self-heating risk.

    VBA Reference: modCalc.bas lines 1272-1310 (CalculateselfHeatRisk)

    Args:
        ghs_category: GHS category ("1" or "2")
        amount_level: Amount level (1=large to 5=small)
        contact_controlled: Whether contact with air/water is controlled

    Returns:
        Risk level (1-4), or None if no classification
    """
    if ghs_category is None or ghs_category == "-9999":
        return None

    # Risk by amount only
    base_risks = {1: 5, 2: 4, 3: 3, 4: 2, 5: 2}
    temp_risk = base_risks.get(amount_level, 0)

    # Apply control reduction
    if contact_controlled:
        temp_risk -= 1

    return _cap_risk_level(temp_risk)


def calculate_water_react_risk(
    ghs_category: Optional[str],
    amount_level: int,
    ignition_controlled: bool = False,
    contact_controlled: bool = False,
) -> Optional[int]:
    """
    Calculate water-reactive risk.

    VBA Reference: modCalc.bas lines 1312-1378 (CalculatewaterReactRisk)

    Args:
        ghs_category: GHS category ("1", "2", or "3")
        amount_level: Amount level (1=large to 5=small)
        ignition_controlled: Whether ignition sources are controlled
        contact_controlled: Whether contact with water is controlled

    Returns:
        Risk level (1-4), or None if no classification
    """
    if ghs_category is None or ghs_category == "-9999":
        return None

    if ghs_category == "1":
        # Category 1 always has temp_risk = 5
        temp_risk = 5
    elif ghs_category == "2":
        base_risks = {1: 5, 2: 5, 3: 4, 4: 4, 5: 3}
        temp_risk = base_risks.get(amount_level, 0)

        # Apply control reductions
        if ignition_controlled and contact_controlled:
            temp_risk -= 2
        elif ignition_controlled or contact_controlled:
            temp_risk -= 1
    elif ghs_category == "3":
        base_risks = {1: 5, 2: 4, 3: 3, 4: 3, 5: 2}
        temp_risk = base_risks.get(amount_level, 0)

        # Apply control reductions
        if ignition_controlled and contact_controlled:
            temp_risk -= 2
        elif ignition_controlled or contact_controlled:
            temp_risk -= 1
    else:
        return None

    return _cap_risk_level(temp_risk)


def calculate_flam_liq_risk(
    ghs_category: Optional[str],
    amount_level: int,
    flash_point: Optional[float] = None,
    process_temp: Optional[float] = None,
    ignition_controlled: bool = False,
    explosive_atm_controlled: bool = False,
) -> Optional[int]:
    """
    Calculate flammable liquid risk.

    VBA Reference: modCalc.bas lines 1050-1139 (CalculateFlamLiqRisk)

    Special handling:
    - If flash_point is not provided, estimate from GHS category
    - If process_temp > flash_point, treat as higher risk

    Args:
        ghs_category: GHS category ("1", "2", "3", or "4")
        amount_level: Amount level (1=large to 5=small)
        flash_point: Flash point in °C (optional)
        process_temp: Process temperature in °C (optional)
        ignition_controlled: Whether ignition sources are controlled
        explosive_atm_controlled: Whether explosive atmosphere is controlled

    Returns:
        Risk level (1-4), or None if no classification
    """
    if (ghs_category is None or ghs_category == "-9999") and flash_point is None:
        return None

    # If flash_point not provided, estimate from GHS category (conservative)
    effective_flash_point = flash_point
    if flash_point is None or flash_point == -9999:
        if ghs_category in ["1", "2", "3"]:
            effective_flash_point = 23  # Conservative for categories 1-3
        elif ghs_category == "4":
            effective_flash_point = 60  # Conservative for category 4
        else:
            effective_flash_point = 23  # Default conservative

    # Check if process temp exceeds flash point
    process_temp_exceeds = False
    if process_temp is not None and effective_flash_point is not None:
        process_temp_exceeds = process_temp > effective_flash_point

    # Determine base risk
    if process_temp_exceeds:
        # Process temp > flash point: higher risk
        base_risks = {1: 5, 2: 5, 3: 4, 4: 3, 5: 2}
        temp_risk = base_risks.get(amount_level, 0)
    elif ghs_category in ["1", "2"]:
        base_risks = {1: 5, 2: 5, 3: 4, 4: 3, 5: 2}
        temp_risk = base_risks.get(amount_level, 0)
    elif ghs_category == "3":
        base_risks = {1: 4, 2: 3, 3: 2, 4: 2, 5: 2}
        temp_risk = base_risks.get(amount_level, 0)
    elif ghs_category == "4":
        base_risks = {1: 3, 2: 2, 3: 2, 4: 2, 5: 1}
        temp_risk = base_risks.get(amount_level, 0)
    else:
        return None

    # Apply control reductions
    if ignition_controlled and explosive_atm_controlled:
        temp_risk -= 2
    elif ignition_controlled or explosive_atm_controlled:
        temp_risk -= 1

    return _cap_risk_level(temp_risk)


def calculate_explosives_risk(
    ghs_category: Optional[str],
) -> Optional[int]:
    """
    Calculate explosives risk.

    VBA Reference: modCalc.bas lines 836-846 (CalculateExplosivesRisk)

    Note: Explosives always return risk level 4 (highest).

    Args:
        ghs_category: GHS category (any non-empty value indicates classification)

    Returns:
        Risk level 4 (always), or None if no classification
    """
    if ghs_category is None or ghs_category == "-9999" or ghs_category == "":
        return None

    return 4


def calculate_org_perox_risk(
    ghs_category: Optional[str],
    amount_level: int,
) -> Optional[int]:
    """
    Calculate organic peroxide risk.

    VBA Reference: modCalc.bas lines 1509-1551 (CalculateOrgPerox)

    Args:
        ghs_category: GHS type ("A", "B", "C", "D", "E", "F", "G")
        amount_level: Amount level (1=large to 5=small)

    Returns:
        Risk level (1-4), or None if no classification
    """
    if ghs_category is None or ghs_category == "-9999":
        return None

    # Types A-E always have temp_risk = 5 (high risk)
    if ghs_category in ["A", "B", "C", "D", "E"]:
        temp_risk = 5
    elif ghs_category in ["F", "G"]:
        # Type F and G have variable risk by amount
        base_risks = {1: 5, 2: 4, 3: 3, 4: 2, 5: 1}
        temp_risk = base_risks.get(amount_level, 0)
    else:
        return None

    return _cap_risk_level(temp_risk)


def calculate_met_corr_risk(
    ghs_category: Optional[str],
) -> Optional[int]:
    """
    Calculate metal corrosive risk.

    VBA Reference: modCalc.bas lines 1552-1565 (CalculateInertMetCorrRisk)

    Note: Metal corrosives always return risk level 2.

    Args:
        ghs_category: GHS category (any non-empty value indicates classification)

    Returns:
        Risk level 2 (always), or None if no classification
    """
    if ghs_category is None or ghs_category == "-9999" or ghs_category == "":
        return None

    return 2


def calculate_inert_explosives_risk(
    ghs_category: Optional[str],
) -> Optional[int]:
    """
    Calculate desensitized (inert) explosives risk.

    VBA Reference: modCalc.bas lines 1567-1579 (CalculateInertExplosivesRisk)

    Note: Desensitized explosives always return risk level 4 (highest).

    Args:
        ghs_category: GHS category (any non-empty value indicates classification)

    Returns:
        Risk level 4 (always), or None if no classification
    """
    if ghs_category is None or ghs_category == "-9999" or ghs_category == "":
        return None

    return 4
