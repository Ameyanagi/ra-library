"""
Tests for volatility/dustiness calculator.

Based on VBA modFunction.bas lines 307-359.

Volatility determination rules:
- Liquids: Based on boiling point
  - BP < 50°C → "high"
  - BP 50-149°C → "medium"
  - BP ≥ 150°C → "low"
  - VP < 0.5 Pa → "very_low"

- Solids with vapor pressure:
  - VP > 25000 Pa → "high"
  - VP 500-25000 Pa → "medium"
  - VP < 500 Pa → "low"
  - No VP → dustiness based on form
"""

import pytest
from ra_library.data.volatility import (
    calculate_volatility_from_boiling_point,
    calculate_volatility_from_vapor_pressure,
    determine_volatility_level,
    should_treat_solid_as_vapor,
    get_dustiness_level,
)
from ra_library.data import SubstanceData


class TestVolatilityFromBoilingPoint:
    """Tests for boiling point-based volatility calculation."""

    def test_high_volatility_bp_below_50(self):
        """BP < 50°C → high volatility."""
        assert calculate_volatility_from_boiling_point(30) == "high"
        assert calculate_volatility_from_boiling_point(49.9) == "high"

    def test_medium_volatility_bp_50_to_149(self):
        """BP 50-149°C → medium volatility."""
        assert calculate_volatility_from_boiling_point(50) == "medium"
        assert calculate_volatility_from_boiling_point(100) == "medium"
        assert calculate_volatility_from_boiling_point(149) == "medium"

    def test_low_volatility_bp_150_and_above(self):
        """BP ≥ 150°C → low volatility."""
        assert calculate_volatility_from_boiling_point(150) == "low"
        assert calculate_volatility_from_boiling_point(200) == "low"
        assert calculate_volatility_from_boiling_point(500) == "low"

    def test_none_bp_returns_none(self):
        """No boiling point data returns None."""
        assert calculate_volatility_from_boiling_point(None) is None


class TestVolatilityFromVaporPressure:
    """Tests for vapor pressure-based volatility calculation."""

    def test_very_low_volatility_vp_below_0_5(self):
        """VP < 0.5 Pa → very_low volatility."""
        assert calculate_volatility_from_vapor_pressure(0.1) == "very_low"
        assert calculate_volatility_from_vapor_pressure(0.4) == "very_low"

    def test_low_volatility_vp_0_5_to_500(self):
        """VP 0.5-500 Pa → low volatility (liquid)."""
        assert calculate_volatility_from_vapor_pressure(0.5) == "low"
        assert calculate_volatility_from_vapor_pressure(100) == "low"
        assert calculate_volatility_from_vapor_pressure(499) == "low"

    def test_medium_volatility_vp_500_to_25000(self):
        """VP 500-25000 Pa → medium volatility."""
        assert calculate_volatility_from_vapor_pressure(500) == "medium"
        assert calculate_volatility_from_vapor_pressure(10000) == "medium"
        assert calculate_volatility_from_vapor_pressure(24999) == "medium"

    def test_high_volatility_vp_above_25000(self):
        """VP > 25000 Pa → high volatility."""
        assert calculate_volatility_from_vapor_pressure(25000) == "high"
        assert calculate_volatility_from_vapor_pressure(50000) == "high"

    def test_none_vp_returns_none(self):
        """No vapor pressure data returns None."""
        assert calculate_volatility_from_vapor_pressure(None) is None


class TestDetermineVolatilityLevel:
    """Tests for combined volatility determination logic."""

    def test_liquid_with_bp_only(self):
        """Liquid with only boiling point uses BP-based calculation."""
        substance = SubstanceData(
            cas_number="test-001",
            name_ja="テスト液体",
            name_en="Test Liquid",
            property_type=1,  # Liquid
            boiling_point=80,  # Medium volatility
        )
        assert determine_volatility_level(substance) == "medium"

    def test_liquid_with_low_vp_overrides_bp(self):
        """Liquid with VP < 0.5 Pa → very_low regardless of BP."""
        substance = SubstanceData(
            cas_number="test-002",
            name_ja="低蒸気圧液体",
            name_en="Low VP Liquid",
            property_type=1,
            boiling_point=80,  # Would be medium by BP
            vapor_pressure=0.3,  # Very low VP overrides
        )
        assert determine_volatility_level(substance) == "very_low"

    def test_liquid_with_high_bp_and_no_vp(self):
        """High BP liquid with no VP data uses BP calculation."""
        substance = SubstanceData(
            cas_number="test-003",
            name_ja="高沸点液体",
            name_en="High BP Liquid",
            property_type=1,
            boiling_point=250,  # Low volatility
        )
        assert determine_volatility_level(substance) == "low"

    def test_solid_returns_none(self):
        """Solids don't have volatility (use dustiness instead)."""
        substance = SubstanceData(
            cas_number="test-004",
            name_ja="固体",
            name_en="Solid",
            property_type=2,  # Solid
        )
        assert determine_volatility_level(substance) is None

    def test_gas_returns_high(self):
        """Gases always have high volatility."""
        substance = SubstanceData(
            cas_number="test-005",
            name_ja="ガス",
            name_en="Gas",
            property_type=3,  # Gas
        )
        assert determine_volatility_level(substance) == "high"


class TestShouldTreatSolidAsVapor:
    """Tests for determining if solid should be treated as vapor."""

    def test_solid_with_high_vp_treated_as_vapor(self):
        """Solid with VP ≥ 0.5 Pa should be treated as vapor."""
        substance = SubstanceData(
            cas_number="test-006",
            name_ja="昇華性固体",
            name_en="Subliming Solid",
            property_type=2,  # Solid
            vapor_pressure=1.0,  # High enough to treat as vapor
        )
        assert should_treat_solid_as_vapor(substance) is True

    def test_solid_with_low_vp_not_vapor(self):
        """Solid with VP < 0.5 Pa treated as dust."""
        substance = SubstanceData(
            cas_number="test-007",
            name_ja="通常固体",
            name_en="Normal Solid",
            property_type=2,
            vapor_pressure=0.1,  # Too low
        )
        assert should_treat_solid_as_vapor(substance) is False

    def test_solid_without_vp_not_vapor(self):
        """Solid without VP data treated as dust."""
        substance = SubstanceData(
            cas_number="test-008",
            name_ja="固体",
            name_en="Solid",
            property_type=2,
        )
        assert should_treat_solid_as_vapor(substance) is False

    def test_liquid_not_checked(self):
        """Liquids return False (not applicable)."""
        substance = SubstanceData(
            cas_number="test-009",
            name_ja="液体",
            name_en="Liquid",
            property_type=1,
            vapor_pressure=1000,
        )
        assert should_treat_solid_as_vapor(substance) is False


class TestDustinessLevel:
    """Tests for dustiness level determination for solids."""

    def test_solid_without_vp_default_medium(self):
        """Solid without VP data defaults to medium dustiness."""
        substance = SubstanceData(
            cas_number="test-010",
            name_ja="固体",
            name_en="Solid",
            property_type=2,
        )
        assert get_dustiness_level(substance) == "medium"

    def test_solid_with_subliming_vp_high_dustiness(self):
        """Solid with significant VP has high dustiness."""
        substance = SubstanceData(
            cas_number="test-011",
            name_ja="昇華性固体",
            name_en="Subliming Solid",
            property_type=2,
            vapor_pressure=10.0,
        )
        # When VP is significant, dustiness is high
        assert get_dustiness_level(substance) == "high"

    def test_liquid_returns_none(self):
        """Liquids don't have dustiness."""
        substance = SubstanceData(
            cas_number="test-012",
            name_ja="液体",
            name_en="Liquid",
            property_type=1,
        )
        assert get_dustiness_level(substance) is None

    def test_gas_returns_none(self):
        """Gases don't have dustiness."""
        substance = SubstanceData(
            cas_number="test-013",
            name_ja="ガス",
            name_en="Gas",
            property_type=3,
        )
        assert get_dustiness_level(substance) is None


class TestRealSubstancesVolatility:
    """Test volatility calculation with real substance data."""

    def test_formaldehyde_high_volatility(self):
        """Formaldehyde (BP -19°C) should have high volatility."""
        # Formaldehyde has very low BP
        substance = SubstanceData(
            cas_number="50-00-0",
            name_ja="ホルムアルデヒド",
            name_en="Formaldehyde",
            property_type=3,  # Gas at room temp
            boiling_point=-19,
        )
        assert determine_volatility_level(substance) == "high"

    def test_toluene_medium_volatility(self):
        """Toluene (BP 111°C) should have medium volatility."""
        substance = SubstanceData(
            cas_number="108-88-3",
            name_ja="トルエン",
            name_en="Toluene",
            property_type=1,
            boiling_point=111,
        )
        assert determine_volatility_level(substance) == "medium"

    def test_ethylene_glycol_low_volatility(self):
        """Ethylene glycol (BP 197°C) should have low volatility."""
        substance = SubstanceData(
            cas_number="107-21-1",
            name_ja="エチレングリコール",
            name_en="Ethylene Glycol",
            property_type=1,
            boiling_point=197,
        )
        assert determine_volatility_level(substance) == "low"
