"""
Regulatory classification and health check requirement models.

References:
- 特定化学物質障害予防規則 (Ordinance on Prevention of Hazards Due to Specified Chemical Substances)
- 有機溶剤中毒予防規則 (Ordinance on Prevention of Organic Solvent Poisoning)
- 鉛中毒予防規則 (Ordinance on Prevention of Lead Poisoning)
- 廃棄物の処理及び清掃に関する法律 (Waste Management and Public Cleansing Act)
- 特定化学物質の環境への排出量の把握等及び管理の改善の促進に関する法律
  (Act on Confirmation, etc. of Release Amounts of Specific Chemical Substances in the Environment and Promotion of Improvements in Their Management)
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class RegulationType(str, Enum):
    """Japanese chemical regulation types."""

    TOKKA = "tokka"  # 特定化学物質障害予防規則
    ORGANIC = "organic"  # 有機溶剤中毒予防規則
    LEAD = "lead"  # 鉛中毒予防規則
    PROHIBITED = "prohibited"  # 製造禁止物質
    WASTE = "waste"  # 廃棄物の処理及び清掃に関する法律 (廃掃法)
    PRTR1 = "prtr1"  # 化管法 第一種指定化学物質
    PRTR2 = "prtr2"  # 化管法 第二種指定化学物質


# Regulation labels for display
REGULATION_LABELS = {
    (RegulationType.TOKKA, 1): "特化則第1類",
    (RegulationType.TOKKA, 2): "特化則第2類",
    (RegulationType.TOKKA, 3): "特化則第3類",
    (RegulationType.ORGANIC, 1): "有機則第1種",
    (RegulationType.ORGANIC, 2): "有機則第2種",
    (RegulationType.ORGANIC, 3): "有機則第3種",
    (RegulationType.LEAD, None): "鉛則",
    (RegulationType.PROHIBITED, None): "製造禁止物質",
    (RegulationType.WASTE, None): "廃掃法",
    (RegulationType.PRTR1, None): "化管法 第一種指定化学物質",
    (RegulationType.PRTR2, None): "化管法 第二種指定化学物質",
}

REGULATION_LABELS_EN = {
    (RegulationType.TOKKA, 1): "Specified Chemical Substances Class 1",
    (RegulationType.TOKKA, 2): "Specified Chemical Substances Class 2",
    (RegulationType.TOKKA, 3): "Specified Chemical Substances Class 3",
    (RegulationType.ORGANIC, 1): "Organic Solvents Type 1",
    (RegulationType.ORGANIC, 2): "Organic Solvents Type 2",
    (RegulationType.ORGANIC, 3): "Organic Solvents Type 3",
    (RegulationType.LEAD, None): "Lead Regulation",
    (RegulationType.PROHIBITED, None): "Manufacturing Prohibited",
    (RegulationType.WASTE, None): "Waste Management and Public Cleansing Act",
    (RegulationType.PRTR1, None): "PRTR First Class Designated Chemical Substance",
    (RegulationType.PRTR2, None): "PRTR Second Class Designated Chemical Substance",
}

REGULATION_DESCRIPTIONS = {
    RegulationType.TOKKA: "特定化学物質障害予防規則",
    RegulationType.ORGANIC: "有機溶剤中毒予防規則",
    RegulationType.LEAD: "鉛中毒予防規則",
    RegulationType.PROHIBITED: "労働安全衛生法施行令別表第3",
    RegulationType.WASTE: "廃棄物の処理及び清掃に関する法律",
    RegulationType.PRTR1: "化管法（第一種指定化学物質）",
    RegulationType.PRTR2: "化管法（第二種指定化学物質）",
}


@dataclass
class RegulatoryInfo:
    """Regulatory classification and health check requirements."""

    # Classification
    regulation_type: Optional[RegulationType]  # tokka, organic, lead, prohibited, waste, prtr1, prtr2
    regulation_class: Optional[int]  # 1, 2, 3 (None for lead/prohibited/waste/prtr1/prtr2)
    regulation_label: str  # "特化則第2類", "有機則第1種", etc.

    # Special Designations
    special_management: bool  # 特別管理物質 (30-year records)
    special_organic: bool  # 特別有機溶剤 (有機則→特化則 dual regulation)
    carcinogen: bool  # がん原性物質

    # Health Check Requirements
    health_check_required: bool
    health_check_type: Optional[str]  # "特定化学物質健康診断", etc.
    health_check_interval: Optional[str]  # "6ヶ月以内ごとに1回"
    health_check_reference: Optional[str]  # "令22-2-3" (regulation reference)

    # Administrative Requirements
    record_retention_years: int  # 5 or 30
    work_env_measurement_required: bool
    control_concentration: Optional[float]
    control_concentration_unit: Optional[str]

    # Applicability Threshold
    threshold_percent: Optional[str]  # "1%", "0.1%", etc.

    def get_label(self, language: str = "ja") -> str:
        """Get regulation label in specified language."""
        if language == "ja":
            return self.regulation_label
        key = (self.regulation_type, self.regulation_class)
        return REGULATION_LABELS_EN.get(key, self.regulation_label)

    def get_special_designations(self, language: str = "ja") -> list[str]:
        """Get list of special designation labels."""
        designations = []
        if self.special_management:
            designations.append(
                "特別管理物質" if language == "ja" else "Special Management Substance"
            )
        if self.special_organic:
            designations.append(
                "特別有機溶剤" if language == "ja" else "Special Organic Solvent"
            )
        if self.carcinogen:
            designations.append(
                "がん原性物質" if language == "ja" else "Carcinogenic Substance"
            )
        return designations

    def to_dict(self, language: str = "ja") -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "regulation_type": self.regulation_type.value if self.regulation_type else None,
            "regulation_class": self.regulation_class,
            "regulation_label": self.get_label(language),
            "special_management": self.special_management,
            "special_organic": self.special_organic,
            "carcinogen": self.carcinogen,
        }

        if self.health_check_required:
            result["health_check"] = {
                "required": True,
                "type": self.health_check_type,
                "interval": self.health_check_interval,
                "reference": self.health_check_reference,
            }
        else:
            result["health_check"] = {"required": False}

        result["administrative"] = {
            "record_retention_years": self.record_retention_years,
            "work_env_measurement_required": self.work_env_measurement_required,
        }

        if self.work_env_measurement_required and self.control_concentration:
            result["administrative"]["control_concentration"] = self.control_concentration
            result["administrative"]["control_concentration_unit"] = self.control_concentration_unit

        if self.threshold_percent:
            result["threshold_percent"] = self.threshold_percent

        return result
