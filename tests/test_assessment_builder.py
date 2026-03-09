"""
Tests for RiskAssessment builder pattern API.
"""

import pytest
from ra_library import (
    RiskAssessment,
    AssessmentResult,
    ComponentResult,
    Substance,
    PropertyType,
    GHSClassification,
    OccupationalExposureLimits,
    AmountLevel,
    VentilationLevel,
    RPEType,
    GloveType,
    DetailedRiskLevel,
)


class TestBuilderBasic:
    """Test basic builder functionality."""

    def test_simple_assessment(self):
        """Test basic assessment with single substance."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)  # Platinum
            .with_conditions(
                property_type="solid",
                amount="medium",
                ventilation="local_external",
            )
            .with_duration(hours=6.0, days_per_week=5)
            .calculate()
        )

        assert isinstance(result, AssessmentResult)
        assert result.overall_risk_level == 4
        assert "7440-06-4" in result.components

    def test_method_chaining(self):
        """Test that all builder methods return self for chaining."""
        builder = RiskAssessment()

        # Each method should return the builder
        assert builder.add_substance("7440-06-4", 100.0) is builder
        assert builder.with_conditions(amount="medium") is builder
        assert builder.with_duration(hours=8.0) is builder
        assert builder.with_protection(rpe="half_mask") is builder

    def test_validation_errors(self):
        """Test that invalid configurations raise errors."""
        # No substance
        builder = RiskAssessment()
        errors = builder.validate()
        assert "At least one substance is required" in errors

        # Invalid content
        builder = RiskAssessment().add_substance("7440-06-4", 150.0)
        errors = builder.validate()
        assert any("Content must be 0-100%" in e for e in errors)

    def test_is_valid(self):
        """Test is_valid helper method."""
        # Invalid - no substances
        assert not RiskAssessment().is_valid()

        # Valid
        assert (
            RiskAssessment()
            .add_substance("7440-06-4", 100.0)
            .is_valid()
        )


class TestMultiSubstance:
    """Test multi-substance product assessment."""

    def test_two_substances(self):
        """Test assessment with two substances."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=50.0)  # Platinum
            .add_substance("7440-16-6", content=30.0)  # Rhodium
            .with_conditions(
                property_type="solid",
                amount="medium",
                ventilation="local_external",
            )
            .with_duration(hours=6.0, days_per_week=5)
            .calculate()
        )

        assert len(result.components) == 2
        assert "7440-06-4" in result.components
        assert "7440-16-6" in result.components

    def test_total_content_validation(self):
        """Test that total content over 100% is flagged."""
        builder = (
            RiskAssessment()
            .add_substance("7440-06-4", content=60.0)
            .add_substance("7440-16-6", content=50.0)
        )
        errors = builder.validate()
        assert any("Total content exceeds 100%" in e for e in errors)


class TestResultAccess:
    """Test multiple access patterns for result data."""

    @pytest.fixture
    def result(self):
        """Create a standard result for testing."""
        return (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(
                property_type="solid",
                amount="medium",
                ventilation="local_external",
            )
            .with_duration(hours=6.0, days_per_week=5)
            .calculate()
        )

    def test_property_access(self, result):
        """Test property-based access."""
        assert isinstance(result.overall_risk_level, int)
        assert isinstance(result.overall_risk_label, str)
        assert isinstance(result.components, dict)

    def test_method_access(self, result):
        """Test method-based access."""
        assert result.get_risk_level() == result.overall_risk_level
        assert result.get_risk_label() == result.overall_risk_label

        comp = result.get_component("7440-06-4")
        assert comp is not None
        assert comp.cas_number == "7440-06-4"

    def test_dict_access(self, result):
        """Test dict-like access."""
        assert result["overall_risk_level"] == result.overall_risk_level
        assert result["overall_risk_label"] == result.overall_risk_label

        components = result["components"]
        assert "7440-06-4" in components

    def test_component_dict_access(self, result):
        """Test dict access for component results."""
        comp = result.components["7440-06-4"]

        assert comp["cas_number"] == "7440-06-4"
        assert isinstance(comp["risk_level"], int)
        assert comp["content_percent"] == 100.0

    def test_to_dict(self, result):
        """Test serialization to dict."""
        d = result.to_dict()

        assert "overall_risk_level" in d
        assert "overall_risk_label" in d
        assert "components" in d
        assert "7440-06-4" in d["components"]

    def test_to_json(self, result):
        """Test JSON serialization."""
        import json

        json_str = result.to_json()
        parsed = json.loads(json_str)

        assert parsed["overall_risk_level"] == result.overall_risk_level


class TestWhatIfAnalysis:
    """Test what-if scenario analysis."""

    def test_what_if_ventilation(self):
        """Test what-if with improved ventilation."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(
                property_type="solid",
                amount="medium",
                ventilation="local_external",
            )
            .with_duration(hours=6.0, days_per_week=5)
            .calculate()
        )

        # What if we use sealed container?
        better = result.what_if(ventilation="sealed")

        # Sealed should have much lower RCR
        original_rcr = result.components["7440-06-4"].inhalation.rcr
        new_rcr = better.components["7440-06-4"].inhalation.rcr
        assert new_rcr < original_rcr

    def test_what_if_amount(self):
        """Test what-if with reduced amount."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(
                property_type="solid",
                amount="medium",
                ventilation="local_external",
            )
            .with_duration(hours=6.0, days_per_week=5)
            .calculate()
        )

        # What if we reduce amount?
        smaller = result.what_if(amount="small")

        original_rcr = result.components["7440-06-4"].inhalation.rcr
        new_rcr = smaller.components["7440-06-4"].inhalation.rcr
        assert new_rcr < original_rcr


class TestProtection:
    """Test protection measures (PPE)."""

    def test_rpe_reduces_rcr(self):
        """Test that RPE reduces the RCR value."""
        # Without RPE
        baseline = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(
                property_type="solid",
                amount="medium",
                ventilation="local_external",
            )
            .with_duration(hours=6.0, days_per_week=5)
            .calculate()
        )

        # With half-mask RPE (APF=10)
        protected = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(
                property_type="solid",
                amount="medium",
                ventilation="local_external",
            )
            .with_duration(hours=6.0, days_per_week=5)
            .with_protection(rpe="half_mask")
            .calculate()
        )

        baseline_rcr = baseline.components["7440-06-4"].inhalation.rcr
        protected_rcr = protected.components["7440-06-4"].inhalation.rcr

        # APF=10 should reduce RCR by 10x
        assert abs(protected_rcr - baseline_rcr / 10) < 0.01

    def test_rpe_string_parsing(self):
        """Test that RPE types can be specified as strings."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="local_external")
            .with_duration(hours=6.0, days_per_week=5)
            .with_protection(rpe="full_mask")  # APF=50
            .calculate()
        )

        # Full mask should provide significant protection
        assert result.overall_risk_level <= 4

    def test_rpe_enum_values(self):
        """Test RPE with enum values."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="local_external")
            .with_duration(hours=6.0, days_per_week=5)
            .with_protection(rpe=RPEType.TIGHT_FIT_50)
            .calculate()
        )

        assert isinstance(result, AssessmentResult)


class TestPlanMode:
    """Test planning mode (no PPE)."""

    def test_plan_shows_unprotected_risk(self):
        """Test that plan() calculates without PPE to show baseline risk."""
        assessment = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(
                property_type="solid",
                amount="medium",
                ventilation="local_external",
            )
            .with_duration(hours=6.0, days_per_week=5)
            .with_protection(rpe="half_mask")
        )

        # Plan mode should show unprotected baseline (ignores RPE setting)
        planned = assessment.plan()

        # Calculate should use the RPE
        calculated = assessment.calculate()

        # Plan should have higher RCR (no protection)
        plan_rcr = planned.components["7440-06-4"].inhalation.rcr
        calc_rcr = calculated.components["7440-06-4"].inhalation.rcr

        # Plan shows 10x higher RCR since half_mask has APF=10
        assert abs(plan_rcr / calc_rcr - 10) < 0.01


class TestSummary:
    """Test summary output methods."""

    def test_summary_english(self):
        """Test English summary output."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="local_external")
            .with_duration(hours=6.0, days_per_week=5)
            .calculate()
        )

        summary = result.summary()
        assert "Risk Assessment Summary" in summary
        assert "7440-06-4" in summary

    def test_summary_japanese(self):
        """Test Japanese summary output."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="local_external")
            .with_duration(hours=6.0, days_per_week=5)
            .calculate()
        )

        summary = result.summary_ja()
        assert "リスクアセスメント" in summary


class TestRecommendations:
    """Test recommendation integration."""

    def test_recommendations_available(self):
        """Test that recommendations are generated."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="local_external")
            .with_duration(hours=6.0, days_per_week=5)
            .calculate()
        )

        recs = result.recommendations
        assert isinstance(recs, list)

    def test_get_recommendations_top_n(self):
        """Test getting top N recommendations."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="local_external")
            .with_duration(hours=6.0, days_per_week=5)
            .calculate()
        )

        top_3 = result.get_recommendations(top_n=3)
        assert len(top_3) <= 3


class TestConditionParsing:
    """Test string parsing for conditions."""

    def test_property_type_parsing(self):
        """Test property type string parsing."""
        # Solid
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(property_type="solid")
            .calculate()
        )
        assert result is not None

        # Liquid
        result = (
            RiskAssessment()
            .add_substance("50-00-0", content=10.0)  # Formaldehyde
            .with_conditions(property_type="liquid")
            .calculate()
        )
        assert result is not None

    def test_amount_level_parsing(self):
        """Test amount level string parsing."""
        for amount in ["large", "medium", "small", "minute", "trace"]:
            result = (
                RiskAssessment()
                .add_substance("7440-06-4", content=100.0)
                .with_conditions(amount=amount)
                .calculate()
            )
            assert result is not None

    def test_ventilation_parsing(self):
        """Test ventilation level string parsing."""
        for vent in ["none", "basic", "industrial", "local_external", "local_enclosed", "sealed"]:
            result = (
                RiskAssessment()
                .add_substance("7440-06-4", content=100.0)
                .with_conditions(ventilation=vent)
                .calculate()
            )
            assert result is not None

    def test_invalid_property_type_raises(self):
        """Test that invalid property type raises error."""
        with pytest.raises(ValueError, match="Invalid property type"):
            (
                RiskAssessment()
                .add_substance("7440-06-4", content=100.0)
                .with_conditions(property_type="plasma")
                .calculate()
            )

    def test_invalid_amount_raises(self):
        """Test that invalid amount raises error."""
        with pytest.raises(ValueError, match="Invalid amount level"):
            (
                RiskAssessment()
                .add_substance("7440-06-4", content=100.0)
                .with_conditions(amount="huge")
                .calculate()
            )


class TestCustomSubstance:
    """Test custom substance objects."""

    def test_custom_substance(self):
        """Test assessment with custom substance object."""
        custom = Substance(
            cas_number="custom-001",
            name_ja="カスタム物質",
            name_en="Custom Substance",
            property_type=PropertyType.SOLID,
            ghs_classification=GHSClassification(
                acute_toxicity_inhalation_category="3",
            ),
            oel=OccupationalExposureLimits(
                acgih_tlv_twa=0.05,
                acgih_tlv_twa_unit="mg/m³",
            ),
        )

        result = (
            RiskAssessment()
            .add_substance(custom, content=100.0)
            .with_conditions(amount="medium", ventilation="basic")
            .with_duration(hours=8.0, days_per_week=5)
            .calculate()
        )

        assert "custom-001" in result.components
        assert result.components["custom-001"].name == "カスタム物質"


class TestTargetLevels:
    """Test target level configuration for recommendations."""

    def test_default_target_levels(self):
        """Test that default target levels are Level I."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="local_external")
            .calculate()
        )

        assert result.target_inhalation == DetailedRiskLevel.I
        assert result.target_dermal == DetailedRiskLevel.I
        assert result.target_physical == DetailedRiskLevel.I

    def test_custom_target_levels_with_enum(self):
        """Test setting custom target levels with DetailedRiskLevel enum."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="local_external")
            .with_target_levels(
                inhalation=DetailedRiskLevel.II_A,
                dermal=DetailedRiskLevel.II_B,
            )
            .calculate()
        )

        assert result.target_inhalation == DetailedRiskLevel.II_A
        assert result.target_dermal == DetailedRiskLevel.II_B
        assert result.target_physical == DetailedRiskLevel.I  # unchanged

    def test_custom_target_levels_with_strings(self):
        """Test setting target levels with string values."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="local_external")
            .with_target_levels(inhalation="II-A", dermal="II-B")
            .calculate()
        )

        assert result.target_inhalation == DetailedRiskLevel.II_A
        assert result.target_dermal == DetailedRiskLevel.II_B

    def test_ii_a_vs_ii_b_distinction(self):
        """Test that II-A and II-B have different RCR thresholds."""
        # II-A threshold is 0.5, II-B threshold is 1.0
        assert DetailedRiskLevel.II_A.get_rcr_threshold() == 0.5
        assert DetailedRiskLevel.II_B.get_rcr_threshold() == 1.0

        # With RCR=0.7, targeting II-A should recommend (0.7 > 0.5)
        # but targeting II-B should NOT recommend (0.7 < 1.0)

    def test_target_level_affects_recommendations(self):
        """Test that higher target levels reduce recommendations."""
        # With strict target (Level I) - should get recommendations
        strict_result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="local_external")
            .with_target_levels(inhalation=DetailedRiskLevel.I)
            .calculate()
        )

        # With lenient target (Level IV) - fewer/no recommendations
        lenient_result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="local_external")
            .with_target_levels(inhalation=DetailedRiskLevel.IV)
            .calculate()
        )

        # Lenient target should have fewer recommendations
        assert len(lenient_result.recommendations) <= len(strict_result.recommendations)

    def test_invalid_target_level_raises(self):
        """Test that invalid target levels raise errors."""
        with pytest.raises(ValueError, match="Invalid risk level"):
            (
                RiskAssessment()
                .add_substance("7440-06-4", content=100.0)
                .with_target_levels(inhalation="V")
            )

        with pytest.raises(ValueError, match="Invalid risk level"):
            (
                RiskAssessment()
                .add_substance("7440-06-4", content=100.0)
                .with_target_levels(dermal="invalid")
            )


class TestPhysicalHazards:
    """Test physical hazard assessment integration."""

    def test_physical_disabled_by_default(self):
        """Test that physical assessment is disabled by default."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="local_external")
            .calculate()
        )

        # Physical should be None when not enabled
        assert result.components["7440-06-4"].physical is None

    def test_physical_enabled_by_conditions(self):
        """Test that with_physical_conditions enables physical assessment."""
        result = (
            RiskAssessment()
            .add_substance("50-00-0", content=10.0)  # Formaldehyde - flammable
            .with_conditions(property_type="liquid", amount="medium", ventilation="local_external")
            .with_physical_conditions(
                process_temperature=50.0,
                has_ignition_sources=True,
            )
            .calculate()
        )

        # Physical should be assessed
        comp = result.components["50-00-0"]
        if comp.physical:  # May not be assessed if substance lacks physical properties
            assert comp.physical.risk_level is not None
            assert isinstance(comp.physical.hazard_type, str)

    def test_physical_enabled_by_with_assessments(self):
        """Test enabling physical via with_assessments method."""
        result = (
            RiskAssessment()
            .add_substance("50-00-0", content=10.0)
            .with_conditions(property_type="liquid", amount="medium")
            .with_assessments(physical=True)
            .calculate()
        )

        # Physical assessment was enabled (but may be None if no physical hazards)
        # Just verify no exception occurred
        assert result is not None

    def test_physical_in_summary(self):
        """Test that physical hazards appear in summary."""
        result = (
            RiskAssessment()
            .add_substance("50-00-0", content=10.0)
            .with_conditions(property_type="liquid", amount="medium")
            .with_physical_conditions(process_temperature=60.0)
            .calculate()
        )

        summary = result.summary()
        # Summary should at least have the basic structure
        assert "Risk Assessment Summary" in summary

    def test_physical_in_to_dict(self):
        """Test physical hazard serialization in to_dict."""
        result = (
            RiskAssessment()
            .add_substance("50-00-0", content=10.0)
            .with_conditions(property_type="liquid", amount="medium")
            .with_physical_conditions(process_temperature=50.0)
            .calculate()
        )

        d = result.to_dict()
        # Components should be in dict
        assert "components" in d
        assert "50-00-0" in d["components"]
        # Physical key should exist (may be None)
        assert "physical" in d["components"]["50-00-0"]

    def test_physical_target_level(self):
        """Test setting physical target level."""
        result = (
            RiskAssessment()
            .add_substance("50-00-0", content=10.0)
            .with_conditions(property_type="liquid", amount="medium")
            .with_target_levels(physical=DetailedRiskLevel.II_A)
            .calculate()
        )

        assert result.target_physical == DetailedRiskLevel.II_A

    def test_what_if_preserves_physical_conditions(self):
        """Test that what_if preserves physical conditions."""
        result = (
            RiskAssessment()
            .add_substance("50-00-0", content=10.0)
            .with_conditions(property_type="liquid", amount="medium", ventilation="local_external")
            .with_physical_conditions(process_temperature=50.0, has_ignition_sources=True)
            .calculate()
        )

        # Run what-if with changed ventilation
        new_result = result.what_if(ventilation="sealed")

        # Should complete without error
        assert new_result is not None
        # Overall risk level should be valid
        assert new_result.overall_risk_level >= 0


class TestWarnings:
    """Test skin notation, carcinogen, and mutagen warnings."""

    def test_skin_notation_with_custom_substance(self):
        """Test that skin notation warning appears when set."""
        custom = Substance(
            cas_number="skin-001",
            name_ja="経皮吸収物質",
            name_en="Skin Absorbing Substance",
            property_type=PropertyType.LIQUID,
            ghs=GHSClassification(
                acute_toxicity_inhalation_vapor="3",
            ),
            oel=OccupationalExposureLimits(
                acgih_tlv_twa=0.1,
                acgih_tlv_twa_unit="mg/m³",
                skin_notation=True,  # Skin notation set
            ),
        )

        result = (
            RiskAssessment()
            .add_substance(custom, content=100.0)
            .with_conditions(property_type="liquid", amount="medium", ventilation="local_external")
            .calculate()
        )

        comp = result.components["skin-001"]
        assert comp.has_skin_notation is True
        assert len(comp.warnings) > 0
        assert any("SKIN" in w for w in comp.warnings)

    def test_carcinogen_warning(self):
        """Test that carcinogen warning appears for carcinogenic substances."""
        custom = Substance(
            cas_number="carc-001",
            name_ja="発がん性物質",
            name_en="Carcinogenic Substance",
            property_type=PropertyType.SOLID,
            ghs=GHSClassification(
                acute_toxicity_inhalation_dust="3",
                carcinogenicity="1A",  # Carcinogen Category 1A
            ),
            oel=OccupationalExposureLimits(
                acgih_tlv_twa=0.01,
                acgih_tlv_twa_unit="mg/m³",
            ),
        )

        result = (
            RiskAssessment()
            .add_substance(custom, content=100.0)
            .with_conditions(property_type="solid", amount="medium", ventilation="local_external")
            .calculate()
        )

        comp = result.components["carc-001"]
        assert comp.is_carcinogen is True
        assert comp.carcinogenicity_category == "1A"
        assert len(comp.warnings) > 0
        assert any("CARCINOGEN" in w for w in comp.warnings)

    def test_mutagen_warning(self):
        """Test that mutagen warning appears for mutagenic substances."""
        custom = Substance(
            cas_number="mutag-001",
            name_ja="変異原性物質",
            name_en="Mutagenic Substance",
            property_type=PropertyType.SOLID,
            ghs=GHSClassification(
                acute_toxicity_inhalation_dust="3",
                germ_cell_mutagenicity="1B",  # Mutagen Category 1B
            ),
            oel=OccupationalExposureLimits(
                acgih_tlv_twa=0.01,
                acgih_tlv_twa_unit="mg/m³",
            ),
        )

        result = (
            RiskAssessment()
            .add_substance(custom, content=100.0)
            .with_conditions(property_type="solid", amount="medium", ventilation="local_external")
            .calculate()
        )

        comp = result.components["mutag-001"]
        assert comp.is_mutagen is True
        assert comp.mutagenicity_category == "1B"
        assert len(comp.warnings) > 0
        assert any("MUTAGEN" in w for w in comp.warnings)

    def test_no_warnings_for_safe_substance(self):
        """Test that no warnings appear for substances without hazards."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="local_external")
            .calculate()
        )

        # Platinum shouldn't have these warnings
        comp = result.components["7440-06-4"]
        # Verify warnings is a list (may be empty)
        assert isinstance(comp.warnings, list)

    def test_warnings_in_to_dict(self):
        """Test that warnings are included in to_dict output."""
        custom = Substance(
            cas_number="warn-001",
            name_ja="警告物質",
            name_en="Warning Substance",
            property_type=PropertyType.SOLID,
            ghs=GHSClassification(
                carcinogenicity="2",
            ),
            oel=OccupationalExposureLimits(
                acgih_tlv_twa=0.1,
                acgih_tlv_twa_unit="mg/m³",
                skin_notation=True,
            ),
        )

        result = (
            RiskAssessment()
            .add_substance(custom, content=100.0)
            .with_conditions(property_type="solid", amount="medium")
            .calculate()
        )

        d = result.components["warn-001"].to_dict()
        assert "warnings" in d
        assert "has_skin_notation" in d
        assert "is_carcinogen" in d
        assert "is_mutagen" in d
        assert d["has_skin_notation"] is True
        assert d["is_carcinogen"] is True

    def test_japanese_warnings(self):
        """Test that Japanese warnings are properly formatted."""
        custom = Substance(
            cas_number="ja-warn-001",
            name_ja="警告物質",
            name_en="Warning Substance",
            property_type=PropertyType.SOLID,
            ghs=GHSClassification(
                carcinogenicity="1B",
            ),
            oel=OccupationalExposureLimits(
                acgih_tlv_twa=0.1,
                acgih_tlv_twa_unit="mg/m³",
            ),
        )

        result = (
            RiskAssessment()
            .add_substance(custom, content=100.0)
            .with_conditions(property_type="solid", amount="medium")
            .calculate()
        )

        comp = result.components["ja-warn-001"]
        ja_warnings = comp.warnings_ja
        assert len(ja_warnings) > 0
        assert any("発がん性" in w for w in ja_warnings)


class TestSTEL:
    """Test STEL (Short-Term Exposure Limit) assessment."""

    def test_stel_assessment_with_stel_oel(self):
        """Test that STEL is assessed when STEL OEL is available."""
        custom = Substance(
            cas_number="stel-001",
            name_ja="STEL物質",
            name_en="STEL Substance",
            property_type=PropertyType.LIQUID,
            ghs=GHSClassification(
                acute_toxicity_inhalation_vapor="3",
            ),
            oel=OccupationalExposureLimits(
                acgih_tlv_twa=50.0,
                acgih_tlv_twa_unit="ppm",
                acgih_tlv_stel=100.0,  # STEL is 2x TWA
                acgih_tlv_stel_unit="ppm",
            ),
        )

        result = (
            RiskAssessment()
            .add_substance(custom, content=100.0)
            .with_conditions(property_type="liquid", amount="medium", ventilation="local_external")
            .calculate()
        )

        comp = result.components["stel-001"]
        # Should have STEL assessment
        assert comp.has_stel_assessment is True
        assert comp.stel_rcr is not None
        assert comp.stel_risk_level is not None

    def test_stel_in_inhalation_dict(self):
        """Test STEL fields appear in inhalation dict."""
        custom = Substance(
            cas_number="stel-002",
            name_ja="STEL物質2",
            name_en="STEL Substance 2",
            property_type=PropertyType.SOLID,
            ghs=GHSClassification(
                acute_toxicity_inhalation_dust="3",
            ),
            oel=OccupationalExposureLimits(
                acgih_tlv_twa=0.5,
                acgih_tlv_twa_unit="mg/m³",
                acgih_tlv_stel=1.0,
                acgih_tlv_stel_unit="mg/m³",
            ),
        )

        result = (
            RiskAssessment()
            .add_substance(custom, content=100.0)
            .with_conditions(property_type="solid", amount="medium")
            .calculate()
        )

        comp = result.components["stel-002"]
        d = comp["inhalation"]
        if comp.has_stel_assessment:
            assert "stel_rcr" in d
            assert "stel_risk_level" in d
            assert "stel_oel" in d

    def test_stel_fallback_when_no_stel_oel(self):
        """Test that STEL uses OEL×3 fallback when no specific STEL OEL available.

        Reference: VBA modCalc.bas lines 193-194, 218-221
        """
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)  # Platinum has no specific STEL OEL
            .with_conditions(amount="medium", ventilation="local_external")
            .calculate()
        )

        comp = result.components["7440-06-4"]
        # Should have STEL assessment using OEL×3 fallback
        assert comp.has_stel_assessment is True
        assert comp.stel_rcr is not None
        # STEL OEL should be 3× the 8-hour OEL
        assert comp.inhalation.stel_oel == comp.inhalation.oel * 3
        # Source should indicate it's a ×3 calculation
        assert "×3" in comp.inhalation.stel_oel_source

    def test_stel_in_summary(self):
        """Test STEL appears in summary when available."""
        custom = Substance(
            cas_number="stel-003",
            name_ja="STEL物質3",
            name_en="STEL Substance 3",
            property_type=PropertyType.LIQUID,
            ghs=GHSClassification(
                acute_toxicity_inhalation_vapor="3",
            ),
            oel=OccupationalExposureLimits(
                acgih_tlv_twa=25.0,
                acgih_tlv_twa_unit="ppm",
                acgih_tlv_stel=50.0,
                acgih_tlv_stel_unit="ppm",
            ),
        )

        result = (
            RiskAssessment()
            .add_substance(custom, content=100.0)
            .with_conditions(property_type="liquid", amount="medium")
            .calculate()
        )

        summary = result.summary()
        if result.components["stel-003"].has_stel_assessment:
            assert "STEL" in summary


class TestMixedExposure:
    """Test mixed exposure (additive effect) calculation."""

    def test_mixed_inhalation_rcr_single_substance(self):
        """Test that mixed RCR equals individual RCR for single substance."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="local_external")
            .calculate()
        )

        # For single substance, mixed = individual
        if result.mixed_inhalation_rcr is not None:
            comp = result.components["7440-06-4"]
            assert abs(result.mixed_inhalation_rcr - comp.inhalation.rcr) < 0.001

    def test_mixed_inhalation_rcr_multiple_substances(self):
        """Test that mixed RCR is sum of individual RCRs for multiple substances."""
        # Use two substances with known OEL values
        custom1 = Substance(
            cas_number="mix-001",
            name_ja="物質1",
            name_en="Substance 1",
            property_type=PropertyType.SOLID,
            ghs=GHSClassification(acute_toxicity_inhalation_dust="3"),
            oel=OccupationalExposureLimits(acgih_tlv_twa=1.0, acgih_tlv_twa_unit="mg/m³"),
        )
        custom2 = Substance(
            cas_number="mix-002",
            name_ja="物質2",
            name_en="Substance 2",
            property_type=PropertyType.SOLID,
            ghs=GHSClassification(acute_toxicity_inhalation_dust="3"),
            oel=OccupationalExposureLimits(acgih_tlv_twa=2.0, acgih_tlv_twa_unit="mg/m³"),
        )

        result = (
            RiskAssessment()
            .add_substance(custom1, content=50.0)
            .add_substance(custom2, content=50.0)
            .with_conditions(property_type="solid", amount="medium", ventilation="local_external")
            .calculate()
        )

        # Mixed RCR should be sum of individual RCRs
        rcr1 = result.components["mix-001"].inhalation.rcr
        rcr2 = result.components["mix-002"].inhalation.rcr
        assert result.mixed_inhalation_rcr is not None
        assert abs(result.mixed_inhalation_rcr - (rcr1 + rcr2)) < 0.001

    def test_mixed_exposure_in_to_dict(self):
        """Test that mixed exposure appears in to_dict for multiple substances."""
        custom1 = Substance(
            cas_number="dict-001",
            name_ja="物質1",
            name_en="Substance 1",
            property_type=PropertyType.SOLID,
            ghs=GHSClassification(acute_toxicity_inhalation_dust="3"),
            oel=OccupationalExposureLimits(acgih_tlv_twa=1.0, acgih_tlv_twa_unit="mg/m³"),
        )
        custom2 = Substance(
            cas_number="dict-002",
            name_ja="物質2",
            name_en="Substance 2",
            property_type=PropertyType.SOLID,
            ghs=GHSClassification(acute_toxicity_inhalation_dust="3"),
            oel=OccupationalExposureLimits(acgih_tlv_twa=2.0, acgih_tlv_twa_unit="mg/m³"),
        )

        result = (
            RiskAssessment()
            .add_substance(custom1, content=50.0)
            .add_substance(custom2, content=50.0)
            .with_conditions(property_type="solid", amount="medium")
            .calculate()
        )

        d = result.to_dict()
        assert "mixed_exposure" in d
        assert "inhalation_rcr" in d["mixed_exposure"]
        assert d["mixed_exposure"]["inhalation_rcr"] is not None

    def test_no_mixed_exposure_for_single_substance(self):
        """Test that mixed_exposure is not in to_dict for single substance."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="local_external")
            .calculate()
        )

        d = result.to_dict()
        assert "mixed_exposure" not in d

    def test_mixed_exposure_in_summary(self):
        """Test that mixed exposure appears in summary for multiple substances."""
        custom1 = Substance(
            cas_number="sum-001",
            name_ja="物質1",
            name_en="Substance 1",
            property_type=PropertyType.SOLID,
            ghs=GHSClassification(acute_toxicity_inhalation_dust="3"),
            oel=OccupationalExposureLimits(acgih_tlv_twa=1.0, acgih_tlv_twa_unit="mg/m³"),
        )
        custom2 = Substance(
            cas_number="sum-002",
            name_ja="物質2",
            name_en="Substance 2",
            property_type=PropertyType.SOLID,
            ghs=GHSClassification(acute_toxicity_inhalation_dust="3"),
            oel=OccupationalExposureLimits(acgih_tlv_twa=2.0, acgih_tlv_twa_unit="mg/m³"),
        )

        result = (
            RiskAssessment()
            .add_substance(custom1, content=50.0)
            .add_substance(custom2, content=50.0)
            .with_conditions(property_type="solid", amount="medium")
            .calculate()
        )

        summary = result.summary()
        assert "Mixed Exposure" in summary
        assert "Combined RCR" in summary

    def test_mixed_exposure_risk_level(self):
        """Test that mixed exposure risk level is calculated correctly."""
        custom1 = Substance(
            cas_number="level-001",
            name_ja="物質1",
            name_en="Substance 1",
            property_type=PropertyType.SOLID,
            ghs=GHSClassification(acute_toxicity_inhalation_dust="3"),
            oel=OccupationalExposureLimits(acgih_tlv_twa=1.0, acgih_tlv_twa_unit="mg/m³"),
        )
        custom2 = Substance(
            cas_number="level-002",
            name_ja="物質2",
            name_en="Substance 2",
            property_type=PropertyType.SOLID,
            ghs=GHSClassification(acute_toxicity_inhalation_dust="3"),
            oel=OccupationalExposureLimits(acgih_tlv_twa=1.0, acgih_tlv_twa_unit="mg/m³"),
        )

        result = (
            RiskAssessment()
            .add_substance(custom1, content=50.0)
            .add_substance(custom2, content=50.0)
            .with_conditions(property_type="solid", amount="medium")
            .calculate()
        )

        # Mixed risk level should be valid
        assert result.mixed_inhalation_risk_level is not None
        assert result.mixed_inhalation_risk_level >= 1
        assert result.mixed_inhalation_risk_level <= 4


class TestAchievability:
    """Test minimum achievable level display."""

    def test_level_one_achievable_property(self):
        """Test level_one_achievable property on result."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="small", ventilation="local_external")
            .calculate()
        )

        # Should have boolean achievability property
        assert isinstance(result.level_one_achievable, bool)

    def test_min_achievable_level_property(self):
        """Test min_achievable_level property on result."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="local_external")
            .calculate()
        )

        # Should have min_achievable_level property
        assert isinstance(result.min_achievable_level, int)
        assert result.min_achievable_level >= 1
        assert result.min_achievable_level <= 4

    def test_component_level_one_achievable(self):
        """Test level_one_achievable property on component result."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="local_external")
            .calculate()
        )

        comp = result.components["7440-06-4"]
        assert isinstance(comp.level_one_achievable, bool)

    def test_component_min_achievable_level(self):
        """Test min_achievable_level property on component result."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="local_external")
            .calculate()
        )

        comp = result.components["7440-06-4"]
        # May be None if not calculated
        min_level = comp.min_achievable_level
        if min_level is not None:
            assert min_level >= 1
            assert min_level <= 4

    def test_limitations_summary(self):
        """Test limitations_summary property."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="local_external")
            .calculate()
        )

        summary = result.limitations_summary
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_dict_access_achievability(self):
        """Test dict-like access to achievability properties."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="local_external")
            .calculate()
        )

        # Result level access
        assert isinstance(result["level_one_achievable"], bool)
        assert isinstance(result["min_achievable_level"], int)
        assert isinstance(result["limitations_summary"], str)

    def test_to_dict_includes_achievability(self):
        """Test that to_dict includes achievability information."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="local_external")
            .calculate()
        )

        d = result.to_dict()
        assert "achievability" in d
        assert "level_one_achievable" in d["achievability"]
        assert "min_achievable_level" in d["achievability"]

    def test_summary_shows_achievability_when_limited(self):
        """Test that summary shows achievability info when Level I is not achievable."""
        # Use a low OEL to ensure Level I is not achievable
        custom = Substance(
            cas_number="ach-001",
            name_ja="テスト物質",
            name_en="Test Substance",
            property_type=PropertyType.SOLID,
            ghs=GHSClassification(carcinogenicity="1A"),  # Carcinogen triggers ACRmax
            oel=OccupationalExposureLimits(acgih_tlv_twa=0.001, acgih_tlv_twa_unit="mg/m³"),
        )

        result = (
            RiskAssessment()
            .add_substance(custom, content=100.0)
            .with_conditions(property_type="solid", amount="large")
            .calculate()
        )

        # If Level I is not achievable, summary should mention it
        if not result.level_one_achievable:
            summary = result.summary()
            assert "Level I" in summary or "Achievability" in summary


class TestRegulations:
    """Test regulation checking."""

    def test_regulations_property(self):
        """Test that regulations are checked."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="local_external")
            .calculate()
        )

        # Regulations should be a list (may be empty)
        assert isinstance(result.regulations, list)


class TestWorkAreaSize:
    """Test work area size factor for liquids."""

    def test_work_area_size_small_increases_exposure(self):
        """Test that small work area increases exposure for liquids."""
        # Baseline without work area size
        baseline = (
            RiskAssessment()
            .add_substance("67-64-1", content=100.0)  # Acetone (liquid)
            .with_conditions(property_type="liquid", amount="medium", ventilation="industrial")
            .calculate()
        )

        # Small work area should increase exposure
        small_area = (
            RiskAssessment()
            .add_substance("67-64-1", content=100.0)
            .with_conditions(
                property_type="liquid",
                amount="medium",
                ventilation="industrial",
                work_area_size="small",
            )
            .calculate()
        )

        baseline_exp = baseline.components["67-64-1"].inhalation.exposure_8hr
        small_exp = small_area.components["67-64-1"].inhalation.exposure_8hr
        assert small_exp > baseline_exp

    def test_work_area_size_large_decreases_exposure(self):
        """Test that large work area decreases exposure for liquids."""
        # Baseline without work area size
        baseline = (
            RiskAssessment()
            .add_substance("67-64-1", content=100.0)  # Acetone
            .with_conditions(property_type="liquid", amount="medium", ventilation="industrial")
            .calculate()
        )

        # Large work area should decrease exposure
        large_area = (
            RiskAssessment()
            .add_substance("67-64-1", content=100.0)
            .with_conditions(
                property_type="liquid",
                amount="medium",
                ventilation="industrial",
                work_area_size="large",
            )
            .calculate()
        )

        baseline_exp = baseline.components["67-64-1"].inhalation.exposure_8hr
        large_exp = large_area.components["67-64-1"].inhalation.exposure_8hr
        assert large_exp < baseline_exp

    def test_work_area_size_no_effect_on_solids(self):
        """Test that work area size has no effect on solids."""
        # Solid baseline
        solid_baseline = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)  # Platinum (solid)
            .with_conditions(property_type="solid", amount="medium", ventilation="industrial")
            .calculate()
        )

        # Solid with work area size (should have no effect)
        solid_large = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(
                property_type="solid",
                amount="medium",
                ventilation="industrial",
                work_area_size="large",
            )
            .calculate()
        )

        baseline_exp = solid_baseline.components["7440-06-4"].inhalation.exposure_8hr
        large_exp = solid_large.components["7440-06-4"].inhalation.exposure_8hr
        # Should be equal for solids
        assert baseline_exp == large_exp

    def test_invalid_work_area_size_raises(self):
        """Test that invalid work area size raises error."""
        import pytest

        with pytest.raises(ValueError, match="Invalid work area size"):
            RiskAssessment().with_conditions(work_area_size="extra_large")


class TestGloveTraining:
    """Test glove training effect for dermal exposure."""

    def test_glove_training_reduces_dermal_exposure(self):
        """Test that glove training reduces dermal exposure when gloves are worn."""
        from ra_library.models.substance import PhysicochemicalProperties

        # Create substance with required dermal properties
        custom = Substance(
            cas_number="glove-001",
            name_ja="テスト物質",
            name_en="Test Substance",
            property_type=PropertyType.LIQUID,
            oel=OccupationalExposureLimits(
                acgih_tlv_twa=50.0,
                acgih_tlv_twa_unit="ppm",
                dnel_worker_inhalation=10.0,
            ),
            properties=PhysicochemicalProperties(
                molecular_weight=100.0,
                log_kow=2.0,
                density=1.0,
            ),
        )

        # Without training
        no_training = (
            RiskAssessment()
            .add_substance(custom, content=100.0)
            .with_conditions(property_type="liquid", amount="medium")
            .with_protection(gloves="resistant", glove_training=False)
            .calculate()
        )

        # With training
        with_training = (
            RiskAssessment()
            .add_substance(custom, content=100.0)
            .with_conditions(property_type="liquid", amount="medium")
            .with_protection(gloves="resistant", glove_training=True)
            .calculate()
        )

        no_train_dermal = no_training.components["glove-001"].dermal
        with_train_dermal = with_training.components["glove-001"].dermal

        # With training should have lower absorption
        assert with_train_dermal.skin_absorption < no_train_dermal.skin_absorption

    def test_glove_training_no_effect_without_gloves(self):
        """Test that glove training has no effect when no gloves are worn."""
        from ra_library.models.substance import PhysicochemicalProperties

        custom = Substance(
            cas_number="glove-002",
            name_ja="テスト物質2",
            name_en="Test Substance 2",
            property_type=PropertyType.LIQUID,
            oel=OccupationalExposureLimits(
                acgih_tlv_twa=50.0,
                dnel_worker_inhalation=10.0,
            ),
            properties=PhysicochemicalProperties(
                molecular_weight=100.0,
                log_kow=2.0,
                density=1.0,
            ),
        )

        # Without gloves, no training
        no_gloves_no_train = (
            RiskAssessment()
            .add_substance(custom, content=100.0)
            .with_conditions(property_type="liquid", amount="medium")
            .with_protection(gloves="none", glove_training=False)
            .calculate()
        )

        # Without gloves, with training (should have no effect)
        no_gloves_with_train = (
            RiskAssessment()
            .add_substance(custom, content=100.0)
            .with_conditions(property_type="liquid", amount="medium")
            .with_protection(gloves="none", glove_training=True)
            .calculate()
        )

        no_train_abs = no_gloves_no_train.components["glove-002"].dermal.skin_absorption
        with_train_abs = no_gloves_with_train.components["glove-002"].dermal.skin_absorption

        # Should be equal - training without gloves has no effect
        assert no_train_abs == with_train_abs


class TestComparisonMode:
    """Test comparison between assessment results."""

    def test_compare_to_returns_dict(self):
        """Test that compare_to returns a dictionary."""
        baseline = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="large", ventilation="none")
            .calculate()
        )

        improved = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="large", ventilation="local_external")
            .calculate()
        )

        comparison = improved.compare_to(baseline)
        assert isinstance(comparison, dict)
        assert "overall" in comparison
        assert "components" in comparison
        assert "summary" in comparison

    def test_compare_detects_improvement(self):
        """Test that comparison correctly detects improvement."""
        baseline = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="large", ventilation="none")
            .calculate()
        )

        improved = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="large", ventilation="local_external")
            .calculate()
        )

        # Better conditions should improve risk
        comparison = improved.compare_to(baseline)

        # improved has lower exposure than baseline
        inh_comp = comparison["components"]["7440-06-4"]["inhalation"]
        assert inh_comp["improved"]  # Lower RCR = improved
        assert inh_comp["this_rcr"] < inh_comp["other_rcr"]

    def test_compare_summary_string(self):
        """Test that compare_summary returns readable string."""
        baseline = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="industrial")
            .calculate()
        )

        improved = baseline.what_if(ventilation="local_external")

        summary = improved.compare_summary(baseline)
        assert isinstance(summary, str)
        assert "Comparison" in summary or "RCR" in summary

    def test_compare_summary_ja(self):
        """Test that compare_summary_ja returns Japanese string."""
        baseline = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="industrial")
            .calculate()
        )

        improved = baseline.what_if(ventilation="local_external")

        summary = improved.compare_summary_ja(baseline)
        assert isinstance(summary, str)
        assert "比較" in summary or "RCR" in summary

    def test_compare_with_what_if(self):
        """Test using compare with what_if analysis."""
        baseline = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="basic")
            .calculate()
        )

        # Run what-if and compare
        with_better_vent = baseline.what_if(ventilation="local_external")
        comparison = with_better_vent.compare_to(baseline)

        # Should show improvement
        assert comparison["overall"]["level_improved"] or comparison["components"]["7440-06-4"]["inhalation"]["improved"]


class TestExport:
    """Test export features."""

    def test_to_csv_returns_string(self):
        """Test that to_csv returns CSV string."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="industrial")
            .calculate()
        )

        csv_output = result.to_csv()
        assert isinstance(csv_output, str)
        assert "7440-06-4" in csv_output
        assert "CAS Number" in csv_output

    def test_to_csv_multiple_substances(self):
        """Test CSV export with multiple substances."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=50.0)
            .add_substance("67-64-1", content=25.0)
            .with_conditions(amount="medium", ventilation="industrial")
            .calculate()
        )

        csv_output = result.to_csv()
        assert "7440-06-4" in csv_output
        assert "67-64-1" in csv_output

    def test_to_csv_without_header(self):
        """Test CSV export without header."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="industrial")
            .calculate()
        )

        csv_no_header = result.to_csv(include_header=False)
        assert "CAS Number" not in csv_no_header
        assert "7440-06-4" in csv_no_header

    def test_to_json_returns_string(self):
        """Test that to_json returns JSON string."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="industrial")
            .calculate()
        )

        json_output = result.to_json()
        assert isinstance(json_output, str)
        import json
        parsed = json.loads(json_output)
        assert "overall_risk_level" in parsed

    def test_to_toml_returns_string(self):
        """Test that to_toml returns TOML string."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="industrial")
            .calculate()
        )

        toml_output = result.to_toml()
        assert isinstance(toml_output, str)
        assert "[meta]" in toml_output
        assert "[conditions]" in toml_output
        assert "7440-06-4" in toml_output

    def test_to_toml_with_constraints(self):
        """Test TOML export includes constraints."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(amount="medium", ventilation="local_enclosed")
            .with_constraints(max_ventilation="local_enclosed", excluded_rpe=["scba"])
            .calculate()
        )

        toml_output = result.to_toml()
        assert "[constraints]" in toml_output
        assert "max_ventilation" in toml_output
        assert "excluded_rpe" in toml_output


class TestAutoControlVelocity:
    """Test auto-enable control velocity for draft."""

    def test_auto_control_velocity_for_local_enclosed(self):
        """Test that control velocity is auto-enabled for enclosed local exhaust."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(ventilation="local_enclosed")
            .calculate()
        )

        assert result.builder._control_velocity_verified is True
        assert result.builder._control_velocity_auto_enabled is True

    def test_auto_control_velocity_for_local_external(self):
        """Test that control velocity is auto-enabled for external local exhaust."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(ventilation="local_external")
            .calculate()
        )

        assert result.builder._control_velocity_verified is True
        assert result.builder._control_velocity_auto_enabled is True

    def test_can_override_auto_control_velocity(self):
        """Test that auto control velocity can be overridden."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(ventilation="local_enclosed", control_velocity_verified=False)
            .calculate()
        )

        assert result.builder._control_velocity_verified is False
        assert result.builder._control_velocity_auto_enabled is False

    def test_auto_note_in_output(self):
        """Test that auto-enable note appears in output."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(ventilation="local_enclosed")
            .calculate()
        )

        report = result.full_report("ja")
        assert "局所排気のため自動適用" in report


class TestConstraints:
    """Test recommendation constraints."""

    def test_max_ventilation_excludes_sealed(self):
        """Test that max_ventilation=local_enclosed excludes sealed system."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(ventilation="industrial", property_type="solid", amount="medium")
            .with_constraints(max_ventilation="local_enclosed")
            .with_target_levels(inhalation=DetailedRiskLevel.II_A)
            .calculate()
        )

        report = result.full_report("ja")
        # Sealed should be excluded
        assert "密閉系システム" not in report or "制約による除外" in report

    def test_excluded_rpe_removes_scba(self):
        """Test that excluded_rpe removes SCBA from recommendations."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(ventilation="industrial", property_type="solid", amount="medium")
            .with_constraints(excluded_rpe=["scba"])
            .with_target_levels(inhalation=DetailedRiskLevel.II_A)
            .calculate()
        )

        report = result.full_report("ja")
        # SCBA should be excluded from recommendations
        # Check that it's not in the actual measure descriptions (〈レベル〉 sections)
        # but it should be noted in the exclusion list (制約による除外)
        lines = report.split("\n")
        in_level_section = False
        scba_as_measure = False
        for line in lines:
            if line.strip().startswith("〈レベル"):
                in_level_section = True
            if "制限事項" in line or "制約による除外" in line:
                in_level_section = False
            if in_level_section and "最小対策:" in line and "自給式空気呼吸器" in line:
                scba_as_measure = True

        assert not scba_as_measure, "SCBA should not appear as a recommended measure"
        # But it should appear in the exclusion notes
        assert "制約による除外" in report
        assert "自給式空気呼吸器" in report  # Should be in exclusion notes

    def test_constraint_exclusions_shown_in_output(self):
        """Test that constraint exclusions are shown in output."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=5.0)
            .with_conditions(ventilation="local_enclosed", property_type="solid", amount="medium")
            .with_constraints(max_ventilation="local_enclosed", excluded_rpe=["scba"])
            .with_target_levels(inhalation=DetailedRiskLevel.II_A)
            .calculate()
        )

        report = result.full_report("ja")
        assert "制約による除外" in report

    def test_with_constraints_returns_builder(self):
        """Test that with_constraints returns builder for chaining."""
        builder = RiskAssessment()
        result = builder.with_constraints(max_ventilation="local_enclosed")
        assert result is builder


class TestEngineeringLimitDisplay:
    """Test engineering control limit display with contextual explanation."""

    def test_at_limit_shows_optimized_message(self):
        """Test that when at engineering limit, shows optimized message."""
        # Note: Using sealed ventilation to reach engineering limit
        # With VBA-correct time coefficient (0.1 for ≤4 weekly hrs),
        # sealed ventilation (0.001 coeff) is needed to reach model floor
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=5.0)  # Platinum - low OEL = model floor
            .with_conditions(
                property_type="solid",
                amount="medium",
                ventilation="sealed",  # Sealed to reach engineering limit
            )
            .with_duration(hours=0.5, days_per_week=1)
            .calculate()
        )

        report = result.full_report("ja")
        # Should show "optimized" message since current RCR equals min achievable
        assert "工学的対策の限界" in report
        assert "工学的対策として最適化済み" in report
        assert "暴露推定モデル下限値" in report

    def test_shows_reason_for_limit(self):
        """Test that the reason for the limit is shown."""
        # Note: Using sealed ventilation to reach engineering limit
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=5.0)
            .with_conditions(
                property_type="solid",
                amount="medium",
                ventilation="sealed",  # Sealed to reach engineering limit
            )
            .with_duration(hours=0.5, days_per_week=1)
            .calculate()
        )

        report = result.full_report("ja")
        # Should show reason
        assert "理由:" in report

    def test_shows_rpe_needed_for_target(self):
        """Test that RPE recommendation is shown when needed for target."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=5.0)
            .with_conditions(
                property_type="solid",
                amount="medium",
                ventilation="local_enclosed",
                control_velocity_verified=True,
            )
            .with_duration(hours=0.5, days_per_week=1)
            .calculate()
        )

        report = result.full_report("ja")
        # Should show that RPE is needed
        assert "呼吸用保護具（RPE）が必要" in report

    def test_limitations_in_recommendations_section(self):
        """Test that engineering limit is shown in recommendations section."""
        # Note: Using sealed ventilation to reach engineering limit
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=5.0)
            .with_conditions(
                property_type="solid",
                amount="medium",
                ventilation="sealed",  # Sealed to reach engineering limit
            )
            .with_duration(hours=0.5, days_per_week=1)
            .calculate()
        )

        report = result.full_report("ja")
        # Recommendations section should mention the limitation
        assert "工学的対策は最適化済み（モデル下限に到達）" in report


class TestDetailedRiskLevelDisplay:
    """Test that detailed risk levels (II-A, II-B) display correctly."""

    def test_8hr_twa_shows_detailed_level_ii_b(self):
        """Test that 8-hour TWA shows II-B when RCR is around 1.0."""
        # RCR 0.5 < x <= 1.0 should show II-B
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=5.0)  # Platinum at 5%
            .with_conditions(
                property_type="solid",
                amount="medium",
                ventilation="local_enclosed",
                control_velocity_verified=True,
            )
            .with_duration(hours=0.5, days_per_week=1)
            .calculate()
        )

        report = result.full_report("ja")
        # 8-hour TWA should show II-B (detailed level)
        assert "リスクレベル: II-B" in report or "レベルII-B" in report

    def test_8hr_twa_shows_detailed_level_ii_a(self):
        """Test that 8-hour TWA shows II-A when RCR is around 0.5."""
        # RCR 0.1 < x <= 0.5 should show II-A
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=1.0)  # Platinum at 1%
            .with_conditions(
                property_type="solid",
                amount="small",
                ventilation="local_enclosed",
                control_velocity_verified=True,
            )
            .with_duration(hours=0.5, days_per_week=1)
            .calculate()
        )

        report = result.full_report("ja")
        comp = result.components.get("7440-06-4")
        if comp and comp.inhalation and comp.inhalation.rcr <= 0.5:
            # If RCR is <= 0.5, should show II-A
            assert "レベルII-A" in report or "リスクレベル: II-A" in report or "リスクレベル: I" in report

    def test_stel_shows_basic_level_only(self):
        """Test that STEL shows basic level (II, not II-A/II-B)."""
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=5.0)
            .with_conditions(
                property_type="solid",
                amount="medium",
                ventilation="local_enclosed",
                control_velocity_verified=True,
            )
            .with_duration(hours=0.5, days_per_week=1)
            .calculate()
        )

        report = result.full_report("ja")
        lines = report.split("\n")

        # Find STEL detailed section (【吸入リスク（短時間暴露）】) and its risk level
        in_stel_detailed_section = False
        stel_level_line = None
        for line in lines:
            if "【吸入リスク（短時間暴露）】" in line:
                in_stel_detailed_section = True
            elif in_stel_detailed_section:
                # Exit at next section or blank paragraph
                if line.startswith("【") or (line.strip() == "" and stel_level_line):
                    break
                if "リスクレベル:" in line:
                    stel_level_line = line
                    break

        # STEL should show basic level (II), not II-A or II-B
        assert stel_level_line is not None, "STEL risk level line not found"
        # If it shows II, it should NOT have -A or -B suffix
        if "II" in stel_level_line:
            assert "II-A" not in stel_level_line and "II-B" not in stel_level_line, \
                f"STEL should use basic level, got: {stel_level_line}"


class TestCalculationDiagnostics:
    """Test structured diagnostics when recoverable calculation errors occur."""

    def test_component_records_calculation_errors(self, monkeypatch):
        """Inhalation failures should be captured in component and result diagnostics."""
        from ra_library.calculators import inhalation as inhalation_module

        def _raise_inhalation(*args, **kwargs):
            raise ValueError("forced failure for test")

        monkeypatch.setattr(inhalation_module, "calculate_inhalation_risk", _raise_inhalation)

        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=100.0)
            .with_conditions(property_type="solid", amount="medium", ventilation="local_external")
            .calculate()
        )

        comp = result.components["7440-06-4"]
        assert comp.inhalation is None
        assert comp.has_calculation_errors is True
        assert comp.calculation_errors[0]["risk_type"] == "inhalation"
        assert comp.calculation_errors[0]["error_type"] == "ValueError"
        assert "forced failure for test" in comp.calculation_errors[0]["message"]

        assert result.errors
        assert any("inhalation" in warning for warning in result.warnings)

        as_dict = result.to_dict()
        assert as_dict["warnings"]
        assert as_dict["errors"]
