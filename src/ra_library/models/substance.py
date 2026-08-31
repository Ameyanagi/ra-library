"""
Chemical substance data models.

References:
- CREATE-SIMPLE Design Document v3.1.1, Section 2
- GHS (Globally Harmonized System) Rev.9
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class PropertyType(str, Enum):
    """Physical state of the substance."""

    LIQUID = "liquid"  # 液体
    SOLID = "solid"  # 固体（粉体）
    GAS = "gas"  # 気体


class VolatilityLevel(str, Enum):
    """
    Volatility classification for liquids.

    Reference: CREATE-SIMPLE Design v3.1.1, Section 3.2
    Based on vapor pressure and boiling point.
    """

    VERY_HIGH = "very_high"  # 揮発性極高: BP < 50°C or VP > 25000 Pa
    HIGH = "high"  # 揮発性高: 50°C ≤ BP < 150°C or 500 < VP ≤ 25000 Pa
    MEDIUM = "medium"  # 揮発性中: 150°C ≤ BP < 250°C or 10 < VP ≤ 500 Pa
    LOW = "low"  # 揮発性低: BP ≥ 250°C or VP ≤ 10 Pa


class DustinessLevel(str, Enum):
    """
    Dustiness classification for solids.

    Reference: CREATE-SIMPLE Design v3.1.1, Section 3.2
    """

    HIGH = "high"  # 飛散性高: Fine powder, easily airborne
    MEDIUM = "medium"  # 飛散性中: Crystalline, granular
    LOW = "low"  # 飛散性低: Pellets, flakes, waxy


class GHSClassification(BaseModel):
    """
    GHS hazard classification.

    Reference: CREATE-SIMPLE Design v3.1.1, Section 2.2
    """

    # Health hazards
    acute_toxicity_oral: Optional[str] = None  # 急性毒性（経口）
    acute_toxicity_dermal: Optional[str] = None  # 急性毒性（経皮）
    acute_toxicity_inhalation_gas: Optional[str] = None  # 急性毒性（吸入：ガス）
    acute_toxicity_inhalation_vapor: Optional[str] = None  # 急性毒性（吸入：蒸気）
    acute_toxicity_inhalation_dust: Optional[str] = None  # 急性毒性（吸入：粉じん）
    skin_corrosion: Optional[str] = None  # 皮膚腐食性/刺激性
    eye_damage: Optional[str] = None  # 眼損傷性/刺激性
    respiratory_sensitization: Optional[str] = None  # 呼吸器感作性
    skin_sensitization: Optional[str] = None  # 皮膚感作性
    germ_cell_mutagenicity: Optional[str] = None  # 生殖細胞変異原性
    carcinogenicity: Optional[str] = None  # 発がん性
    reproductive_toxicity: Optional[str] = None  # 生殖毒性
    stot_single: Optional[str] = None  # 特定標的臓器毒性（単回）
    stot_repeated: Optional[str] = None  # 特定標的臓器毒性（反復）
    aspiration_hazard: Optional[str] = None  # 誤えん有害性

    # Physical hazards
    flammable_gases: Optional[str] = None  # 可燃性ガス
    flammable_aerosols: Optional[str] = None  # エアゾール
    oxidizing_gases: Optional[str] = None  # 酸化性ガス
    gases_under_pressure: Optional[str] = None  # 高圧ガス
    flammable_liquids: Optional[str] = None  # 引火性液体
    flammable_solids: Optional[str] = None  # 可燃性固体
    self_reactive: Optional[str] = None  # 自己反応性
    pyrophoric_liquids: Optional[str] = None  # 自然発火性液体
    pyrophoric_solids: Optional[str] = None  # 自然発火性固体
    self_heating: Optional[str] = None  # 自己発熱性
    water_reactive: Optional[str] = None  # 水反応可燃性
    oxidizing_liquids: Optional[str] = None  # 酸化性液体
    oxidizing_solids: Optional[str] = None  # 酸化性固体
    organic_peroxides: Optional[str] = None  # 有機過酸化物
    corrosive_to_metals: Optional[str] = None  # 金属腐食性
    explosives: Optional[str] = None  # 爆発物

    @staticmethod
    def _category(val: Optional[str]) -> Optional[str]:
        """Normalize workbook and API category spellings."""
        if val is None:
            return None
        category = val.strip().upper()
        if not category or category == "-9999":
            return None
        if category.startswith("CATEGORY "):
            category = category.removeprefix("CATEGORY ").strip()
        if category.startswith("区分"):
            category = category.removeprefix("区分").strip()
        return category

    @classmethod
    def _is_category(cls, val: Optional[str], *categories: str) -> bool:
        """Return whether *val* is one of the normalized GHS categories."""
        return cls._category(val) in categories

    @classmethod
    def _is_unavailable(cls, val: Optional[str]) -> bool:
        """Match CREATE-SIMPLE's ``-9999`` unavailable-route sentinel."""
        return cls._category(val) is None

    def get_hazard_level(self) -> str:
        """
        Get hazard level (HL1-HL5) based on GHS classification.

        Reference: CREATE-SIMPLE Design v3.1.1, Section 2.2
        VBA Reference: modCalc.bas lines 231-277 (CalculateACRMax)
        """
        # Acute-toxicity inhalation routes are checked exactly as in the workbook.  Oral
        # toxicity is used only when at least one inhalation route is unavailable.  Acute
        # dermal toxicity is deliberately not part of CalculateACRMax in CREATE-SIMPLE v3.
        acute_inhal = [
            self.acute_toxicity_inhalation_gas,
            self.acute_toxicity_inhalation_vapor,
            self.acute_toxicity_inhalation_dust,
        ]
        any_inhalation_unavailable = any(self._is_unavailable(cat) for cat in acute_inhal)

        # HL5
        if (
            (self._is_category(self.acute_toxicity_oral, "1") and any_inhalation_unavailable)
            or any(self._is_category(cat, "1") for cat in acute_inhal)
            or self._is_category(self.germ_cell_mutagenicity, "1", "1A", "1B")
            or self._is_category(self.carcinogenicity, "1", "1A", "1B")
        ):
            return "HL5"

        # HL4
        if (
            (self._is_category(self.acute_toxicity_oral, "2") and any_inhalation_unavailable)
            or any(self._is_category(cat, "2") for cat in acute_inhal)
            or self._is_category(self.skin_corrosion, "1A")
            or self._is_category(self.respiratory_sensitization, "1", "1A", "1B")
            or self._is_category(self.germ_cell_mutagenicity, "2", "2A", "2B")
            or self._is_category(self.carcinogenicity, "2", "2A", "2B")
            or self._is_category(self.reproductive_toxicity, "1", "1A", "1B")
            or self._is_category(self.stot_repeated, "1")
        ):
            return "HL4"

        # HL3
        if (
            (self._is_category(self.acute_toxicity_oral, "3") and any_inhalation_unavailable)
            or any(self._is_category(cat, "3") for cat in acute_inhal)
            or self._is_category(self.skin_corrosion, "1", "1B", "1C")
            or self._is_category(self.eye_damage, "1")
            or self._is_category(self.skin_sensitization, "1", "1A", "1B")
            or self._is_category(self.reproductive_toxicity, "2")
            or self._is_category(self.stot_single, "1")
            or self._is_category(self.stot_repeated, "2")
        ):
            return "HL3"

        # HL2
        if (
            (self._is_category(self.acute_toxicity_oral, "4") and any_inhalation_unavailable)
            or any(self._is_category(cat, "4") for cat in acute_inhal)
            or self._is_category(self.skin_corrosion, "2")
            or self._is_category(self.eye_damage, "2")
            or self._is_category(self.stot_single, "2", "3")
        ):
            return "HL2"

        # HL1: No significant health hazards
        return "HL1"

    def should_apply_acrmax(self) -> bool:
        """
        Determine if ACRmax should be applied for this substance.

        CREATE-SIMPLE derives an ACRmax for every HL1-HL5 classification and uses it
        whenever an occupational exposure limit is unavailable.

        Reference: CREATE-SIMPLE Design v3.1.1, Section 5.3.3

        Returns:
            True if ACRmax should be applied, False otherwise
        """
        return True

    def get_acrmax_hazard_level(self) -> Optional[str]:
        """
        Get the hazard level to use for ACRmax lookup, if applicable.

        Compatibility alias for the full CREATE-SIMPLE GHS hazard level.

        Returns:
            Hazard level string ("HL1" through "HL5") for ACRmax lookup
        """
        return self.get_hazard_level()


class OccupationalExposureLimits(BaseModel):
    """
    Occupational Exposure Limits (OEL) from various sources.

    Priority order for selection (matches VBA oelSourceSelection):
    1. 濃度基準値 (Concentration Standard - Japan)
    2. 許容濃度 (JSOH Permissible Concentration)
    3. TLV-TWA (ACGIH)
    4. DFG MAK (Germany)
    5. DNEL (Derived No-Effect Level)
    6. Other

    Reference: CREATE-SIMPLE Design v3.1.1, Section 2.1
    VBA Reference: modCalc.bas lines 96-142 (SelectOEL8hour)
    """

    # Japanese regulatory values (highest priority)
    concentration_standard_8hr: Optional[float] = Field(
        None, description="濃度基準値 8時間TWA (ppm or mg/m³)"
    )
    concentration_standard_8hr_unit: Optional[str] = None
    concentration_standard_stel: Optional[float] = Field(
        None, description="濃度基準値 短時間 (ppm or mg/m³)"
    )
    concentration_standard_stel_unit: Optional[str] = None

    # JSOH values
    jsoh_8hr: Optional[float] = Field(None, description="許容濃度 (ppm or mg/m³)")
    jsoh_8hr_unit: Optional[str] = None

    # ACGIH values
    acgih_tlv_twa: Optional[float] = Field(None, description="TLV-TWA (ppm or mg/m³)")
    acgih_tlv_twa_unit: Optional[str] = None
    acgih_tlv_stel: Optional[float] = Field(None, description="TLV-STEL (ppm or mg/m³)")
    acgih_tlv_stel_unit: Optional[str] = None

    # DFG MAK values (Germany) - VBA: oelSourceSelection = 4
    dfg_mak: Optional[float] = Field(None, description="DFG MAK (ppm or mg/m³)")
    dfg_mak_unit: Optional[str] = None

    # DNEL
    dnel_worker_inhalation: Optional[float] = Field(
        None, description="DNEL Worker Inhalation (mg/m³)"
    )

    # Other sources
    other_8hr: Optional[float] = None
    other_8hr_unit: Optional[str] = None
    other_stel: Optional[float] = None
    other_stel_unit: Optional[str] = None

    # Skin notation - indicates significant potential for skin absorption
    skin_notation: bool = Field(
        False,
        description="Skin notation (経皮吸収注意) - significant potential for skin absorption",
    )

    def get_primary_oel(self) -> tuple[Optional[float], Optional[str]]:
        """
        Get the primary OEL value following priority order.

        VBA Reference: modCalc.bas lines 96-142 (SelectOEL8hour)

        Returns:
            Tuple of (value, unit) or (None, None) if no OEL available
        """
        # Priority 1: Concentration Standard (濃度基準値)
        if self.concentration_standard_8hr is not None:
            return (self.concentration_standard_8hr, self.concentration_standard_8hr_unit)

        # Priority 2: JSOH (許容濃度)
        if self.jsoh_8hr is not None:
            return (self.jsoh_8hr, self.jsoh_8hr_unit)

        # Priority 3: ACGIH TLV-TWA
        if self.acgih_tlv_twa is not None:
            return (self.acgih_tlv_twa, self.acgih_tlv_twa_unit)

        # Priority 4: DFG MAK (Germany)
        if self.dfg_mak is not None:
            return (self.dfg_mak, self.dfg_mak_unit)

        # Priority 5: DNEL
        if self.dnel_worker_inhalation is not None:
            return (self.dnel_worker_inhalation, "mg/m³")

        # Priority 6: Other
        if self.other_8hr is not None:
            return (self.other_8hr, self.other_8hr_unit)

        return (None, None)


class PhysicochemicalProperties(BaseModel):
    """
    Physicochemical properties of a substance.

    Reference: CREATE-SIMPLE Design v3.1.1, Section 3.1 & 4.3
    """

    molecular_weight: Optional[float] = Field(None, description="Molecular weight (g/mol)")
    boiling_point: Optional[float] = Field(None, description="Boiling point (°C)")
    vapor_pressure: Optional[float] = Field(None, description="Vapor pressure (Pa)")
    vapor_pressure_unit: Optional[str] = None
    log_kow: Optional[float] = Field(None, description="Log octanol-water partition coefficient")
    flash_point: Optional[float] = Field(None, description="Flash point (°C)")
    water_solubility: Optional[float] = Field(None, description="Water solubility (mg/L)")
    water_solubility_unit: Optional[str] = None
    density: Optional[float] = Field(None, description="Density (g/cm³)")

    def get_volatility_level(self) -> VolatilityLevel:
        """
        Determine volatility level from boiling point or vapor pressure.

        Reference: CREATE-SIMPLE Design v3.1.1, Section 3.2
        """
        # Check vapor pressure first (more reliable)
        if self.vapor_pressure is not None:
            vp = self.vapor_pressure
            if vp > 25000:
                return VolatilityLevel.VERY_HIGH
            elif vp > 500:
                return VolatilityLevel.HIGH
            elif vp > 10:
                return VolatilityLevel.MEDIUM
            else:
                return VolatilityLevel.LOW

        # Fall back to boiling point
        if self.boiling_point is not None:
            bp = self.boiling_point
            if bp < 50:
                return VolatilityLevel.VERY_HIGH
            elif bp < 150:
                return VolatilityLevel.HIGH
            elif bp < 250:
                return VolatilityLevel.MEDIUM
            else:
                return VolatilityLevel.LOW

        # Default to medium if unknown
        return VolatilityLevel.MEDIUM


class Substance(BaseModel):
    """Complete substance data model."""

    cas_number: str
    name_ja: str
    name_en: Optional[str] = None
    property_type: PropertyType
    ghs: GHSClassification = Field(default_factory=GHSClassification)
    oel: OccupationalExposureLimits = Field(default_factory=OccupationalExposureLimits)
    properties: PhysicochemicalProperties = Field(default_factory=PhysicochemicalProperties)

    # Regulatory status
    is_concentration_standard_substance: bool = False  # 濃度基準値設定物質
    is_skin_hazard_substance: bool = False  # 皮膚等障害化学物質
    is_carcinogen: bool = False  # がん原性物質

    def get_hazard_level(self) -> str:
        """Get hazard level (HL1-HL5)."""
        return self.ghs.get_hazard_level()

    def get_volatility(self) -> VolatilityLevel:
        """Get volatility level for liquids and gases."""
        if self.property_type == PropertyType.GAS:
            return VolatilityLevel.HIGH
        if self.property_type != PropertyType.LIQUID:
            raise ValueError("Volatility is only applicable to liquids and gases")
        return self.properties.get_volatility_level()
