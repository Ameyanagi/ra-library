"""
Demonstration of enhanced database features with Platinum and Rhodium.

This test demonstrates the complete workflow:
1. Look up substance from database
2. Get hazard level, volatility, and regulations
3. Convert to Substance model
4. Run comprehensive risk assessment
"""

import pytest
from ra_library.data import (
    get_database,
    lookup_substance,
    to_substance_model,
    get_hazard_level,
    get_volatility_for_assessment,
    get_applicable_regulations,
    get_regulatory_summary,
)
from ra_library.models.substance import PropertyType
from ra_library.models.assessment import (
    AssessmentInput,
    AmountLevel,
    VentilationLevel,
    ExposureVariation,
)
from ra_library.calculators.inhalation import calculate_inhalation_risk


class TestEnhancedDatabaseWorkflow:
    """Demonstrate the enhanced database workflow."""

    def test_platinum_complete_workflow(self):
        """Complete workflow for Platinum using enhanced database."""
        # Step 1: Get database instance
        db = get_database()

        # Step 2: Look up Platinum (CAS 7440-06-4)
        pt_data = db.lookup("7440-06-4")
        assert pt_data is not None, "Platinum not found in database"

        print("\n=== PLATINUM (Pt) COMPLETE ANALYSIS ===")
        print(f"CAS Number: {pt_data.cas_number}")
        print(f"Japanese Name: {pt_data.name_ja}")
        print(f"English Name: {pt_data.name_en}")
        print(f"Property Type: {pt_data.property_type} (2=solid)")

        # Step 3: Get hazard level using enhanced method
        hazard_level = db.get_hazard_level("7440-06-4")
        print(f"\nHazard Level: {hazard_level}")

        # Step 4: Get volatility (for solids, this returns None)
        volatility = db.get_volatility("7440-06-4")
        print(f"Volatility: {volatility or 'N/A (solid)'}")

        # Step 5: Check regulations
        regulations = db.check_regulations("7440-06-4", content_pct=100.0)
        print(f"\nRegulations:")
        print(f"  - Tokka: {regulations['tokka']}")
        print(f"  - Organic Solvent: {regulations['organic_solvent']}")
        print(f"  - Skin Hazard: {regulations['skin_hazard']}")
        print(f"  - Carcinogen: {regulations['carcinogen']}")

        # Step 6: Convert to Substance model
        pt_model = db.get_as_model("7440-06-4")
        assert pt_model is not None
        assert pt_model.property_type == PropertyType.SOLID
        print(f"\nSubstance Model Created: {pt_model.property_type}")

        # Step 7: OEL values
        print(f"\nOEL Values:")
        print(f"  - ACGIH TLV-TWA: {pt_model.oel.acgih_tlv_twa} {pt_model.oel.acgih_tlv_twa_unit}")
        print(f"  - JSOH 8hr: {pt_model.oel.jsoh_8hr} {pt_model.oel.jsoh_8hr_unit}")

        # Step 8: Run risk assessment
        assessment_input = AssessmentInput(
            product_property=PropertyType.SOLID,
            amount_level=AmountLevel.MEDIUM,
            ventilation=VentilationLevel.LOCAL_EXTERNAL,
            working_hours_per_day=6.0,
            frequency_type="weekly",
            frequency_value=4,
            exposure_variation=ExposureVariation.CONSTANT,
        )

        risk = calculate_inhalation_risk(
            assessment_input=assessment_input,
            substance=pt_model,
            content_percent=100.0,
        )

        print(f"\nRisk Assessment Results:")
        print(f"  - Selected OEL: {risk.oel}")
        print(f"  - Exposure (8hr): {risk.exposure_8hr:.4f}")
        print(f"  - RCR: {risk.rcr:.2f}")
        print(f"  - Risk Level: {risk.risk_level}")

    def test_rhodium_complete_workflow(self):
        """Complete workflow for Rhodium using enhanced database."""
        db = get_database()

        # Look up Rhodium
        rh_data = db.lookup("7440-16-6")
        assert rh_data is not None, "Rhodium not found in database"

        print("\n=== RHODIUM (Rh) COMPLETE ANALYSIS ===")
        print(f"CAS Number: {rh_data.cas_number}")
        print(f"Japanese Name: {rh_data.name_ja}")
        print(f"English Name: {rh_data.name_en}")

        # Get all info using enhanced methods
        hazard_level = db.get_hazard_level("7440-16-6")
        regulations = db.check_regulations("7440-16-6")
        rh_model = db.get_as_model("7440-16-6")

        print(f"\nHazard Level: {hazard_level}")
        print(f"Property Type: {rh_model.property_type}")
        print(f"\nOEL Values:")
        print(f"  - ACGIH TLV-TWA: {rh_model.oel.acgih_tlv_twa} {rh_model.oel.acgih_tlv_twa_unit}")

        # Run risk assessment
        assessment_input = AssessmentInput(
            product_property=PropertyType.SOLID,
            amount_level=AmountLevel.MEDIUM,
            ventilation=VentilationLevel.LOCAL_EXTERNAL,
            working_hours_per_day=6.0,
            frequency_type="weekly",
            frequency_value=4,
            exposure_variation=ExposureVariation.CONSTANT,
        )

        risk = calculate_inhalation_risk(
            assessment_input=assessment_input,
            substance=rh_model,
            content_percent=100.0,
        )

        print(f"\nRisk Assessment Results:")
        print(f"  - Selected OEL: {risk.oel}")
        print(f"  - Exposure (8hr): {risk.exposure_8hr:.4f}")
        print(f"  - RCR: {risk.rcr:.2f}")
        print(f"  - Risk Level: {risk.risk_level}")

    def test_formaldehyde_workflow(self):
        """Complete workflow for Formaldehyde (liquid/gas)."""
        db = get_database()

        # Look up Formaldehyde
        fa_data = db.lookup("50-00-0")
        assert fa_data is not None, "Formaldehyde not found in database"

        print("\n=== FORMALDEHYDE (HCHO) COMPLETE ANALYSIS ===")
        print(f"CAS Number: {fa_data.cas_number}")
        print(f"Japanese Name: {fa_data.name_ja}")

        # Get hazard info
        hazard_level = db.get_hazard_level("50-00-0")
        volatility = db.get_volatility("50-00-0")

        print(f"\nHazard Level: {hazard_level}")
        print(f"Volatility: {volatility}")
        print(f"Is Carcinogen: {fa_data.is_carcinogen or fa_data.ghs_carcinogenicity is not None}")

        # Get regulatory summary
        summary = get_regulatory_summary(fa_data, 100.0)
        print(f"\nApplicable Regulations: {', '.join(summary) if summary else 'None'}")

        # Get model and run assessment
        fa_model = db.get_as_model("50-00-0")

        print(f"\nOEL Values:")
        print(f"  - JSOH 8hr: {fa_model.oel.jsoh_8hr} {fa_model.oel.jsoh_8hr_unit}")

        # Use LIQUID for gas/vapor
        assessment_input = AssessmentInput(
            product_property=PropertyType.LIQUID,
            amount_level=AmountLevel.SMALL,
            ventilation=VentilationLevel.LOCAL_EXTERNAL,
            control_velocity_verified=True,
            working_hours_per_day=4.0,
            frequency_type="weekly",
            frequency_value=3,
            exposure_variation=ExposureVariation.INTERMITTENT,
        )

        risk = calculate_inhalation_risk(
            assessment_input=assessment_input,
            substance=fa_model,
            content_percent=37.0,  # Typical formalin concentration
        )

        print(f"\nRisk Assessment (37% solution):")
        print(f"  - Selected OEL: {risk.oel}")
        print(f"  - Exposure (8hr): {risk.exposure_8hr:.4f}")
        print(f"  - RCR: {risk.rcr:.2f}")
        print(f"  - Risk Level: {risk.risk_level}")

    def test_database_statistics(self):
        """Show database statistics."""
        db = get_database()

        print("\n=== DATABASE STATISTICS ===")
        print(f"Total substances: {db.substance_count}")

        # Count substances by type
        all_cas = db.get_all_cas_numbers()
        liquids = 0
        solids = 0
        gases = 0
        unknown = 0

        for cas in all_cas:
            data = db.lookup(cas)
            if data.property_type == 1:
                liquids += 1
            elif data.property_type == 2:
                solids += 1
            elif data.property_type == 3:
                gases += 1
            else:
                unknown += 1

        print(f"Liquids: {liquids}")
        print(f"Solids: {solids}")
        print(f"Gases: {gases}")
        print(f"Unknown: {unknown}")
