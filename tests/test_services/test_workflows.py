"""Service-layer workflow tests."""

from __future__ import annotations

import pytest

from ra_library.assessment.result import AssessmentResult
from ra_library.services import ServiceError, calculate_risk, get_recommendations, lookup_substances


def test_lookup_substances_returns_structured_results():
    """Service lookup should return the same transport-ready payload shape."""
    result = lookup_substances(query="50-00-0", search_by="cas")

    assert result.data["found"] is True
    assert result.data["count"] == 1
    assert result.data["results"][0]["cas_number"] == "50-00-0"


def test_calculate_risk_raises_machine_readable_error_for_invalid_methodology():
    """Invalid methodology should fail with a typed service error."""
    with pytest.raises(ServiceError) as exc_info:
        calculate_risk(
            substances=[{"cas_number": "7440-06-4", "content_percent": 100.0}],
            methodology_version="v0.0.0",
        )

    assert exc_info.value.code == "INVALID_METHODOLOGY_VERSION"


def test_get_recommendations_returns_fallback_warning(monkeypatch):
    """Recommendation fallback should still return a usable payload plus warning metadata."""

    def _raise_recommendations(*args, **kwargs):
        raise RuntimeError("forced recommendation failure")

    monkeypatch.setattr(AssessmentResult, "get_recommendations_for_substance", _raise_recommendations)

    result = get_recommendations(cas_number="7440-06-4", target_level="I")

    warning_codes = {warning["code"] for warning in result.warnings}
    assert "RECOMMENDATION_ANALYSIS_FALLBACK" in warning_codes
    assert result.data["mode"] == "fallback"


def test_calculate_risk_defaults_to_v32_methodology():
    """Default service output should report the latest supported methodology."""
    result = calculate_risk(
        substances=[{"cas_number": "7440-06-4", "content_percent": 100.0}],
        assess_dermal=False,
        assess_physical=False,
        include_recommendations="never",
    )

    assert result.data["methodology"]["version"] == "v3.2"
    assert result.data["methodology"]["details"]["is_recommended"] is True


def test_calculate_risk_hydrogen_uses_workbook_faithful_gas_behavior():
    """Hydrogen should expose gas skips plus workbook-faithful quantity metadata."""
    result = calculate_risk(
        substances=[{"cas_number": "1333-74-0", "content_percent": 100.0}],
        preset="lab_gas",
        assess_inhalation=True,
        assess_dermal=True,
        assess_physical=True,
        include_recommendations="never",
    )

    payload = result.data
    component = payload["components"]["1333-74-0"]

    assert payload["conditions_used"]["property_type"]["key"] == "gas"
    assert payload["conditions_used"]["amount"]["band_basis"] == "workbook_q1_gas_mass_band"
    assert payload["conditions_used"]["amount"]["volume_equivalent_at_25c_1atm"]["max_liters"] is not None
    assert component["inhalation"]["status"] == "not_assessed"
    assert component["inhalation"]["reason_code"] == "WORKBOOK_GAS_HEALTH_RA_NOT_ASSESSED"
    assert component["dermal"]["status"] == "not_assessed"
    assert component["physical"]["hazard_type"] == "flammable_gas"
    assert component["risk_label"] == "III"
    assert component["gas_quantity_estimate"]["volume_equivalent_at_25c_1atm"]["min_liters"] is not None
