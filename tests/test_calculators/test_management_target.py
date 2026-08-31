"""CREATE-SIMPLE v3 workbook-parity tests for the no-OEL fallback."""

import pytest

from ra_library.calculators.inhalation import calculate_inhalation_risk
from ra_library.data.substance_db import get_database
from ra_library.models.assessment import AmountLevel, AssessmentInput, VentilationLevel
from ra_library.models.risk import RiskLevel
from ra_library.models.risk import InhalationRisk
from ra_library.models.substance import (
    GHSClassification,
    OccupationalExposureLimits,
    PropertyType,
    Substance,
)
from ra_library.services.calculate import calculate_risk


def _controlled_powder_input() -> AssessmentInput:
    return AssessmentInput(
        product_property=PropertyType.SOLID,
        amount_level=AmountLevel.SMALL,
        ventilation=VentilationLevel.LOCAL_ENCLOSED,
        control_velocity_verified=True,
        working_hours_per_day=4,
        frequency_type="weekly",
        frequency_value=5,
    )


def test_indium_oxide_without_oel_uses_hl5_management_target() -> None:
    """The workbook row has GHS 1B but no OEL and remains assessable."""
    substance = get_database().get_as_model("1312-43-2")
    assert substance is not None
    assert substance.oel.get_primary_oel() == (None, None)

    risk = calculate_inhalation_risk(_controlled_powder_input(), substance)

    assert risk.registered_oel is None
    assert risk.evaluation_standard_kind == "ghs_management_target"
    assert risk.evaluation_standard == pytest.approx(0.001)
    assert risk.evaluation_standard_source == "管理目標濃度（GHS HL5）"
    assert risk.exposure_8hr == pytest.approx(0.001)
    assert risk.rcr == pytest.approx(1.0)
    assert risk.risk_level == RiskLevel.II
    assert risk.stel_oel == pytest.approx(0.003)
    assert risk.stel_oel_source == "ACRmax ×3"


def test_non_carcinogen_without_oel_uses_full_ghs_hazard_level() -> None:
    """The fallback is an HL1-HL5 rule, not an indium/carcinogen exception."""
    substance = Substance(
        cas_number="test-hl4",
        name_ja="反復ばく露区分1物質",
        property_type=PropertyType.SOLID,
        ghs=GHSClassification(stot_repeated="1"),
        oel=OccupationalExposureLimits(),
    )

    risk = calculate_inhalation_risk(_controlled_powder_input(), substance)

    assert substance.get_hazard_level() == "HL4"
    assert risk.registered_oel is None
    assert risk.evaluation_standard_kind == "ghs_management_target"
    assert risk.evaluation_standard == pytest.approx(0.01)


def test_registered_oel_takes_precedence_over_management_target() -> None:
    """The workbook does not choose the lower of OEL and ACRmax."""
    substance = Substance(
        cas_number="test-oel-precedence",
        name_ja="OEL優先物質",
        property_type=PropertyType.SOLID,
        ghs=GHSClassification(carcinogenicity="1B"),
        oel=OccupationalExposureLimits(jsoh_8hr=1.0, jsoh_8hr_unit="mg/m³"),
    )

    risk = calculate_inhalation_risk(_controlled_powder_input(), substance)

    assert risk.acrmax == pytest.approx(0.001)
    assert risk.registered_oel == pytest.approx(1.0)
    assert risk.evaluation_standard == pytest.approx(1.0)
    assert risk.evaluation_standard_kind == "oel"
    assert risk.rcr == pytest.approx(0.001)


def test_selected_product_form_controls_management_target_table() -> None:
    """STEP 1 form wins over the database's neat-substance form."""
    substance = Substance(
        cas_number="test-form",
        name_ja="溶液として扱う固体物質",
        property_type=PropertyType.SOLID,
        ghs=GHSClassification(stot_single="2"),
        oel=OccupationalExposureLimits(),
    )
    assessment_input = _controlled_powder_input().model_copy(
        update={"product_property": PropertyType.LIQUID}
    )

    risk = calculate_inhalation_risk(assessment_input, substance)

    assert substance.get_hazard_level() == "HL2"
    assert risk.evaluation_standard == pytest.approx(50.0)
    assert risk.evaluation_standard_unit == "ppm"


def test_pre_041_inhalation_result_construction_remains_compatible() -> None:
    """The new provenance fields do not make existing constructors invalid."""
    risk = InhalationRisk(
        exposure_8hr=0.1,
        oel=1.0,
        oel_unit="ppm",
        oel_source="test OEL",
        rcr=0.1,
        risk_level=RiskLevel.I,
    )

    assert risk.registered_oel == 1.0
    assert risk.evaluation_standard == 1.0
    assert risk.evaluation_standard_unit == "ppm"
    assert risk.evaluation_standard_source == "test OEL"


@pytest.mark.parametrize("version", ["v3.0.2", "v3.1.2", "v3.2", "v3.2.1"])
def test_supported_v3_versions_expose_same_no_oel_fallback(version: str) -> None:
    """The audited v3 VBA functions are identical across supported package versions."""
    result = calculate_risk(
        substances=[{"cas_number": "1312-43-2", "content_percent": 100}],
        conditions={
            "property_type": "solid",
            "amount": "small",
            "ventilation": "local_enc",
            "control_velocity_verified": True,
        },
        duration={"hours": 4, "days_per_week": 5},
        assess_inhalation=True,
        assess_dermal=False,
        assess_physical=False,
        include_recommendations="never",
        methodology_version=version,
    )

    inhalation = result.data["components"]["1312-43-2"]["inhalation"]
    assert inhalation["registered_oel"] is None
    assert inhalation["evaluation_standard_kind"] == "ghs_management_target"
    assert inhalation["evaluation_standard"] == pytest.approx(0.001)
