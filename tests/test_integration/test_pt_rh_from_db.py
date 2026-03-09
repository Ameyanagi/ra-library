"""
Integration tests for Platinum (Pt) and Rhodium (Rh) risk assessment using database.

This demonstrates the complete workflow:
1. Look up substance from database
2. Create substance model from database data
3. Run comprehensive risk assessment
"""

import pytest
from ra_library.data import lookup_substance, SubstanceData
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
from ra_library.calculators.acr import get_acrmax
from ra_library.models.risk import RiskLevel


def db_to_substance(data: SubstanceData) -> Substance:
    """Convert database SubstanceData to Substance model."""
    # Determine property type (gas not supported, treated as liquid)
    prop_map = {1: PropertyType.LIQUID, 2: PropertyType.SOLID, 3: PropertyType.LIQUID}
    prop_type = prop_map.get(data.property_type, PropertyType.SOLID)

    # Build GHS classification
    ghs = GHSClassification(
        explosives=data.ghs_explosives,
        flammable_gases=data.ghs_flam_gas,
        aerosols=data.ghs_aerosol,
        oxidizing_gases=data.ghs_ox_gas,
        gases_under_pressure=data.ghs_gases_pressure,
        flammable_liquids=data.ghs_flam_liq,
        flammable_solids=data.ghs_flam_sol,
        self_reactive=data.ghs_self_react,
        pyrophoric_liquids=data.ghs_pyr_liq,
        pyrophoric_solids=data.ghs_pyr_sol,
        self_heating=data.ghs_self_heat,
        water_reactive=data.ghs_water_react,
        oxidizing_liquids=data.ghs_ox_liq,
        oxidizing_solids=data.ghs_ox_sol,
        organic_peroxides=data.ghs_org_perox,
        corrosive_to_metals=data.ghs_met_corr,
        acute_toxicity_oral=data.ghs_acute_oral,
        acute_toxicity_dermal=data.ghs_acute_dermal,
        acute_toxicity_inhalation_gas=data.ghs_acute_inhal_gas,
        acute_toxicity_inhalation_vapor=data.ghs_acute_inhal_vapor,
        acute_toxicity_inhalation_dust=data.ghs_acute_inhal_dust,
        skin_corrosion_irritation=data.ghs_skin_corr,
        serious_eye_damage=data.ghs_eye_damage,
        respiratory_sensitization=data.ghs_resp_sens,
        skin_sensitization=data.ghs_skin_sens,
        germ_cell_mutagenicity=data.ghs_mutagenicity,
        carcinogenicity=data.ghs_carcinogenicity,
        reproductive_toxicity=data.ghs_reproductive,
        stot_single=data.ghs_stot_se,
        stot_repeated=data.ghs_stot_re,
        aspiration_hazard=data.ghs_aspiration,
    )

    # Build OEL
    # Use mg/m³ values for solids, ppm for liquids
    if prop_type == PropertyType.SOLID:
        oel = OccupationalExposureLimits(
            concentration_standard_8hr=data.conc_standard_8hr_mgm3,
            concentration_standard_8hr_unit="mg/m³",
            concentration_standard_stel=data.conc_standard_stel_mgm3,
            concentration_standard_stel_unit="mg/m³",
            jsoh_8hr=data.jsoh_8hr_mgm3,
            jsoh_8hr_unit="mg/m³",
            jsoh_ceiling=data.jsoh_ceiling_mgm3,
            acgih_tlv_twa=data.acgih_tlv_twa_mgm3,
            acgih_tlv_twa_unit="mg/m³",
            acgih_tlv_stel=data.acgih_tlv_stel_mgm3,
            acgih_tlv_stel_unit="mg/m³",
            acgih_tlv_c=data.acgih_tlv_c_mgm3,
        )
    else:
        oel = OccupationalExposureLimits(
            concentration_standard_8hr=data.conc_standard_8hr_ppm,
            concentration_standard_8hr_unit="ppm",
            concentration_standard_stel=data.conc_standard_stel_ppm,
            concentration_standard_stel_unit="ppm",
            jsoh_8hr=data.jsoh_8hr_ppm,
            jsoh_8hr_unit="ppm",
            jsoh_ceiling=data.jsoh_ceiling_ppm,
            acgih_tlv_twa=data.acgih_tlv_twa_ppm,
            acgih_tlv_twa_unit="ppm",
            acgih_tlv_stel=data.acgih_tlv_stel_ppm,
            acgih_tlv_stel_unit="ppm",
            acgih_tlv_c=data.acgih_tlv_c_ppm,
        )

    # Build physical properties
    properties = PhysicochemicalProperties(
        molecular_weight=data.molecular_weight,
        boiling_point=data.boiling_point,
        log_kow=data.log_kow,
        flash_point=data.flash_point,
        vapor_pressure=data.vapor_pressure,
    )

    return Substance(
        cas_number=data.cas_number,
        name_ja=data.name_ja,
        name_en=data.name_en,
        property_type=prop_type,
        ghs=ghs,
        oel=oel,
        properties=properties,
        is_carcinogen=data.is_carcinogen or data.ghs_carcinogenicity is not None,
    )


class TestPlatinumFromDatabase:
    """Integration tests for Platinum using database lookup."""

    @pytest.fixture
    def platinum_data(self):
        """Load Platinum from database."""
        data = lookup_substance("7440-06-4")
        if data is None:
            pytest.skip("Platinum not found in database")
        return data

    @pytest.fixture
    def platinum(self, platinum_data):
        """Convert database data to Substance model."""
        return db_to_substance(platinum_data)

    def test_platinum_loaded_from_db(self, platinum_data):
        """Platinum is loaded from database correctly."""
        assert platinum_data.cas_number == "7440-06-4"
        assert platinum_data.property_type == 2  # Solid

    def test_platinum_has_oel(self, platinum_data):
        """Platinum has OEL values from database."""
        # Check for any OEL value
        has_oel = (
            platinum_data.acgih_tlv_twa_mgm3 is not None or
            platinum_data.jsoh_8hr_mgm3 is not None or
            platinum_data.conc_standard_8hr_mgm3 is not None
        )
        assert has_oel, "Platinum should have OEL values"

    def test_platinum_risk_assessment_high_exposure(self, platinum):
        """Platinum: High exposure scenario."""
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
            substance=platinum,
            content_percent=100.0,
        )

        assert risk is not None
        # High exposure should result in high risk
        assert risk.risk_level in [RiskLevel.III, RiskLevel.IV]

    def test_platinum_risk_assessment_controlled(self, platinum):
        """Platinum: Controlled exposure scenario."""
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
            substance=platinum,
            content_percent=100.0,
        )

        assert risk is not None
        # Controlled exposure should result in lower risk
        assert risk.risk_level in [RiskLevel.I, RiskLevel.II, RiskLevel.III]


class TestRhodiumFromDatabase:
    """Integration tests for Rhodium using database lookup."""

    @pytest.fixture
    def rhodium_data(self):
        """Load Rhodium from database."""
        data = lookup_substance("7440-16-6")
        if data is None:
            pytest.skip("Rhodium not found in database")
        return data

    @pytest.fixture
    def rhodium(self, rhodium_data):
        """Convert database data to Substance model."""
        return db_to_substance(rhodium_data)

    def test_rhodium_loaded_from_db(self, rhodium_data):
        """Rhodium is loaded from database correctly."""
        assert rhodium_data.cas_number == "7440-16-6"
        assert rhodium_data.property_type == 2  # Solid

    def test_rhodium_risk_assessment_high_exposure(self, rhodium):
        """Rhodium: High exposure scenario."""
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
            substance=rhodium,
            content_percent=100.0,
        )

        assert risk is not None
        # High exposure should result in high risk
        assert risk.risk_level in [RiskLevel.III, RiskLevel.IV]

    def test_rhodium_risk_assessment_controlled(self, rhodium):
        """Rhodium: Controlled exposure scenario."""
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
            substance=rhodium,
            content_percent=100.0,
        )

        assert risk is not None
        # Controlled exposure should result in lower risk
        assert risk.risk_level in [RiskLevel.I, RiskLevel.II, RiskLevel.III]


class TestComparisonPtRhFromDB:
    """Compare Platinum and Rhodium assessments from database."""

    def test_both_substances_exist(self):
        """Both Platinum and Rhodium exist in database."""
        pt = lookup_substance("7440-06-4")
        rh = lookup_substance("7440-16-6")

        assert pt is not None, "Platinum not found in database"
        assert rh is not None, "Rhodium not found in database"

    def test_both_are_solids(self):
        """Both Platinum and Rhodium are solids."""
        pt = lookup_substance("7440-06-4")
        rh = lookup_substance("7440-16-6")

        assert pt.property_type == 2, "Platinum should be solid"
        assert rh.property_type == 2, "Rhodium should be solid"

    def test_same_conditions_comparison(self):
        """Compare Pt and Rh under identical conditions."""
        pt_data = lookup_substance("7440-06-4")
        rh_data = lookup_substance("7440-16-6")

        if pt_data is None or rh_data is None:
            pytest.skip("Pt or Rh not found in database")

        pt = db_to_substance(pt_data)
        rh = db_to_substance(rh_data)

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
            substance=pt,
            content_percent=100.0,
        )

        rh_risk = calculate_inhalation_risk(
            assessment_input=assessment_input,
            substance=rh,
            content_percent=100.0,
        )

        assert pt_risk is not None
        assert rh_risk is not None

        # Both should produce valid results
        print(f"\n=== Platinum (7440-06-4) ===")
        print(f"OEL: {pt_risk.oel}")
        print(f"Exposure (8hr): {pt_risk.exposure_8hr}")
        print(f"RCR: {pt_risk.rcr}")
        print(f"Risk Level: {pt_risk.risk_level}")

        print(f"\n=== Rhodium (7440-16-6) ===")
        print(f"OEL: {rh_risk.oel}")
        print(f"Exposure (8hr): {rh_risk.exposure_8hr}")
        print(f"RCR: {rh_risk.rcr}")
        print(f"Risk Level: {rh_risk.risk_level}")
