"""Service-layer APIs used by transport wrappers."""

from .common import ServiceError, ServiceResult
from .substances import lookup_substances
from .calculate import calculate_risk
from .explain import explain_calculation
from .recommendations import get_recommendations

__all__ = [
    "ServiceError",
    "ServiceResult",
    "lookup_substances",
    "calculate_risk",
    "explain_calculation",
    "get_recommendations",
]
