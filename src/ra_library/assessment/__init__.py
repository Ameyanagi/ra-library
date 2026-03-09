"""
Assessment module for chemical risk assessment.

Provides a fluent builder API for constructing and executing risk assessments.
"""

from .builder import RiskAssessment
from .result import AssessmentResult, ComponentResult

__all__ = [
    "RiskAssessment",
    "AssessmentResult",
    "ComponentResult",
]
