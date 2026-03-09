"""
Version-specific calculators for CREATE-SIMPLE methodology.

This module implements calculation logic specific to each CREATE-SIMPLE version,
allowing accurate comparison of results between versions.

Key Differences:
================

v3.0.2:
  - NO exposure floor (can calculate to any low value)
  - 3 regulatory categories only (皮膚等障害, がん原性, 濃度基準値)
  - Skin hazard: database flag only
  - Data columns: 83 (A-CE)

v3.1.2:
  - Exposure floor: 0.005 ppm (liquid), 0.001 mg/m³ (solid)
  - 11 regulatory categories with cutoff thresholds
  - Skin hazard: database flag + GHS classification check
  - Data columns: 93 (A-CO)
  - Added: 特化則1-3類, 有機則1-3種, 鉛則, 四アルキル鉛
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .constants import (
    MIN_EXPOSURE_LIQUID,
    MIN_EXPOSURE_SOLID,
    CUTOFF_SKIN_HAZARD,
    CUTOFF_SPECIFIED_CHEMICAL,
    CUTOFF_ORGANIC_SOLVENT,
    EXPOSURE_BANDS_LIQUID,
    EXPOSURE_BANDS_SOLID,
    CONTENT_COEFFICIENTS,
    VENTILATION_COEFFICIENTS,
    DURATION_COEFFICIENTS,
)


class CalculationVersion(Enum):
    """CREATE-SIMPLE calculation versions."""

    V3_0_2 = "v3.0.2"  # No floor, 3 regulatory categories
    V3_1_2 = "v3.1.2"  # With floor, 11 regulatory categories + GHS


@dataclass
class VersionConfig:
    """Configuration for version-specific calculation behavior."""

    version: CalculationVersion

    # Exposure floor settings
    apply_exposure_floor: bool = True
    floor_liquid_ppm: float = MIN_EXPOSURE_LIQUID  # 0.005
    floor_solid_mg_m3: float = MIN_EXPOSURE_SOLID  # 0.001

    # Regulatory detection settings
    use_ghs_skin_detection: bool = True
    regulatory_categories: int = 11  # Number of regulatory categories

    # Cutoff thresholds
    skin_hazard_cutoff: float = CUTOFF_SKIN_HAZARD  # 1.0%
    tokka_cutoff: float = CUTOFF_SPECIFIED_CHEMICAL  # 1.0%
    organic_cutoff: float = CUTOFF_ORGANIC_SOLVENT  # 5.0%

    @classmethod
    def v3_0_2(cls) -> "VersionConfig":
        """Configuration for v3.0.2 calculation."""
        return cls(
            version=CalculationVersion.V3_0_2,
            apply_exposure_floor=False,  # KEY DIFFERENCE
            use_ghs_skin_detection=False,  # KEY DIFFERENCE
            regulatory_categories=3,  # Only 3 categories
        )

    @classmethod
    def v3_1_2(cls) -> "VersionConfig":
        """Configuration for v3.1.2 calculation (current/recommended)."""
        return cls(
            version=CalculationVersion.V3_1_2,
            apply_exposure_floor=True,
            use_ghs_skin_detection=True,
            regulatory_categories=11,
        )


@dataclass
class RegulatoryResult:
    """Result of regulatory substance check."""

    # v3.0.2 categories (always included)
    skin_hazard: bool = False
    carcinogen: bool = False
    concentration_standard: bool = False
    risk_level_s: bool = False  # Skin notation in OEL

    # v3.1.2 additional categories
    tokka_class1: bool = False  # 特定化学物質 第1類
    tokka_class2: bool = False  # 特定化学物質 第2類
    tokka_class3: bool = False  # 特定化学物質 第3類
    organic_class1: bool = False  # 第1種有機溶剤
    organic_class2: bool = False  # 第2種有機溶剤
    organic_class3: bool = False  # 第3種有機溶剤
    lead: bool = False  # 鉛等
    tetraalkyl_lead: bool = False  # 四アルキル鉛等

    # Detection details
    skin_hazard_from_ghs: bool = False  # True if detected via GHS (v3.1.2 only)
    cutoff_applied: dict = field(default_factory=dict)

    def to_list_v302(self) -> list[str]:
        """Return regulatory substances as v3.0.2 format (4 elements max)."""
        result = []
        if self.skin_hazard:
            result.append("皮膚等障害化学物質")
        if self.carcinogen:
            result.append("がん原性物質")
        if self.concentration_standard:
            result.append("濃度基準値設定物質")
        if self.risk_level_s:
            result.append("リスクレベルS")
        return result

    def to_list_v312(self) -> list[str]:
        """Return regulatory substances as v3.1.2 format (12 elements max)."""
        result = []
        if self.tokka_class1:
            result.append("特定化学物質（第1類物質）")
        if self.tokka_class2:
            result.append("特定化学物質（第2類物質）")
        if self.tokka_class3:
            result.append("特定化学物質（第3類物質）")
        if self.organic_class1:
            result.append("第1種有機溶剤")
        if self.organic_class2:
            result.append("第2種有機溶剤")
        if self.organic_class3:
            result.append("第3種有機溶剤")
        if self.lead:
            result.append("鉛等")
        if self.tetraalkyl_lead:
            result.append("四アルキル鉛等")
        if self.skin_hazard:
            result.append("皮膚等障害化学物質")
        if self.carcinogen:
            result.append("がん原性物質")
        if self.concentration_standard:
            result.append("濃度基準値設定物質")
        if self.risk_level_s:
            result.append("リスクレベルS")
        return result


@dataclass
class ExposureResult:
    """Result of exposure calculation."""

    exposure_8hr: float
    exposure_stel: float
    unit: str  # "ppm" or "mg/m³"

    # Floor application tracking
    floor_applied_8hr: bool = False
    floor_applied_stel: bool = False
    floor_value: Optional[float] = None

    # Calculation details
    initial_band: float = 0.0
    coefficients: dict = field(default_factory=dict)


class VersionCalculator:
    """
    Version-specific calculator for CREATE-SIMPLE methodology.

    Usage:
        # For v3.0.2 calculation (no floor)
        calc = VersionCalculator(VersionConfig.v3_0_2())
        result = calc.calculate_exposure(...)

        # For v3.1.2 calculation (with floor)
        calc = VersionCalculator(VersionConfig.v3_1_2())
        result = calc.calculate_exposure(...)
    """

    def __init__(self, config: VersionConfig):
        self.config = config

    def calculate_exposure(
        self,
        property_type: str,  # "liquid" or "solid"
        volatility_or_dustiness: str,  # "high", "medium", "low", "very_low"
        amount_level: str,  # "large", "medium", "small", "minute", "trace"
        content_percent: float = 100.0,
        ventilation: str = "industrial",
        control_velocity_verified: bool = False,
        is_spray: bool = False,
        working_hours: float = 8.0,
        days_per_week: int = 5,
        apf_coefficient: float = 1.0,
    ) -> ExposureResult:
        """
        Calculate exposure using version-specific logic.

        Key version differences:
        - v3.0.2: No minimum floor applied
        - v3.1.2: Minimum floor of 0.005 ppm (liquid) or 0.001 mg/m³ (solid)
        """
        # Get initial exposure band
        initial_band = self._get_exposure_band(
            property_type, volatility_or_dustiness, amount_level
        )

        # Calculate coefficients
        content_coeff = self._get_content_coefficient(content_percent)
        vent_coeff = self._get_ventilation_coefficient(ventilation, control_velocity_verified)
        spray_coeff = 10.0 if is_spray else 1.0
        time_coeff = self._get_time_coefficient(working_hours, days_per_week)

        # Calculate 8-hour exposure
        exposure_8hr = (
            initial_band
            * content_coeff
            * spray_coeff
            * vent_coeff
            * time_coeff
            * apf_coefficient
        )

        # Calculate STEL exposure
        # For very low volatility without spray, STEL = 8hr
        if volatility_or_dustiness == "very_low" and not is_spray:
            exposure_stel = exposure_8hr
        else:
            # STEL uses exposure variation coefficient instead of time coefficient
            exposure_variation_coeff = 3.0  # Standard variation factor
            exposure_stel = (
                initial_band
                * content_coeff
                * spray_coeff
                * vent_coeff
                * exposure_variation_coeff
                * apf_coefficient
            )

        # Round to 2 significant figures
        exposure_8hr = self._round_significant(exposure_8hr, 2)
        exposure_stel = self._round_significant(exposure_stel, 2)

        # Determine unit
        unit = "ppm" if property_type == "liquid" else "mg/m³"

        # Apply floor (v3.1.2 only)
        floor_applied_8hr = False
        floor_applied_stel = False
        floor_value = None

        if self.config.apply_exposure_floor:
            if property_type == "liquid":
                floor_value = self.config.floor_liquid_ppm
                if exposure_8hr < floor_value:
                    exposure_8hr = floor_value
                    floor_applied_8hr = True
                if exposure_stel < floor_value:
                    exposure_stel = floor_value
                    floor_applied_stel = True
            else:  # solid
                floor_value = self.config.floor_solid_mg_m3
                if exposure_8hr < floor_value:
                    exposure_8hr = floor_value
                    floor_applied_8hr = True
                if exposure_stel < floor_value:
                    exposure_stel = floor_value
                    floor_applied_stel = True

        # Apply maximum cap (5000 for both versions)
        max_exposure = 5000.0
        exposure_8hr = min(exposure_8hr, max_exposure)
        exposure_stel = min(exposure_stel, max_exposure)

        return ExposureResult(
            exposure_8hr=exposure_8hr,
            exposure_stel=exposure_stel,
            unit=unit,
            floor_applied_8hr=floor_applied_8hr,
            floor_applied_stel=floor_applied_stel,
            floor_value=floor_value,
            initial_band=initial_band,
            coefficients={
                "content": content_coeff,
                "ventilation": vent_coeff,
                "spray": spray_coeff,
                "time": time_coeff,
                "apf": apf_coefficient,
            },
        )

    def check_regulatory(
        self,
        substance_flags: dict,  # From database
        ghs_classification: Optional[dict] = None,  # GHS data
        content_percent: float = 100.0,
    ) -> RegulatoryResult:
        """
        Check regulatory substance classification using version-specific logic.

        Key version differences:
        - v3.0.2: Only 3 categories, no GHS-based skin detection
        - v3.1.2: 11 categories with cutoffs + GHS-based skin detection

        Args:
            substance_flags: Database flags for regulatory substances
            ghs_classification: GHS classification dict (optional, used in v3.1.2)
            content_percent: Content percentage for cutoff comparison
        """
        result = RegulatoryResult()

        # v3.0.2 logic: Simple database flag check
        if self.config.version == CalculationVersion.V3_0_2:
            result.skin_hazard = substance_flags.get("is_skin_hazard", False)
            result.carcinogen = substance_flags.get("is_carcinogen", False)
            result.concentration_standard = substance_flags.get("is_conc_standard", False)

            # Risk level S from OEL skin notation
            if (substance_flags.get("skin_corr_irrit") or
                substance_flags.get("eye_damage") or
                substance_flags.get("skin_sens")):
                result.risk_level_s = True

            return result

        # v3.1.2 logic: Extended categories with cutoffs and GHS detection

        # Get thresholds (use substance-specific if available, else defaults)
        skin_cutoff = substance_flags.get("skin_hazard_threshold", self.config.skin_hazard_cutoff)
        tokka_cutoff = substance_flags.get("tokka_threshold", self.config.tokka_cutoff)
        organic_cutoff = self.config.organic_cutoff

        result.cutoff_applied = {
            "skin_hazard": skin_cutoff,
            "tokka": tokka_cutoff,
            "organic": organic_cutoff,
        }

        # 特化則 (Specified Chemical Substances) - with cutoff
        if content_percent > tokka_cutoff:
            result.tokka_class1 = substance_flags.get("tokka_class1", False)
            result.tokka_class2 = substance_flags.get("tokka_class2", False)
            result.tokka_class3 = substance_flags.get("tokka_class3", False)

        # 有機則 (Organic Solvents) - with cutoff
        if content_percent > organic_cutoff:
            result.organic_class1 = substance_flags.get("organic_class1", False)
            result.organic_class2 = substance_flags.get("organic_class2", False)
            result.organic_class3 = substance_flags.get("organic_class3", False)

        # 鉛則 (Lead) - no cutoff
        result.lead = substance_flags.get("lead_regulation", False)
        result.tetraalkyl_lead = substance_flags.get("tetraalkyl_lead", False)

        # 皮膚等障害化学物質 (Skin Hazard) - with cutoff + GHS detection
        db_skin_flag = substance_flags.get("is_skin_hazard", False)
        ghs_skin_flag = False

        if self.config.use_ghs_skin_detection and ghs_classification:
            ghs_skin_flag = self._check_ghs_skin_hazard(ghs_classification)
            result.skin_hazard_from_ghs = ghs_skin_flag

        # Apply skin hazard if database says "1" OR GHS indicates hazard
        # But NOT if database explicitly says "0" (override)
        if content_percent >= skin_cutoff:
            if db_skin_flag or (ghs_skin_flag and substance_flags.get("is_skin_hazard") != "0"):
                result.skin_hazard = True

        # がん原性物質 (Carcinogen) - no cutoff
        result.carcinogen = substance_flags.get("is_carcinogen", False)

        # 濃度基準値設定物質 (Concentration Standard) - no cutoff
        result.concentration_standard = substance_flags.get("is_conc_standard", False)

        # Risk level S
        if (substance_flags.get("skin_corr_irrit") or
            substance_flags.get("eye_damage") or
            substance_flags.get("skin_sens")):
            result.risk_level_s = True

        return result

    def _check_ghs_skin_hazard(self, ghs: dict) -> bool:
        """
        Check if GHS classification indicates skin hazard.

        Reference: v3.1.2 modCalc.bas lines 700-711

        Categories that trigger skin hazard flag:
        - Skin corrosion/irritation: 1A, 1B, 1C, 1
        - Eye damage: 1
        - Respiratory sensitization: 1, 1A, 1B
        - Skin sensitization: 1, 1A, 1B
        """
        skin_corr = ghs.get("skin_corr_irrit", "")
        eye_damage = ghs.get("eye_damage", "")
        resp_sens = ghs.get("resp_sens", "")
        skin_sens = ghs.get("skin_sens", "")

        if skin_corr in ("1A", "1B", "1C", "1"):
            return True
        if eye_damage == "1":
            return True
        if resp_sens in ("1", "1A", "1B"):
            return True
        if skin_sens in ("1", "1A", "1B"):
            return True

        return False

    def _get_exposure_band(
        self,
        property_type: str,
        volatility_or_dustiness: str,
        amount_level: str,
    ) -> float:
        """Get base exposure band from lookup tables."""
        # Use string keys directly (tables use string tuples)
        key = (volatility_or_dustiness, amount_level)

        if property_type == "liquid":
            return EXPOSURE_BANDS_LIQUID.get(key, 500.0)
        else:
            return EXPOSURE_BANDS_SOLID.get(key, 10.0)

    def _get_content_coefficient(self, content_percent: float) -> float:
        """Get content coefficient based on percentage."""
        for threshold, coeff in CONTENT_COEFFICIENTS:
            if content_percent >= threshold:
                return coeff
        return 0.1

    def _get_ventilation_coefficient(
        self,
        ventilation: str,
        control_velocity_verified: bool = False,
    ) -> float:
        """Get ventilation coefficient."""
        # Use tuple key (ventilation, verified)
        key = (ventilation, control_velocity_verified)
        return VENTILATION_COEFFICIENTS.get(key, 1.0)

    def _get_time_coefficient(
        self,
        working_hours: float,
        days_per_week: int,
    ) -> float:
        """Calculate time coefficient based on working duration."""
        # Hours coefficient (linear based on 8hr reference)
        hours_coeff = working_hours / 8.0

        # Days coefficient (linear based on 5 days reference)
        days_coeff = days_per_week / 5.0

        return hours_coeff * days_coeff

    def _round_significant(self, value: float, digits: int) -> float:
        """Round to significant figures."""
        if value == 0:
            return 0
        import math
        magnitude = math.floor(math.log10(abs(value)))
        return round(value, -int(magnitude) + (digits - 1))


def compare_versions(
    property_type: str,
    volatility_or_dustiness: str,
    amount_level: str,
    oel: float,
    content_percent: float = 100.0,
    ventilation: str = "industrial",
    control_velocity_verified: bool = False,
    is_spray: bool = False,
    working_hours: float = 8.0,
    days_per_week: int = 5,
    apf_coefficient: float = 1.0,
    substance_flags: Optional[dict] = None,
    ghs_classification: Optional[dict] = None,
) -> dict:
    """
    Compare calculation results between v3.0.2 and v3.1.2.

    Returns a comprehensive comparison showing differences in:
    - Exposure values (8hr and STEL)
    - RCR values
    - Risk levels
    - Regulatory detection
    - Floor application
    """
    # Create calculators
    calc_302 = VersionCalculator(VersionConfig.v3_0_2())
    calc_312 = VersionCalculator(VersionConfig.v3_1_2())

    # Calculate exposure for both versions
    exp_302 = calc_302.calculate_exposure(
        property_type=property_type,
        volatility_or_dustiness=volatility_or_dustiness,
        amount_level=amount_level,
        content_percent=content_percent,
        ventilation=ventilation,
        control_velocity_verified=control_velocity_verified,
        is_spray=is_spray,
        working_hours=working_hours,
        days_per_week=days_per_week,
        apf_coefficient=apf_coefficient,
    )

    exp_312 = calc_312.calculate_exposure(
        property_type=property_type,
        volatility_or_dustiness=volatility_or_dustiness,
        amount_level=amount_level,
        content_percent=content_percent,
        ventilation=ventilation,
        control_velocity_verified=control_velocity_verified,
        is_spray=is_spray,
        working_hours=working_hours,
        days_per_week=days_per_week,
        apf_coefficient=apf_coefficient,
    )

    # Calculate RCR
    evaluation_standard = oel if oel > 0 else 500.0
    rcr_302 = exp_302.exposure_8hr / evaluation_standard
    rcr_312 = exp_312.exposure_8hr / evaluation_standard

    # Determine risk levels
    def get_risk_level(rcr: float) -> str:
        if rcr <= 0.1:
            return "I"
        elif rcr <= 0.5:
            return "II-A"
        elif rcr <= 1.0:
            return "II-B"
        elif rcr <= 10.0:
            return "III"
        else:
            return "IV"

    risk_302 = get_risk_level(rcr_302)
    risk_312 = get_risk_level(rcr_312)

    # Check regulatory if flags provided
    reg_302 = None
    reg_312 = None
    if substance_flags:
        reg_302 = calc_302.check_regulatory(substance_flags, None, content_percent)
        reg_312 = calc_312.check_regulatory(substance_flags, ghs_classification, content_percent)

    # Build comparison result
    result = {
        "v3_0_2": {
            "version": "v3.0.2 (CREATE-SIMPLE)",
            "exposure_8hr": exp_302.exposure_8hr,
            "exposure_stel": exp_302.exposure_stel,
            "unit": exp_302.unit,
            "rcr": round(rcr_302, 4),
            "risk_level": risk_302,
            "floor_applied": False,
            "features": [
                "8時間TWA",
                "短時間STEL",
                "経皮吸収",
                "物理的危険性",
            ],
            "regulatory_categories": 3,
        },
        "v3_1_2": {
            "version": "v3.1.2 (CREATE-SIMPLE 最新版)",
            "exposure_8hr": exp_312.exposure_8hr,
            "exposure_stel": exp_312.exposure_stel,
            "unit": exp_312.unit,
            "rcr": round(rcr_312, 4),
            "risk_level": risk_312,
            "floor_applied": exp_312.floor_applied_8hr,
            "floor_value": exp_312.floor_value,
            "recommended": True,
            "features": [
                "8時間TWA",
                "短時間STEL",
                "経皮吸収",
                "物理的危険性",
                "ばく露下限値 (exposure floor)",
                "GHS皮膚障害検出",
            ],
            "regulatory_categories": 11,
        },
        "comparison": {
            "exposure_differs": exp_302.exposure_8hr != exp_312.exposure_8hr,
            "exposure_difference_pct": round(
                (exp_312.exposure_8hr - exp_302.exposure_8hr) / exp_302.exposure_8hr * 100
                if exp_302.exposure_8hr > 0 else 0,
                2
            ),
            "rcr_differs": rcr_302 != rcr_312,
            "risk_level_differs": risk_302 != risk_312,
            "floor_caused_difference": exp_312.floor_applied_8hr,
        },
    }

    # Add regulatory comparison if available
    if reg_302 and reg_312:
        result["v3_0_2"]["regulatory"] = reg_302.to_list_v302()
        result["v3_1_2"]["regulatory"] = reg_312.to_list_v312()
        result["comparison"]["regulatory_differs"] = (
            reg_302.to_list_v302() != reg_312.to_list_v312()[:4]  # Compare first 4 for v3.0.2
        )
        if reg_312.skin_hazard_from_ghs:
            result["comparison"]["ghs_skin_detection"] = True

    return result
