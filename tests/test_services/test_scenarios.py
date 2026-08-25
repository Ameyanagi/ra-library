"""Verified control-scenario service tests."""

from ra_library import RiskAssessment
from ra_library.services import calculate_control_scenarios, calculate_risk


MIXTURE = [
    {"cas_number": "108-88-3", "content_percent": 50.0},
    {"cas_number": "67-56-1", "content_percent": 50.0},
]


def test_verified_scenarios_preserve_mixture_and_report_full_recalculation():
    result = calculate_risk(
        substances=MIXTURE,
        preset="lab_organic",
        assess_dermal=False,
        assess_physical=False,
        include_recommendations="verified",
        recommendation_scope={
            "rpe": ["half_mask"],
            "max_combination_size": 1,
            "max_scenarios": 5,
        },
        language="ja",
    )

    analysis = result.data["recommendation_analysis"]
    scenario = analysis["scenarios"][0]
    assert analysis["calculation_basis"] == "full_recalculation"
    assert scenario["calculation_status"] == "recalculated"
    assert scenario["baseline_fingerprint"].startswith("sha256:")
    assert scenario["changes"] == {"protection": {"rpe": "half_mask"}}
    assert [
        component["content_percent"] for component in scenario["result"]["components"].values()
    ] == [50.0, 50.0]
    assert set(scenario["covered_risk_types"]) >= {"inhalation_8h", "inhalation_stel"}


def test_explicit_batch_recalculates_only_requested_scenarios():
    result = calculate_control_scenarios(
        substances=MIXTURE,
        preset="lab_organic",
        assess_dermal=False,
        assess_physical=False,
        scenarios=[
            {
                "changes": {
                    "conditions": {"amount": "minute"},
                    "duration": {"hours": 1.0},
                }
            },
            {"changes": {"conditions": {"ventilation": "sealed"}}},
        ],
        language="ja",
    )

    assert result.data["coverage"]["generation_mode"] == "explicit"
    assert result.data["coverage"]["recalculated_scenario_count"] == 2
    assert result.data["coverage"]["truncated"] is False
    assert all(
        scenario["calculation_status"] == "recalculated"
        for scenario in result.data["scenarios"]
    )


def test_what_if_preserves_methodology_and_physical_conditions():
    baseline = (
        RiskAssessment()
        .with_methodology_version("v3.2")
        .add_substance("108-88-3", content=100.0)
        .with_assessments(inhalation=True, dermal=False, physical=True)
        .with_physical_conditions(
            process_temperature=40.0,
            has_ignition_sources=True,
            has_explosive_atmosphere=True,
            has_organic_matter=True,
            has_air_water_contact=True,
        )
        .calculate()
    )

    scenario = baseline.what_if(amount="small")
    assert scenario.assessment_input.methodology_version == "v3.2"
    assert scenario.assessment_input.process_temperature == 40.0
    assert scenario.assessment_input.has_organic_matter is True
    assert scenario.assessment_input.has_air_water_contact is True


def test_rpe_scenario_switches_to_implementation_report_mode():
    baseline = (
        RiskAssessment()
        .add_substance("108-88-3", content=100.0)
        .with_assessments(inhalation=True, dermal=False, physical=False)
        .calculate()
    )

    scenario = baseline.what_if(rpe="half_mask")
    assert scenario.assessment_input.mode.value == "report"
    assert scenario.assessment_input.rpe_type.value == "tight_fit_10"
    assert scenario.components["108-88-3"].inhalation.rcr <= baseline.components[
        "108-88-3"
    ].inhalation.rcr

