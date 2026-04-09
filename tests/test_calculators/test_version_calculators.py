"""Tests for version-specific regulatory logic."""

from ra_library.calculators.version_calculators import VersionCalculator, VersionConfig


def _ghs_skin_hazard() -> dict[str, str]:
    return {
        "skin_corr_irrit": "1",
        "eye_damage": "1",
        "resp_sens": "1",
        "skin_sens": "1",
    }


def test_v312_blocks_ghs_skin_detection_when_raw_flag_is_zero():
    """v3.1.2 should not infer skin hazard when the raw workbook flag is 0."""
    calc = VersionCalculator(VersionConfig.v3_1_2())

    result = calc.check_regulatory(
        substance_flags={
            "skin_hazard_flag_code": "0",
            "is_skin_hazard": False,
        },
        ghs_classification=_ghs_skin_hazard(),
        content_percent=100.0,
    )

    assert result.skin_hazard is False
    assert result.skin_hazard_from_ghs is True


def test_v32_blocks_ghs_skin_detection_when_raw_flag_is_two():
    """v3.2 raw code 2 should suppress GHS-based skin hazard labeling."""
    calc = VersionCalculator(VersionConfig.v3_2())

    result = calc.check_regulatory(
        substance_flags={
            "skin_hazard_flag_code": "2",
            "is_skin_hazard": False,
        },
        ghs_classification=_ghs_skin_hazard(),
        content_percent=100.0,
    )

    assert result.skin_hazard is False
    assert result.skin_hazard_from_ghs is True


def test_v32_keeps_explicit_skin_hazard_designation():
    """An explicit workbook skin-hazard flag should still mark the substance."""
    calc = VersionCalculator(VersionConfig.v3_2())

    result = calc.check_regulatory(
        substance_flags={
            "skin_hazard_flag_code": "1",
            "is_skin_hazard": True,
        },
        ghs_classification={},
        content_percent=100.0,
    )

    assert result.skin_hazard is True
