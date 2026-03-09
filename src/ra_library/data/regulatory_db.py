"""
Regulatory database module.

Provides access to Japanese chemical regulatory data including:
- 特化則 (Specified Chemical Substances)
- 有機則 (Organic Solvents)
- 鉛則 (Lead)
- 廃掃法 (Waste Management and Public Cleansing Act)
- 化管法 第一種/第二種指定化学物質 (PRTR First/Second Class)
- Health check requirements (特殊健康診断)
"""

import csv
import logging
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RegulatoryData:
    """Raw regulatory data from SQLite or CSV."""

    cas_number: str
    name_ja: str
    name_en: str
    regulation_type: str  # "tokka", "organic", "lead", "prohibited", "waste", "prtr1", "prtr2"
    regulation_class: int  # 1, 2, 3, or 0 (0 for lead/prohibited/waste/prtr1/prtr2)
    regulation_label: str  # "特化則第2類"
    special_management: bool
    special_organic: bool
    carcinogen: bool
    health_check_required: bool
    health_check_type: Optional[str]
    health_check_interval: Optional[str]
    health_check_ref: Optional[str]
    control_concentration: Optional[float]
    control_concentration_unit: Optional[str]
    threshold_pct: Optional[str]
    record_retention_years: int
    work_env_measurement_required: bool
    law_name_ja: Optional[str] = None
    law_name_en: Optional[str] = None


class RegulatoryDatabase:
    """
    Database for regulatory classification data.

    Usage:
        db = RegulatoryDatabase.get_instance()
        data = db.lookup("108-88-3")  # Primary row
        rows = db.lookup_all("108-88-3")  # All regulation rows
    """

    _instance: Optional["RegulatoryDatabase"] = None
    _data: Dict[str, List[RegulatoryData]]
    _loaded: bool

    def __init__(self):
        """Initialize the database."""
        self._data = {}
        self._loaded = False
        self._load_stats = {
            "rows_loaded": 0,
            "rows_skipped": 0,
            "parse_errors": 0,
            "error_samples": [],
        }
        self.csv_path = Path(
            os.environ.get(
                "RA_LIBRARY_REGULATORY_DB_PATH",
                Path(__file__).parent / "regulatory.sqlite3",
            )
        )

    @classmethod
    def get_instance(cls) -> "RegulatoryDatabase":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._load_data()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing)."""
        cls._instance = None

    def _load_data(self) -> None:
        """Load regulatory data from SQLite or CSV."""
        if not self.csv_path.exists():
            # Silently handle missing file - not all deployments have regulatory data
            self._loaded = True
            return

        self._data = {}
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
                "Regulatory database loaded with parse errors: %s",
                self._load_stats["parse_errors"],
            )

    def _load_from_csv(self) -> None:
        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row_index, row in enumerate(reader, start=2):
                cas = row.get("cas_number", "").strip()
                if not cas or cas == "―":
                    self._load_stats["rows_skipped"] += 1
                    continue

                try:
                    data = self._parse_row(row)
                    self._data.setdefault(cas, []).append(data)
                    self._load_stats["rows_loaded"] += 1
                except Exception as exc:
                    self._record_load_error(row_index, cas, exc)

    def _load_from_sqlite(self) -> None:
        connection = sqlite3.connect(self.csv_path)
        connection.row_factory = sqlite3.Row
        try:
            for row_index, row in enumerate(
                connection.execute("SELECT * FROM regulatory_substances ORDER BY cas_number"),
                start=1,
            ):
                cas = (row["cas_number"] or "").strip()
                if not cas or cas == "―":
                    self._load_stats["rows_skipped"] += 1
                    continue
                try:
                    record = dict(row)
                    for key in (
                        "special_management",
                        "special_organic",
                        "carcinogen",
                        "health_check_required",
                        "work_env_measurement_required",
                    ):
                        record[key] = bool(record.get(key))
                    self._data.setdefault(cas, []).append(RegulatoryData(**record))
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

    def _parse_row(self, row: Dict[str, str]) -> RegulatoryData:
        """Parse a CSV row into RegulatoryData."""

        def safe_bool(value: str) -> bool:
            return value.strip().lower() in ("true", "1", "yes")

        def safe_float(value: str) -> Optional[float]:
            if not value or value.strip() == "":
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                return None

        def safe_int(value: str, default: int = 0) -> int:
            if not value or value.strip() == "":
                return default
            try:
                return int(value)
            except (ValueError, TypeError):
                return default

        def safe_str(value: str) -> Optional[str]:
            if not value or value.strip() == "":
                return None
            return value.strip()

        return RegulatoryData(
            cas_number=row["cas_number"].strip(),
            name_ja=row.get("name_ja", "") or "",
            name_en=row.get("name_en", "") or "",
            regulation_type=row.get("regulation_type", "") or "",
            regulation_class=safe_int(row.get("regulation_class", "")),
            regulation_label=row.get("regulation_label", "") or "",
            law_name_ja=safe_str(row.get("law_name_ja", "")),
            law_name_en=safe_str(row.get("law_name_en", "")),
            special_management=safe_bool(row.get("special_management", "")),
            special_organic=safe_bool(row.get("special_organic", "")),
            carcinogen=safe_bool(row.get("carcinogen", "")),
            health_check_required=safe_bool(row.get("health_check_required", "")),
            health_check_type=safe_str(row.get("health_check_type", "")),
            health_check_interval=safe_str(row.get("health_check_interval", "")),
            health_check_ref=safe_str(row.get("health_check_ref", "")),
            control_concentration=safe_float(row.get("control_concentration", "")),
            control_concentration_unit=safe_str(row.get("control_concentration_unit", "")),
            threshold_pct=safe_str(row.get("threshold_pct", "")),
            record_retention_years=safe_int(row.get("record_retention_years", ""), 5),
            work_env_measurement_required=safe_bool(row.get("work_env_measurement_required", "")),
        )

    def lookup(self, cas_number: str) -> Optional[RegulatoryData]:
        """
        Look up primary regulatory data by CAS number.

        Args:
            cas_number: CAS registry number (e.g., "108-88-3")

        Returns:
            First matching RegulatoryData if found, None otherwise
        """
        if not self._loaded:
            self._load_data()

        matches = self._data.get(cas_number.strip(), [])
        return matches[0] if matches else None

    def lookup_all(self, cas_number: str) -> List[RegulatoryData]:
        """
        Look up all regulatory rows by CAS number.

        Args:
            cas_number: CAS registry number (e.g., "108-88-3")

        Returns:
            List of matching regulatory rows (possibly empty)
        """
        if not self._loaded:
            self._load_data()

        return list(self._data.get(cas_number.strip(), []))

    def get_by_regulation(
        self,
        reg_type: str,
        reg_class: Optional[int] = None,
    ) -> List[RegulatoryData]:
        """
        Get all substances under a specific regulation.

        Args:
            reg_type: Regulation type ("tokka", "organic", "lead", "prohibited", "waste", "prtr1", "prtr2")
            reg_class: Optional regulation class (1, 2, 3)

        Returns:
            List of matching substances
        """
        if not self._loaded:
            self._load_data()

        results: List[RegulatoryData] = []
        for rows in self._data.values():
            for data in rows:
                if data.regulation_type != reg_type:
                    continue
                if reg_class is not None and data.regulation_class != reg_class:
                    continue
                results.append(data)

        return results

    def get_all(self) -> List[RegulatoryData]:
        """Get all regulatory data."""
        if not self._loaded:
            self._load_data()
        return [data for rows in self._data.values() for data in rows]

    @property
    def substance_count(self) -> int:
        """Get the number of substances in the database."""
        if not self._loaded:
            self._load_data()
        return len(self._data)

    @property
    def load_stats(self) -> dict:
        """Get summary stats from the most recent CSV load."""
        if not self._loaded:
            self._load_data()
        return {
            "rows_loaded": self._load_stats["rows_loaded"],
            "rows_skipped": self._load_stats["rows_skipped"],
            "parse_errors": self._load_stats["parse_errors"],
            "error_samples": list(self._load_stats["error_samples"]),
        }


# Convenience functions
def get_regulatory_database() -> RegulatoryDatabase:
    """Get the global regulatory database instance."""
    return RegulatoryDatabase.get_instance()


def lookup_regulatory(cas_number: str) -> Optional[RegulatoryData]:
    """
    Look up regulatory data by CAS number.

    Convenience function that uses the global database instance.

    Args:
        cas_number: CAS registry number (e.g., "108-88-3")

    Returns:
        RegulatoryData if found, None otherwise
    """
    return get_regulatory_database().lookup(cas_number)


def lookup_regulatory_all(cas_number: str) -> List[RegulatoryData]:
    """
    Look up all regulatory rows by CAS number.

    Convenience function that uses the global database instance.

    Args:
        cas_number: CAS registry number (e.g., "108-88-3")

    Returns:
        List of RegulatoryData rows
    """
    return get_regulatory_database().lookup_all(cas_number)


def to_regulatory_info(data: RegulatoryData):
    """
    Convert RegulatoryData to RegulatoryInfo model.

    Args:
        data: Raw regulatory data from database

    Returns:
        RegulatoryInfo model instance
    """
    from ..models.regulatory import RegulatoryInfo, RegulationType

    reg_type = None
    if data.regulation_type:
        try:
            reg_type = RegulationType(data.regulation_type)
        except ValueError:
            pass

    return RegulatoryInfo(
        regulation_type=reg_type,
        regulation_class=data.regulation_class if data.regulation_class > 0 else None,
        regulation_label=data.regulation_label,
        special_management=data.special_management,
        special_organic=data.special_organic,
        carcinogen=data.carcinogen,
        health_check_required=data.health_check_required,
        health_check_type=data.health_check_type,
        health_check_interval=data.health_check_interval,
        health_check_reference=data.health_check_ref,
        record_retention_years=data.record_retention_years,
        work_env_measurement_required=data.work_env_measurement_required,
        control_concentration=data.control_concentration,
        control_concentration_unit=data.control_concentration_unit,
        threshold_percent=data.threshold_pct,
    )


def to_regulatory_info_list(data_rows: List[RegulatoryData]):
    """
    Convert multiple RegulatoryData rows to RegulatoryInfo models.

    Args:
        data_rows: List of raw regulatory rows from database

    Returns:
        List of RegulatoryInfo model instances
    """
    return [to_regulatory_info(data) for data in data_rows]


def get_regulatory_info(cas_number: str):
    """
    Get regulatory info for a substance.

    Convenience function that combines lookup and conversion.

    Args:
        cas_number: CAS registry number

    Returns:
        RegulatoryInfo if found, None otherwise
    """
    data = lookup_regulatory(cas_number)
    if data is None:
        return None
    return to_regulatory_info(data)


def get_regulatory_info_list(cas_number: str):
    """
    Get all regulatory info rows for a substance.

    Convenience function that combines lookup and conversion.

    Args:
        cas_number: CAS registry number

    Returns:
        List of RegulatoryInfo rows (possibly empty)
    """
    return to_regulatory_info_list(lookup_regulatory_all(cas_number))
