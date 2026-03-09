"""
Tests for ACRmax (Management Target Concentration) calculation.

VBA Reference: modCalc.bas lines 231-277 (CalculateACRMax)
"""

import pytest
from ra_library.calculators.acr import get_acrmax


class TestACRmaxLiquid:
    """Tests for ACRmax liquid values (ppm)."""

    def test_acrmax_liquid_hl5(self):
        """HL5 liquid (Carcinogen 1A/1B) should return 0.05 ppm."""
        assert get_acrmax("HL5", "liquid") == 0.05

    def test_acrmax_liquid_hl4(self):
        """HL4 liquid (Carcinogen 2, Mutagen) should return 0.5 ppm."""
        assert get_acrmax("HL4", "liquid") == 0.5

    def test_acrmax_liquid_hl3(self):
        """HL3 liquid should return 5.0 ppm."""
        assert get_acrmax("HL3", "liquid") == 5.0

    def test_acrmax_liquid_hl2(self):
        """HL2 liquid should return 50.0 ppm."""
        assert get_acrmax("HL2", "liquid") == 50.0

    def test_acrmax_liquid_hl1(self):
        """HL1 liquid should return 500.0 ppm."""
        assert get_acrmax("HL1", "liquid") == 500.0


class TestACRmaxSolid:
    """Tests for ACRmax solid values (mg/m³)."""

    def test_acrmax_solid_hl5(self):
        """HL5 solid (Carcinogen 1A/1B) should return 0.001 mg/m³."""
        assert get_acrmax("HL5", "solid") == 0.001

    def test_acrmax_solid_hl4(self):
        """HL4 solid (Carcinogen 2, Mutagen) should return 0.01 mg/m³."""
        assert get_acrmax("HL4", "solid") == 0.01

    def test_acrmax_solid_hl3(self):
        """HL3 solid should return 0.1 mg/m³."""
        assert get_acrmax("HL3", "solid") == 0.1

    def test_acrmax_solid_hl2(self):
        """HL2 solid should return 1.0 mg/m³."""
        assert get_acrmax("HL2", "solid") == 1.0

    def test_acrmax_solid_hl1(self):
        """HL1 solid should return 10.0 mg/m³."""
        assert get_acrmax("HL1", "solid") == 10.0


class TestACRmaxEdgeCases:
    """Tests for edge cases."""

    def test_acrmax_unknown_hazard_level(self):
        """Unknown hazard level should return None."""
        assert get_acrmax("HL99", "liquid") is None
        assert get_acrmax("HL99", "solid") is None

    def test_acrmax_invalid_property_type(self):
        """Invalid property type should raise or return None."""
        # The function should handle invalid property types gracefully
        result = get_acrmax("HL5", "gas")
        assert result is None

    def test_acrmax_none_inputs(self):
        """None inputs should return None."""
        assert get_acrmax(None, "liquid") is None
        assert get_acrmax("HL5", None) is None
