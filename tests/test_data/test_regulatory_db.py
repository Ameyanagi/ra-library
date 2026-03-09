"""Tests for regulatory database loading and diagnostics."""

from ra_library.data import RegulatoryData, RegulatoryDatabase, to_regulatory_info
from ra_library.models import RegulationType


class TestRegulatoryDatabase:
    """Tests for RegulatoryDatabase class."""

    def test_load_stats_available_after_lookup(self):
        """Lookup should trigger load and expose load stats."""
        db = RegulatoryDatabase()
        _ = db.lookup("108-88-3")

        stats = db.load_stats
        assert stats["rows_loaded"] >= 0
        assert stats["rows_skipped"] >= 0
        assert stats["parse_errors"] >= 0
        assert isinstance(stats["error_samples"], list)

    def test_lookup_nonexistent_returns_none(self):
        """Nonexistent CAS should return None."""
        db = RegulatoryDatabase()
        result = db.lookup("99999-99-9")
        assert result is None

    def test_waste_regulation_rows_are_available(self):
        """Waste-law rows should be queryable by regulation type."""
        db = RegulatoryDatabase()
        results = db.get_by_regulation("waste")

        assert len(results) >= 1
        assert all(item.regulation_type == "waste" for item in results)

    def test_prtr1_regulation_rows_are_available(self):
        """PRTR first-class rows should be queryable by regulation type."""
        db = RegulatoryDatabase()
        results = db.get_by_regulation("prtr1")

        assert len(results) >= 1
        assert all(item.regulation_type == "prtr1" for item in results)

    def test_lookup_all_supports_multiple_regulations_per_cas(self):
        """CAS can map to multiple regulation rows."""
        db = RegulatoryDatabase()
        results = db.lookup_all("79-01-6")
        regulation_types = {row.regulation_type for row in results}

        assert "tokka" in regulation_types
        assert "waste" in regulation_types

    def test_to_regulatory_info_supports_waste_regulation(self):
        """Waste law entries should map to the RegulationType enum."""
        data = RegulatoryData(
            cas_number="123-45-6",
            name_ja="テスト物質",
            name_en="Test Substance",
            regulation_type="waste",
            regulation_class=0,
            regulation_label="廃掃法",
            special_management=False,
            special_organic=False,
            carcinogen=False,
            health_check_required=False,
            health_check_type=None,
            health_check_interval=None,
            health_check_ref=None,
            control_concentration=None,
            control_concentration_unit=None,
            threshold_pct=None,
            record_retention_years=5,
            work_env_measurement_required=False,
        )

        info = to_regulatory_info(data)

        assert info.regulation_type == RegulationType.WASTE
        assert info.regulation_class is None
        assert info.get_label("ja") == "廃掃法"
        assert info.get_label("en") == "Waste Management and Public Cleansing Act"

    def test_to_regulatory_info_supports_prtr1_regulation(self):
        """PRTR first-class entries should map to the RegulationType enum."""
        data = RegulatoryData(
            cas_number="123-45-6",
            name_ja="テスト物質",
            name_en="Test Substance",
            regulation_type="prtr1",
            regulation_class=0,
            regulation_label="化管法 第一種指定化学物質",
            special_management=False,
            special_organic=False,
            carcinogen=False,
            health_check_required=False,
            health_check_type=None,
            health_check_interval=None,
            health_check_ref=None,
            control_concentration=None,
            control_concentration_unit=None,
            threshold_pct=None,
            record_retention_years=5,
            work_env_measurement_required=False,
        )

        info = to_regulatory_info(data)

        assert info.regulation_type == RegulationType.PRTR1
        assert info.regulation_class is None
        assert info.get_label("ja") == "化管法 第一種指定化学物質"
        assert info.get_label("en") == "PRTR First Class Designated Chemical Substance"
