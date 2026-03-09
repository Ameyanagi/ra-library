"""Risk assessment calculators."""

from .constants import (
    MIN_EXPOSURE_LIQUID,
    MIN_EXPOSURE_SOLID,
    ACRMAX_VALUES,
    CUTOFF_SKIN_HAZARD,
    CUTOFF_SPECIFIED_CHEMICAL,
    CUTOFF_ORGANIC_SOLVENT,
    EXPOSURE_BANDS_LIQUID,
    EXPOSURE_BANDS_SOLID,
    CONTENT_COEFFICIENTS,
    VENTILATION_COEFFICIENTS,
    DURATION_COEFFICIENTS,
)
from .exposure import (
    calculate_exposure,
    get_exposure_band,
    apply_content_coefficient,
    apply_ventilation_coefficient,
    apply_minimum_floor,
)
from .oel import select_oel, get_oel_source
from .acr import get_acrmax, calculate_rcr
from .inhalation import calculate_inhalation_risk
from .dermal import calculate_dermal_risk
from .physical import calculate_physical_risk
from .rpe import calculate_apf_coefficient
from .version_comparison import (
    compare_versions,
    calculate_v2_comparison,
    calculate_v302_comparison,
    get_v3_risk_level,
    V2ComparisonResult,
    V3ComparisonResult,
    CreateSimpleVersion,
    EXPOSURE_FLOOR_LIQUID_PPM,
    EXPOSURE_FLOOR_SOLID_MG_M3,
)
from .version_calculators import (
    CalculationVersion,
    VersionConfig,
    VersionCalculator,
    ExposureResult,
    RegulatoryResult,
    compare_versions as compare_versions_detailed,
)

__all__ = [
    # Constants
    "MIN_EXPOSURE_LIQUID",
    "MIN_EXPOSURE_SOLID",
    "ACRMAX_VALUES",
    "CUTOFF_SKIN_HAZARD",
    "CUTOFF_SPECIFIED_CHEMICAL",
    "CUTOFF_ORGANIC_SOLVENT",
    "EXPOSURE_BANDS_LIQUID",
    "EXPOSURE_BANDS_SOLID",
    "CONTENT_COEFFICIENTS",
    "VENTILATION_COEFFICIENTS",
    "DURATION_COEFFICIENTS",
    # Calculators
    "calculate_exposure",
    "get_exposure_band",
    "apply_content_coefficient",
    "apply_ventilation_coefficient",
    "apply_minimum_floor",
    "select_oel",
    "get_oel_source",
    "get_acrmax",
    "calculate_rcr",
    "calculate_inhalation_risk",
    "calculate_dermal_risk",
    "calculate_physical_risk",
    "calculate_apf_coefficient",
    # Version comparison
    "compare_versions",
    "calculate_v2_comparison",
    "calculate_v302_comparison",
    "get_v3_risk_level",
    "V2ComparisonResult",
    "V3ComparisonResult",
    "CreateSimpleVersion",
    "EXPOSURE_FLOOR_LIQUID_PPM",
    "EXPOSURE_FLOOR_SOLID_MG_M3",
    # Version-specific calculators
    "CalculationVersion",
    "VersionConfig",
    "VersionCalculator",
    "ExposureResult",
    "RegulatoryResult",
    "compare_versions_detailed",
]
