"""
RA Library - Chemical Risk Assessment Library

Independent implementation of a chemical risk assessment workflow
with verbose explanations, what-if analysis, and recommendations.

Features:
- Verbose calculations with step-by-step explanations
- What-if analysis for control measure evaluation
- Recommendation engine with prioritized actions
- Limitation transparency (explains when Level I is impossible)
- Bilingual support (English/Japanese)

References:
- Public CREATE-SIMPLE design and manual documents
- HSE COSHH Essentials
- ECETOC TRA
"""

__version__ = "0.2.0"

# Core models
from .models.substance import (
    Substance,
    PropertyType,
    GHSClassification,
    OccupationalExposureLimits,
    PhysicochemicalProperties,
    VolatilityLevel,
    DustinessLevel,
)
from .models.assessment import (
    AssessmentInput,
    AssessmentMode,
    VentilationLevel,
    AmountLevel,
    ExposureVariation,
    SkinArea,
    GloveType,
    RPEType,
    ComponentInput,
    SKIN_AREA_VALUES,
    RPE_APF_VALUES,
)
from .models.risk import RiskLevel, DetailedRiskLevel, RiskResult, InhalationRisk, DermalRisk, PhysicalRisk
from .models.explanation import CalculationExplanation, CalculationStep
from .models.recommendation import Recommendation, RecommendationSet

# Calculators
from .calculators import (
    calculate_exposure,
    calculate_inhalation_risk,
    calculate_dermal_risk,
    calculate_physical_risk,
)

# Recommenders
from .recommenders.inhalation import get_inhalation_recommendations
from .recommenders.dermal import get_dermal_recommendations
from .recommenders.physical import get_physical_recommendations

# Assessment builder (fluent API)
from .assessment import RiskAssessment, AssessmentResult, ComponentResult

# Presets
from .presets import (
    WorkPreset,
    PRESETS,
    get_preset,
    list_presets,
    print_presets,
    # Common presets
    LAB_ORGANIC,
    LAB_POWDER,
    LAB_CATALYST,
    LAB_ANALYTICAL,
    LAB_GAS,
    PRODUCTION_BATCH,
    PRODUCTION_CONTINUOUS,
    MAINTENANCE_CLEANING,
    SPRAY_PAINTING,
)

# Data module
from .data import (
    get_database,
    get_database_metadata,
    lookup_substance,
    SubstanceData,
    SubstanceDatabase,
)
from .services import (
    ServiceError,
    ServiceResult,
    lookup_substances,
    calculate_risk,
    explain_calculation,
    get_recommendations,
)

__all__ = [
    # Version
    "__version__",
    # Substance models
    "Substance",
    "PropertyType",
    "GHSClassification",
    "OccupationalExposureLimits",
    "PhysicochemicalProperties",
    "VolatilityLevel",
    "DustinessLevel",
    # Assessment models
    "AssessmentInput",
    "AssessmentMode",
    "VentilationLevel",
    "AmountLevel",
    "ExposureVariation",
    "SkinArea",
    "GloveType",
    "RPEType",
    "ComponentInput",
    "SKIN_AREA_VALUES",
    "RPE_APF_VALUES",
    # Risk models
    "RiskLevel",
    "DetailedRiskLevel",
    "RiskResult",
    "InhalationRisk",
    "DermalRisk",
    "PhysicalRisk",
    # Explanation models
    "CalculationExplanation",
    "CalculationStep",
    # Recommendation models
    "Recommendation",
    "RecommendationSet",
    # Calculators
    "calculate_exposure",
    "calculate_inhalation_risk",
    "calculate_dermal_risk",
    "calculate_physical_risk",
    # Recommenders
    "get_inhalation_recommendations",
    "get_dermal_recommendations",
    "get_physical_recommendations",
    # Assessment builder
    "RiskAssessment",
    "AssessmentResult",
    "ComponentResult",
    # Presets
    "WorkPreset",
    "PRESETS",
    "get_preset",
    "list_presets",
    "print_presets",
    "LAB_ORGANIC",
    "LAB_POWDER",
    "LAB_CATALYST",
    "LAB_ANALYTICAL",
    "LAB_GAS",
    "PRODUCTION_BATCH",
    "PRODUCTION_CONTINUOUS",
    "MAINTENANCE_CLEANING",
    "SPRAY_PAINTING",
    # Data module
    "get_database",
    "get_database_metadata",
    "lookup_substance",
    "SubstanceData",
    "SubstanceDatabase",
    # Services
    "ServiceError",
    "ServiceResult",
    "lookup_substances",
    "calculate_risk",
    "explain_calculation",
    "get_recommendations",
]
