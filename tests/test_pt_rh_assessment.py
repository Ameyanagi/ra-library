"""
Risk Assessment Tests for Platinum (Pt) and Rhodium (Rh).

These tests verify the ra-library can perform complete risk assessments
for Platinum and Rhodium under various work conditions.

Reference: VBA CREATE-SIMPLE test cases
"""

import pytest
from ra_library.models.substance import (
    Substance,
    PropertyType,
    GHSClassification,
    OccupationalExposureLimits,
    PhysicochemicalProperties,
)
from ra_library.models.assessment import (
    AssessmentInput,
    AmountLevel,
    VentilationLevel,
    ExposureVariation,
)
from ra_library.calculators.inhalation import calculate_inhalation_risk
from ra_library.models.risk import RiskLevel


# ============================================================================
# Platinum (Pt) - CAS 7440-06-4
# ============================================================================
# Property: Solid
# OEL: JSOH 0.001 mg/m³ (soluble Pt salts as Pt)
# ACGIH TLV-TWA: 1 mg/m³ (metal)
# GHS: Carcinogenicity 2A, Mutagenicity 2, Reproductive toxicity 1
# ============================================================================


@pytest.fixture
def platinum_substance():
    """Create Platinum substance data."""
    return Substance(
        cas_number="7440-06-4",
        name_ja="白金",
        name_en="Platinum",
        property_type=PropertyType.SOLID,
        ghs=GHSClassification(
            carcinogenicity="2A",  # IARC Group 2A
            germ_cell_mutagenicity="2",
            reproductive_toxicity="1",
        ),
        oel=OccupationalExposureLimits(
            jsoh_8hr=0.001,  # Soluble Pt salts as Pt
            jsoh_8hr_unit="mg/m³",
            acgih_tlv_twa=1.0,  # Pt metal
            acgih_tlv_twa_unit="mg/m³",
        ),
        properties=PhysicochemicalProperties(
            molecular_weight=195.08,
            boiling_point=3695,  # °C
            log_kow=1.03,
        ),
        is_carcinogen=True,
    )


class TestPlatinumRiskAssessment:
    """Test Platinum (Pt) risk assessment."""

    def test_platinum_hazard_level(self, platinum_substance):
        """Platinum should have HL4 due to carcinogenicity 2A."""
        hazard_level = platinum_substance.get_hazard_level()
        # Carcinogenicity 2A = HL4
        assert hazard_level == "HL4"

    def test_platinum_large_amount_no_control(self, platinum_substance):
        """Platinum: Large amount, no ventilation control."""
        assessment_input = AssessmentInput(
            product_property=PropertyType.SOLID,
            amount_level=AmountLevel.LARGE,  # ≥1 ton
            ventilation=VentilationLevel.NONE,
            working_hours_per_day=8.0,
            frequency_type="weekly",
            frequency_value=5,
            exposure_variation=ExposureVariation.CONSTANT,
        )

        risk = calculate_inhalation_risk(
            assessment_input=assessment_input,
            substance=platinum_substance,
            content_percent=100.0,
        )

        # Expect high risk due to large amount, no ventilation
        assert risk.risk_level == RiskLevel.IV
        assert risk.oel == 0.001  # JSOH OEL
        assert risk.acrmax is not None  # Should have ACRmax for HL4

    def test_platinum_small_amount_local_exhaust(self, platinum_substance):
        """Platinum: Small amount with local exhaust ventilation."""
        assessment_input = AssessmentInput(
            product_property=PropertyType.SOLID,
            amount_level=AmountLevel.SMALL,  # 100g-1kg
            ventilation=VentilationLevel.LOCAL_ENCLOSED,
            control_velocity_verified=True,
            working_hours_per_day=4.0,
            frequency_type="weekly",
            frequency_value=3,
            exposure_variation=ExposureVariation.INTERMITTENT,
        )

        risk = calculate_inhalation_risk(
            assessment_input=assessment_input,
            substance=platinum_substance,
            content_percent=100.0,
        )

        # Risk should be lower with controls
        assert risk.risk_level in [RiskLevel.I, RiskLevel.II, RiskLevel.III]
        assert risk.oel == 0.001

    def test_platinum_trace_amount_sealed(self, platinum_substance):
        """Platinum: Trace amount with sealed system."""
        assessment_input = AssessmentInput(
            product_property=PropertyType.SOLID,
            amount_level=AmountLevel.TRACE,  # <10g
            ventilation=VentilationLevel.SEALED,
            working_hours_per_day=2.0,
            frequency_type="weekly",
            frequency_value=1,
            exposure_variation=ExposureVariation.BRIEF,
        )

        risk = calculate_inhalation_risk(
            assessment_input=assessment_input,
            substance=platinum_substance,
            content_percent=100.0,
        )

        # Best possible risk level with maximum controls
        assert risk.risk_level in [RiskLevel.I, RiskLevel.II]


# ============================================================================
# Rhodium (Rh) - CAS 7440-16-6
# ============================================================================
# Property: Solid
# OEL: JSOH 0.001 mg/m³
# ACGIH TLV-TWA: 1 mg/m³
# GHS: Carcinogenicity 1, Vapor pressure 1 Pa
# ============================================================================


@pytest.fixture
def rhodium_substance():
    """Create Rhodium substance data."""
    return Substance(
        cas_number="7440-16-6",
        name_ja="ロジウム",
        name_en="Rhodium",
        property_type=PropertyType.SOLID,
        ghs=GHSClassification(
            carcinogenicity="1A",  # GHS Category 1A → HL5 (highest hazard)
        ),
        oel=OccupationalExposureLimits(
            jsoh_8hr=0.001,
            jsoh_8hr_unit="mg/m³",
            acgih_tlv_twa=1.0,
            acgih_tlv_twa_unit="mg/m³",
        ),
        properties=PhysicochemicalProperties(
            molecular_weight=102.91,
            boiling_point=3695,
            vapor_pressure=1.0,  # Pa
        ),
        is_carcinogen=True,
    )


class TestRhodiumRiskAssessment:
    """Test Rhodium (Rh) risk assessment."""

    def test_rhodium_hazard_level(self, rhodium_substance):
        """Rhodium should have HL5 due to carcinogenicity 1A."""
        hazard_level = rhodium_substance.get_hazard_level()
        # Carcinogenicity 1A = HL5 (highest hazard level)
        assert hazard_level == "HL5"

    def test_rhodium_large_amount_no_control(self, rhodium_substance):
        """Rhodium: Large amount, no ventilation control."""
        assessment_input = AssessmentInput(
            product_property=PropertyType.SOLID,
            amount_level=AmountLevel.LARGE,
            ventilation=VentilationLevel.NONE,
            working_hours_per_day=8.0,
            frequency_type="weekly",
            frequency_value=5,
            exposure_variation=ExposureVariation.CONSTANT,
        )

        risk = calculate_inhalation_risk(
            assessment_input=assessment_input,
            substance=rhodium_substance,
            content_percent=100.0,
        )

        # Expect high risk
        assert risk.risk_level == RiskLevel.IV
        assert risk.oel == 0.001

    def test_rhodium_medium_amount_industrial_vent(self, rhodium_substance):
        """Rhodium: Medium amount with industrial ventilation."""
        assessment_input = AssessmentInput(
            product_property=PropertyType.SOLID,
            amount_level=AmountLevel.MEDIUM,  # 1kg-1ton
            ventilation=VentilationLevel.INDUSTRIAL,
            working_hours_per_day=8.0,
            frequency_type="weekly",
            frequency_value=5,
            exposure_variation=ExposureVariation.CONSTANT,
        )

        risk = calculate_inhalation_risk(
            assessment_input=assessment_input,
            substance=rhodium_substance,
            content_percent=100.0,
        )

        # Risk should be high but not maximum
        assert risk.risk_level in [RiskLevel.III, RiskLevel.IV]

    def test_rhodium_small_amount_enclosed_exhaust(self, rhodium_substance):
        """Rhodium: Small amount with enclosed local exhaust."""
        assessment_input = AssessmentInput(
            product_property=PropertyType.SOLID,
            amount_level=AmountLevel.SMALL,
            ventilation=VentilationLevel.LOCAL_ENCLOSED,
            control_velocity_verified=True,
            working_hours_per_day=4.0,
            frequency_type="weekly",
            frequency_value=3,
            exposure_variation=ExposureVariation.INTERMITTENT,
        )

        risk = calculate_inhalation_risk(
            assessment_input=assessment_input,
            substance=rhodium_substance,
            content_percent=100.0,
        )

        # Risk should be reduced
        assert risk.risk_level in [RiskLevel.II, RiskLevel.III]


class TestComparisonPtRh:
    """Compare Platinum and Rhodium risk assessments."""

    def test_same_conditions_different_hazards(
        self, platinum_substance, rhodium_substance
    ):
        """Compare Pt and Rh under identical conditions."""
        assessment_input = AssessmentInput(
            product_property=PropertyType.SOLID,
            amount_level=AmountLevel.MEDIUM,
            ventilation=VentilationLevel.LOCAL_EXTERNAL,
            working_hours_per_day=6.0,
            frequency_type="weekly",
            frequency_value=4,
            exposure_variation=ExposureVariation.CONSTANT,
        )

        pt_risk = calculate_inhalation_risk(
            assessment_input=assessment_input,
            substance=platinum_substance,
            content_percent=100.0,
        )

        rh_risk = calculate_inhalation_risk(
            assessment_input=assessment_input,
            substance=rhodium_substance,
            content_percent=100.0,
        )

        # Both should have same OEL (0.001 mg/m³)
        assert pt_risk.oel == rh_risk.oel == 0.001

        # Both are carcinogens, so both should have ACRmax
        assert pt_risk.acrmax is not None
        assert rh_risk.acrmax is not None

        # Exposure values should be the same (same conditions)
        assert pt_risk.exposure_8hr == rh_risk.exposure_8hr


class TestRiskLevelTransitions:
    """Test risk level transitions with control improvements."""

    def test_platinum_control_improvement_sequence(self, platinum_substance):
        """Test how risk level improves with better controls."""
        # Baseline: no controls
        no_control = AssessmentInput(
            product_property=PropertyType.SOLID,
            amount_level=AmountLevel.SMALL,
            ventilation=VentilationLevel.NONE,
            working_hours_per_day=8.0,
            frequency_type="weekly",
            frequency_value=5,
        )

        # With local exhaust
        local_exhaust = AssessmentInput(
            product_property=PropertyType.SOLID,
            amount_level=AmountLevel.SMALL,
            ventilation=VentilationLevel.LOCAL_EXTERNAL,
            working_hours_per_day=8.0,
            frequency_type="weekly",
            frequency_value=5,
        )

        # With enclosed local exhaust + verified
        enclosed_verified = AssessmentInput(
            product_property=PropertyType.SOLID,
            amount_level=AmountLevel.SMALL,
            ventilation=VentilationLevel.LOCAL_ENCLOSED,
            control_velocity_verified=True,
            working_hours_per_day=8.0,
            frequency_type="weekly",
            frequency_value=5,
        )

        risk_no_control = calculate_inhalation_risk(
            no_control, platinum_substance, 100.0
        )
        risk_local = calculate_inhalation_risk(local_exhaust, platinum_substance, 100.0)
        risk_enclosed = calculate_inhalation_risk(
            enclosed_verified, platinum_substance, 100.0
        )

        # Risk should decrease with better controls
        # (RCR decreases as ventilation improves)
        assert risk_no_control.rcr >= risk_local.rcr
        assert risk_local.rcr >= risk_enclosed.rcr

        # Exposure should also decrease
        assert risk_no_control.exposure_8hr >= risk_local.exposure_8hr
        assert risk_local.exposure_8hr >= risk_enclosed.exposure_8hr
