"""
Tests for substance database.

Tests the substance database loading and lookup functionality.
"""

import pytest
from ra_library.data import SubstanceDatabase, lookup_substance, get_database


class TestSubstanceDatabase:
    """Tests for SubstanceDatabase class."""

    @pytest.fixture
    def db(self):
        """Create a fresh database instance for each test."""
        return SubstanceDatabase()

    def test_database_loads(self, db):
        """Database loads without errors."""
        db.load()
        assert db.substance_count > 0
        stats = db.load_stats
        assert stats["rows_loaded"] == db.substance_count
        assert stats["parse_errors"] >= 0
        assert isinstance(stats["error_samples"], list)

    def test_database_has_many_substances(self, db):
        """Database contains a reasonable number of substances."""
        db.load()
        assert db.substance_count > 3400

    def test_lookup_platinum(self, db):
        """Look up Platinum (Pt) by CAS number."""
        db.load()
        pt = db.lookup("7440-06-4")

        assert pt is not None
        assert pt.cas_number == "7440-06-4"
        assert "白金" in pt.name_ja or "プラチナ" in pt.name_ja or "Platinum" in pt.name_en

    def test_lookup_rhodium(self, db):
        """Look up Rhodium (Rh) by CAS number."""
        db.load()
        rh = db.lookup("7440-16-6")

        assert rh is not None
        assert rh.cas_number == "7440-16-6"
        assert "ロジウム" in rh.name_ja or "Rhodium" in rh.name_en

    def test_lookup_formaldehyde(self, db):
        """Look up Formaldehyde by CAS number."""
        db.load()
        substance = db.lookup("50-00-0")

        assert substance is not None
        assert substance.cas_number == "50-00-0"
        assert "ホルムアルデヒド" in substance.name_ja
        assert "Formaldehyde" in substance.name_en

    def test_formaldehyde_has_oel(self, db):
        """Formaldehyde has OEL values."""
        db.load()
        substance = db.lookup("50-00-0")

        assert substance is not None
        # Formaldehyde has JSOH OEL of 0.1 ppm
        assert substance.jsoh_8hr_ppm == 0.1
        assert substance.jsoh_ceiling_ppm == 0.2

    def test_formaldehyde_preserves_v32_skin_hazard_flag_code(self, db):
        """v3.2 raw code should be preserved for downstream version logic."""
        db.load()
        substance = db.lookup("50-00-0")

        assert substance is not None
        assert substance.skin_hazard_flag_code == "2"
        assert substance.is_skin_hazard is False

    def test_formaldehyde_has_ghs(self, db):
        """Formaldehyde has GHS classification."""
        db.load()
        substance = db.lookup("50-00-0")

        assert substance is not None
        # Formaldehyde is a known carcinogen (Cat 1A)
        assert substance.ghs_carcinogenicity is not None
        assert "1A" in substance.ghs_carcinogenicity

    def test_formaldehyde_physical_properties(self, db):
        """Formaldehyde has physical properties."""
        db.load()
        substance = db.lookup("50-00-0")

        assert substance is not None
        assert substance.molecular_weight == pytest.approx(30.03, rel=0.01)
        assert substance.boiling_point == pytest.approx(98, rel=0.1)

    def test_lookup_nonexistent(self, db):
        """Looking up nonexistent CAS returns None."""
        db.load()
        result = db.lookup("99999-99-9")
        assert result is None

    def test_search_by_name_japanese(self, db):
        """Search by Japanese name."""
        db.load()
        results = db.search_by_name("ホルムアルデヒド")

        assert len(results) > 0
        assert any("50-00-0" == s.cas_number for s in results)

    def test_search_by_name_english(self, db):
        """Search by English name."""
        db.load()
        results = db.search_by_name("Formaldehyde")

        assert len(results) > 0
        assert any("50-00-0" == s.cas_number for s in results)

    def test_get_all_cas_numbers(self, db):
        """Get all CAS numbers."""
        db.load()
        cas_numbers = db.get_all_cas_numbers()

        assert len(cas_numbers) > 3000
        assert "50-00-0" in cas_numbers
        assert "7440-06-4" in cas_numbers

    def test_updated_substance_metadata_is_available(self, db):
        """Updated workbook rows should carry v3.2 update metadata."""
        db.load()
        substance = db.lookup("75-21-8")

        assert substance is not None
        assert substance.update_status == "1"
        assert substance.update_summary == "GHS（更新）"
        assert "皮膚腐食性" in (substance.update_details or "")


class TestGlobalDatabase:
    """Tests for global database functions."""

    def test_get_database(self):
        """get_database() returns a loaded database."""
        db = get_database()
        assert db is not None
        assert db.substance_count > 0

    def test_lookup_substance(self):
        """lookup_substance() convenience function works."""
        substance = lookup_substance("50-00-0")
        assert substance is not None
        assert substance.cas_number == "50-00-0"

    def test_database_metadata_reports_v32(self):
        """Bundled metadata should identify the v3.2 workbook."""
        db = get_database()
        metadata = db.metadata

        assert metadata["methodology_version"] == "v3.2"
        assert metadata["substance_unique_cas"] > 3400


class TestPlatinumData:
    """Specific tests for Platinum data."""

    def test_platinum_properties(self):
        """Verify Platinum data matches expected values."""
        pt = lookup_substance("7440-06-4")

        if pt is None:
            pytest.skip("Platinum not found in database")

        # Basic info
        assert pt.cas_number == "7440-06-4"

        # Physical properties - Platinum is a solid
        assert pt.property_type == 2  # Solid

        # Check molecular weight (should be around 195)
        if pt.molecular_weight is not None:
            assert pt.molecular_weight == pytest.approx(195.08, rel=0.01)


class TestRhodiumData:
    """Specific tests for Rhodium data."""

    def test_rhodium_properties(self):
        """Verify Rhodium data matches expected values."""
        rh = lookup_substance("7440-16-6")

        if rh is None:
            pytest.skip("Rhodium not found in database")

        # Basic info
        assert rh.cas_number == "7440-16-6"

        # Physical properties - Rhodium is a solid
        assert rh.property_type == 2  # Solid

        # Check molecular weight (should be around 102.91)
        if rh.molecular_weight is not None:
            assert rh.molecular_weight == pytest.approx(102.91, rel=0.01)
