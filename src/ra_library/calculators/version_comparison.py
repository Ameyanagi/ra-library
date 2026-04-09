"""
Version comparison calculator for CREATE-SIMPLE methodology.

This module provides version-specific calculation logic for comparison.
Used to show how risk assessments would differ across methodology versions.

References:
- CREATE-SIMPLE v1.0-v2.5.1: Module1.bas / ModCalcRA.bas
- CREATE-SIMPLE v3.0.2: modCalc.bas (no exposure floor)
- CREATE-SIMPLE v3.1+: modCalc.bas (with exposure floor)
- Key differences documented in CALCULATION_EVOLUTION_ANALYSIS.md

Version History Summary:
========================
v1.0-v2.5.1 (v2.x):
  - 3 volatility levels (no very_low)
  - 4 amount levels (no large)
  - Max exposure 500 ppm (liquid), 10 mg/m³ (solid)
  - No STEL, no dermal quantification, no physical hazards
  - Risk levels: I, II, III, IV (no subdivisions)

v3.0.2:
  - 4 volatility levels (added very_low)
  - 5 amount levels (added large)
  - Max exposure 5000 ppm (liquid)
  - STEL, dermal, physical hazards added
  - Risk levels: I, II-A, II-B, III, IV
  - NO exposure floor (can go to any low value)

v3.1+ (v3.1, v3.1.1, v3.1.2, v3.2):
  - Same as v3.0.2 BUT with exposure floor:
    - Liquid: minimum 0.005 ppm
    - Solid: minimum 0.001 mg/m³
  - Enhanced regulatory substance detection
  - Skin hazard cutoff thresholds
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CreateSimpleVersion(Enum):
    """Supported CREATE-SIMPLE versions for comparison."""

    V2 = "v2.x"  # v1.0-v2.5.1 (same core logic)
    V3_0_2 = "v3.0.2"  # First v3 release (no floor)
    V3_1 = "v3.1+"  # v3.1, v3.1.1, v3.1.2 (with floor)
    V3_2 = "v3.2"  # Latest workbook-aligned implementation
    V3 = "v3.2"  # Current implementation (alias for latest)


# =============================================================================
# Exposure Floor Constants (v3.1+ only)
# Reference: modCalc.bas lines 440-447, 459-466 (v3.1.2/v3.2)
# Added in v3.1, NOT present in v3.0.2
# =============================================================================

EXPOSURE_FLOOR_LIQUID_PPM = 0.005  # v3.1+ minimum for liquids
EXPOSURE_FLOOR_SOLID_MG_M3 = 0.001  # v3.1+ minimum for solids


@dataclass
class V2ComparisonResult:
    """Result of v2.x calculation for comparison."""

    version: str
    exposure_ppm: Optional[float]  # For liquids
    exposure_mg_m3: Optional[float]  # For solids
    rcr: float
    risk_level: str  # I, II, III, IV (no II-A/II-B in v2)
    notes: list[str]  # Differences from v3 calculation


@dataclass
class V3ComparisonResult:
    """Result of v3.x calculation for comparison (v3.0.2 vs v3.1+)."""

    version: str
    exposure_ppm: Optional[float]  # For liquids
    exposure_mg_m3: Optional[float]  # For solids
    exposure_floor_applied: bool  # True if floor was applied
    rcr: float
    risk_level: str  # I, II-A, II-B, III, IV
    notes: list[str]  # Differences from current version


# =============================================================================
# v2.x Exposure Band Tables
# Reference: VBA Module1.bas / ModCalcRA.bas (v1.0-v2.5.1)
# Key differences from v3:
# - 3 volatility levels (no "very_low")
# - 4 amount levels (no "large")
# - Max exposure 500 ppm (not 5000 ppm)
# =============================================================================

EXPOSURE_BANDS_V2_LIQUID: dict[tuple[str, str], float] = {
    # High volatility (揮発性高)
    ("high", "medium"): 500,
    ("high", "small"): 50,
    ("high", "minute"): 50,
    ("high", "trace"): 5,
    # Medium volatility (揮発性中)
    ("medium", "medium"): 500,
    ("medium", "small"): 50,
    ("medium", "minute"): 5,
    ("medium", "trace"): 5,
    # Low volatility (揮発性低)
    ("low", "medium"): 50,
    ("low", "small"): 5,
    ("low", "minute"): 5,
    ("low", "trace"): 0.5,
}

EXPOSURE_BANDS_V2_SOLID: dict[tuple[str, str], float] = {
    # High dustiness (飛散性高)
    ("high", "medium"): 10,
    ("high", "small"): 1,
    ("high", "minute"): 0.1,
    ("high", "trace"): 0.1,
    # Medium dustiness (飛散性中)
    ("medium", "medium"): 10,
    ("medium", "small"): 0.1,
    ("medium", "minute"): 0.1,
    ("medium", "trace"): 0.1,
    # Low dustiness (飛散性低)
    ("low", "medium"): 1,
    ("low", "small"): 0.1,
    ("low", "minute"): 0.1,
    ("low", "trace"): 0.01,
}

# v2.x ventilation coefficients (same as v3 but without sealed option in early versions)
VENTILATION_COEFFICIENTS_V2: dict[str, float] = {
    "none": 4.0,
    "basic": 3.0,
    "industrial": 1.0,
    "local_ext": 0.1,  # v2 used fixed 0.1 for external LEV
    "local_enc": 0.01,  # v2 used fixed 0.01 for enclosed LEV
    "sealed": 0.001,  # Added in later v2 versions
}

# v2.x content coefficients (same as v3)
CONTENT_COEFFICIENTS_V2: list[tuple[float, float]] = [
    (25.0, 1.0),  # ≥25%
    (5.0, 0.6),  # 5-25%
    (1.0, 0.2),  # 1-5%
    (0.0, 0.1),  # <1%
]


def get_content_coefficient_v2(content_percent: float) -> float:
    """Get content coefficient using v2 logic."""
    for threshold, coeff in CONTENT_COEFFICIENTS_V2:
        if content_percent >= threshold:
            return coeff
    return 0.1


def get_v2_exposure_band(
    property_type: str,
    volatility_or_dustiness: str,
    amount_level: str,
) -> tuple[Optional[float], list[str]]:
    """
    Get v2.x exposure band value.

    Returns (exposure_value, notes) where notes explain any adaptations made.
    """
    notes = []

    # Adapt v3 volatility to v2 (very_low doesn't exist in v2)
    v2_volatility = volatility_or_dustiness
    if volatility_or_dustiness == "very_low":
        v2_volatility = "low"
        notes.append("v2.x: 'very_low' volatility mapped to 'low' (極低揮発性は低揮発性として評価)")

    # Adapt v3 amount to v2 (large doesn't exist in v2)
    v2_amount = amount_level
    if amount_level == "large":
        v2_amount = "medium"
        notes.append("v2.x: 'large' amount mapped to 'medium' (大量は中量として評価)")

    # Look up exposure band
    key = (v2_volatility, v2_amount)

    if property_type == "liquid":
        exposure = EXPOSURE_BANDS_V2_LIQUID.get(key)
        if exposure is None:
            notes.append(f"v2.x: No exposure band for {key}, using default 500 ppm")
            exposure = 500.0
    else:  # solid
        exposure = EXPOSURE_BANDS_V2_SOLID.get(key)
        if exposure is None:
            notes.append(f"v2.x: No exposure band for {key}, using default 10 mg/m³")
            exposure = 10.0

    return exposure, notes


def calculate_v2_exposure(
    property_type: str,
    volatility_or_dustiness: str,
    amount_level: str,
    content_percent: float = 100.0,
    ventilation: str = "industrial",
    is_spray: bool = False,
    working_hours: float = 8.0,
    days_per_week: int = 5,
) -> tuple[float, list[str]]:
    """
    Calculate exposure using v2.x methodology.

    Returns (exposure, notes) where exposure is in ppm (liquids) or mg/m³ (solids).
    """
    notes = []

    # Get base exposure band
    base_exposure, band_notes = get_v2_exposure_band(
        property_type, volatility_or_dustiness, amount_level
    )
    notes.extend(band_notes)

    # Apply content coefficient
    content_coeff = get_content_coefficient_v2(content_percent)

    # Apply ventilation coefficient
    vent_coeff = VENTILATION_COEFFICIENTS_V2.get(ventilation, 1.0)

    # Apply spray coefficient (same as v3)
    spray_coeff = 10.0 if is_spray else 1.0

    # v2.x time coefficient logic (threshold-based, not linear)
    weekly_hours = working_hours * days_per_week
    if weekly_hours > 40:
        time_coeff = 10.0
    elif weekly_hours <= 4:
        time_coeff = 0.1
    else:
        time_coeff = 1.0

    # Calculate final exposure
    exposure = base_exposure * content_coeff * vent_coeff * spray_coeff * time_coeff

    # v2.x limits
    if property_type == "liquid":
        exposure = min(exposure, 500.0)  # Max 500 ppm in v2
        exposure = max(exposure, 0.005)  # Min 0.005 ppm
    else:
        exposure = min(exposure, 10.0)  # Max 10 mg/m³ in v2
        exposure = max(exposure, 0.0001)  # Min 0.0001 mg/m³

    return exposure, notes


def get_v2_risk_level(rcr: float) -> str:
    """
    Get v2.x risk level (simple I/II/III/IV, no subdivisions).

    Reference: Module1.bas RL_Exposure subroutine.
    """
    if rcr <= 0.1:
        return "I"
    elif rcr <= 1.0:
        return "II"  # No II-A/II-B in v2
    elif rcr <= 10.0:
        return "III"
    else:
        return "IV"


def calculate_v2_comparison(
    property_type: str,
    volatility_or_dustiness: str,
    amount_level: str,
    oel: float,
    content_percent: float = 100.0,
    ventilation: str = "industrial",
    is_spray: bool = False,
    working_hours: float = 8.0,
    days_per_week: int = 5,
    acrmax: Optional[float] = None,
) -> V2ComparisonResult:
    """
    Calculate risk assessment using v2.x methodology for comparison.

    Args:
        property_type: 'liquid' or 'solid'
        volatility_or_dustiness: v3 volatility/dustiness level (will be adapted for v2)
        amount_level: v3 amount level (will be adapted for v2)
        oel: Occupational Exposure Limit
        content_percent: Substance content percentage
        ventilation: Ventilation level
        is_spray: Whether spray operation
        working_hours: Working hours per day
        days_per_week: Days per week
        acrmax: Management target concentration (used if no OEL)

    Returns:
        V2ComparisonResult with calculated values and notes about adaptations.
    """
    notes = []

    # Note that v2 doesn't support STEL or dermal quantification
    notes.append("v2.x: STEL not assessed (短時間ばく露評価なし)")
    notes.append("v2.x: Dermal absorption not quantified (経皮吸収定量評価なし)")

    # Calculate exposure using v2 logic
    exposure, exposure_notes = calculate_v2_exposure(
        property_type=property_type,
        volatility_or_dustiness=volatility_or_dustiness,
        amount_level=amount_level,
        content_percent=content_percent,
        ventilation=ventilation,
        is_spray=is_spray,
        working_hours=working_hours,
        days_per_week=days_per_week,
    )
    notes.extend(exposure_notes)

    # Calculate RCR
    evaluation_standard = oel if oel > 0 else (acrmax if acrmax else 500.0)
    rcr = exposure / evaluation_standard

    # Get v2 risk level
    risk_level = get_v2_risk_level(rcr)

    # Build result
    return V2ComparisonResult(
        version="v2.x (CREATE-SIMPLE v1.0-v2.5.1)",
        exposure_ppm=exposure if property_type == "liquid" else None,
        exposure_mg_m3=exposure if property_type == "solid" else None,
        rcr=round(rcr, 4),
        risk_level=risk_level,
        notes=notes,
    )


# =============================================================================
# v3.0.2 Specific Functions (no exposure floor)
# Reference: modCalc.bas (v3.0.2) - lines 438-461 have NO floor check
# =============================================================================


def get_v3_risk_level(rcr: float) -> str:
    """
    Get v3.x risk level (with II-A/II-B subdivisions).

    Reference: modCalc.bas DetermineRiskLevelInhalation8Hour.
    Same for v3.0.2 and v3.1+.
    """
    if rcr <= 0.1:
        return "I"
    elif rcr <= 0.5:
        return "II-A"
    elif rcr <= 1.0:
        return "II-B"
    elif rcr <= 10.0:
        return "III"
    else:
        return "IV"


def calculate_v302_exposure_without_floor(
    v31_exposure: float,
    property_type: str,
) -> tuple[float, bool, list[str]]:
    """
    Calculate what v3.0.2 exposure would be (without floor).

    v3.0.2 does NOT have the exposure floor that v3.1+ has.
    This function takes the v3.1+ exposure and removes the floor effect.

    Args:
        v31_exposure: The exposure calculated with v3.1+ logic (with floor)
        property_type: 'liquid' or 'solid'

    Returns:
        (v302_exposure, floor_was_applied, notes)
        - v302_exposure: Same as v31 if above floor, otherwise "unknown" (floor was applied)
        - floor_was_applied: True if v31 exposure was at the floor value
        - notes: Explanation of differences
    """
    notes = []

    if property_type == "liquid":
        floor = EXPOSURE_FLOOR_LIQUID_PPM
        if v31_exposure <= floor:
            # v3.1+ applied floor - v3.0.2 would have a lower value
            notes.append(
                f"v3.0.2: No exposure floor (v3.1+ applied {floor} ppm floor)"
            )
            notes.append(
                "v3.0.2: Actual exposure could be lower than floor value"
            )
            return v31_exposure, True, notes
    else:  # solid
        floor = EXPOSURE_FLOOR_SOLID_MG_M3
        if v31_exposure <= floor:
            notes.append(
                f"v3.0.2: No exposure floor (v3.1+ applied {floor} mg/m³ floor)"
            )
            notes.append(
                "v3.0.2: Actual exposure could be lower than floor value"
            )
            return v31_exposure, True, notes

    # Above floor - v3.0.2 and v3.1+ would calculate the same
    return v31_exposure, False, notes


def calculate_v302_comparison(
    property_type: str,
    v31_exposure: float,
    oel: float,
    acrmax: Optional[float] = None,
) -> V3ComparisonResult:
    """
    Calculate risk assessment showing v3.0.2 differences from v3.1+.

    The main difference is that v3.0.2 has no exposure floor.
    When exposure is very low, v3.0.2 would show lower values than v3.1+.

    Args:
        property_type: 'liquid' or 'solid'
        v31_exposure: Exposure calculated with v3.1+ methodology
        oel: Occupational Exposure Limit
        acrmax: Management target concentration (used if no OEL)

    Returns:
        V3ComparisonResult showing v3.0.2 behavior.
    """
    notes = []

    # Check if floor was applied
    v302_exposure, floor_applied, floor_notes = calculate_v302_exposure_without_floor(
        v31_exposure, property_type
    )
    notes.extend(floor_notes)

    if not floor_applied:
        notes.append("v3.0.2: Same exposure as v3.1+ (above floor threshold)")

    # Calculate RCR
    evaluation_standard = oel if oel > 0 else (acrmax if acrmax else 500.0)
    rcr = v302_exposure / evaluation_standard

    # Get risk level (same logic in v3.0.2 and v3.1+)
    risk_level = get_v3_risk_level(rcr)

    return V3ComparisonResult(
        version="v3.0.2 (CREATE-SIMPLE)",
        exposure_ppm=v302_exposure if property_type == "liquid" else None,
        exposure_mg_m3=v302_exposure if property_type == "solid" else None,
        exposure_floor_applied=floor_applied,
        rcr=round(rcr, 4),
        risk_level=risk_level,
        notes=notes,
    )


def compare_versions(
    property_type: str,
    volatility_or_dustiness: str,
    amount_level: str,
    oel: float,
    v3_exposure: float,
    v3_rcr: float,
    v3_risk_level: str,
    content_percent: float = 100.0,
    ventilation: str = "industrial",
    is_spray: bool = False,
    working_hours: float = 8.0,
    days_per_week: int = 5,
    acrmax: Optional[float] = None,
    include_v302: bool = True,
) -> dict:
    """
    Compare v3.1+ calculation result with older methodologies.

    Returns a comparison dict showing differences between versions:
    - v3_current: Current v3.2 results (recommended)
    - v302_intermediate: v3.0.2 results (no exposure floor)
    - v2_legacy: v2.x results (older methodology)

    Args:
        property_type: 'liquid' or 'solid'
        volatility_or_dustiness: Volatility/dustiness level
        amount_level: Amount level
        oel: Occupational Exposure Limit
        v3_exposure: Exposure from v3.1+ calculation
        v3_rcr: RCR from v3.1+ calculation
        v3_risk_level: Risk level from v3.1+ calculation
        content_percent: Substance content percentage
        ventilation: Ventilation level
        is_spray: Whether spray operation
        working_hours: Working hours per day
        days_per_week: Days per week
        acrmax: Management target concentration (fallback if no OEL)
        include_v302: Include v3.0.2 comparison (default True)

    Returns:
        Comparison dict with v3_current, v302_intermediate (optional), v2_legacy,
        and comparison_summary.
    """
    # Calculate using v2 methodology
    v2_result = calculate_v2_comparison(
        property_type=property_type,
        volatility_or_dustiness=volatility_or_dustiness,
        amount_level=amount_level,
        oel=oel,
        content_percent=content_percent,
        ventilation=ventilation,
        is_spray=is_spray,
        working_hours=working_hours,
        days_per_week=days_per_week,
        acrmax=acrmax,
    )

    # Calculate v3.0.2 comparison if requested
    v302_result = None
    if include_v302:
        v302_result = calculate_v302_comparison(
            property_type=property_type,
            v31_exposure=v3_exposure,
            oel=oel,
            acrmax=acrmax,
        )

    # Determine exposure unit
    unit = "ppm" if property_type == "liquid" else "mg/m³"
    v2_exposure = v2_result.exposure_ppm if property_type == "liquid" else v2_result.exposure_mg_m3

    # Build comparison
    comparison = {
        "v3_current": {
            "version": "v3.2 (CREATE-SIMPLE 最新版)",
            "exposure": round(v3_exposure, 4),
            "exposure_unit": unit,
            "rcr": round(v3_rcr, 4),
            "risk_level": v3_risk_level,
            "recommended": True,
            "features": [
                "8時間TWA",
                "短時間STEL",
                "経皮吸収",
                "物理的危険性",
                "ばく露下限値 (exposure floor)",
            ],
            "floor_values": {
                "liquid_ppm": EXPOSURE_FLOOR_LIQUID_PPM,
                "solid_mg_m3": EXPOSURE_FLOOR_SOLID_MG_M3,
            },
        },
    }

    # Add v3.0.2 comparison if calculated
    if v302_result:
        v302_exposure = (
            v302_result.exposure_ppm
            if property_type == "liquid"
            else v302_result.exposure_mg_m3
        )
        comparison["v302_intermediate"] = {
            "version": v302_result.version,
            "exposure": round(v302_exposure, 4) if v302_exposure else None,
            "exposure_unit": unit,
            "rcr": v302_result.rcr,
            "risk_level": v302_result.risk_level,
            "recommended": False,
            "features": [
                "8時間TWA",
                "短時間STEL",
                "経皮吸収",
                "物理的危険性",
            ],
            "floor_applied_in_v31": v302_result.exposure_floor_applied,
            "notes": v302_result.notes,
        }

    # Add v2 legacy comparison
    comparison["v2_legacy"] = {
        "version": v2_result.version,
        "exposure": round(v2_exposure, 4) if v2_exposure else None,
        "exposure_unit": unit,
        "rcr": v2_result.rcr,
        "risk_level": v2_result.risk_level,
        "recommended": False,
        "features": ["8時間TWAのみ"],
        "adaptation_notes": v2_result.notes,
    }

    # Build comparison summary
    comparison["comparison_summary"] = {
        "risk_level_differs_v2": v3_risk_level != v2_result.risk_level,
        "v3_more_conservative_than_v2": v3_rcr > v2_result.rcr,
        "recommendation": "v3.2を推奨 (最新の評価手法、STEL・経皮・物理危険性を含む)",
    }

    # Add v3.0.2 specific comparison notes
    if v302_result and v302_result.exposure_floor_applied:
        comparison["comparison_summary"]["floor_note"] = (
            "v3.1+ではばく露下限値が適用されました。"
            "v3.0.2では下限値がないため、より低いばく露値・RCRになる可能性があります。"
        )

    # Add specific difference notes
    if v3_risk_level != v2_result.risk_level:
        comparison["comparison_summary"]["risk_difference"] = (
            f"v3={v3_risk_level}, v2={v2_result.risk_level}"
        )
        if v3_rcr > v2_result.rcr:
            comparison["comparison_summary"]["note"] = (
                "v3ではより保守的な評価 (リスクレベルが高い)"
            )
        else:
            comparison["comparison_summary"]["note"] = (
                "v2では評価手法の違いによりリスクレベルが異なる"
            )

    return comparison
