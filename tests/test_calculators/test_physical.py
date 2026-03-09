"""
Tests for physical hazard risk calculation.

VBA Reference:
- CalculateFlamGasRisk: modCalc.bas lines 848-907
- CalculateAerosolRisk: modCalc.bas lines 908-976
- CalculateOxGasRisk: modCalc.bas lines 977-1012
- CalculateGasesUnderPressureRisk: modCalc.bas lines 1013-1048
- CalculateFlamSolRisk: modCalc.bas lines 1140-1206
- CalculateSelfReactRisk: modCalc.bas lines 1207-1247
- CalculatePyrLiqRisk: modCalc.bas lines 1248-1260
- CalculatePyrSolRisk: modCalc.bas lines 1261-1271
- CalculateSelfHeatRisk: modCalc.bas lines 1272-1310
- CalculateWaterReactRisk: modCalc.bas lines 1312-1378
"""

import pytest
from ra_library.calculators.physical_hazards import (
    calculate_flam_gas_risk,
    calculate_flam_sol_risk,
    calculate_flam_liq_risk,
    calculate_aerosol_risk,
    calculate_ox_gas_risk,
    calculate_ox_liq_risk,
    calculate_ox_sol_risk,
    calculate_gases_under_pressure_risk,
    calculate_self_react_risk,
    calculate_pyr_liq_risk,
    calculate_pyr_sol_risk,
    calculate_self_heat_risk,
    calculate_water_react_risk,
    calculate_explosives_risk,
    calculate_org_perox_risk,
    calculate_met_corr_risk,
    calculate_inert_explosives_risk,
)


class TestFlamGasRisk:
    """
    Tests for flammable gas risk calculation.

    VBA Reference: modCalc.bas lines 848-907

    Amount levels: 1=large, 2=medium-large, 3=medium, 4=medium-small, 5=small
    """

    def test_category_1_large_amount(self):
        """GHS Cat 1 + large amount = risk level 5, capped to 4."""
        level = calculate_flam_gas_risk(
            ghs_category="1",
            amount_level=1,
            ignition_controlled=False,
            explosive_atm_controlled=False,
        )
        assert level == 4

    def test_category_1_small_amount(self):
        """GHS Cat 1 + small amount = risk level 3."""
        level = calculate_flam_gas_risk(
            ghs_category="1",
            amount_level=5,
            ignition_controlled=False,
            explosive_atm_controlled=False,
        )
        assert level == 3

    def test_category_2_large_amount(self):
        """GHS Cat 2 + large amount = risk level 5, capped to 4."""
        level = calculate_flam_gas_risk(
            ghs_category="2",
            amount_level=1,
            ignition_controlled=False,
            explosive_atm_controlled=False,
        )
        assert level == 4

    def test_category_2_small_amount(self):
        """GHS Cat 2 + small amount = risk level 2."""
        level = calculate_flam_gas_risk(
            ghs_category="2",
            amount_level=5,
            ignition_controlled=False,
            explosive_atm_controlled=False,
        )
        assert level == 2

    def test_ignition_control_reduces_risk_by_1(self):
        """Ignition source control reduces risk by 1."""
        # Use Cat 1 small amount where base=3 (not capped)
        base = calculate_flam_gas_risk("1", 5, False, False)
        controlled = calculate_flam_gas_risk("1", 5, True, False)
        assert base == 3
        assert controlled == 2

    def test_explosive_atm_control_reduces_risk_by_1(self):
        """Explosive atmosphere control reduces risk by 1."""
        # Use Cat 1 small amount where base=3 (not capped)
        base = calculate_flam_gas_risk("1", 5, False, False)
        controlled = calculate_flam_gas_risk("1", 5, False, True)
        assert base == 3
        assert controlled == 2

    def test_both_controls_reduce_risk_by_2(self):
        """Both controls reduce risk by 2."""
        # Use Cat 1 medium-small amount where base=4 (not capped from 5)
        base = calculate_flam_gas_risk("1", 4, False, False)
        controlled = calculate_flam_gas_risk("1", 4, True, True)
        assert base == 4
        assert controlled == 2

    def test_no_classification_returns_none(self):
        """No GHS classification returns None."""
        level = calculate_flam_gas_risk(
            ghs_category=None,
            amount_level=1,
        )
        assert level is None


class TestFlamSolRisk:
    """
    Tests for flammable solid risk calculation.

    VBA Reference: modCalc.bas lines 1140-1206

    Note: Category 2 solids have additional dustiness consideration
    """

    def test_category_1_large_amount(self):
        """GHS Cat 1 + large amount = risk level 5, capped to 4."""
        level = calculate_flam_sol_risk(
            ghs_category="1",
            amount_level=1,
            ignition_controlled=False,
            explosive_atm_controlled=False,
            low_dustiness=False,
        )
        assert level == 4

    def test_category_1_small_amount(self):
        """GHS Cat 1 + small amount = risk level 2."""
        level = calculate_flam_sol_risk(
            ghs_category="1",
            amount_level=5,
            ignition_controlled=False,
            explosive_atm_controlled=False,
            low_dustiness=False,
        )
        assert level == 2

    def test_category_2_all_controls_reduce_by_3(self):
        """Cat 2: ignition + explosive atm + low dustiness reduces by 3."""
        # Use medium amount where base=4
        base = calculate_flam_sol_risk("2", 3, False, False, False)
        controlled = calculate_flam_sol_risk("2", 3, True, True, True)
        assert base == 4
        assert controlled == 1  # 4 - 3 = 1

    def test_category_2_two_controls_reduce_by_2(self):
        """Cat 2: any two controls reduce by 2."""
        # Use medium amount where base=4
        base = calculate_flam_sol_risk("2", 3, False, False, False)
        controlled = calculate_flam_sol_risk("2", 3, True, True, False)
        assert base == 4
        assert controlled == 2  # 4 - 2 = 2

    def test_no_classification_returns_none(self):
        """No GHS classification returns None."""
        level = calculate_flam_sol_risk(
            ghs_category=None,
            amount_level=1,
        )
        assert level is None


class TestAerosolRisk:
    """
    Tests for aerosol risk calculation.

    VBA Reference: modCalc.bas lines 908-976
    """

    def test_category_1_large_amount(self):
        """GHS Cat 1 + large amount = risk level 5, capped to 4."""
        level = calculate_aerosol_risk(
            ghs_category="1",
            amount_level=1,
            ignition_controlled=False,
            explosive_atm_controlled=False,
        )
        assert level == 4

    def test_category_2_medium_amount(self):
        """GHS Cat 2 + medium amount = risk level 4."""
        level = calculate_aerosol_risk(
            ghs_category="2",
            amount_level=3,
            ignition_controlled=False,
            explosive_atm_controlled=False,
        )
        assert level == 4

    def test_category_3_low_risk(self):
        """GHS Cat 3 has lower risk levels."""
        level = calculate_aerosol_risk(
            ghs_category="3",
            amount_level=1,
            ignition_controlled=False,
            explosive_atm_controlled=False,
        )
        assert level == 2

    def test_no_classification_returns_none(self):
        """No GHS classification returns None."""
        level = calculate_aerosol_risk(ghs_category=None, amount_level=1)
        assert level is None


class TestOxGasRisk:
    """
    Tests for oxidizing gas risk calculation.

    VBA Reference: modCalc.bas lines 977-1012
    Note: No control measure reductions for oxidizing gases
    """

    def test_large_amount(self):
        """Large amount = risk level 5, capped to 4."""
        level = calculate_ox_gas_risk(ghs_category="1", amount_level=1)
        assert level == 4

    def test_medium_amount(self):
        """Medium-large amount = risk level 4."""
        level = calculate_ox_gas_risk(ghs_category="1", amount_level=2)
        assert level == 4

    def test_medium_small_amount(self):
        """Medium-small amount = risk level 2."""
        level = calculate_ox_gas_risk(ghs_category="1", amount_level=4)
        assert level == 2

    def test_no_classification_returns_none(self):
        """No GHS classification returns None."""
        level = calculate_ox_gas_risk(ghs_category=None, amount_level=1)
        assert level is None


class TestOxLiqRisk:
    """
    Tests for oxidizing liquid risk calculation.

    VBA Reference: modCalc.bas lines 1381-1443
    """

    def test_category_1_large_amount(self):
        """GHS Cat 1 + large amount = risk level 5, capped to 4."""
        level = calculate_ox_liq_risk(
            ghs_category="1",
            amount_level=1,
            organic_controlled=False,
        )
        assert level == 4

    def test_category_2_large_amount(self):
        """GHS Cat 2 + large amount = risk level 4."""
        level = calculate_ox_liq_risk(
            ghs_category="2",
            amount_level=1,
            organic_controlled=False,
        )
        assert level == 4

    def test_category_3_large_amount(self):
        """GHS Cat 3 + large amount = risk level 3."""
        level = calculate_ox_liq_risk(
            ghs_category="3",
            amount_level=1,
            organic_controlled=False,
        )
        assert level == 3

    def test_organic_control_reduces_risk_by_1(self):
        """Organic matter control reduces risk by 1."""
        base = calculate_ox_liq_risk("1", 2, False)  # base = 4
        controlled = calculate_ox_liq_risk("1", 2, True)
        assert base == 4
        assert controlled == 3

    def test_no_classification_returns_none(self):
        """No GHS classification returns None."""
        level = calculate_ox_liq_risk(ghs_category=None, amount_level=1)
        assert level is None


class TestOxSolRisk:
    """
    Tests for oxidizing solid risk calculation.

    VBA Reference: modCalc.bas lines 1445-1507
    """

    def test_category_1_large_amount(self):
        """GHS Cat 1 + large amount = risk level 5, capped to 4."""
        level = calculate_ox_sol_risk(
            ghs_category="1",
            amount_level=1,
            organic_controlled=False,
        )
        assert level == 4

    def test_category_2_medium_amount(self):
        """GHS Cat 2 + medium-large amount = risk level 3."""
        level = calculate_ox_sol_risk(
            ghs_category="2",
            amount_level=2,
            organic_controlled=False,
        )
        assert level == 3

    def test_organic_control_reduces_risk_by_1(self):
        """Organic matter control reduces risk by 1."""
        base = calculate_ox_sol_risk("1", 2, False)  # base = 4
        controlled = calculate_ox_sol_risk("1", 2, True)
        assert base == 4
        assert controlled == 3

    def test_no_classification_returns_none(self):
        """No GHS classification returns None."""
        level = calculate_ox_sol_risk(ghs_category=None, amount_level=1)
        assert level is None


class TestGasesUnderPressureRisk:
    """
    Tests for gases under pressure risk calculation.

    VBA Reference: modCalc.bas lines 1013-1048
    """

    def test_large_amount(self):
        """Large amount = risk level 2."""
        level = calculate_gases_under_pressure_risk(
            ghs_category="compressed",
            amount_level=1,
        )
        assert level == 2

    def test_small_amount(self):
        """Small amount = risk level 1."""
        level = calculate_gases_under_pressure_risk(
            ghs_category="compressed",
            amount_level=5,
        )
        assert level == 1

    def test_no_classification_returns_none(self):
        """No GHS classification returns None."""
        level = calculate_gases_under_pressure_risk(ghs_category=None, amount_level=1)
        assert level is None


class TestSelfReactRisk:
    """
    Tests for self-reactive risk calculation.

    VBA Reference: modCalc.bas lines 1207-1247
    """

    def test_type_a_always_level_4(self):
        """Type A always returns risk level 4 (capped from 5)."""
        level = calculate_self_react_risk(ghs_category="A", amount_level=5)
        assert level == 4

    def test_type_b_always_level_4(self):
        """Type B always returns risk level 4 (capped from 5)."""
        level = calculate_self_react_risk(ghs_category="B", amount_level=5)
        assert level == 4

    def test_type_g_varies_by_amount(self):
        """Type G risk varies by amount level."""
        level_large = calculate_self_react_risk(ghs_category="G", amount_level=1)
        level_small = calculate_self_react_risk(ghs_category="G", amount_level=5)
        assert level_large == 4  # capped from 5
        assert level_small == 1

    def test_no_classification_returns_none(self):
        """No GHS classification returns None."""
        level = calculate_self_react_risk(ghs_category=None, amount_level=1)
        assert level is None


class TestPyrLiqRisk:
    """
    Tests for pyrophoric liquid risk calculation.

    VBA Reference: modCalc.bas lines 1248-1260
    """

    def test_always_returns_level_4(self):
        """Pyrophoric liquid always returns risk level 4."""
        level = calculate_pyr_liq_risk(ghs_category="1")
        assert level == 4

    def test_no_classification_returns_none(self):
        """No GHS classification returns None."""
        level = calculate_pyr_liq_risk(ghs_category=None)
        assert level is None


class TestPyrSolRisk:
    """
    Tests for pyrophoric solid risk calculation.

    VBA Reference: modCalc.bas lines 1261-1271
    """

    def test_always_returns_level_4(self):
        """Pyrophoric solid always returns risk level 4."""
        level = calculate_pyr_sol_risk(ghs_category="1")
        assert level == 4

    def test_no_classification_returns_none(self):
        """No GHS classification returns None."""
        level = calculate_pyr_sol_risk(ghs_category=None)
        assert level is None


class TestSelfHeatRisk:
    """
    Tests for self-heating risk calculation.

    VBA Reference: modCalc.bas lines 1272-1310
    """

    def test_large_amount(self):
        """Large amount = risk level 5, capped to 4."""
        level = calculate_self_heat_risk(
            ghs_category="1",
            amount_level=1,
            contact_controlled=False,
        )
        assert level == 4

    def test_small_amount(self):
        """Small amount = risk level 2."""
        level = calculate_self_heat_risk(
            ghs_category="1",
            amount_level=5,
            contact_controlled=False,
        )
        assert level == 2

    def test_contact_control_reduces_risk_by_1(self):
        """Contact control reduces risk by 1."""
        base = calculate_self_heat_risk("1", 1, False)
        controlled = calculate_self_heat_risk("1", 1, True)
        # 5 → cap 4 for base, 5-1=4 → cap 4 for controlled
        # Actually check with amount level that shows difference
        base = calculate_self_heat_risk("1", 2, False)
        controlled = calculate_self_heat_risk("1", 2, True)
        assert controlled == base - 1

    def test_no_classification_returns_none(self):
        """No GHS classification returns None."""
        level = calculate_self_heat_risk(ghs_category=None, amount_level=1)
        assert level is None


class TestWaterReactRisk:
    """
    Tests for water-reactive risk calculation.

    VBA Reference: modCalc.bas lines 1312-1378
    """

    def test_category_1_always_level_4(self):
        """Category 1 always returns risk level 4 (capped from 5)."""
        level = calculate_water_react_risk(
            ghs_category="1",
            amount_level=5,
            ignition_controlled=False,
            contact_controlled=False,
        )
        assert level == 4

    def test_category_2_large_amount(self):
        """Category 2 + large amount = risk level 5, capped to 4."""
        level = calculate_water_react_risk(
            ghs_category="2",
            amount_level=1,
            ignition_controlled=False,
            contact_controlled=False,
        )
        assert level == 4

    def test_category_2_small_amount(self):
        """Category 2 + small amount = risk level 3."""
        level = calculate_water_react_risk(
            ghs_category="2",
            amount_level=5,
            ignition_controlled=False,
            contact_controlled=False,
        )
        assert level == 3

    def test_category_3_large_amount(self):
        """Category 3 + large amount = risk level 5, capped to 4."""
        level = calculate_water_react_risk(
            ghs_category="3",
            amount_level=1,
            ignition_controlled=False,
            contact_controlled=False,
        )
        assert level == 4

    def test_both_controls_reduce_risk_by_2(self):
        """Both ignition + contact controls reduce risk by 2."""
        # Use cat 2 medium amount (base=4)
        base = calculate_water_react_risk("2", 3, False, False)
        controlled = calculate_water_react_risk("2", 3, True, True)
        assert controlled == base - 2

    def test_no_classification_returns_none(self):
        """No GHS classification returns None."""
        level = calculate_water_react_risk(ghs_category=None, amount_level=1)
        assert level is None


class TestFlamLiqRisk:
    """
    Tests for flammable liquid risk calculation.

    VBA Reference: modCalc.bas lines 1050-1139 (CalculateFlamLiqRisk)
    """

    def test_category_1_large_amount(self):
        """GHS Cat 1 + large amount = risk level 5, capped to 4."""
        level = calculate_flam_liq_risk(
            ghs_category="1",
            amount_level=1,
            flash_point=None,
            process_temp=None,
            ignition_controlled=False,
            explosive_atm_controlled=False,
        )
        assert level == 4

    def test_category_2_large_amount(self):
        """GHS Cat 2 + large amount = risk level 5, capped to 4."""
        level = calculate_flam_liq_risk(
            ghs_category="2",
            amount_level=1,
        )
        assert level == 4

    def test_category_3_large_amount(self):
        """GHS Cat 3 + large amount = risk level 4."""
        level = calculate_flam_liq_risk(
            ghs_category="3",
            amount_level=1,
        )
        assert level == 4

    def test_category_4_large_amount(self):
        """GHS Cat 4 + large amount = risk level 3."""
        level = calculate_flam_liq_risk(
            ghs_category="4",
            amount_level=1,
        )
        assert level == 3

    def test_category_4_small_amount(self):
        """GHS Cat 4 + small amount = risk level 1."""
        level = calculate_flam_liq_risk(
            ghs_category="4",
            amount_level=5,
        )
        assert level == 1

    def test_process_temp_exceeds_flash_point(self):
        """When process temp > flash point, higher risk is applied."""
        # Cat 4 with low flash point = 60°C
        # If process temp > flash point, treat as higher risk
        level = calculate_flam_liq_risk(
            ghs_category="4",
            amount_level=3,
            flash_point=50,
            process_temp=80,  # Exceeds flash point
        )
        # Should be treated as "ProcessTemp>FlashPoint" risk
        assert level == 4

    def test_ignition_control_reduces_risk(self):
        """Ignition source control reduces risk by 1."""
        base = calculate_flam_liq_risk("3", 2, ignition_controlled=False)
        controlled = calculate_flam_liq_risk("3", 2, ignition_controlled=True)
        assert controlled == base - 1

    def test_both_controls_reduce_risk_by_2(self):
        """Both controls reduce risk by 2."""
        base = calculate_flam_liq_risk("3", 1)
        controlled = calculate_flam_liq_risk("3", 1, ignition_controlled=True, explosive_atm_controlled=True)
        assert controlled == base - 2

    def test_no_classification_returns_none(self):
        """No GHS classification and no flash point returns None."""
        level = calculate_flam_liq_risk(ghs_category=None, amount_level=1, flash_point=None)
        assert level is None


class TestExplosivesRisk:
    """
    Tests for explosives risk calculation.

    VBA Reference: modCalc.bas lines 836-846 (CalculateExplosivesRisk)
    """

    def test_always_returns_level_4(self):
        """Explosives always return risk level 4 (highest)."""
        level = calculate_explosives_risk(ghs_category="1")
        assert level == 4

    def test_unstable_explosives(self):
        """Unstable explosives return risk level 4."""
        level = calculate_explosives_risk(ghs_category="UnstableExplosive")
        assert level == 4

    def test_any_category_returns_level_4(self):
        """Any GHS classification returns risk level 4."""
        for cat in ["1", "2", "3", "4", "5", "6", "UnstableExplosive"]:
            level = calculate_explosives_risk(ghs_category=cat)
            assert level == 4

    def test_no_classification_returns_none(self):
        """No GHS classification returns None."""
        level = calculate_explosives_risk(ghs_category=None)
        assert level is None

    def test_empty_classification_returns_none(self):
        """Empty GHS classification returns None."""
        level = calculate_explosives_risk(ghs_category="")
        assert level is None


class TestOrgPeroxRisk:
    """
    Tests for organic peroxide risk calculation.

    VBA Reference: modCalc.bas lines 1509-1551 (CalculateOrgPerox)
    """

    def test_type_a_always_level_4(self):
        """Type A always returns risk level 4 (capped from 5)."""
        level = calculate_org_perox_risk(ghs_category="A", amount_level=5)
        assert level == 4

    def test_type_b_always_level_4(self):
        """Type B always returns risk level 4 (capped from 5)."""
        level = calculate_org_perox_risk(ghs_category="B", amount_level=5)
        assert level == 4

    def test_type_c_d_e_always_level_4(self):
        """Types C, D, E always return risk level 4 (capped from 5)."""
        for cat in ["C", "D", "E"]:
            level = calculate_org_perox_risk(ghs_category=cat, amount_level=5)
            assert level == 4

    def test_type_f_varies_by_amount(self):
        """Type F risk varies by amount level."""
        level_large = calculate_org_perox_risk(ghs_category="F", amount_level=1)
        level_small = calculate_org_perox_risk(ghs_category="F", amount_level=5)
        assert level_large == 4  # capped from 5
        assert level_small == 1

    def test_type_g_varies_by_amount(self):
        """Type G risk varies by amount level."""
        level_large = calculate_org_perox_risk(ghs_category="G", amount_level=1)
        level_small = calculate_org_perox_risk(ghs_category="G", amount_level=5)
        assert level_large == 4  # capped from 5
        assert level_small == 1

    def test_no_classification_returns_none(self):
        """No GHS classification returns None."""
        level = calculate_org_perox_risk(ghs_category=None, amount_level=1)
        assert level is None


class TestMetCorrRisk:
    """
    Tests for metal corrosive risk calculation.

    VBA Reference: modCalc.bas lines 1552-1565 (CalculateInertMetCorrRisk)
    """

    def test_always_returns_level_2(self):
        """Metal corrosives always return risk level 2."""
        level = calculate_met_corr_risk(ghs_category="1")
        assert level == 2

    def test_no_classification_returns_none(self):
        """No GHS classification returns None."""
        level = calculate_met_corr_risk(ghs_category=None)
        assert level is None

    def test_empty_classification_returns_none(self):
        """Empty GHS classification returns None."""
        level = calculate_met_corr_risk(ghs_category="")
        assert level is None


class TestInertExplosivesRisk:
    """
    Tests for desensitized (inert) explosives risk calculation.

    VBA Reference: modCalc.bas lines 1567-1579 (CalculateInertExplosivesRisk)
    """

    def test_always_returns_level_4(self):
        """Desensitized explosives always return risk level 4."""
        level = calculate_inert_explosives_risk(ghs_category="1")
        assert level == 4

    def test_no_classification_returns_none(self):
        """No GHS classification returns None."""
        level = calculate_inert_explosives_risk(ghs_category=None)
        assert level is None

    def test_empty_classification_returns_none(self):
        """Empty GHS classification returns None."""
        level = calculate_inert_explosives_risk(ghs_category="")
        assert level is None


class TestSelfReactTypeF:
    """
    Tests for self-reactive Type F handling (previously missing).

    VBA Reference: modCalc.bas lines 1207-1247 (CalculateSelfReactRisk)
    """

    def test_type_f_varies_by_amount(self):
        """Type F risk varies by amount level (same as Type G)."""
        level_large = calculate_self_react_risk(ghs_category="F", amount_level=1)
        level_medium = calculate_self_react_risk(ghs_category="F", amount_level=3)
        level_small = calculate_self_react_risk(ghs_category="F", amount_level=5)
        assert level_large == 4  # capped from 5
        assert level_medium == 3
        assert level_small == 1
