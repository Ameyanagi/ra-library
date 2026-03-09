"""
Tests for hazard level calculator.

Based on CREATE-SIMPLE hazard level (HL) determination.

Hazard levels:
- HL5: Carcinogenicity 1A/1B, Mutagenicity 1A/1B, Reproductive 1A/1B
- HL4: Carcinogenicity 2, Mutagenicity 2, Reproductive 2
- HL3: STOT-RE 1/2, Respiratory sensitization 1
- HL2: Other health hazards (acute toxicity, skin irritation, etc.)
- HL1: No significant health hazards
"""

import pytest
from ra_library.data.hazard_level import (
    get_hazard_level,
    is_carcinogen,
    is_mutagen,
    is_reproductive_toxicant,
    is_stot_re,
    is_respiratory_sensitizer,
    has_health_hazards,
)
from ra_library.data import SubstanceData


class TestCarcinogenicity:
    """Tests for carcinogenicity detection."""

    def test_carcinogenicity_1a(self):
        """Carcinogenicity 1A is detected."""
        substance = SubstanceData(
            cas_number="test-001",
            name_ja="発がん物質1A",
            name_en="Carcinogen 1A",
            ghs_carcinogenicity="1A",
        )
        assert is_carcinogen(substance) is True

    def test_carcinogenicity_1b(self):
        """Carcinogenicity 1B is detected."""
        substance = SubstanceData(
            cas_number="test-002",
            name_ja="発がん物質1B",
            name_en="Carcinogen 1B",
            ghs_carcinogenicity="1B",
        )
        assert is_carcinogen(substance) is True

    def test_carcinogenicity_2(self):
        """Carcinogenicity 2 is detected."""
        substance = SubstanceData(
            cas_number="test-003",
            name_ja="発がん物質2",
            name_en="Carcinogen 2",
            ghs_carcinogenicity="2",
        )
        assert is_carcinogen(substance) is True

    def test_no_carcinogenicity(self):
        """No carcinogenicity returns False."""
        substance = SubstanceData(
            cas_number="test-004",
            name_ja="非発がん物質",
            name_en="Non-carcinogen",
        )
        assert is_carcinogen(substance) is False

    def test_carcinogenicity_from_flag(self):
        """Carcinogenicity detected from is_carcinogen flag."""
        substance = SubstanceData(
            cas_number="test-005",
            name_ja="発がん物質",
            name_en="Carcinogen",
            is_carcinogen=True,
        )
        assert is_carcinogen(substance) is True


class TestMutagenicity:
    """Tests for mutagenicity detection."""

    def test_mutagenicity_1a(self):
        """Mutagenicity 1A is detected."""
        substance = SubstanceData(
            cas_number="test-010",
            name_ja="変異原性物質1A",
            name_en="Mutagen 1A",
            ghs_mutagenicity="1A",
        )
        assert is_mutagen(substance) is True

    def test_mutagenicity_1b(self):
        """Mutagenicity 1B is detected."""
        substance = SubstanceData(
            cas_number="test-011",
            name_ja="変異原性物質1B",
            name_en="Mutagen 1B",
            ghs_mutagenicity="1B",
        )
        assert is_mutagen(substance) is True

    def test_mutagenicity_2(self):
        """Mutagenicity 2 is detected."""
        substance = SubstanceData(
            cas_number="test-012",
            name_ja="変異原性物質2",
            name_en="Mutagen 2",
            ghs_mutagenicity="2",
        )
        assert is_mutagen(substance) is True

    def test_no_mutagenicity(self):
        """No mutagenicity returns False."""
        substance = SubstanceData(
            cas_number="test-013",
            name_ja="非変異原性物質",
            name_en="Non-mutagen",
        )
        assert is_mutagen(substance) is False


class TestReproductiveToxicity:
    """Tests for reproductive toxicity detection."""

    def test_reproductive_1a(self):
        """Reproductive toxicity 1A is detected."""
        substance = SubstanceData(
            cas_number="test-020",
            name_ja="生殖毒性物質1A",
            name_en="Reproductive toxicant 1A",
            ghs_reproductive="1A",
        )
        assert is_reproductive_toxicant(substance) is True

    def test_reproductive_1b(self):
        """Reproductive toxicity 1B is detected."""
        substance = SubstanceData(
            cas_number="test-021",
            name_ja="生殖毒性物質1B",
            name_en="Reproductive toxicant 1B",
            ghs_reproductive="1B",
        )
        assert is_reproductive_toxicant(substance) is True

    def test_reproductive_2(self):
        """Reproductive toxicity 2 is detected."""
        substance = SubstanceData(
            cas_number="test-022",
            name_ja="生殖毒性物質2",
            name_en="Reproductive toxicant 2",
            ghs_reproductive="2",
        )
        assert is_reproductive_toxicant(substance) is True

    def test_no_reproductive(self):
        """No reproductive toxicity returns False."""
        substance = SubstanceData(
            cas_number="test-023",
            name_ja="非生殖毒性物質",
            name_en="Non-reproductive toxicant",
        )
        assert is_reproductive_toxicant(substance) is False


class TestSTOTRE:
    """Tests for STOT-RE (specific target organ toxicity - repeated exposure)."""

    def test_stot_re_1(self):
        """STOT-RE 1 is detected."""
        substance = SubstanceData(
            cas_number="test-030",
            name_ja="STOT-RE1物質",
            name_en="STOT-RE 1",
            ghs_stot_re="1",
        )
        assert is_stot_re(substance) is True

    def test_stot_re_2(self):
        """STOT-RE 2 is detected."""
        substance = SubstanceData(
            cas_number="test-031",
            name_ja="STOT-RE2物質",
            name_en="STOT-RE 2",
            ghs_stot_re="2",
        )
        assert is_stot_re(substance) is True

    def test_no_stot_re(self):
        """No STOT-RE returns False."""
        substance = SubstanceData(
            cas_number="test-032",
            name_ja="非STOT-RE物質",
            name_en="No STOT-RE",
        )
        assert is_stot_re(substance) is False


class TestRespiratorySensitization:
    """Tests for respiratory sensitization detection."""

    def test_resp_sens_1(self):
        """Respiratory sensitization 1 is detected."""
        substance = SubstanceData(
            cas_number="test-040",
            name_ja="呼吸器感作性物質",
            name_en="Respiratory sensitizer",
            ghs_resp_sens="1",
        )
        assert is_respiratory_sensitizer(substance) is True

    def test_resp_sens_1a(self):
        """Respiratory sensitization 1A is detected."""
        substance = SubstanceData(
            cas_number="test-041",
            name_ja="呼吸器感作性物質1A",
            name_en="Respiratory sensitizer 1A",
            ghs_resp_sens="1A",
        )
        assert is_respiratory_sensitizer(substance) is True

    def test_no_resp_sens(self):
        """No respiratory sensitization returns False."""
        substance = SubstanceData(
            cas_number="test-042",
            name_ja="非呼吸器感作性物質",
            name_en="No respiratory sensitizer",
        )
        assert is_respiratory_sensitizer(substance) is False


class TestHazardLevel:
    """Tests for overall hazard level determination."""

    def test_hl5_carcinogen_1a(self):
        """Carcinogenicity 1A → HL5."""
        substance = SubstanceData(
            cas_number="test-050",
            name_ja="発がん物質1A",
            name_en="Carcinogen 1A",
            ghs_carcinogenicity="1A",
        )
        assert get_hazard_level(substance) == "HL5"

    def test_hl5_carcinogen_1b(self):
        """Carcinogenicity 1B → HL5."""
        substance = SubstanceData(
            cas_number="test-051",
            name_ja="発がん物質1B",
            name_en="Carcinogen 1B",
            ghs_carcinogenicity="1B",
        )
        assert get_hazard_level(substance) == "HL5"

    def test_hl5_mutagen_1a(self):
        """Mutagenicity 1A → HL5."""
        substance = SubstanceData(
            cas_number="test-052",
            name_ja="変異原性物質1A",
            name_en="Mutagen 1A",
            ghs_mutagenicity="1A",
        )
        assert get_hazard_level(substance) == "HL5"

    def test_hl5_mutagen_1b(self):
        """Mutagenicity 1B → HL5."""
        substance = SubstanceData(
            cas_number="test-053",
            name_ja="変異原性物質1B",
            name_en="Mutagen 1B",
            ghs_mutagenicity="1B",
        )
        assert get_hazard_level(substance) == "HL5"

    def test_hl5_reproductive_1a(self):
        """Reproductive toxicity 1A → HL5."""
        substance = SubstanceData(
            cas_number="test-054",
            name_ja="生殖毒性物質1A",
            name_en="Reproductive toxicant 1A",
            ghs_reproductive="1A",
        )
        assert get_hazard_level(substance) == "HL5"

    def test_hl5_reproductive_1b(self):
        """Reproductive toxicity 1B → HL5."""
        substance = SubstanceData(
            cas_number="test-055",
            name_ja="生殖毒性物質1B",
            name_en="Reproductive toxicant 1B",
            ghs_reproductive="1B",
        )
        assert get_hazard_level(substance) == "HL5"

    def test_hl4_carcinogen_2(self):
        """Carcinogenicity 2 → HL4."""
        substance = SubstanceData(
            cas_number="test-060",
            name_ja="発がん物質2",
            name_en="Carcinogen 2",
            ghs_carcinogenicity="2",
        )
        assert get_hazard_level(substance) == "HL4"

    def test_hl4_mutagen_2(self):
        """Mutagenicity 2 → HL4."""
        substance = SubstanceData(
            cas_number="test-061",
            name_ja="変異原性物質2",
            name_en="Mutagen 2",
            ghs_mutagenicity="2",
        )
        assert get_hazard_level(substance) == "HL4"

    def test_hl4_reproductive_2(self):
        """Reproductive toxicity 2 → HL4."""
        substance = SubstanceData(
            cas_number="test-062",
            name_ja="生殖毒性物質2",
            name_en="Reproductive toxicant 2",
            ghs_reproductive="2",
        )
        assert get_hazard_level(substance) == "HL4"

    def test_hl3_stot_re_1(self):
        """STOT-RE 1 → HL3."""
        substance = SubstanceData(
            cas_number="test-070",
            name_ja="STOT-RE1物質",
            name_en="STOT-RE 1",
            ghs_stot_re="1",
        )
        assert get_hazard_level(substance) == "HL3"

    def test_hl3_stot_re_2(self):
        """STOT-RE 2 → HL3."""
        substance = SubstanceData(
            cas_number="test-071",
            name_ja="STOT-RE2物質",
            name_en="STOT-RE 2",
            ghs_stot_re="2",
        )
        assert get_hazard_level(substance) == "HL3"

    def test_hl3_respiratory_sensitization(self):
        """Respiratory sensitization → HL3."""
        substance = SubstanceData(
            cas_number="test-072",
            name_ja="呼吸器感作性物質",
            name_en="Respiratory sensitizer",
            ghs_resp_sens="1",
        )
        assert get_hazard_level(substance) == "HL3"

    def test_hl2_acute_toxicity(self):
        """Acute toxicity → HL2."""
        substance = SubstanceData(
            cas_number="test-080",
            name_ja="急性毒性物質",
            name_en="Acutely toxic",
            ghs_acute_oral="3",
        )
        assert get_hazard_level(substance) == "HL2"

    def test_hl2_skin_corrosion(self):
        """Skin corrosion/irritation → HL2."""
        substance = SubstanceData(
            cas_number="test-081",
            name_ja="皮膚腐食性物質",
            name_en="Skin corrosive",
            ghs_skin_corr="1A",
        )
        assert get_hazard_level(substance) == "HL2"

    def test_hl2_eye_damage(self):
        """Eye damage → HL2."""
        substance = SubstanceData(
            cas_number="test-082",
            name_ja="眼損傷物質",
            name_en="Eye damage",
            ghs_eye_damage="1",
        )
        assert get_hazard_level(substance) == "HL2"

    def test_hl2_skin_sensitization(self):
        """Skin sensitization → HL2."""
        substance = SubstanceData(
            cas_number="test-083",
            name_ja="皮膚感作性物質",
            name_en="Skin sensitizer",
            ghs_skin_sens="1",
        )
        assert get_hazard_level(substance) == "HL2"

    def test_hl2_stot_se(self):
        """STOT-SE → HL2."""
        substance = SubstanceData(
            cas_number="test-084",
            name_ja="STOT-SE物質",
            name_en="STOT-SE",
            ghs_stot_se="1",
        )
        assert get_hazard_level(substance) == "HL2"

    def test_hl2_aspiration(self):
        """Aspiration hazard → HL2."""
        substance = SubstanceData(
            cas_number="test-085",
            name_ja="吸引性呼吸器有害性",
            name_en="Aspiration hazard",
            ghs_aspiration="1",
        )
        assert get_hazard_level(substance) == "HL2"

    def test_hl1_no_hazards(self):
        """No health hazards → HL1."""
        substance = SubstanceData(
            cas_number="test-090",
            name_ja="無害物質",
            name_en="Harmless",
        )
        assert get_hazard_level(substance) == "HL1"

    def test_hl1_physical_hazards_only(self):
        """Physical hazards only (no health hazards) → HL1."""
        substance = SubstanceData(
            cas_number="test-091",
            name_ja="可燃性液体",
            name_en="Flammable liquid",
            ghs_flam_liq="2",
        )
        assert get_hazard_level(substance) == "HL1"


class TestHazardLevelPriority:
    """Tests for hazard level priority (highest hazard wins)."""

    def test_hl5_takes_priority_over_hl4(self):
        """HL5 (carcinogen 1A) takes priority over HL4 (mutagen 2)."""
        substance = SubstanceData(
            cas_number="test-100",
            name_ja="複合有害物質",
            name_en="Multiple hazards",
            ghs_carcinogenicity="1A",  # HL5
            ghs_mutagenicity="2",  # HL4
        )
        assert get_hazard_level(substance) == "HL5"

    def test_hl5_takes_priority_over_hl3(self):
        """HL5 takes priority over HL3."""
        substance = SubstanceData(
            cas_number="test-101",
            name_ja="複合有害物質",
            name_en="Multiple hazards",
            ghs_reproductive="1B",  # HL5
            ghs_stot_re="1",  # HL3
        )
        assert get_hazard_level(substance) == "HL5"

    def test_hl4_takes_priority_over_hl3(self):
        """HL4 takes priority over HL3."""
        substance = SubstanceData(
            cas_number="test-102",
            name_ja="複合有害物質",
            name_en="Multiple hazards",
            ghs_carcinogenicity="2",  # HL4
            ghs_resp_sens="1",  # HL3
        )
        assert get_hazard_level(substance) == "HL4"

    def test_hl3_takes_priority_over_hl2(self):
        """HL3 takes priority over HL2."""
        substance = SubstanceData(
            cas_number="test-103",
            name_ja="複合有害物質",
            name_en="Multiple hazards",
            ghs_stot_re="1",  # HL3
            ghs_acute_oral="3",  # HL2
        )
        assert get_hazard_level(substance) == "HL3"


class TestRealSubstancesHazardLevel:
    """Test hazard level with known substances."""

    def test_formaldehyde_hl5(self):
        """Formaldehyde (Carcinogen 1A) → HL5."""
        # Simulate formaldehyde data
        substance = SubstanceData(
            cas_number="50-00-0",
            name_ja="ホルムアルデヒド",
            name_en="Formaldehyde",
            ghs_carcinogenicity="1A",
            ghs_mutagenicity="2",
            ghs_resp_sens="1",
        )
        assert get_hazard_level(substance) == "HL5"

    def test_benzene_hl5(self):
        """Benzene (Carcinogen 1A) → HL5."""
        substance = SubstanceData(
            cas_number="71-43-2",
            name_ja="ベンゼン",
            name_en="Benzene",
            ghs_carcinogenicity="1A",
            ghs_mutagenicity="1B",
        )
        assert get_hazard_level(substance) == "HL5"

    def test_ethanol_hl1(self):
        """Ethanol (low hazard) → HL1 or HL2."""
        substance = SubstanceData(
            cas_number="64-17-5",
            name_ja="エタノール",
            name_en="Ethanol",
            ghs_flam_liq="2",  # Physical hazard only
        )
        # Ethanol has low health hazard
        assert get_hazard_level(substance) in ["HL1", "HL2"]
