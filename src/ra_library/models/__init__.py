"""Core data models for risk assessment."""

from .substance import (
    Substance,
    PropertyType,
    VolatilityLevel,
    DustinessLevel,
    GHSClassification,
    OccupationalExposureLimits,
    PhysicochemicalProperties,
)
from .assessment import (
    AssessmentInput,
    AssessmentMode,
    ComponentInput,
    AmountLevel,
    VentilationLevel,
    ExposureVariation,
    SkinArea,
    GloveType,
    RPEType,
    RPE_APF_VALUES,
)
from .risk import (
    RiskLevel,
    RiskResult,
    InhalationRisk,
    DermalRisk,
    PhysicalRisk,
)
from .explanation import (
    CalculationStep,
    FactorContribution,
    Limitation,
    CalculationExplanation,
)
from .recommendation import (
    Recommendation,
    ActionCategory,
    Feasibility,
    Effectiveness,
)
from .reference import Reference
from .regulatory import (
    RegulatoryInfo,
    RegulationType,
    REGULATION_LABELS,
    REGULATION_LABELS_EN,
    REGULATION_DESCRIPTIONS,
)

__all__ = [
    # Substance
    "Substance",
    "PropertyType",
    "VolatilityLevel",
    "DustinessLevel",
    "GHSClassification",
    "OccupationalExposureLimits",
    "PhysicochemicalProperties",
    # Assessment
    "AssessmentInput",
    "AssessmentMode",
    "ComponentInput",
    "AmountLevel",
    "VentilationLevel",
    "ExposureVariation",
    "SkinArea",
    "GloveType",
    "RPEType",
    "RPE_APF_VALUES",
    # Risk
    "RiskLevel",
    "RiskResult",
    "InhalationRisk",
    "DermalRisk",
    "PhysicalRisk",
    # Explanation
    "CalculationStep",
    "FactorContribution",
    "Limitation",
    "CalculationExplanation",
    # Recommendation
    "Recommendation",
    "ActionCategory",
    "Feasibility",
    "Effectiveness",
    # Reference
    "Reference",
    # Regulatory
    "RegulatoryInfo",
    "RegulationType",
    "REGULATION_LABELS",
    "REGULATION_LABELS_EN",
    "REGULATION_DESCRIPTIONS",
]
