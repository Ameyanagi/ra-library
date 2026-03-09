"""
Tests for dermal risk calculation.

VBA Reference: modCalc.bas lines 2-79 (CalculateDermalAbsorption)
               modCalc.bas lines 278-311 (CalculateOELDermal)
"""

import pytest
import math
from ra_library.calculators.dermal import (
    calculate_oel_dermal,
    calculate_dermal_kp_detailed,
    calculate_skin_retention_time,
    calculate_total_skin_exposure_time,
)


class TestDermalOEL:
    """
    Tests for dermal OEL calculation.

    VBA Reference: modCalc.bas lines 278-311 (CalculateOELDermal)
    """

    def test_dermal_oel_liquid(self):
        """Dermal OEL for liquid: MW / (22.41 × 298.15/273.15) × OEL × 0.75 × 10."""
        # MW=100, OEL=1.0 ppm
        # = 100 / (22.41 × 1.0917) × 1.0 × 0.75 × 10
        # = 100 / 24.465 × 7.5 = 30.66
        result = calculate_oel_dermal(
            oel_8hr=1.0,
            property_type="liquid",
            molecular_weight=100.0,
        )
        assert 30 < result < 32

    def test_dermal_oel_solid(self):
        """Dermal OEL for solid: OEL × 0.75 × 10."""
        # OEL=1.0 mg/m³ → 1.0 × 0.75 × 10 = 7.5
        result = calculate_oel_dermal(
            oel_8hr=1.0,
            property_type="solid",
            molecular_weight=100.0,
        )
        assert result == 7.5

    def test_dermal_oel_uses_acrmax_if_no_oel(self):
        """Use ACRmax if OEL is not available."""
        result = calculate_oel_dermal(
            oel_8hr=None,
            acrmax=0.5,
            property_type="solid",
            molecular_weight=100.0,
        )
        assert result == 0.5 * 0.75 * 10

    def test_dermal_oel_prefers_oel_over_acrmax(self):
        """OEL should be preferred over ACRmax if both provided."""
        result = calculate_oel_dermal(
            oel_8hr=1.0,
            acrmax=0.5,
            property_type="solid",
            molecular_weight=100.0,
        )
        assert result == 1.0 * 0.75 * 10


class TestDermalKpDetailed:
    """
    Tests for detailed Kp (permeability coefficient) calculation.

    VBA Reference: modCalc.bas lines 2-50
    Uses the detailed formula with KpSc, KPol, and KAq components.
    """

    def test_kp_calculation_basic(self):
        """Test Kp calculation with known values."""
        # VBA formula:
        # LogKpSc = -1.326 + 0.6097 × logKow - 0.1786 × √MW
        # MW=100, logKow=2.0
        # LogKpSc = -1.326 + 0.6097×2 - 0.1786×10 = -1.8926
        # KpSc = 10^-1.8926 = 0.0128
        # KPol = 0.0001519 / √100 = 0.00001519
        # KAq = 2.5 / √100 = 0.25
        result = calculate_dermal_kp_detailed(
            molecular_weight=100.0,
            log_kow=2.0,
        )
        # Result should be reasonable Kp value
        assert 0.001 < result < 1.0

    def test_kp_increases_with_log_kow(self):
        """Higher log Kow should increase Kp (more lipophilic = higher permeability)."""
        kp_low = calculate_dermal_kp_detailed(molecular_weight=100.0, log_kow=0.0)
        kp_high = calculate_dermal_kp_detailed(molecular_weight=100.0, log_kow=4.0)
        assert kp_high > kp_low

    def test_kp_decreases_with_molecular_weight(self):
        """Higher MW should decrease Kp (larger molecules = lower permeability)."""
        kp_small = calculate_dermal_kp_detailed(molecular_weight=50.0, log_kow=2.0)
        kp_large = calculate_dermal_kp_detailed(molecular_weight=500.0, log_kow=2.0)
        assert kp_small > kp_large


class TestSkinRetentionTime:
    """
    Tests for skin retention time calculation.

    VBA Reference: modCalc.bas lines 51-60
    """

    def test_skin_retention_liquid(self):
        """Skin retention time for liquid: 7 / (absorption + evaporation)."""
        result = calculate_skin_retention_time(
            absorption_rate=0.5,
            evaporation_rate=0.5,
            property_type="liquid",
        )
        assert result == 7.0  # 7 / (0.5 + 0.5) = 7

    def test_skin_retention_solid(self):
        """Skin retention time for solid: 3 / (absorption + evaporation)."""
        result = calculate_skin_retention_time(
            absorption_rate=0.5,
            evaporation_rate=0.5,
            property_type="solid",
        )
        assert result == 3.0  # 3 / (0.5 + 0.5) = 3

    def test_skin_retention_zero_rates(self):
        """Zero rates should result in very long retention (capped)."""
        result = calculate_skin_retention_time(
            absorption_rate=0.0,
            evaporation_rate=0.0,
            property_type="liquid",
        )
        # Should be capped at a reasonable maximum
        assert result <= 100  # Reasonable cap


class TestTotalSkinExposureTime:
    """
    Tests for total skin exposure time calculation.

    VBA Reference: modCalc.bas lines 61-70
    """

    def test_exposure_time_sum(self):
        """Total exposure time = working hours + retention time."""
        result = calculate_total_skin_exposure_time(
            working_hours=8.0,
            skin_retention_time=2.0,
        )
        assert result == 10.0

    def test_exposure_time_cap_at_10(self):
        """Total exposure time should be capped at 10 hours."""
        result = calculate_total_skin_exposure_time(
            working_hours=8.0,
            skin_retention_time=5.0,  # Total would be 13
        )
        assert result == 10.0

    def test_exposure_time_below_cap(self):
        """Exposure time below cap should remain unchanged."""
        result = calculate_total_skin_exposure_time(
            working_hours=4.0,
            skin_retention_time=2.0,
        )
        assert result == 6.0
