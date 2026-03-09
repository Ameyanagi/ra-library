"""Test configuration and fixtures."""

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
    AssessmentMode,
    ComponentInput,
    AmountLevel,
    VentilationLevel,
    ExposureVariation,
)


@pytest.fixture
def toluene_substance() -> Substance:
    """Toluene test substance."""
    return Substance(
        cas_number="108-88-3",
        name_ja="トルエン",
        name_en="Toluene",
        property_type=PropertyType.LIQUID,
        ghs=GHSClassification(
            flammable_liquids="2",
            skin_corrosion="2",
            stot_single="3",
            stot_repeated="2",
            aspiration_hazard="1",
        ),
        oel=OccupationalExposureLimits(
            concentration_standard_8hr=20.0,
            concentration_standard_8hr_unit="ppm",
            jsoh_8hr=50.0,
            jsoh_8hr_unit="ppm",
            acgih_tlv_twa=20.0,
            acgih_tlv_twa_unit="ppm",
        ),
        properties=PhysicochemicalProperties(
            molecular_weight=92.14,
            boiling_point=110.6,
            vapor_pressure=2900,  # Pa at 20°C
            flash_point=4.0,
            log_kow=2.73,
        ),
    )


@pytest.fixture
def benzene_substance() -> Substance:
    """Benzene test substance (carcinogen 1A)."""
    return Substance(
        cas_number="71-43-2",
        name_ja="ベンゼン",
        name_en="Benzene",
        property_type=PropertyType.LIQUID,
        ghs=GHSClassification(
            carcinogenicity="1A",
            germ_cell_mutagenicity="1B",
            flammable_liquids="2",
        ),
        oel=OccupationalExposureLimits(
            concentration_standard_8hr=1.0,
            concentration_standard_8hr_unit="ppm",
        ),
        properties=PhysicochemicalProperties(
            molecular_weight=78.11,
            boiling_point=80.1,
            vapor_pressure=10000,  # Pa at 20°C
            flash_point=-11.0,
            log_kow=2.13,
        ),
        is_carcinogen=True,
    )


@pytest.fixture
def basic_assessment_input() -> AssessmentInput:
    """Basic assessment input for testing."""
    return AssessmentInput(
        mode=AssessmentMode.RA_SHEET,
        title="Test Assessment",
        assessor="Test User",
        workplace="Test Lab",
        work_description="Testing chemicals",
        assess_inhalation=True,
        assess_dermal=False,
        assess_physical=False,
        product_property=PropertyType.LIQUID,
        components=[
            ComponentInput(
                cas_number="108-88-3",
                name="Toluene",
                content_percent=100.0,
            )
        ],
        amount_level=AmountLevel.MEDIUM,
        is_spray_operation=False,
        ventilation=VentilationLevel.INDUSTRIAL,
        control_velocity_verified=False,
        working_hours_per_day=8.0,
        frequency_type="weekly",
        frequency_value=5,
        exposure_variation=ExposureVariation.CONSTANT,
    )
