"""
Visualization data providers for risk assessment.

These modules generate data structures for frontend charts:
- Risk curves showing how risk changes with parameters
- Sensitivity analysis bars
- Interactive slider data
"""

from .risk_curves import (
    generate_risk_curves,
    generate_ventilation_curve,
    generate_amount_curve,
    generate_rpe_curve,
    RiskCurvePoint,
    RiskCurve,
)
from .sensitivity import (
    calculate_sensitivity,
    SensitivityBar,
    SensitivityAnalysis,
)

__all__ = [
    "generate_risk_curves",
    "generate_ventilation_curve",
    "generate_amount_curve",
    "generate_rpe_curve",
    "RiskCurvePoint",
    "RiskCurve",
    "calculate_sensitivity",
    "SensitivityBar",
    "SensitivityAnalysis",
]
