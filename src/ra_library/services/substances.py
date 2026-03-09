"""Service helpers for substance lookup workflows."""

from __future__ import annotations

from .. import get_database
from .common import ServiceResult


def lookup_substances(
    query: str,
    search_by: str = "auto",
    limit: int = 10,
) -> ServiceResult:
    """Query the substance database by CAS number or name."""
    db = get_database()

    bounded_limit = max(1, min(50, limit))
    effective_search_by = search_by
    if effective_search_by == "auto":
        effective_search_by = "cas" if "-" in query and query.replace("-", "").isdigit() else "name"

    if effective_search_by == "cas":
        data = db.lookup(query)
        if data is None:
            return ServiceResult(
                data={
                    "found": False,
                    "count": 0,
                    "results": [],
                    "message": f"No substance found with CAS: {query}",
                    "query_meta": {
                        "query": query,
                        "search_by": "cas",
                        "limit": bounded_limit,
                    },
                }
            )
        return ServiceResult(
            data={
                "found": True,
                "count": 1,
                "results": [_format_substance(data)],
                "query_meta": {
                    "query": query,
                    "search_by": "cas",
                    "limit": bounded_limit,
                },
            }
        )

    results = db.search_by_name(query, limit=bounded_limit)
    if not results:
        return ServiceResult(
            data={
                "found": False,
                "count": 0,
                "results": [],
                "message": f"No substances found matching: {query}",
                "query_meta": {
                    "query": query,
                    "search_by": "name",
                    "limit": bounded_limit,
                },
            }
        )
    return ServiceResult(
        data={
            "found": True,
            "count": len(results),
            "results": [_format_substance(s) for s in results],
            "query_meta": {
                "query": query,
                "search_by": "name",
                "limit": bounded_limit,
            },
        }
    )


def _format_substance(data) -> dict:
    """Format SubstanceData for transport responses."""
    property_map = {1: "liquid", 2: "solid", 3: "gas"}

    return {
        "cas_number": data.cas_number,
        "name_ja": data.name_ja,
        "name_en": data.name_en,
        "property_type": property_map.get(data.property_type, "unknown"),
        "oel": {
            "conc_standard_8hr_ppm": data.conc_standard_8hr_ppm,
            "conc_standard_8hr_mgm3": data.conc_standard_8hr_mgm3,
            "conc_standard_stel_ppm": data.conc_standard_stel_ppm,
            "jsoh_8hr_ppm": data.jsoh_8hr_ppm,
            "acgih_tlv_twa_ppm": data.acgih_tlv_twa_ppm,
            "acgih_tlv_stel_ppm": data.acgih_tlv_stel_ppm,
            "acgih_skin": data.acgih_skin,
            "dfg_mak_ppm": data.dfg_mak_ppm,
        },
        "physical_properties": {
            "molecular_weight": data.molecular_weight,
            "boiling_point_celsius": data.boiling_point,
            "flash_point_celsius": data.flash_point,
            "vapor_pressure": data.vapor_pressure,
            "vapor_pressure_unit": data.vapor_pressure_unit,
            "log_kow": data.log_kow,
        },
        "classifications": {
            "is_carcinogen": data.is_carcinogen,
            "is_skin_hazard": data.is_skin_hazard,
            "ghs_carcinogenicity": data.ghs_carcinogenicity,
            "ghs_mutagenicity": data.ghs_mutagenicity,
            "ghs_reproductive": data.ghs_reproductive,
            "ghs_skin_sens": data.ghs_skin_sens,
            "ghs_resp_sens": data.ghs_resp_sens,
            "ghs_acute_oral": data.ghs_acute_oral,
            "ghs_acute_dermal": data.ghs_acute_dermal,
            "ghs_flam_liq": data.ghs_flam_liq,
        },
    }
