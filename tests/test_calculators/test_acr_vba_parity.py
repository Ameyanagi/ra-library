"""Direct parity cases for CREATE-SIMPLE v3 CalculateACRMax."""

import pytest

from ra_library.calculators.acr import get_acrmax
from ra_library.models.substance import GHSClassification


@pytest.mark.parametrize(
    ("field", "category", "expected"),
    [
        ("acute_toxicity_oral", "1", "HL5"),
        ("acute_toxicity_inhalation_gas", "1", "HL5"),
        ("acute_toxicity_inhalation_vapor", "1", "HL5"),
        ("acute_toxicity_inhalation_dust", "1", "HL5"),
        ("germ_cell_mutagenicity", "1A", "HL5"),
        ("carcinogenicity", "1B", "HL5"),
        ("acute_toxicity_oral", "2", "HL4"),
        ("acute_toxicity_inhalation_gas", "2", "HL4"),
        ("skin_corrosion", "1A", "HL4"),
        ("respiratory_sensitization", "1B", "HL4"),
        ("germ_cell_mutagenicity", "2B", "HL4"),
        ("carcinogenicity", "2A", "HL4"),
        ("reproductive_toxicity", "1A", "HL4"),
        ("stot_repeated", "1", "HL4"),
        ("acute_toxicity_oral", "3", "HL3"),
        ("acute_toxicity_inhalation_vapor", "3", "HL3"),
        ("skin_corrosion", "1C", "HL3"),
        ("eye_damage", "1", "HL3"),
        ("skin_sensitization", "1A", "HL3"),
        ("reproductive_toxicity", "2", "HL3"),
        ("stot_single", "1", "HL3"),
        ("stot_repeated", "2", "HL3"),
        ("acute_toxicity_oral", "4", "HL2"),
        ("acute_toxicity_inhalation_dust", "4", "HL2"),
        ("skin_corrosion", "2", "HL2"),
        ("eye_damage", "2", "HL2"),
        ("stot_single", "3", "HL2"),
    ],
)
def test_each_vba_hazard_branch(field: str, category: str, expected: str) -> None:
    assert GHSClassification(**{field: category}).get_hazard_level() == expected


def test_oral_acute_toxicity_is_not_used_when_all_inhalation_routes_are_available() -> None:
    classification = GHSClassification(
        acute_toxicity_oral="1",
        acute_toxicity_inhalation_gas="NC",
        acute_toxicity_inhalation_vapor="NC",
        acute_toxicity_inhalation_dust="NC",
    )
    assert classification.get_hazard_level() == "HL1"


def test_any_unavailable_inhalation_route_enables_oral_fallback() -> None:
    classification = GHSClassification(
        acute_toxicity_oral="1",
        acute_toxicity_inhalation_gas="NC",
        acute_toxicity_inhalation_vapor="-9999",
        acute_toxicity_inhalation_dust="NC",
    )
    assert classification.get_hazard_level() == "HL5"


def test_acute_dermal_and_aspiration_do_not_enter_v3_acr_classification() -> None:
    classification = GHSClassification(
        acute_toxicity_dermal="1",
        aspiration_hazard="1",
    )
    assert classification.get_hazard_level() == "HL1"


@pytest.mark.parametrize(
    ("hazard_level", "liquid", "solid"),
    [
        ("HL5", 0.05, 0.001),
        ("HL4", 0.5, 0.01),
        ("HL3", 5.0, 0.1),
        ("HL2", 50.0, 1.0),
        ("HL1", 500.0, 10.0),
    ],
)
def test_vba_management_target_table(hazard_level: str, liquid: float, solid: float) -> None:
    assert get_acrmax(hazard_level, "liquid") == liquid
    assert get_acrmax(hazard_level, "gas") == liquid
    assert get_acrmax(hazard_level, "solid") == solid
