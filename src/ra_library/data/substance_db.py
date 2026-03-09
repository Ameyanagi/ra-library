"""
Substance database module.

Provides access to bundled or external substance data.
Can load data from SQLite by default, with CSV kept as a compatibility input.

Reference: public methodology sources and compatibility data loaders
"""

import csv
import logging
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class SubstanceData:
    """Raw substance data from the database."""

    cas_number: str
    name_ja: str
    name_en: str

    # GHS Physical Hazards (columns 6-22)
    ghs_explosives: Optional[str] = None
    ghs_flam_gas: Optional[str] = None
    ghs_aerosol: Optional[str] = None
    ghs_ox_gas: Optional[str] = None
    ghs_gases_pressure: Optional[str] = None
    ghs_flam_liq: Optional[str] = None
    ghs_flam_sol: Optional[str] = None
    ghs_self_react: Optional[str] = None
    ghs_pyr_liq: Optional[str] = None
    ghs_pyr_sol: Optional[str] = None
    ghs_self_heat: Optional[str] = None
    ghs_water_react: Optional[str] = None
    ghs_ox_liq: Optional[str] = None
    ghs_ox_sol: Optional[str] = None
    ghs_org_perox: Optional[str] = None
    ghs_met_corr: Optional[str] = None
    ghs_inert_explosives: Optional[str] = None

    # GHS Health Hazards (columns 23-37)
    ghs_acute_oral: Optional[str] = None
    ghs_acute_dermal: Optional[str] = None
    ghs_acute_inhal_gas: Optional[str] = None
    ghs_acute_inhal_vapor: Optional[str] = None
    ghs_acute_inhal_dust: Optional[str] = None
    ghs_skin_corr: Optional[str] = None
    ghs_eye_damage: Optional[str] = None
    ghs_resp_sens: Optional[str] = None
    ghs_skin_sens: Optional[str] = None
    ghs_mutagenicity: Optional[str] = None
    ghs_carcinogenicity: Optional[str] = None
    ghs_reproductive: Optional[str] = None
    ghs_stot_se: Optional[str] = None
    ghs_stot_re: Optional[str] = None
    ghs_aspiration: Optional[str] = None

    # OEL Values
    conc_standard_8hr_ppm: Optional[float] = None
    conc_standard_8hr_mgm3: Optional[float] = None
    conc_standard_stel_ppm: Optional[float] = None
    conc_standard_stel_mgm3: Optional[float] = None

    jsoh_8hr_ppm: Optional[float] = None
    jsoh_8hr_mgm3: Optional[float] = None
    jsoh_ceiling_ppm: Optional[float] = None
    jsoh_ceiling_mgm3: Optional[float] = None

    acgih_tlv_twa_ppm: Optional[float] = None
    acgih_tlv_twa_mgm3: Optional[float] = None
    acgih_tlv_stel_ppm: Optional[float] = None
    acgih_tlv_stel_mgm3: Optional[float] = None
    acgih_tlv_c_ppm: Optional[float] = None
    acgih_tlv_c_mgm3: Optional[float] = None
    acgih_skin: Optional[bool] = None

    dfg_mak_ppm: Optional[float] = None
    dfg_mak_mgm3: Optional[float] = None
    dfg_peak_ppm: Optional[float] = None
    dfg_peak_mgm3: Optional[float] = None

    # Physical Properties
    property_type: Optional[int] = None  # 1=liquid, 2=solid, 3=gas
    molecular_weight: Optional[float] = None
    boiling_point: Optional[float] = None
    log_kow: Optional[float] = None
    flash_point: Optional[float] = None
    water_solubility: Optional[float] = None
    water_solubility_unit: Optional[str] = None
    vapor_pressure: Optional[float] = None
    vapor_pressure_unit: Optional[str] = None

    # Regulatory
    is_skin_hazard: bool = False
    is_carcinogen: bool = False
    is_conc_standard: bool = False
    skin_hazard_threshold: Optional[float] = None
    tokka_class1: bool = False
    tokka_class2: bool = False
    tokka_class3: bool = False
    tokka_threshold: Optional[float] = None
    organic_class1: bool = False
    organic_class2: bool = False
    organic_class3: bool = False
    lead_regulation: bool = False
    tetraalkyl_lead: bool = False


class SubstanceDatabase:
    """
    Substance database with lookup functionality.

    Usage:
        db = SubstanceDatabase()
        db.load()  # Load from bundled SQLite data
        substance = db.lookup("7440-06-4")  # Platinum
    """

    def __init__(self, csv_path: Optional[str] = None):
        """
        Initialize the database.

        Args:
            csv_path: Path to a SQLite or CSV file. If None, uses bundled SQLite data.
        """
        default_path = Path(
            os.environ.get(
                "RA_LIBRARY_SUBSTANCE_DB_PATH",
                Path(__file__).parent / "substances.sqlite3",
            )
        )
        self.csv_path = Path(csv_path) if csv_path is not None else default_path

        self._substances: Dict[str, SubstanceData] = {}
        self._loaded = False
        self._load_stats: dict[str, Any] = {
            "rows_loaded": 0,
            "rows_skipped": 0,
            "parse_errors": 0,
            "error_samples": [],
        }

    def load(self) -> None:
        """Load substances from SQLite or CSV."""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Substance database not found: {self.csv_path}")

        self._substances = {}
        self._load_stats = {
            "rows_loaded": 0,
            "rows_skipped": 0,
            "parse_errors": 0,
            "error_samples": [],
        }

        if self.csv_path.suffix.lower() in {".sqlite", ".sqlite3", ".db"}:
            self._load_from_sqlite()
        else:
            self._load_from_csv()

        self._loaded = True
        if self._load_stats["parse_errors"] > 0:
            logger.warning(
                "Substance database loaded with parse errors: %s",
                self._load_stats["parse_errors"],
            )

    def _load_from_csv(self) -> None:
        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)

            for _ in range(4):
                next(reader, None)

            for row_index, row in enumerate(reader, start=5):
                if len(row) < 5 or not row[0]:
                    self._load_stats["rows_skipped"] += 1
                    continue

                cas = row[0].strip()
                if not cas or cas == "CAS RN":
                    self._load_stats["rows_skipped"] += 1
                    continue

                try:
                    substance = self._parse_row(row)
                    self._substances[cas] = substance
                    self._load_stats["rows_loaded"] += 1
                except Exception as exc:
                    self._record_load_error(row_index, cas, exc)

    def _load_from_sqlite(self) -> None:
        connection = sqlite3.connect(self.csv_path)
        connection.row_factory = sqlite3.Row
        try:
            for row_index, row in enumerate(
                connection.execute("SELECT * FROM substances ORDER BY cas_number"),
                start=1,
            ):
                cas = (row["cas_number"] or "").strip()
                if not cas:
                    self._load_stats["rows_skipped"] += 1
                    continue
                try:
                    record = dict(row)
                    for key in (
                        "acgih_skin",
                        "is_skin_hazard",
                        "is_carcinogen",
                        "is_conc_standard",
                        "tokka_class1",
                        "tokka_class2",
                        "tokka_class3",
                        "organic_class1",
                        "organic_class2",
                        "organic_class3",
                        "lead_regulation",
                        "tetraalkyl_lead",
                    ):
                        record[key] = bool(record.get(key))
                    self._substances[cas] = SubstanceData(**record)
                    self._load_stats["rows_loaded"] += 1
                except Exception as exc:
                    self._record_load_error(row_index, cas, exc)
        finally:
            connection.close()

    def _record_load_error(self, row_index: int, cas: str, exc: Exception) -> None:
        self._load_stats["parse_errors"] += 1
        self._load_stats["rows_skipped"] += 1
        if len(self._load_stats["error_samples"]) < 10:
            self._load_stats["error_samples"].append({
                "row": row_index,
                "cas_number": cas,
                "error_type": type(exc).__name__,
                "message": str(exc) or type(exc).__name__,
            })

    def _parse_row(self, row: List[str]) -> SubstanceData:
        """Parse a CSV row into SubstanceData."""
        def safe_float(value: str) -> Optional[float]:
            if not value or value.strip() == "":
                return None
            try:
                return float(value.replace(",", ""))
            except (ValueError, TypeError):
                return None

        def safe_int(value: str) -> Optional[int]:
            if not value or value.strip() == "":
                return None
            try:
                return int(float(value))
            except (ValueError, TypeError):
                return None

        def safe_str(value: str) -> Optional[str]:
            if not value or value.strip() == "":
                return None
            return value.strip()

        def safe_bool(value: str) -> bool:
            return value.strip() == "1" if value else False

        # Ensure row has enough columns
        while len(row) < 94:
            row.append("")

        return SubstanceData(
            cas_number=row[0].strip(),
            name_ja=safe_str(row[2]) or "",
            name_en=safe_str(row[3]) or "",

            # GHS Physical Hazards
            ghs_explosives=safe_str(row[5]),
            ghs_flam_gas=safe_str(row[6]),
            ghs_aerosol=safe_str(row[7]),
            ghs_ox_gas=safe_str(row[8]),
            ghs_gases_pressure=safe_str(row[9]),
            ghs_flam_liq=safe_str(row[10]),
            ghs_flam_sol=safe_str(row[11]),
            ghs_self_react=safe_str(row[12]),
            ghs_pyr_liq=safe_str(row[13]),
            ghs_pyr_sol=safe_str(row[14]),
            ghs_self_heat=safe_str(row[15]),
            ghs_water_react=safe_str(row[16]),
            ghs_ox_liq=safe_str(row[17]),
            ghs_ox_sol=safe_str(row[18]),
            ghs_org_perox=safe_str(row[19]),
            ghs_met_corr=safe_str(row[20]),
            ghs_inert_explosives=safe_str(row[21]),

            # GHS Health Hazards
            ghs_acute_oral=safe_str(row[22]),
            ghs_acute_dermal=safe_str(row[23]),
            ghs_acute_inhal_gas=safe_str(row[24]),
            ghs_acute_inhal_vapor=safe_str(row[25]),
            ghs_acute_inhal_dust=safe_str(row[26]),
            ghs_skin_corr=safe_str(row[27]),
            ghs_eye_damage=safe_str(row[28]),
            ghs_resp_sens=safe_str(row[29]),
            ghs_skin_sens=safe_str(row[30]),
            ghs_mutagenicity=safe_str(row[31]),
            ghs_carcinogenicity=safe_str(row[32]),
            ghs_reproductive=safe_str(row[33]),
            ghs_stot_se=safe_str(row[34]),
            ghs_stot_re=safe_str(row[35]),
            ghs_aspiration=safe_str(row[36]),

            # OEL Values
            conc_standard_8hr_ppm=safe_float(row[42]),
            conc_standard_8hr_mgm3=safe_float(row[43]),
            conc_standard_stel_ppm=safe_float(row[44]),
            conc_standard_stel_mgm3=safe_float(row[45]),

            jsoh_8hr_ppm=safe_float(row[49]),
            jsoh_8hr_mgm3=safe_float(row[50]),
            jsoh_ceiling_ppm=safe_float(row[51]),
            jsoh_ceiling_mgm3=safe_float(row[52]),

            acgih_tlv_twa_ppm=safe_float(row[56]),
            acgih_tlv_twa_mgm3=safe_float(row[57]),
            acgih_tlv_stel_ppm=safe_float(row[58]),
            acgih_tlv_stel_mgm3=safe_float(row[59]),
            acgih_tlv_c_ppm=safe_float(row[60]),
            acgih_tlv_c_mgm3=safe_float(row[61]),
            acgih_skin=safe_str(row[54]) == "Skin" if len(row) > 54 else False,

            dfg_mak_ppm=safe_float(row[65]),
            dfg_mak_mgm3=safe_float(row[66]),
            dfg_peak_ppm=safe_float(row[67]),
            dfg_peak_mgm3=safe_float(row[68]),

            # Physical Properties
            property_type=safe_int(row[71]),
            molecular_weight=safe_float(row[72]),
            boiling_point=safe_float(row[73]),
            log_kow=safe_float(row[74]),
            flash_point=safe_float(row[75]),
            water_solubility=safe_float(row[76]),
            water_solubility_unit=safe_str(row[77]),
            vapor_pressure=safe_float(row[78]),
            vapor_pressure_unit=safe_str(row[79]),

            # Regulatory
            is_skin_hazard=safe_bool(row[80]),
            is_carcinogen=safe_bool(row[81]),
            is_conc_standard=safe_bool(row[82]),
            skin_hazard_threshold=safe_float(row[83]),
            tokka_class1=safe_bool(row[84]),
            tokka_class2=safe_bool(row[85]),
            tokka_class3=safe_bool(row[86]),
            tokka_threshold=safe_float(row[87]),
            organic_class1=safe_bool(row[88]),
            organic_class2=safe_bool(row[89]),
            organic_class3=safe_bool(row[90]),
            lead_regulation=safe_bool(row[91]),
            tetraalkyl_lead=safe_bool(row[92]),
        )

    def lookup(self, cas_number: str) -> Optional[SubstanceData]:
        """
        Look up a substance by CAS number.

        Args:
            cas_number: CAS registry number (e.g., "7440-06-4")

        Returns:
            SubstanceData if found, None otherwise
        """
        if not self._loaded:
            self.load()

        return self._substances.get(cas_number.strip())

    def search_by_name(self, name: str, limit: int = 10) -> List[SubstanceData]:
        """
        Search substances by name (Japanese or English).

        Args:
            name: Partial name to search
            limit: Maximum results to return

        Returns:
            List of matching substances
        """
        if not self._loaded:
            self.load()

        name_lower = name.lower()
        results = []

        for substance in self._substances.values():
            if (name_lower in substance.name_ja.lower() or
                name_lower in substance.name_en.lower()):
                results.append(substance)
                if len(results) >= limit:
                    break

        return results

    def get_all_cas_numbers(self) -> List[str]:
        """Get all CAS numbers in the database."""
        if not self._loaded:
            self.load()
        return list(self._substances.keys())

    @property
    def substance_count(self) -> int:
        """Get the number of substances in the database."""
        if not self._loaded:
            self.load()
        return len(self._substances)

    @property
    def load_stats(self) -> dict[str, Any]:
        """Get summary stats from the most recent CSV load."""
        if not self._loaded:
            self.load()
        return {
            "rows_loaded": self._load_stats["rows_loaded"],
            "rows_skipped": self._load_stats["rows_skipped"],
            "parse_errors": self._load_stats["parse_errors"],
            "error_samples": list(self._load_stats["error_samples"]),
        }

    def get_as_model(self, cas_number: str):
        """
        Get substance as a Substance model ready for risk assessment.

        Args:
            cas_number: CAS registry number

        Returns:
            Substance model or None if not found
        """
        from .converter import to_substance_model

        data = self.lookup(cas_number)
        if data is None:
            return None
        return to_substance_model(data)

    def get_hazard_level(self, cas_number: str) -> Optional[str]:
        """
        Get hazard level for a substance.

        Args:
            cas_number: CAS registry number

        Returns:
            Hazard level string ("HL1" to "HL5") or None if not found
        """
        from .hazard_level import get_hazard_level

        data = self.lookup(cas_number)
        if data is None:
            return None
        return get_hazard_level(data)

    def get_volatility(self, cas_number: str) -> Optional[str]:
        """
        Get volatility level for a liquid substance.

        Args:
            cas_number: CAS registry number

        Returns:
            Volatility level or None if not found/not applicable
        """
        from .volatility import determine_volatility_level

        data = self.lookup(cas_number)
        if data is None:
            return None
        return determine_volatility_level(data)

    def check_regulations(self, cas_number: str, content_pct: float = 100.0) -> Optional[dict]:
        """
        Check all regulations for a substance.

        Args:
            cas_number: CAS registry number
            content_pct: Content percentage (0-100)

        Returns:
            Dict with all regulation check results or None if not found
        """
        from .regulations import get_applicable_regulations

        data = self.lookup(cas_number)
        if data is None:
            return None
        return get_applicable_regulations(data, content_pct)


# Global database instance
_db_instance: Optional[SubstanceDatabase] = None


def get_database() -> SubstanceDatabase:
    """Get the global database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = SubstanceDatabase()
        _db_instance.load()
    return _db_instance


def lookup_substance(cas_number: str) -> Optional[SubstanceData]:
    """
    Look up a substance by CAS number.

    Convenience function that uses the global database instance.

    Args:
        cas_number: CAS registry number (e.g., "7440-06-4")

    Returns:
        SubstanceData if found, None otherwise
    """
    return get_database().lookup(cas_number)
