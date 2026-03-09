"""
OEL (Occupational Exposure Limit) selection logic.

Reference: CREATE-SIMPLE Design v3.1.1, Section 2.1
VBA Reference: modCalc.bas lines 81-141 (SelectOEL8Hour)
"""

from typing import Optional, Tuple

from ..models.substance import OccupationalExposureLimits


def select_oel(oel_data: OccupationalExposureLimits) -> Tuple[Optional[float], str, str]:
    """
    Select the primary OEL value using the LOWEST available value (most conservative).

    This matches CREATE-SIMPLE default behavior (oelSourceSelection=0):
    - Finds the minimum value among all available OEL sources
    - Uses the most conservative (protective) limit

    Available sources evaluated:
    - 濃度基準値 (Concentration Standard - Japan regulatory)
    - 許容濃度 (JSOH Permissible Concentration)
    - TLV-TWA (ACGIH)
    - DFG MAK (Germany)
    - DNEL (Derived No-Effect Level)
    - Other sources

    VBA Reference: modCalc.bas lines 81-141 (SelectOEL8Hour)
    Key code: minOELValue = Application.Min(minOELValue, oelXXX)

    Args:
        oel_data: OEL data structure

    Returns:
        Tuple of (value, unit, source_name)
    """
    # Collect all available OEL values with their sources
    candidates: list[tuple[float, str, str]] = []

    if oel_data.concentration_standard_8hr is not None:
        candidates.append((
            oel_data.concentration_standard_8hr,
            oel_data.concentration_standard_8hr_unit or "ppm",
            "濃度基準値",
        ))

    if oel_data.jsoh_8hr is not None:
        candidates.append((
            oel_data.jsoh_8hr,
            oel_data.jsoh_8hr_unit or "ppm",
            "許容濃度 (JSOH)",
        ))

    if oel_data.acgih_tlv_twa is not None:
        candidates.append((
            oel_data.acgih_tlv_twa,
            oel_data.acgih_tlv_twa_unit or "ppm",
            "TLV-TWA (ACGIH)",
        ))

    if oel_data.dfg_mak is not None:
        candidates.append((
            oel_data.dfg_mak,
            oel_data.dfg_mak_unit or "ppm",
            "DFG MAK",
        ))

    if oel_data.dnel_worker_inhalation is not None:
        candidates.append((
            oel_data.dnel_worker_inhalation,
            "mg/m³",
            "DNEL",
        ))

    if oel_data.other_8hr is not None:
        candidates.append((
            oel_data.other_8hr,
            oel_data.other_8hr_unit or "ppm",
            "Other",
        ))

    if not candidates:
        return (None, "", "None")

    # Select the LOWEST value (most conservative)
    # VBA: minOELValue = Application.Min(minOELValue, oelXXX)
    min_candidate = min(candidates, key=lambda x: x[0])
    return min_candidate


def get_oel_source(oel_data: OccupationalExposureLimits) -> str:
    """Get the source name for the selected OEL."""
    _, _, source = select_oel(oel_data)
    return source


def select_oel_stel(
    oel_data: OccupationalExposureLimits,
    property_type: str,
    oel_8hr: float,
    acrmax: Optional[float] = None,
) -> Tuple[Optional[float], str, str]:
    """
    Select STEL value following CREATE-SIMPLE priority.

    VBA Reference: modCalc.bas lines 145-229 (SelectOELShortTerm)

    Priority:
    1. 濃度基準値（短時間）- Concentration Standard STEL
    2. ACGIH TLV-STEL
    3. Other STEL
    4. Fallback: Concentration Standard 8hr × 3 (if exists)
    5. Fallback: Selected OEL 8hr × 3
    6. Fallback: ACRmax × 3

    Args:
        oel_data: OEL data structure
        property_type: "liquid" or "solid"
        oel_8hr: Selected 8-hour OEL value
        acrmax: ACRmax value if applicable

    Returns:
        Tuple of (value, unit, source_name)
    """
    unit = "ppm" if property_type == "liquid" else "mg/m³"

    # Priority 1: Concentration Standard STEL (濃度基準値 短時間)
    if oel_data.concentration_standard_stel is not None:
        return (
            oel_data.concentration_standard_stel,
            oel_data.concentration_standard_stel_unit or unit,
            "濃度基準値（短時間）",
        )

    # Priority 2: ACGIH TLV-STEL
    if oel_data.acgih_tlv_stel is not None:
        return (
            oel_data.acgih_tlv_stel,
            oel_data.acgih_tlv_stel_unit or unit,
            "TLV-STEL (ACGIH)",
        )

    # Priority 3: Other STEL
    if oel_data.other_stel is not None:
        return (
            oel_data.other_stel,
            oel_data.other_stel_unit or unit,
            "Other STEL",
        )

    # Priority 4: Fallback to Concentration Standard 8hr × 3
    if oel_data.concentration_standard_8hr is not None:
        return (
            oel_data.concentration_standard_8hr * 3,
            oel_data.concentration_standard_8hr_unit or unit,
            "濃度基準値 × 3",
        )

    # Priority 5: Fallback to selected OEL × 3
    if oel_8hr is not None and oel_8hr > 0:
        return (
            oel_8hr * 3,
            unit,
            "OEL 8hr × 3",
        )

    # Priority 6: Fallback to ACRmax × 3
    if acrmax is not None and acrmax > 0:
        return (
            acrmax * 3,
            unit,
            "ACRmax × 3",
        )

    return (None, "", "None")


def convert_oel_units(
    value: float,
    from_unit: str,
    to_unit: str,
    molecular_weight: float,
) -> float:
    """
    Convert OEL between ppm and mg/m³.

    Formula: mg/m³ = ppm × (MW / 24.45)

    Args:
        value: OEL value
        from_unit: Source unit (ppm or mg/m³)
        to_unit: Target unit (ppm or mg/m³)
        molecular_weight: Molecular weight in g/mol

    Returns:
        Converted value
    """
    if from_unit == to_unit:
        return value

    if from_unit == "ppm" and to_unit == "mg/m³":
        # ppm to mg/m³
        return value * (molecular_weight / 24.45)
    elif from_unit == "mg/m³" and to_unit == "ppm":
        # mg/m³ to ppm
        return value * (24.45 / molecular_weight)
    else:
        raise ValueError(f"Cannot convert from {from_unit} to {to_unit}")
