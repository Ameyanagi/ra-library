"""
Risk assessment input and output models.

References:
- CREATE-SIMPLE Design Document v3.1.1, Sections 3-7
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

from .substance import PropertyType


class AssessmentMode(str, Enum):
    """
    Assessment mode - determines available control options.

    Reference: CREATE-SIMPLE VBA modRASheet.bas vs modRAReport.bas

    Key difference: Report mode (実施レポート) allows RPE selection,
    while RA Sheet mode does NOT support RPE (apfCoeff = 1 always).
    """

    RA_SHEET = "ra_sheet"  # リスクアセスメントシート (No RPE)
    REPORT = "report"  # 実施レポート (RPE available)


class AmountLevel(str, Enum):
    """
    Usage amount classification.

    Reference: CREATE-SIMPLE Design v3.1.1, Figure 12
    """

    LARGE = "large"  # 大量: ≥1kL (liquid) or ≥1ton (solid)
    MEDIUM = "medium"  # 中量: 1L-1kL or 1kg-1ton
    SMALL = "small"  # 少量: 100mL-1L or 100g-1kg
    MINUTE = "minute"  # 微量: 10mL-100mL or 10g-100g
    TRACE = "trace"  # 極微量: <10mL or <10g


class VentilationLevel(str, Enum):
    """
    Ventilation condition classification.

    Reference: CREATE-SIMPLE Design v3.1.1, Figure 17
    """

    NONE = "none"  # Level A: No ventilation (coefficient: 4)
    BASIC = "basic"  # Level B: Basic ventilation (coefficient: 3)
    INDUSTRIAL = "industrial"  # Level C: Industrial/outdoor (coefficient: 1)
    LOCAL_EXTERNAL = "local_ext"  # Level D: Local exhaust - external
    LOCAL_ENCLOSED = "local_enc"  # Level E: Local exhaust - enclosed
    SEALED = "sealed"  # Level F: Sealed container (coefficient: 0.001)


class ExposureVariation(str, Enum):
    """
    Exposure variation pattern for STEL calculation.

    Reference: CREATE-SIMPLE Design v3.1 (June 2025), Figure 23

    The variation pattern determines the STEL multiplier:
    - SMALL: GSD = 3.0 → STEL = 8hr TWA × 4
    - LARGE: GSD = 6.0 → STEL = 8hr TWA × 6

    Legacy values (constant, intermittent, brief) are mapped to SMALL for
    backwards compatibility.
    """

    SMALL = "small"  # ばらつきの小さな作業 (GSD = 3.0, multiplier: 4)
    LARGE = "large"  # ばらつきの大きな作業 (GSD = 6.0, multiplier: 6)
    # Legacy values - kept for backwards compatibility
    CONSTANT = "constant"  # Maps to SMALL
    INTERMITTENT = "intermittent"  # Maps to SMALL
    BRIEF = "brief"  # Maps to SMALL

    def get_stel_multiplier(self) -> float:
        """
        Get the STEL multiplier for this variation pattern.

        Reference: CREATE-SIMPLE Design v3.1, Figure 23
        """
        if self in (
            ExposureVariation.LARGE,
        ):
            return 6.0
        # SMALL and all legacy values use multiplier 4
        return 4.0


class SkinArea(str, Enum):
    """
    Exposed skin area options.

    Reference: CREATE-SIMPLE SelectList.csv Q8_Exposure_area
    Values match the official CREATE-SIMPLE documentation.
    """

    COIN_SPLASH = "coin_splash"  # 大きなコインのサイズ、小さな飛沫: 10 cm²
    PALM_ONE = "palm_one"  # 片手の手のひら付着: 240 cm²
    PALM_BOTH = "palm_both"  # 両手の手のひらに付着: 480 cm²
    HANDS_BOTH = "hands_both"  # 両手全体に付着: 960 cm²
    WRISTS = "wrists"  # 両手及び手首: 1500 cm²
    FOREARMS = "forearms"  # 両手の肘から下全体: 1980 cm²


# Skin area values in cm² - matches CREATE-SIMPLE Q8
SKIN_AREA_VALUES: dict[SkinArea, float] = {
    SkinArea.COIN_SPLASH: 10,
    SkinArea.PALM_ONE: 240,
    SkinArea.PALM_BOTH: 480,
    SkinArea.HANDS_BOTH: 960,
    SkinArea.WRISTS: 1500,
    SkinArea.FOREARMS: 1980,
}


class GloveType(str, Enum):
    """Chemical protective glove classification."""

    NONE = "none"  # なし (coefficient: 1.0)
    NON_RESISTANT = "non_resistant"  # 非耐透過性 (coefficient: 1.0)
    RESISTANT = "resistant"  # 耐透過性・耐浸透性 (coefficient: 0.2)


class RPEType(str, Enum):
    """
    Respiratory Protective Equipment (RPE) classification.

    Only available in Report mode (実施レポート).
    NOT available in RA Sheet mode.

    Reference: CREATE-SIMPLE VBA modRAReport.bas lines 775-782
    """

    NONE = "none"  # なし (APF: 1)
    # Loose-fit types (ルーズフィット型) - No fit test required
    LOOSE_FIT_11 = "loose_fit_11"  # APF: 11
    LOOSE_FIT_20 = "loose_fit_20"  # APF: 20
    LOOSE_FIT_25 = "loose_fit_25"  # APF: 25
    # Tight-fit types (タイトフィット型) - Fit test required
    TIGHT_FIT_10 = "tight_fit_10"  # APF: 10
    TIGHT_FIT_50 = "tight_fit_50"  # APF: 50
    TIGHT_FIT_100 = "tight_fit_100"  # APF: 100
    TIGHT_FIT_1000 = "tight_fit_1000"  # APF: 1000
    TIGHT_FIT_10000 = "tight_fit_10000"  # APF: 10000


# RPE APF (Assigned Protection Factor) values
RPE_APF_VALUES: dict[RPEType, int] = {
    RPEType.NONE: 1,
    RPEType.LOOSE_FIT_11: 11,
    RPEType.LOOSE_FIT_20: 20,
    RPEType.LOOSE_FIT_25: 25,
    RPEType.TIGHT_FIT_10: 10,
    RPEType.TIGHT_FIT_50: 50,
    RPEType.TIGHT_FIT_100: 100,
    RPEType.TIGHT_FIT_1000: 1000,
    RPEType.TIGHT_FIT_10000: 10000,
}


class ComponentInput(BaseModel):
    """Input data for a single chemical component."""

    cas_number: str
    name: Optional[str] = None
    content_percent: float = Field(..., ge=0, le=100)
    volatility_or_dustiness: Optional[str] = None  # Override auto-detection


class AssessmentInput(BaseModel):
    """Input data for a risk assessment."""

    # Assessment mode - determines available control options
    mode: AssessmentMode = AssessmentMode.RA_SHEET

    # Basic information
    title: str = ""
    assessor: str = ""
    workplace: str = ""
    work_description: str = ""

    # Assessment targets
    assess_inhalation: bool = True
    assess_dermal: bool = False
    assess_physical: bool = False

    # Product information
    product_property: PropertyType = PropertyType.LIQUID

    # Component information (up to 10)
    components: List[ComponentInput] = Field(default_factory=list)

    # Work conditions (STEP 3 questions)
    amount_level: AmountLevel = AmountLevel.MEDIUM
    is_spray_operation: bool = False
    work_area_size: Optional[str] = None  # Only for liquids: "small", "medium", "large"
    ventilation: VentilationLevel = VentilationLevel.INDUSTRIAL
    control_velocity_verified: bool = False
    working_hours_per_day: float = 8.0
    frequency_type: str = "weekly"  # "weekly" or "less_than_weekly"
    frequency_value: int = 5  # days per week or days per month
    exposure_variation: ExposureVariation = ExposureVariation.CONSTANT

    # Dermal exposure conditions
    exposed_skin_area: Optional[SkinArea] = None
    glove_type: Optional[GloveType] = None
    glove_training: bool = False

    # Respiratory Protective Equipment (Report mode only)
    # In RA Sheet mode, these fields are ignored (apfCoeff = 1 always)
    rpe_type: Optional[RPEType] = None
    rpe_fit_tested: bool = False  # For tight-fit types
    rpe_fit_test_multiplier: Optional[float] = None  # 0.1-1.0

    # Physical hazard conditions
    process_temperature: Optional[float] = None  # °C
    has_ignition_sources: bool = False
    has_explosive_atmosphere: bool = False
    has_organic_matter: bool = False
    has_air_water_contact: bool = False

    # Exposure calculation options
    ignore_minimum_floor: bool = False  # Disable 0.001 mg/m³ (solid) / 0.005 ppm (liquid) floor
