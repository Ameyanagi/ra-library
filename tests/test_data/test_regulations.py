"""
Tests for regulatory threshold checker.

Based on VBA modFunction.bas lines 562-574.

Checks content percentage against regulatory thresholds:
- 特定化学物質 (Specified Chemical Substances - Tokka)
- 皮膚等障害化学物質 (Skin Hazard Substances)
- Organic solvents
"""

import pytest
from ra_library.data.regulations import (
    check_tokka_regulation,
    check_organic_solvent_regulation,
    check_skin_hazard_regulation,
    get_applicable_regulations,
)
from ra_library.data import SubstanceData


class TestTokkaRegulation:
    """Tests for 特定化学物質 (Tokka) regulation checking."""

    def test_tokka_class1_above_threshold(self):
        """Tokka Class 1 above threshold is flagged."""
        substance = SubstanceData(
            cas_number="test-001",
            name_ja="特化物第一類",
            name_en="Tokka Class 1",
            tokka_class1=True,
            tokka_threshold=1.0,
        )
        result = check_tokka_regulation(substance, content_pct=2.0)

        assert result["applies"] is True
        assert result["class"] == 1
        assert result["threshold"] == 1.0
        assert result["exceeds_threshold"] is True

    def test_tokka_class1_below_threshold(self):
        """Tokka Class 1 below threshold is not flagged as exceeding."""
        substance = SubstanceData(
            cas_number="test-002",
            name_ja="特化物第一類",
            name_en="Tokka Class 1",
            tokka_class1=True,
            tokka_threshold=1.0,
        )
        result = check_tokka_regulation(substance, content_pct=0.5)

        assert result["applies"] is True
        assert result["class"] == 1
        assert result["exceeds_threshold"] is False

    def test_tokka_class2(self):
        """Tokka Class 2 is detected."""
        substance = SubstanceData(
            cas_number="test-003",
            name_ja="特化物第二類",
            name_en="Tokka Class 2",
            tokka_class2=True,
            tokka_threshold=1.0,
        )
        result = check_tokka_regulation(substance, content_pct=2.0)

        assert result["applies"] is True
        assert result["class"] == 2

    def test_tokka_class3(self):
        """Tokka Class 3 is detected."""
        substance = SubstanceData(
            cas_number="test-004",
            name_ja="特化物第三類",
            name_en="Tokka Class 3",
            tokka_class3=True,
        )
        result = check_tokka_regulation(substance, content_pct=50.0)

        assert result["applies"] is True
        assert result["class"] == 3

    def test_no_tokka(self):
        """Non-Tokka substance returns applies=False."""
        substance = SubstanceData(
            cas_number="test-005",
            name_ja="一般物質",
            name_en="General Substance",
        )
        result = check_tokka_regulation(substance, content_pct=100.0)

        assert result["applies"] is False

    def test_tokka_no_threshold(self):
        """Tokka without threshold defaults to always applicable."""
        substance = SubstanceData(
            cas_number="test-006",
            name_ja="特化物",
            name_en="Tokka",
            tokka_class2=True,
            tokka_threshold=None,
        )
        result = check_tokka_regulation(substance, content_pct=0.01)

        assert result["applies"] is True
        assert result["exceeds_threshold"] is True  # No threshold = always exceeds


class TestOrganicSolventRegulation:
    """Tests for organic solvent regulation checking."""

    def test_organic_class1(self):
        """Organic solvent Class 1 is detected."""
        substance = SubstanceData(
            cas_number="test-010",
            name_ja="第一種有機溶剤",
            name_en="Organic Solvent Class 1",
            organic_class1=True,
        )
        result = check_organic_solvent_regulation(substance)

        assert result["applies"] is True
        assert result["class"] == 1

    def test_organic_class2(self):
        """Organic solvent Class 2 is detected."""
        substance = SubstanceData(
            cas_number="test-011",
            name_ja="第二種有機溶剤",
            name_en="Organic Solvent Class 2",
            organic_class2=True,
        )
        result = check_organic_solvent_regulation(substance)

        assert result["applies"] is True
        assert result["class"] == 2

    def test_organic_class3(self):
        """Organic solvent Class 3 is detected."""
        substance = SubstanceData(
            cas_number="test-012",
            name_ja="第三種有機溶剤",
            name_en="Organic Solvent Class 3",
            organic_class3=True,
        )
        result = check_organic_solvent_regulation(substance)

        assert result["applies"] is True
        assert result["class"] == 3

    def test_no_organic_solvent(self):
        """Non-organic solvent returns applies=False."""
        substance = SubstanceData(
            cas_number="test-013",
            name_ja="一般物質",
            name_en="General Substance",
        )
        result = check_organic_solvent_regulation(substance)

        assert result["applies"] is False


class TestSkinHazardRegulation:
    """Tests for 皮膚等障害化学物質 (Skin Hazard) regulation checking."""

    def test_skin_hazard_above_threshold(self):
        """Skin hazard above threshold is flagged."""
        substance = SubstanceData(
            cas_number="test-020",
            name_ja="皮膚障害化学物質",
            name_en="Skin Hazard",
            is_skin_hazard=True,
            skin_hazard_threshold=1.0,
        )
        result = check_skin_hazard_regulation(substance, content_pct=2.0)

        assert result is True

    def test_skin_hazard_below_threshold(self):
        """Skin hazard below threshold is not flagged."""
        substance = SubstanceData(
            cas_number="test-021",
            name_ja="皮膚障害化学物質",
            name_en="Skin Hazard",
            is_skin_hazard=True,
            skin_hazard_threshold=1.0,
        )
        result = check_skin_hazard_regulation(substance, content_pct=0.5)

        assert result is False

    def test_skin_hazard_no_threshold(self):
        """Skin hazard without threshold is always flagged."""
        substance = SubstanceData(
            cas_number="test-022",
            name_ja="皮膚障害化学物質",
            name_en="Skin Hazard",
            is_skin_hazard=True,
            skin_hazard_threshold=None,
        )
        result = check_skin_hazard_regulation(substance, content_pct=0.01)

        assert result is True

    def test_no_skin_hazard(self):
        """Non-skin hazard returns False."""
        substance = SubstanceData(
            cas_number="test-023",
            name_ja="一般物質",
            name_en="General Substance",
        )
        result = check_skin_hazard_regulation(substance, content_pct=100.0)

        assert result is False


class TestApplicableRegulations:
    """Tests for getting all applicable regulations."""

    def test_multiple_regulations(self):
        """Substance with multiple regulations returns all."""
        substance = SubstanceData(
            cas_number="test-030",
            name_ja="複合規制物質",
            name_en="Multiple Regulations",
            tokka_class2=True,
            tokka_threshold=1.0,
            organic_class1=True,
            is_skin_hazard=True,
            skin_hazard_threshold=0.5,
        )
        result = get_applicable_regulations(substance, content_pct=2.0)

        assert "tokka" in result
        assert result["tokka"]["applies"] is True
        assert "organic_solvent" in result
        assert result["organic_solvent"]["applies"] is True
        assert "skin_hazard" in result
        assert result["skin_hazard"] is True

    def test_no_regulations(self):
        """Substance with no regulations returns empty dict."""
        substance = SubstanceData(
            cas_number="test-031",
            name_ja="一般物質",
            name_en="General Substance",
        )
        result = get_applicable_regulations(substance, content_pct=100.0)

        assert result["tokka"]["applies"] is False
        assert result["organic_solvent"]["applies"] is False
        assert result["skin_hazard"] is False

    def test_lead_regulation(self):
        """Lead regulation is detected."""
        substance = SubstanceData(
            cas_number="test-032",
            name_ja="鉛化合物",
            name_en="Lead Compound",
            lead_regulation=True,
        )
        result = get_applicable_regulations(substance, content_pct=100.0)

        assert result["lead"] is True

    def test_tetraalkyl_lead(self):
        """Tetraalkyl lead is detected."""
        substance = SubstanceData(
            cas_number="test-033",
            name_ja="四アルキル鉛",
            name_en="Tetraalkyl Lead",
            tetraalkyl_lead=True,
        )
        result = get_applicable_regulations(substance, content_pct=100.0)

        assert result["tetraalkyl_lead"] is True

    def test_carcinogen_regulation(self):
        """Carcinogen regulation is detected."""
        substance = SubstanceData(
            cas_number="test-034",
            name_ja="発がん物質",
            name_en="Carcinogen",
            is_carcinogen=True,
        )
        result = get_applicable_regulations(substance, content_pct=100.0)

        assert result["carcinogen"] is True

    def test_concentration_standard_substance(self):
        """Concentration standard substance is detected."""
        substance = SubstanceData(
            cas_number="test-035",
            name_ja="濃度基準値設定物質",
            name_en="Concentration Standard Substance",
            is_conc_standard=True,
        )
        result = get_applicable_regulations(substance, content_pct=100.0)

        assert result["concentration_standard"] is True
