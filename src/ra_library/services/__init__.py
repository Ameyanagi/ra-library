"""Service-layer APIs used by transport wrappers."""

from .common import ServiceError, ServiceResult
from .substances import lookup_substances
from .calculate import calculate_control_scenarios, calculate_risk
from .explain import explain_calculation
from .recommendations import get_recommendations
from .presets import list_preset_profiles

__all__ = [
    "ServiceError",
    "ServiceResult",
    "lookup_substances",
    "calculate_risk",
    "calculate_control_scenarios",
    "explain_calculation",
    "get_recommendations",
    "list_preset_profiles",
]
