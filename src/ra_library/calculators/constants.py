"""
Constants and lookup tables for risk assessment calculations.

All values are derived from CREATE-SIMPLE VBA code and design document.

References:
- CREATE-SIMPLE Design Document v3.1.1
- VBA source: modCalc.bas
"""

# =============================================================================
# Minimum Exposure Floors
# Reference: CREATE-SIMPLE Design v3.1.1, Section 3.3 footnote 11
# VBA: modCalc.bas lines 441-448
# =============================================================================

MIN_EXPOSURE_LIQUID: float = 0.005  # ppm
MIN_EXPOSURE_SOLID: float = 0.001  # mg/m³


# =============================================================================
# ACRmax Values (Management Target Concentration)
# Reference: CREATE-SIMPLE Design v3.1.1, Section 5.3.3
# VBA Reference: modCalc.bas lines 231-277 (CalculateACRMax)
# =============================================================================

# Liquid ACRmax values (ppm)
ACRMAX_VALUES_LIQUID: dict[str, float] = {
    "HL5": 0.05,   # Carcinogen 1A/1B
    "HL4": 0.5,    # Carcinogen 2, Mutagen 1A/1B/2
    "HL3": 5.0,    # General hazards
    "HL2": 50.0,   # Moderate hazards
    "HL1": 500.0,  # Low hazards
}

# Solid ACRmax values (mg/m³)
ACRMAX_VALUES_SOLID: dict[str, float] = {
    "HL5": 0.001,  # Carcinogen 1A/1B
    "HL4": 0.01,   # Carcinogen 2, Mutagen 1A/1B/2
    "HL3": 0.1,    # General hazards
    "HL2": 1.0,    # Moderate hazards
    "HL1": 10.0,   # Low hazards
}

# Legacy alias for backwards compatibility
ACRMAX_VALUES: dict[str, float] = ACRMAX_VALUES_LIQUID


# =============================================================================
# Regulatory Cutoffs (裾切値)
# Reference: VBA modCalc.bas lines 691-695
# =============================================================================

CUTOFF_SKIN_HAZARD: float = 1.0  # 皮膚等障害化学物質: 1%
CUTOFF_SPECIFIED_CHEMICAL: float = 1.0  # 特定化学物質: 1%
CUTOFF_ORGANIC_SOLVENT: float = 5.0  # 有機溶剤: 5%


# =============================================================================
# Exposure Band Tables
# Reference: CREATE-SIMPLE Design v3.1.1, Figure 10 (liquid), Figure 11 (solid)
# VBA: modCalc.bas lines 326-394 (CalcEpBandMax function)
# =============================================================================

# Liquid exposure bands (ppm)
# Keys: (volatility, amount_level)
# VBA Reference: modCalc.bas lines 326-365 (CalculateExposureBands)
EXPOSURE_BANDS_LIQUID: dict[tuple[str, str], float] = {
    # High volatility (揮発性高) - VBA case 1
    # VBA: large=5000, medium=500, small/minute=50, trace=5
    ("high", "large"): 5000,
    ("high", "medium"): 500,
    ("high", "small"): 50,
    ("high", "minute"): 50,
    ("high", "trace"): 5,
    # Medium volatility (揮発性中) - VBA case 2
    # VBA: large/medium=500, small=50, minute/trace=5
    ("medium", "large"): 500,
    ("medium", "medium"): 500,
    ("medium", "small"): 50,
    ("medium", "minute"): 5,
    ("medium", "trace"): 5,
    # Low volatility (揮発性低) - VBA case 3
    # VBA: large/medium=50, small/minute=5, trace=0.5
    ("low", "large"): 50,
    ("low", "medium"): 50,
    ("low", "small"): 5,
    ("low", "minute"): 5,
    ("low", "trace"): 0.5,
    # Very low volatility (揮発性極低) - VBA case 4
    # VBA: large/medium=5, small/minute=0.5, trace=0.05
    ("very_low", "large"): 5,
    ("very_low", "medium"): 5,
    ("very_low", "small"): 0.5,
    ("very_low", "minute"): 0.5,
    ("very_low", "trace"): 0.05,
}

# Solid exposure bands (mg/m³)
# Keys: (dustiness, amount_level)
# VBA Reference: modCalc.bas lines 367-398 (CalculateExposureBands)
EXPOSURE_BANDS_SOLID: dict[tuple[str, str], float] = {
    # High dustiness (飛散性高) - VBA case 1
    # VBA: large=100, medium=10, small=1, minute/trace=0.1
    ("high", "large"): 100,
    ("high", "medium"): 10,
    ("high", "small"): 1,
    ("high", "minute"): 0.1,
    ("high", "trace"): 0.1,
    # Medium dustiness (飛散性中) - VBA case 2
    # VBA: large=100, medium=10, small/minute/trace=0.1
    ("medium", "large"): 100,
    ("medium", "medium"): 10,
    ("medium", "small"): 0.1,
    ("medium", "minute"): 0.1,
    ("medium", "trace"): 0.1,
    # Low dustiness (飛散性低) - VBA case 3
    # VBA: large/medium=1, small/minute=0.1, trace=0.01
    ("low", "large"): 1,
    ("low", "medium"): 1,
    ("low", "small"): 0.1,
    ("low", "minute"): 0.1,
    ("low", "trace"): 0.01,
}


# =============================================================================
# Content Percentage Coefficients
# Reference: CREATE-SIMPLE Design v3.1.1, Figure 15
# VBA: modCalc.bas lines 399-408
# Based on ECETOC TRA / Raoult's law
# =============================================================================

# Boundaries for content coefficient lookup
CONTENT_COEFFICIENTS: list[tuple[float, float]] = [
    (25.0, 1.0),  # ≥25%: coefficient = 1.0
    (5.0, 0.6),  # 5-25%: coefficient = 0.6 (3/5)
    (1.0, 0.2),  # 1-5%: coefficient = 0.2 (1/5)
    (0.0, 0.1),  # <1%: coefficient = 0.1 (1/10)
]


# =============================================================================
# Ventilation Coefficients
# Reference: CREATE-SIMPLE Design v3.1.1, Figure 17
# VBA: modCalc.bas lines 410-425
# =============================================================================

# Keys: (ventilation_level, control_velocity_verified)
VENTILATION_COEFFICIENTS: dict[tuple[str, bool], float] = {
    # Level A: No ventilation (無換気)
    ("none", False): 4.0,
    ("none", True): 4.0,
    # Level B: Basic ventilation (一般換気)
    ("basic", False): 3.0,
    ("basic", True): 3.0,
    # Level C: Industrial/outdoor ventilation (工業的換気)
    ("industrial", False): 1.0,
    ("industrial", True): 1.0,
    # Level D: Local exhaust - external type (局所排気・外付け式)
    # Reference: Design v3.1.1 Figure 17 - unverified = 1/2, verified = 1/10
    ("local_ext", False): 0.5,  # Unverified (1/2)
    ("local_ext", True): 0.1,  # Control velocity verified (1/10)
    # Level E: Local exhaust - enclosed type (局所排気・囲い式)
    # Reference: Design v3.1.1 Figure 17 - unverified = 1/10, verified = 1/100
    ("local_enc", False): 0.1,  # Unverified (1/10)
    ("local_enc", True): 0.01,  # Control velocity verified
    # Level F: Sealed/enclosed system (密閉系)
    ("sealed", False): 0.001,
    ("sealed", True): 0.001,
}


# =============================================================================
# Duration/Frequency Coefficients
# Reference: CREATE-SIMPLE Design v3.1.1, Figure 18, 19
# =============================================================================

# Weekly frequency coefficients
# Keys: days per week
DURATION_COEFFICIENTS_WEEKLY: dict[int, float] = {
    5: 1.0,  # 5 days/week
    4: 0.8,  # 4 days/week
    3: 0.6,  # 3 days/week
    2: 0.4,  # 2 days/week
    1: 0.2,  # 1 day/week
}

# Less than weekly frequency coefficients
# Keys: days per month
DURATION_COEFFICIENTS_MONTHLY: dict[int, float] = {
    4: 0.2,  # 4 days/month
    3: 0.15,  # 3 days/month
    2: 0.1,  # 2 days/month
    1: 0.05,  # 1 day/month
}

# Working hours coefficients
# Based on 8-hour standard
DURATION_COEFFICIENTS: dict[str, float] = {
    "8": 1.0,
    "6": 0.75,
    "4": 0.5,
    "2": 0.25,
    "1": 0.125,
}


# =============================================================================
# Exposure Variation Coefficients
# =============================================================================

# =============================================================================
# STEL Multipliers (Short-Term Exposure Limit calculation)
# Reference: CREATE-SIMPLE Design v3.1 (June 2025), Figure 23
# STEL = 8-hour TWA × multiplier based on exposure variation (GSD)
# =============================================================================

STEL_MULTIPLIERS: dict[str, float] = {
    "small": 4.0,  # ばらつきの小さな作業 (GSD = 3.0)
    "large": 6.0,  # ばらつきの大きな作業 (GSD = 6.0)
}

# Legacy exposure variation coefficients (deprecated, use STEL_MULTIPLIERS)
# Kept for backwards compatibility
EXPOSURE_VARIATION_COEFFICIENTS: dict[str, float] = {
    "constant": 1.0,  # 常時
    "intermittent": 0.5,  # 間欠
    "brief": 0.1,  # 短時間
}


# =============================================================================
# Spray Operation Coefficient
# Reference: CREATE-SIMPLE Design v3.1.1, Section 3.3
# =============================================================================

SPRAY_COEFFICIENT: float = 10.0


# =============================================================================
# Work Area Size Coefficients (for liquids only)
# Reference: CREATE-SIMPLE Design v3.1.1, Section 3.4.6
# Larger work areas allow for better air dispersion
# =============================================================================

WORK_AREA_SIZE_COEFFICIENTS: dict[str, float] = {
    "small": 1.5,   # Small/confined area - increased concentration
    "medium": 1.0,  # Standard work area - baseline
    "large": 0.5,   # Large/well-ventilated area - dilution effect
}


# =============================================================================
# Glove Coefficients
# =============================================================================

GLOVE_COEFFICIENTS: dict[str, float] = {
    "none": 1.0,
    "non_resistant": 1.0,
    "resistant": 0.2,
}

# Glove training coefficient - reduces dermal exposure when workers are trained
# Reference: CREATE-SIMPLE Design v3.1.1, Section 4
GLOVE_TRAINING_COEFFICIENT: float = 0.5  # 50% reduction with training


# =============================================================================
# Risk Level Thresholds
# Reference: CREATE-SIMPLE Design v3.1.1, Section 5.3
# =============================================================================

RISK_LEVEL_THRESHOLDS: dict[int, tuple[float, float]] = {
    1: (0.0, 0.1),  # Level I: RCR ≤ 0.1
    2: (0.1, 1.0),  # Level II: 0.1 < RCR ≤ 1.0
    3: (1.0, 10.0),  # Level III: 1.0 < RCR ≤ 10.0
    4: (10.0, float("inf")),  # Level IV: RCR > 10.0
}


# =============================================================================
# RPE APF (Assigned Protection Factor) Values
# Reference: CREATE-SIMPLE VBA modRAReport.bas lines 775-782
# NOTE: RPE is ONLY available in Report mode, not RA Sheet mode
# =============================================================================

RPE_APF_VALUES: dict[str, int] = {
    "none": 1,
    "loose_fit_11": 11,
    "loose_fit_20": 20,
    "loose_fit_25": 25,
    "tight_fit_10": 10,
    "tight_fit_50": 50,
    "tight_fit_100": 100,
    "tight_fit_1000": 1000,
    "tight_fit_10000": 10000,
}
