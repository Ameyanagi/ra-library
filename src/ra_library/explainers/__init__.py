"""
Explainers for risk assessment results.

These modules provide human-readable explanations for:
- Why risk level is what it is
- What limits achieving a lower risk level
- Which factors contribute most to risk
"""

from .risk_level import explain_risk_level
from .limitations import explain_limitations, find_minimum_achievable
from .factors import explain_factors, get_factor_contributions

__all__ = [
    "explain_risk_level",
    "explain_limitations",
    "find_minimum_achievable",
    "explain_factors",
    "get_factor_contributions",
]
