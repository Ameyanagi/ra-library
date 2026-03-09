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
