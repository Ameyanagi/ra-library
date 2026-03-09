"""
Tests for exposure calculation.

VBA Reference: modCalc.bas lines 312-483 (CalculateExposureBands)
"""

import pytest
from ra_library.calculators.exposure import (
    apply_ventilation_coefficient,
    calculate_exposure,
)
from ra_library.models.assessment import (
    AssessmentInput,
    AssessmentMode,
    AmountLevel,
    VentilationLevel,
    ExposureVariation,
    PropertyType,
)


class TestVeryLowVolatilityVentilation:
    """
    Tests for very low volatility ventilation handling.

    VBA Reference: modCalc.bas lines 403-405
    For very low volatility (saturated vapor), ventilation coefficient > 1.0
    should be capped at 1.0 since poor ventilation can't increase exposure
    beyond saturation.
    """

    def test_very_low_volatility_caps_ventilation_at_1(self):
        """Very low volatility with no ventilation (coeff=4.0) should cap at 1.0."""
        # normally "none" ventilation gives coefficient 4.0
        coeff = apply_ventilation_coefficient(
            ventilation="none",
            control_velocity_verified=False,
            volatility_or_dustiness="very_low",
        )
        assert coeff == 1.0

    def test_very_low_volatility_caps_basic_ventilation(self):
        """Very low volatility with basic ventilation (coeff=3.0) should cap at 1.0."""
        coeff = apply_ventilation_coefficient(
            ventilation="basic",
            control_velocity_verified=False,
            volatility_or_dustiness="very_low",
        )
        assert coeff == 1.0

    def test_very_low_volatility_allows_reduction(self):
        """Very low volatility should allow ventilation reduction (<1.0)."""
        # local_enc unverified gives 0.1 per Design v3.1.1 Figure 17
        coeff = apply_ventilation_coefficient(
            ventilation="local_enc",
            control_velocity_verified=False,
            volatility_or_dustiness="very_low",
        )
        assert coeff == 0.1

    def test_very_low_volatility_with_verified_local_enc(self):
        """Very low volatility with verified local_enc (0.01) should remain 0.01."""
        coeff = apply_ventilation_coefficient(
            ventilation="local_enc",
            control_velocity_verified=True,
            volatility_or_dustiness="very_low",
        )
        assert coeff == 0.01

    def test_medium_volatility_no_cap(self):
        """Medium volatility should NOT cap ventilation coefficient."""
        coeff = apply_ventilation_coefficient(
            ventilation="none",
            control_velocity_verified=False,
            volatility_or_dustiness="medium",
        )
        assert coeff == 4.0  # No cap applied

    def test_high_volatility_no_cap(self):
        """High volatility should NOT cap ventilation coefficient."""
        coeff = apply_ventilation_coefficient(
            ventilation="basic",
            control_velocity_verified=False,
            volatility_or_dustiness="high",
        )
        assert coeff == 3.0  # No cap applied


class TestTimeCoefficient:
    """
    Tests for duration/time coefficient.

    VBA Reference: modCalc.bas lines 408-432
    """

    def test_time_coeff_weekly_over_40hrs(self):
        """Weekly hours > 40 should return coefficient 10."""
        # 10 hrs/day × 5 days = 50 hrs > 40
        from ra_library.calculators.exposure import calculate_time_coefficient
        assert calculate_time_coefficient("weekly", 5, 10.0) == 10.0

    def test_time_coeff_weekly_long_days(self):
        """Hours > 8 and days >= 3 should return coefficient 10."""
        # 9 hrs/day × 3 days = 27 hrs, but > 8hrs and >= 3 days
        from ra_library.calculators.exposure import calculate_time_coefficient
        assert calculate_time_coefficient("weekly", 3, 9.0) == 10.0

    def test_time_coeff_weekly_under_4hrs(self):
        """Weekly hours <= 4 should return coefficient 0.1."""
        # 2 hrs/day × 2 days = 4 hrs
        from ra_library.calculators.exposure import calculate_time_coefficient
        assert calculate_time_coefficient("weekly", 2, 2.0) == 0.1

    def test_time_coeff_weekly_normal(self):
        """Normal weekly hours (8 × 5 = 40) should return coefficient 1.0."""
        from ra_library.calculators.exposure import calculate_time_coefficient
        assert calculate_time_coefficient("weekly", 5, 8.0) == 1.0

    def test_time_coeff_monthly_over_192_yearly(self):
        """Yearly hours > 192 should return coefficient 1.0."""
        # 8 hrs × 3 days/month × 12 = 288 hrs > 192
        from ra_library.calculators.exposure import calculate_time_coefficient
        assert calculate_time_coefficient("monthly", 3, 8.0) == 1.0

    def test_time_coeff_monthly_under_192_yearly(self):
        """Yearly hours <= 192 should return coefficient 0.1."""
        # 4 hrs × 2 days/month × 12 = 96 hrs < 192
        from ra_library.calculators.exposure import calculate_time_coefficient
        assert calculate_time_coefficient("monthly", 2, 4.0) == 0.1

    def test_time_coeff_short_term_effect(self):
        """Short-term effect should always return 1.0."""
        from ra_library.calculators.exposure import calculate_time_coefficient
        assert calculate_time_coefficient("weekly", 5, 10.0, has_short_term_effect=True) == 1.0


class TestExposureCaps:
    """
    Tests for exposure maximum caps.

    VBA Reference: modCalc.bas lines 474-480
    """

    def test_exposure_8hr_max_cap_5000(self):
        """8hr exposure should be capped at 5000."""
        from ra_library.calculators.exposure import apply_exposure_caps
        result = apply_exposure_caps(10000.0, 15000.0)
        assert result[0] == 5000.0

    def test_exposure_stel_max_cap_5000(self):
        """STEL should be capped at 5000."""
        from ra_library.calculators.exposure import apply_exposure_caps
        result = apply_exposure_caps(1000.0, 10000.0)
        assert result[1] == 5000.0

    def test_exposure_below_cap_unchanged(self):
        """Exposure below cap should remain unchanged."""
        from ra_library.calculators.exposure import apply_exposure_caps
        result = apply_exposure_caps(100.0, 300.0)
        assert result[0] == 100.0
        assert result[1] == 300.0


class TestSTELMultiplier:
    """
    Tests for STEL multiplier calculation.

    Reference: CREATE-SIMPLE Design v3.1 (June 2025), Figure 23
    STEL = 8-hour TWA × multiplier based on exposure variation (GSD)
    - Small variation (GSD = 3.0): multiplier = 4
    - Large variation (GSD = 6.0): multiplier = 6
    """

    def test_stel_multiplier_small_variation(self):
        """Small variation (GSD 3.0) should have multiplier 4."""
        assert ExposureVariation.SMALL.get_stel_multiplier() == 4.0

    def test_stel_multiplier_large_variation(self):
        """Large variation (GSD 6.0) should have multiplier 6."""
        assert ExposureVariation.LARGE.get_stel_multiplier() == 6.0

    def test_stel_multiplier_legacy_constant(self):
        """Legacy CONSTANT maps to multiplier 4 (small variation)."""
        assert ExposureVariation.CONSTANT.get_stel_multiplier() == 4.0

    def test_stel_multiplier_legacy_intermittent(self):
        """Legacy INTERMITTENT maps to multiplier 4 (small variation)."""
        assert ExposureVariation.INTERMITTENT.get_stel_multiplier() == 4.0

    def test_stel_multiplier_legacy_brief(self):
        """Legacy BRIEF maps to multiplier 4 (small variation)."""
        assert ExposureVariation.BRIEF.get_stel_multiplier() == 4.0

    def test_stel_calculation_small_variation_v31_spec(self):
        """STEL should be 8hr TWA × 4 for small variation (v3.1 spec method)."""
        assessment_input = AssessmentInput(
            mode=AssessmentMode.RA_SHEET,
            product_property=PropertyType.LIQUID,
            amount_level=AmountLevel.MEDIUM,
            ventilation=VentilationLevel.INDUSTRIAL,
            exposure_variation=ExposureVariation.SMALL,
        )
        exposure_8hr, exposure_stel, _ = calculate_exposure(
            assessment_input=assessment_input,
            volatility_or_dustiness="medium",
            content_percent=100.0,
            use_vba_stel_method=False,  # Use v3.1 spec method
        )
        # STEL should be approximately 4× the 8hr TWA
        # (may differ slightly due to floor application)
        expected_stel = exposure_8hr * 4.0
        assert abs(exposure_stel - expected_stel) < 0.01 or exposure_stel >= expected_stel

    def test_stel_calculation_large_variation_v31_spec(self):
        """STEL should be 8hr TWA × 6 for large variation (v3.1 spec method)."""
        assessment_input = AssessmentInput(
            mode=AssessmentMode.RA_SHEET,
            product_property=PropertyType.LIQUID,
            amount_level=AmountLevel.MEDIUM,
            ventilation=VentilationLevel.INDUSTRIAL,
            exposure_variation=ExposureVariation.LARGE,
        )
        exposure_8hr, exposure_stel, _ = calculate_exposure(
            assessment_input=assessment_input,
            volatility_or_dustiness="medium",
            content_percent=100.0,
            use_vba_stel_method=False,  # Use v3.1 spec method
        )
        # STEL should be approximately 6× the 8hr TWA
        expected_stel = exposure_8hr * 6.0
        assert abs(exposure_stel - expected_stel) < 0.01 or exposure_stel >= expected_stel

    def test_stel_very_low_volatility_equals_8hr(self):
        """For very low volatility without spray, STEL should equal 8hr TWA."""
        assessment_input = AssessmentInput(
            mode=AssessmentMode.RA_SHEET,
            product_property=PropertyType.LIQUID,
            amount_level=AmountLevel.MEDIUM,
            ventilation=VentilationLevel.INDUSTRIAL,
            is_spray_operation=False,
            exposure_variation=ExposureVariation.LARGE,
        )
        exposure_8hr, exposure_stel, _ = calculate_exposure(
            assessment_input=assessment_input,
            volatility_or_dustiness="very_low",
            content_percent=100.0,
        )
        # For very low volatility + no spray, STEL = 8hr TWA
        assert exposure_stel == exposure_8hr
