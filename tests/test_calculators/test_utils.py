"""
Tests for utility functions.

VBA Reference:
- RoundDown to significant figures: used throughout modCalc.bas
- Unit conversions: modFunction.bas
"""

import pytest
from ra_library.calculators.utils import (
    round_significant,
    round_down_significant,
    convert_ppm_to_mg_m3,
    convert_mg_m3_to_ppm,
    convert_pressure_to_pa,
    convert_solubility_to_mg_cm3,
)


class TestRoundSignificant:
    """Tests for significant figure rounding."""

    def test_round_down_2_digits_large_number(self):
        """Round down 123.456 to 2 significant figures = 120."""
        result = round_down_significant(123.456, 2)
        assert result == 120

    def test_round_down_2_digits_decimal(self):
        """Round down 0.0456 to 2 significant figures = 0.045."""
        result = round_down_significant(0.0456, 2)
        assert result == 0.045

    def test_round_down_2_digits_single_digit(self):
        """Round down 9.87 to 2 significant figures = 9.8."""
        result = round_down_significant(9.87, 2)
        assert result == 9.8

    def test_round_down_preserves_significant_zeros(self):
        """Round down should preserve trailing zeros in integer part."""
        result = round_down_significant(1234.5, 2)
        assert result == 1200

    def test_round_significant_standard(self):
        """Standard rounding (not down) to 2 significant figures."""
        result = round_significant(0.0456, 2)
        assert result == 0.046  # Rounds up because 6 > 5

    def test_round_significant_3_digits(self):
        """Round to 3 significant figures."""
        result = round_significant(123.456, 3)
        assert result == 123


class TestUnitConversions:
    """Tests for unit conversion functions."""

    def test_ppm_to_mg_m3(self):
        """Convert ppm to mg/m³ using MW."""
        # ppm × (MW / 24.45) = mg/m³
        # 1 ppm of MW=100 = 100/24.45 = 4.09 mg/m³
        result = convert_ppm_to_mg_m3(1.0, molecular_weight=100.0)
        assert pytest.approx(result, rel=0.01) == 4.09

    def test_mg_m3_to_ppm(self):
        """Convert mg/m³ to ppm using MW."""
        # mg/m³ × (24.45 / MW) = ppm
        result = convert_mg_m3_to_ppm(4.09, molecular_weight=100.0)
        assert pytest.approx(result, rel=0.01) == 1.0

    def test_conversion_roundtrip(self):
        """Converting ppm → mg/m³ → ppm should give original value."""
        original = 10.0
        mg_m3 = convert_ppm_to_mg_m3(original, molecular_weight=150.0)
        ppm = convert_mg_m3_to_ppm(mg_m3, molecular_weight=150.0)
        assert pytest.approx(ppm, rel=0.001) == original


class TestPressureConversion:
    """Tests for pressure unit conversions."""

    def test_mmhg_to_pa(self):
        """Convert mmHg to Pa."""
        # 760 mmHg ≈ 101308 Pa (using VBA factor 133.3)
        result = convert_pressure_to_pa(760.0, "mmHg")
        assert pytest.approx(result, rel=0.01) == 760 * 133.3

    def test_kpa_to_pa(self):
        """Convert kPa to Pa."""
        result = convert_pressure_to_pa(101.325, "kPa")
        assert pytest.approx(result, rel=0.001) == 101325

    def test_pa_to_pa(self):
        """Pa to Pa is identity."""
        result = convert_pressure_to_pa(101325.0, "Pa")
        assert result == 101325.0

    def test_hpa_to_pa(self):
        """Convert hPa to Pa (VBA: line 1616)."""
        result = convert_pressure_to_pa(1013.25, "hPa")
        assert result == 101325.0

    def test_mpa_to_pa(self):
        """Convert mPa to Pa (VBA: line 1618)."""
        result = convert_pressure_to_pa(1000.0, "mPa")
        assert result == 1.0  # 1000 mPa = 1 Pa

    def test_torr_to_pa(self):
        """Convert Torr to Pa (same as mmHg)."""
        result = convert_pressure_to_pa(760.0, "Torr")
        assert pytest.approx(result, rel=0.01) == 760 * 133.3


class TestSolubilityConversion:
    """Tests for solubility unit conversions."""

    def test_mg_l_to_mg_cm3(self):
        """Convert mg/L to mg/cm³."""
        # 1000 mg/L = 1.0 mg/cm³
        result = convert_solubility_to_mg_cm3(1000.0, "mg/L")
        assert result == 1.0

    def test_g_l_to_mg_cm3(self):
        """Convert g/L to mg/cm³."""
        # 1 g/L = 1 mg/cm³
        result = convert_solubility_to_mg_cm3(1.0, "g/L")
        assert result == 1.0

    def test_mg_cm3_identity(self):
        """mg/cm³ to mg/cm³ is identity."""
        result = convert_solubility_to_mg_cm3(5.0, "mg/cm³")
        assert result == 5.0

    def test_g_100ml_to_mg_cm3(self):
        """Convert g/100mL to mg/cm³ (VBA: line 1591)."""
        # 1 g/100mL = 10 mg/cm³ (conversionFactor = 10)
        result = convert_solubility_to_mg_cm3(1.0, "g/100mL")
        assert result == 10.0

    def test_g_100ml_to_mg_cm3_example(self):
        """Convert 5 g/100mL to mg/cm³."""
        result = convert_solubility_to_mg_cm3(5.0, "g/100mL")
        assert result == 50.0
