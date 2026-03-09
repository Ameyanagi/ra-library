"""
RPE (Respiratory Protective Equipment) coefficient calculation.

Reference: CREATE-SIMPLE VBA modRAReport.bas lines 775-782

IMPORTANT: RPE is ONLY available in Report mode (実施レポート).
RA Sheet mode does NOT support RPE (apfCoeff = 1 always).
"""

from typing import Optional

from ..models.assessment import RPEType, AssessmentMode, RPE_APF_VALUES


def calculate_apf_coefficient(
    rpe_type: Optional[RPEType],
    fit_tested: bool = False,
    fit_test_multiplier: Optional[float] = None,
) -> float:
    """
    Calculate APF (Assigned Protection Factor) coefficient.

    Reference: CREATE-SIMPLE VBA modRAReport.bas lines 775-782

    The coefficient is 1/APF for the selected RPE type.
    For loose-fit types (APF 11, 20, 25), no fit test is required.
    For tight-fit types, a fit test multiplier may be applied.

    Args:
        rpe_type: Type of respiratory protection
        fit_tested: Whether fit test was performed
        fit_test_multiplier: Multiplier from fit test (0.1-1.0)

    Returns:
        APF coefficient (0 < coeff ≤ 1)
    """
    if rpe_type is None or rpe_type == RPEType.NONE:
        return 1.0

    apf = RPE_APF_VALUES.get(rpe_type, 1)

    # Loose-fit types (11, 20, 25) don't need fit test
    if rpe_type in [RPEType.LOOSE_FIT_11, RPEType.LOOSE_FIT_20, RPEType.LOOSE_FIT_25]:
        return 1.0 / apf

    # Tight-fit types - apply fit test multiplier if provided
    if fit_tested and fit_test_multiplier is not None:
        # VBA: apfCoeff = 1 / QRPECoeff_1 * QRPECoeff_2
        return (1.0 / apf) * fit_test_multiplier
    else:
        return 1.0 / apf


def calculate_apf_coefficient_for_mode(
    mode: str,
    rpe_type: Optional[RPEType],
    fit_tested: bool = False,
    fit_test_multiplier: Optional[float] = None,
) -> float:
    """
    Calculate APF coefficient.

    Note: The mode parameter is kept for backwards compatibility but is now ignored.
    RPE is always applied when specified, regardless of mode.

    Reference:
    - modRAReport.bas lines 775-782: Full RPE support

    Args:
        mode: Assessment mode (ignored, kept for compatibility)
        rpe_type: Type of respiratory protection
        fit_tested: Whether fit test was performed
        fit_test_multiplier: Multiplier from fit test

    Returns:
        APF coefficient
    """
    # Always apply RPE if specified (mode is ignored)
    return calculate_apf_coefficient(rpe_type, fit_tested, fit_test_multiplier)


def get_rpe_description(rpe_type: Optional[RPEType]) -> tuple[str, str]:
    """
    Get RPE type description in English and Japanese.

    Args:
        rpe_type: RPE type

    Returns:
        Tuple of (english, japanese) descriptions
    """
    descriptions = {
        None: ("None", "なし"),
        RPEType.NONE: ("None", "なし"),
        RPEType.LOOSE_FIT_11: ("Loose-fit APF 11", "ルーズフィット型 APF 11"),
        RPEType.LOOSE_FIT_20: ("Loose-fit APF 20", "ルーズフィット型 APF 20"),
        RPEType.LOOSE_FIT_25: ("Loose-fit APF 25", "ルーズフィット型 APF 25"),
        RPEType.TIGHT_FIT_10: ("Tight-fit APF 10", "タイトフィット型 APF 10"),
        RPEType.TIGHT_FIT_50: ("Tight-fit APF 50", "タイトフィット型 APF 50"),
        RPEType.TIGHT_FIT_100: ("Tight-fit APF 100", "タイトフィット型 APF 100"),
        RPEType.TIGHT_FIT_1000: ("Tight-fit APF 1000", "タイトフィット型 APF 1000"),
        RPEType.TIGHT_FIT_10000: ("Tight-fit APF 10000", "タイトフィット型 APF 10000"),
    }
    return descriptions.get(rpe_type, ("Unknown", "不明"))


def is_fit_test_required(rpe_type: Optional[RPEType]) -> bool:
    """
    Check if fit test is required for the RPE type.

    Loose-fit types (APF 11, 20, 25) do not require fit testing.
    All tight-fit types require fit testing.

    Args:
        rpe_type: RPE type

    Returns:
        True if fit test is required
    """
    if rpe_type is None or rpe_type == RPEType.NONE:
        return False

    # Loose-fit types don't need fit test
    if rpe_type in [RPEType.LOOSE_FIT_11, RPEType.LOOSE_FIT_20, RPEType.LOOSE_FIT_25]:
        return False

    return True
