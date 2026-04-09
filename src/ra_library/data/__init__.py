"""
Data module for ra-library.

Provides access to substance database and other reference data.
"""

from .substance_db import (
    SubstanceData,
    SubstanceDatabase,
    get_database,
    get_database_metadata,
    lookup_substance,
)
from .volatility import (
    calculate_volatility_from_boiling_point,
    calculate_volatility_from_vapor_pressure,
    determine_volatility_level,
    should_treat_solid_as_vapor,
    get_dustiness_level,
    get_volatility_for_assessment,
)
from .hazard_level import (
    get_hazard_level,
    get_hazard_level_numeric,
    is_carcinogen,
    is_mutagen,
    is_reproductive_toxicant,
    is_stot_re,
    is_respiratory_sensitizer,
    has_health_hazards,
)
from .converter import (
    to_substance_model,
    to_ghs_classification,
    to_oel_limits,
    to_physical_properties,
)
from .regulations import (
    check_tokka_regulation,
    check_organic_solvent_regulation,
    check_skin_hazard_regulation,
    get_applicable_regulations,
    get_regulatory_summary,
)
from .regulatory_db import (
    RegulatoryData,
    RegulatoryDatabase,
    get_regulatory_database,
    lookup_regulatory,
    lookup_regulatory_all,
    to_regulatory_info,
    to_regulatory_info_list,
    get_regulatory_info,
    get_regulatory_info_list,
)

__all__ = [
    "SubstanceData",
    "SubstanceDatabase",
    "get_database",
    "get_database_metadata",
    "lookup_substance",
    "calculate_volatility_from_boiling_point",
    "calculate_volatility_from_vapor_pressure",
    "determine_volatility_level",
    "should_treat_solid_as_vapor",
    "get_dustiness_level",
    "get_volatility_for_assessment",
    "get_hazard_level",
    "get_hazard_level_numeric",
    "is_carcinogen",
    "is_mutagen",
    "is_reproductive_toxicant",
    "is_stot_re",
    "is_respiratory_sensitizer",
    "has_health_hazards",
    "to_substance_model",
    "to_ghs_classification",
    "to_oel_limits",
    "to_physical_properties",
    "check_tokka_regulation",
    "check_organic_solvent_regulation",
    "check_skin_hazard_regulation",
    "get_applicable_regulations",
    "get_regulatory_summary",
    # Regulatory database
    "RegulatoryData",
    "RegulatoryDatabase",
    "get_regulatory_database",
    "lookup_regulatory",
    "lookup_regulatory_all",
    "to_regulatory_info",
    "to_regulatory_info_list",
    "get_regulatory_info",
    "get_regulatory_info_list",
]
