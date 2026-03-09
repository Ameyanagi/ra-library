"""
Tests for OEL (Occupational Exposure Limit) selection.

VBA Reference: modCalc.bas lines 80-229
"""

import pytest
from ra_library.models.substance import OccupationalExposureLimits
from ra_library.calculators.oel import select_oel, select_oel_stel


class TestOELSelection:
    """Tests for 8-hour OEL selection."""

    def test_concentration_standard_can_be_selected_when_lowest(self):
        """Concentration standard is selected when it is the lowest available OEL."""
        oel = OccupationalExposureLimits(
            concentration_standard_8hr=1.0,
            concentration_standard_8hr_unit="ppm",
            jsoh_8hr=50.0,
            acgih_tlv_twa=20.0,
        )
        value, unit, source = select_oel(oel)
        assert value == 1.0
        assert source == "濃度基準値"

    def test_selects_lowest_available_oel_not_source_priority(self):
        """The lowest available OEL is selected regardless of source ordering."""
        oel = OccupationalExposureLimits(
            jsoh_8hr=50.0,
            jsoh_8hr_unit="ppm",
            acgih_tlv_twa=20.0,
        )
        value, unit, source = select_oel(oel)
        assert value == 20.0
        assert "ACGIH" in source

    def test_acgih_selected_when_only_source(self):
        """ACGIH TLV-TWA is selected when it is the only available source."""
        oel = OccupationalExposureLimits(
            acgih_tlv_twa=20.0,
            acgih_tlv_twa_unit="ppm",
        )
        value, unit, source = select_oel(oel)
        assert value == 20.0
        assert "ACGIH" in source

    def test_returns_none_when_no_oel_values(self):
        """Empty OEL data returns the documented no-data tuple."""
        oel = OccupationalExposureLimits()
        value, unit, source = select_oel(oel)
        assert value is None
        assert unit == ""
        assert source == "None"


class TestOELSTELSelection:
    """
    Tests for STEL OEL selection.

    VBA Reference: modCalc.bas lines 145-229 (SelectOELShortTerm)
    """

    def test_stel_priority_concentration_standard(self):
        """Concentration standard STEL should be first priority."""
        oel = OccupationalExposureLimits(
            concentration_standard_stel=5.0,
            concentration_standard_stel_unit="ppm",
            acgih_tlv_stel=10.0,
        )
        value, unit, source = select_oel_stel(oel, "liquid", oel_8hr=1.0)
        assert value == 5.0
        assert "濃度基準値" in source

    def test_stel_priority_acgih_stel(self):
        """ACGIH TLV-STEL should be used if no concentration standard STEL."""
        oel = OccupationalExposureLimits(
            concentration_standard_8hr=1.0,  # Has 8hr but not STEL
            acgih_tlv_stel=3.0,
            acgih_tlv_stel_unit="ppm",
        )
        value, unit, source = select_oel_stel(oel, "liquid", oel_8hr=1.0)
        assert value == 3.0
        assert "ACGIH" in source or "STEL" in source

    def test_stel_fallback_to_3x_concentration_standard(self):
        """If no STEL but concentration standard 8hr exists, use 3x."""
        oel = OccupationalExposureLimits(
            concentration_standard_8hr=1.0,
            concentration_standard_8hr_unit="ppm",
            # No STEL values
        )
        value, unit, source = select_oel_stel(oel, "liquid", oel_8hr=1.0)
        assert value == 3.0
        assert "× 3" in source or "×3" in source

    def test_stel_fallback_to_3x_oel(self):
        """If no STEL and no concentration standard, use 3x selected OEL."""
        oel = OccupationalExposureLimits(
            acgih_tlv_twa=2.0,
            acgih_tlv_twa_unit="ppm",
            # No STEL values
        )
        value, unit, source = select_oel_stel(oel, "liquid", oel_8hr=2.0)
        assert value == 6.0

    def test_stel_fallback_to_3x_acrmax(self):
        """If no OEL at all, use 3x ACRmax."""
        oel = OccupationalExposureLimits()  # Empty
        value, unit, source = select_oel_stel(oel, "liquid", oel_8hr=0, acrmax=0.5)
        assert value == 1.5

    def test_stel_returns_none_if_nothing(self):
        """If no OEL and no ACRmax, return None."""
        oel = OccupationalExposureLimits()  # Empty
        value, unit, source = select_oel_stel(oel, "liquid", oel_8hr=0, acrmax=None)
        assert value is None
