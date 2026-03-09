"""
Utility functions for risk assessment calculations.

VBA Reference: modCalc.bas, modFunction.bas
"""

import math
from typing import Optional


def round_significant(value: float, digits: int = 2) -> float:
    """
    Round to significant figures (standard rounding).

    Args:
        value: Value to round
        digits: Number of significant figures (default 2)

    Returns:
        Rounded value
    """
    if value == 0:
        return 0.0

    # Calculate order of magnitude
    order = math.floor(math.log10(abs(value)))

    # Decimal places needed
    decimal_places = digits - 1 - order

    return round(value, decimal_places)


def round_down_significant(value: float, digits: int = 2) -> float:
    """
    Round DOWN to significant figures (truncation).

    VBA: WorksheetFunction.RoundDown(value, n - Int(Log(Abs(value))))

    This is used in VBA for conservative estimates.

    Args:
        value: Value to round
        digits: Number of significant figures (default 2)

    Returns:
        Value rounded down to significant figures
    """
    if value == 0:
        return 0.0

    # Calculate order of magnitude
    order = math.floor(math.log10(abs(value)))

    # Decimal places needed
    decimal_places = digits - 1 - order

    # Round down (truncate toward zero)
    if decimal_places >= 0:
        multiplier = 10 ** decimal_places
        return math.floor(value * multiplier) / multiplier
    else:
        # For large numbers, round down to the appropriate place
        divisor = 10 ** (-decimal_places)
        return math.floor(value / divisor) * divisor


def convert_ppm_to_mg_m3(
    ppm: float,
    molecular_weight: float,
    temperature_celsius: float = 25.0,
) -> float:
    """
    Convert concentration from ppm to mg/m³.

    Formula: mg/m³ = ppm × (MW / molar_volume)

    At 25°C and 1 atm: molar_volume = 24.45 L/mol

    Args:
        ppm: Concentration in ppm
        molecular_weight: Molecular weight in g/mol
        temperature_celsius: Temperature in °C (default 25)

    Returns:
        Concentration in mg/m³
    """
    # Molar volume at 25°C, 1 atm
    # V = 22.414 × (273.15 + T) / 273.15
    molar_volume = 22.414 * (273.15 + temperature_celsius) / 273.15

    return ppm * (molecular_weight / molar_volume)


def convert_mg_m3_to_ppm(
    mg_m3: float,
    molecular_weight: float,
    temperature_celsius: float = 25.0,
) -> float:
    """
    Convert concentration from mg/m³ to ppm.

    Formula: ppm = mg/m³ × (molar_volume / MW)

    Args:
        mg_m3: Concentration in mg/m³
        molecular_weight: Molecular weight in g/mol
        temperature_celsius: Temperature in °C (default 25)

    Returns:
        Concentration in ppm
    """
    # Molar volume at 25°C, 1 atm
    molar_volume = 22.414 * (273.15 + temperature_celsius) / 273.15

    return mg_m3 * (molar_volume / molecular_weight)


def convert_pressure_to_pa(value: float, unit: str) -> float:
    """
    Convert pressure to Pascals.

    VBA Reference: modCalc.bas lines 1604-1628 (ConvertToPascals)

    Args:
        value: Pressure value
        unit: Unit of pressure ("Pa", "kPa", "hPa", "mPa", "mmHg", "Torr", "atm", "bar")

    Returns:
        Pressure in Pascals
    """
    unit_lower = unit.lower()

    if unit_lower == "pa":
        return value
    elif unit_lower == "kpa":
        return value * 1000
    elif unit_lower == "hpa":
        return value * 100
    elif unit_lower == "mpa":
        return value * 0.001
    elif unit_lower in ["mmhg", "torr"]:
        return value * 133.3  # VBA uses 133.3
    elif unit_lower == "atm":
        return value * 101325
    elif unit_lower == "bar":
        return value * 100000
    else:
        raise ValueError(f"Unknown pressure unit: {unit}")


def convert_solubility_to_mg_cm3(value: float, unit: str) -> float:
    """
    Convert solubility to mg/cm³.

    VBA Reference: modCalc.bas lines 1581-1603 (ConvertToMgPerCm3)

    Args:
        value: Solubility value
        unit: Unit of solubility ("mg/L", "g/L", "mg/cm³", "g/cm³", "g/100mL")

    Returns:
        Solubility in mg/cm³
    """
    unit_lower = unit.lower()

    if unit_lower == "mg/cm³" or unit_lower == "mg/cm3":
        return value
    elif unit_lower == "g/cm³" or unit_lower == "g/cm3":
        return value * 1000
    elif unit_lower == "mg/l":
        return value / 1000  # 1 L = 1000 cm³ → 0.001 conversion factor
    elif unit_lower == "g/l":
        return value  # 1 g/L = 1 mg/cm³
    elif unit_lower == "g/100ml":
        return value * 10  # 1 g/100mL = 10 mg/cm³ (VBA: conversionFactor = 10)
    else:
        raise ValueError(f"Unknown solubility unit: {unit}")


def vapor_pressure_to_saturated_concentration(
    vapor_pressure_pa: float,
    molecular_weight: float,
    temperature_celsius: float = 25.0,
) -> float:
    """
    Calculate saturated vapor concentration from vapor pressure.

    Formula: C_sat = VP × MW / (R × T)

    Args:
        vapor_pressure_pa: Vapor pressure in Pascals
        molecular_weight: Molecular weight in g/mol
        temperature_celsius: Temperature in °C (default 25)

    Returns:
        Saturated concentration in mg/m³
    """
    # Gas constant: R = 8.314 J/(mol·K)
    R = 8.314

    # Temperature in Kelvin
    T = 273.15 + temperature_celsius

    # C_sat = VP × MW / (R × T) × 1000 (to convert g/m³ to mg/m³)
    c_sat = (vapor_pressure_pa * molecular_weight / (R * T)) * 1000

    return c_sat
