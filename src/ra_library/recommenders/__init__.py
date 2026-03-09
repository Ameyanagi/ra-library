"""
Recommendation engine for risk reduction.

These modules generate actionable recommendations for:
- Reducing inhalation risk
- Reducing dermal risk
- Reducing physical hazard risk
- What-if scenario analysis
"""

from .what_if import WhatIfAnalyzer, WhatIfScenario
from .inhalation import get_inhalation_recommendations
from .dermal import get_dermal_recommendations
from .physical import get_physical_recommendations

__all__ = [
    "WhatIfAnalyzer",
    "WhatIfScenario",
    "get_inhalation_recommendations",
    "get_dermal_recommendations",
    "get_physical_recommendations",
]
