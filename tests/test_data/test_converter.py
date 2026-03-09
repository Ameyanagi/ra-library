"""
Tests for substance model converter.

Converts SubstanceData (database format) to Substance (model format)
for use in risk assessment calculations.
"""

import pytest
from ra_library.data.converter import (
    to_substance_model,
    to_ghs_classification,
    to_oel_limits,
    to_physical_properties,
)
from ra_library.data import SubstanceData, lookup_substance
from ra_library.models.substance import (
    Substance,
    PropertyType,
    GHSClassification,
    OccupationalExposureLimits,
    PhysicochemicalProperties,
)


class TestToGHSClassification:
    """Tests for GHS classification conversion."""

    def test_basic_ghs_conversion(self):
        """Basic GHS data is converted correctly."""
        data = SubstanceData(
            cas_number="test-001",
            name_ja="テスト物質",
            name_en="Test Substance",
            ghs_flam_liq="2",
            ghs_acute_oral="3",
            ghs_carcinogenicity="1A",
        )
        ghs = to_ghs_classification(data)

        assert ghs.flammable_liquids == "2"
        assert ghs.acute_toxicity_oral == "3"
        assert ghs.carcinogenicity == "1A"

    def test_all_ghs_fields(self):
        """All GHS fields are mapped correctly."""
        data = SubstanceData(
            cas_number="test-002",
            name_ja="全GHS物質",
            name_en="All GHS Substance",
            ghs_explosives="1.1",
            ghs_flam_gas="1",
            ghs_aerosol="1",
            ghs_ox_gas="1",
            ghs_gases_pressure="Compressed",
            ghs_flam_liq="1",
            ghs_flam_sol="1",
            ghs_self_react="A",
            ghs_pyr_liq="1",
            ghs_pyr_sol="1",
            ghs_self_heat="1",
            ghs_water_react="1",
            ghs_ox_liq="1",
            ghs_ox_sol="1",
            ghs_org_perox="A",
            ghs_met_corr="1",
            ghs_acute_oral="1",
            ghs_acute_dermal="1",
            ghs_acute_inhal_gas="1",
            ghs_acute_inhal_vapor="1",
            ghs_acute_inhal_dust="1",
            ghs_skin_corr="1A",
            ghs_eye_damage="1",
            ghs_resp_sens="1",
            ghs_skin_sens="1",
            ghs_mutagenicity="1A",
            ghs_carcinogenicity="1A",
            ghs_reproductive="1A",
            ghs_stot_se="1",
            ghs_stot_re="1",
            ghs_aspiration="1",
        )
        ghs = to_ghs_classification(data)

        assert ghs.explosives == "1.1"
        assert ghs.flammable_gases == "1"
        assert ghs.flammable_aerosols == "1"
        assert ghs.oxidizing_gases == "1"
        assert ghs.gases_under_pressure == "Compressed"
        assert ghs.flammable_liquids == "1"
        assert ghs.flammable_solids == "1"
        assert ghs.self_reactive == "A"
        assert ghs.pyrophoric_liquids == "1"
        assert ghs.pyrophoric_solids == "1"
        assert ghs.self_heating == "1"
        assert ghs.water_reactive == "1"
        assert ghs.oxidizing_liquids == "1"
        assert ghs.oxidizing_solids == "1"
        assert ghs.organic_peroxides == "A"
        assert ghs.corrosive_to_metals == "1"
        assert ghs.acute_toxicity_oral == "1"
        assert ghs.acute_toxicity_dermal == "1"
        assert ghs.acute_toxicity_inhalation_gas == "1"
        assert ghs.acute_toxicity_inhalation_vapor == "1"
        assert ghs.acute_toxicity_inhalation_dust == "1"
        assert ghs.skin_corrosion == "1A"
        assert ghs.eye_damage == "1"
        assert ghs.respiratory_sensitization == "1"
        assert ghs.skin_sensitization == "1"
        assert ghs.germ_cell_mutagenicity == "1A"
        assert ghs.carcinogenicity == "1A"
        assert ghs.reproductive_toxicity == "1A"
        assert ghs.stot_single == "1"
        assert ghs.stot_repeated == "1"
        assert ghs.aspiration_hazard == "1"

    def test_empty_ghs(self):
        """Empty GHS data creates empty classification."""
        data = SubstanceData(
            cas_number="test-003",
            name_ja="無害物質",
            name_en="Harmless",
        )
        ghs = to_ghs_classification(data)

        assert ghs.flammable_liquids is None
        assert ghs.carcinogenicity is None


class TestToOELLimits:
    """Tests for OEL limits conversion."""

    def test_solid_uses_mgm3(self):
        """Solid substances use mg/m³ units."""
        data = SubstanceData(
            cas_number="test-010",
            name_ja="固体",
            name_en="Solid",
            property_type=2,  # Solid
            acgih_tlv_twa_mgm3=1.0,
            acgih_tlv_stel_mgm3=3.0,
            jsoh_8hr_mgm3=0.5,
        )
        oel = to_oel_limits(data, PropertyType.SOLID)

        assert oel.acgih_tlv_twa == 1.0
        assert oel.acgih_tlv_twa_unit == "mg/m³"
        assert oel.acgih_tlv_stel == 3.0
        assert oel.acgih_tlv_stel_unit == "mg/m³"
        assert oel.jsoh_8hr == 0.5
        assert oel.jsoh_8hr_unit == "mg/m³"

    def test_liquid_uses_ppm(self):
        """Liquid substances use ppm units."""
        data = SubstanceData(
            cas_number="test-011",
            name_ja="液体",
            name_en="Liquid",
            property_type=1,  # Liquid
            acgih_tlv_twa_ppm=50.0,
            acgih_tlv_stel_ppm=100.0,
            jsoh_8hr_ppm=20.0,
        )
        oel = to_oel_limits(data, PropertyType.LIQUID)

        assert oel.acgih_tlv_twa == 50.0
        assert oel.acgih_tlv_twa_unit == "ppm"
        assert oel.acgih_tlv_stel == 100.0
        assert oel.acgih_tlv_stel_unit == "ppm"
        assert oel.jsoh_8hr == 20.0
        assert oel.jsoh_8hr_unit == "ppm"

    def test_all_oel_fields(self):
        """All OEL fields are mapped correctly."""
        data = SubstanceData(
            cas_number="test-012",
            name_ja="全OEL物質",
            name_en="All OEL",
            property_type=1,
            conc_standard_8hr_ppm=10.0,
            conc_standard_stel_ppm=20.0,
            jsoh_8hr_ppm=5.0,
            jsoh_ceiling_ppm=15.0,
            acgih_tlv_twa_ppm=10.0,
            acgih_tlv_stel_ppm=25.0,
            acgih_tlv_c_ppm=50.0,
        )
        oel = to_oel_limits(data, PropertyType.LIQUID)

        assert oel.concentration_standard_8hr == 10.0
        assert oel.concentration_standard_stel == 20.0
        assert oel.jsoh_8hr == 5.0
        # jsoh_ceiling and acgih_tlv_c are stored in other_stel
        assert oel.other_stel == 15.0  # First available ceiling value
        assert oel.acgih_tlv_twa == 10.0
        assert oel.acgih_tlv_stel == 25.0


class TestToPhysicalProperties:
    """Tests for physical properties conversion."""

    def test_basic_properties(self):
        """Basic physical properties are converted correctly."""
        data = SubstanceData(
            cas_number="test-020",
            name_ja="物質",
            name_en="Substance",
            molecular_weight=100.5,
            boiling_point=150.0,
            flash_point=50.0,
            vapor_pressure=10.0,
            log_kow=2.5,
        )
        props = to_physical_properties(data)

        assert props.molecular_weight == 100.5
        assert props.boiling_point == 150.0
        assert props.flash_point == 50.0
        assert props.vapor_pressure == 10.0
        assert props.log_kow == 2.5

    def test_empty_properties(self):
        """Empty properties creates object with None values."""
        data = SubstanceData(
            cas_number="test-021",
            name_ja="物質",
            name_en="Substance",
        )
        props = to_physical_properties(data)

        assert props.molecular_weight is None
        assert props.boiling_point is None


class TestToSubstanceModel:
    """Tests for full substance model conversion."""

    def test_solid_conversion(self):
        """Solid substance is converted correctly."""
        data = SubstanceData(
            cas_number="7440-06-4",
            name_ja="白金",
            name_en="Platinum",
            property_type=2,  # Solid
            molecular_weight=195.08,
            acgih_tlv_twa_mgm3=1.0,
        )
        substance = to_substance_model(data)

        assert substance.cas_number == "7440-06-4"
        assert substance.name_ja == "白金"
        assert substance.name_en == "Platinum"
        assert substance.property_type == PropertyType.SOLID
        assert substance.oel.acgih_tlv_twa == 1.0
        assert substance.oel.acgih_tlv_twa_unit == "mg/m³"
        assert substance.properties.molecular_weight == 195.08

    def test_liquid_conversion(self):
        """Liquid substance is converted correctly."""
        data = SubstanceData(
            cas_number="108-88-3",
            name_ja="トルエン",
            name_en="Toluene",
            property_type=1,  # Liquid
            molecular_weight=92.14,
            boiling_point=111.0,
            acgih_tlv_twa_ppm=20.0,
        )
        substance = to_substance_model(data)

        assert substance.cas_number == "108-88-3"
        assert substance.property_type == PropertyType.LIQUID
        assert substance.oel.acgih_tlv_twa == 20.0
        assert substance.oel.acgih_tlv_twa_unit == "ppm"

    def test_gas_converts_to_liquid(self):
        """Gas (property_type=3) converts to LIQUID type."""
        data = SubstanceData(
            cas_number="50-00-0",
            name_ja="ホルムアルデヒド",
            name_en="Formaldehyde",
            property_type=3,  # Gas
            acgih_tlv_twa_ppm=0.1,
        )
        substance = to_substance_model(data)

        # Gas is treated as liquid for model purposes
        assert substance.property_type == PropertyType.LIQUID
        assert substance.oel.acgih_tlv_twa == 0.1
        assert substance.oel.acgih_tlv_twa_unit == "ppm"

    def test_carcinogen_flag(self):
        """Carcinogen flag is set from GHS or explicit flag."""
        data1 = SubstanceData(
            cas_number="test-030",
            name_ja="発がん物質",
            name_en="Carcinogen",
            ghs_carcinogenicity="1A",
        )
        substance1 = to_substance_model(data1)
        assert substance1.is_carcinogen is True

        data2 = SubstanceData(
            cas_number="test-031",
            name_ja="発がん物質2",
            name_en="Carcinogen 2",
            is_carcinogen=True,
        )
        substance2 = to_substance_model(data2)
        assert substance2.is_carcinogen is True

    def test_unknown_property_type_defaults_to_solid(self):
        """Unknown property type defaults to SOLID."""
        data = SubstanceData(
            cas_number="test-040",
            name_ja="不明物質",
            name_en="Unknown",
            property_type=None,
        )
        substance = to_substance_model(data)
        assert substance.property_type == PropertyType.SOLID


class TestRealSubstanceConversion:
    """Test conversion with real database substances."""

    def test_platinum_from_db(self):
        """Convert Platinum from database."""
        data = lookup_substance("7440-06-4")
        if data is None:
            pytest.skip("Platinum not found in database")

        substance = to_substance_model(data)

        assert substance.cas_number == "7440-06-4"
        assert substance.property_type == PropertyType.SOLID
        # Should have OEL in mg/m³
        assert substance.oel.acgih_tlv_twa_unit == "mg/m³" or substance.oel.jsoh_8hr_unit == "mg/m³"

    def test_rhodium_from_db(self):
        """Convert Rhodium from database."""
        data = lookup_substance("7440-16-6")
        if data is None:
            pytest.skip("Rhodium not found in database")

        substance = to_substance_model(data)

        assert substance.cas_number == "7440-16-6"
        assert substance.property_type == PropertyType.SOLID

    def test_formaldehyde_from_db(self):
        """Convert Formaldehyde from database."""
        data = lookup_substance("50-00-0")
        if data is None:
            pytest.skip("Formaldehyde not found in database")

        substance = to_substance_model(data)

        assert substance.cas_number == "50-00-0"
        assert substance.is_carcinogen is True
        # Should have ppm OEL
        assert substance.oel.jsoh_8hr == 0.1
        assert substance.oel.jsoh_8hr_unit == "ppm"
