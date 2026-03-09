"""
Risk level and result models.

References:
- CREATE-SIMPLE Design Document v3.1.1, Section 5
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import IntEnum

from .explanation import CalculationExplanation, Limitation
from .recommendation import Recommendation


class RiskLevel(IntEnum):
    """
    Risk level classification (4 levels).

    Reference: CREATE-SIMPLE Design v3.1.1, Section 5.3
    """

    I = 1  # noqa: E741 - Roman numeral for risk level
    II = 2  # 0.1 < RCR ≤ 1 - Monitor
    III = 3  # 1 < RCR ≤ 10 - Action needed
    IV = 4  # RCR > 10 - Immediate action

    @classmethod
    def from_rcr(cls, rcr: float) -> "RiskLevel":
        """Get risk level from RCR value."""
        if rcr <= 0.1:
            return cls.I
        elif rcr <= 1.0:
            return cls.II
        elif rcr <= 10.0:
            return cls.III
        else:
            return cls.IV

    def get_color(self) -> str:
        """Get display color for risk level."""
        colors = {
            RiskLevel.I: "green",
            RiskLevel.II: "yellow",
            RiskLevel.III: "orange",
            RiskLevel.IV: "red",
        }
        return colors[self]

    def get_action_required(self) -> str:
        """Get action requirement description."""
        actions = {
            RiskLevel.I: "Acceptable - maintain current controls",
            RiskLevel.II: "Monitor - consider improvements",
            RiskLevel.III: "Action needed - implement controls",
            RiskLevel.IV: "Immediate action required",
        }
        return actions[self]

    def get_action_required_ja(self) -> str:
        """Get action requirement in Japanese."""
        actions = {
            RiskLevel.I: "許容可能 - 現在の管理を維持",
            RiskLevel.II: "監視必要 - 改善を検討",
            RiskLevel.III: "対策必要 - 管理措置を実施",
            RiskLevel.IV: "直ちに対策が必要",
        }
        return actions[self]

    @staticmethod
    def get_detailed_label(rcr: float) -> str:
        """
        Get detailed risk level label including II-A/II-B subdivision.

        Reference: CREATE-SIMPLE Design v3.1.1
        - Level I: RCR ≤ 0.1
        - Level II-A: 0.1 < RCR ≤ 0.5
        - Level II-B: 0.5 < RCR ≤ 1.0
        - Level III: 1.0 < RCR ≤ 10.0
        - Level IV: RCR > 10.0
        """
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

    @staticmethod
    def get_simple_label(rcr: float) -> str:
        """
        Get simple risk level label (I, II, III, IV) without II-A/II-B subdivision.

        Used for STEL (Short-Term Exposure Limit) which uses simple 4-level scale.

        Reference: CREATE-SIMPLE VBA modCalc.bas DetermineRiskLevelInhalationShortTerm
        - Level I: RCR ≤ 0.1
        - Level II: 0.1 < RCR ≤ 1.0
        - Level III: 1.0 < RCR ≤ 10.0
        - Level IV: RCR > 10.0
        """
        if rcr <= 0.1:
            return "I"
        elif rcr <= 1.0:
            return "II"
        elif rcr <= 10.0:
            return "III"
        else:
            return "IV"


class DetailedRiskLevel(IntEnum):
    """
    Detailed risk level classification (5 levels, distinguishing II-A and II-B).

    Reference: CREATE-SIMPLE Design v3.1.1, Section 5.3

    RCR thresholds:
    - Level I: RCR ≤ 0.1
    - Level II-A: 0.1 < RCR ≤ 0.5
    - Level II-B: 0.5 < RCR ≤ 1.0
    - Level III: 1.0 < RCR ≤ 10.0
    - Level IV: RCR > 10.0
    """

    I = 1  # noqa: E741 - RCR ≤ 0.1
    II_A = 2  # 0.1 < RCR ≤ 0.5
    II_B = 3  # 0.5 < RCR ≤ 1.0
    III = 4  # 1.0 < RCR ≤ 10.0
    IV = 5  # RCR > 10.0

    @classmethod
    def from_rcr(cls, rcr: float) -> "DetailedRiskLevel":
        """Get detailed risk level from RCR value."""
        if rcr <= 0.1:
            return cls.I
        elif rcr <= 0.5:
            return cls.II_A
        elif rcr <= 1.0:
            return cls.II_B
        elif rcr <= 10.0:
            return cls.III
        else:
            return cls.IV

    def to_basic_level(self) -> RiskLevel:
        """Convert to basic 4-level RiskLevel."""
        if self == DetailedRiskLevel.I:
            return RiskLevel.I
        elif self in (DetailedRiskLevel.II_A, DetailedRiskLevel.II_B):
            return RiskLevel.II
        elif self == DetailedRiskLevel.III:
            return RiskLevel.III
        else:
            return RiskLevel.IV

    def get_rcr_threshold(self) -> float:
        """Get the RCR threshold for this level (max RCR to achieve this level)."""
        thresholds = {
            DetailedRiskLevel.I: 0.1,
            DetailedRiskLevel.II_A: 0.5,
            DetailedRiskLevel.II_B: 1.0,
            DetailedRiskLevel.III: 10.0,
            DetailedRiskLevel.IV: float("inf"),
        }
        return thresholds[self]

    def get_label(self) -> str:
        """Get display label."""
        labels = {
            DetailedRiskLevel.I: "I",
            DetailedRiskLevel.II_A: "II-A",
            DetailedRiskLevel.II_B: "II-B",
            DetailedRiskLevel.III: "III",
            DetailedRiskLevel.IV: "IV",
        }
        return labels[self]

    def get_color(self) -> str:
        """Get display color for risk level."""
        colors = {
            DetailedRiskLevel.I: "green",
            DetailedRiskLevel.II_A: "yellow",
            DetailedRiskLevel.II_B: "yellow",
            DetailedRiskLevel.III: "orange",
            DetailedRiskLevel.IV: "red",
        }
        return colors[self]

    def get_action_required(self) -> str:
        """Get action requirement description."""
        actions = {
            DetailedRiskLevel.I: "Acceptable - maintain current controls",
            DetailedRiskLevel.II_A: "Low concern - monitor periodically",
            DetailedRiskLevel.II_B: "Moderate concern - consider improvements",
            DetailedRiskLevel.III: "Action needed - implement controls",
            DetailedRiskLevel.IV: "Immediate action required",
        }
        return actions[self]

    def get_action_required_ja(self) -> str:
        """Get action requirement in Japanese."""
        actions = {
            DetailedRiskLevel.I: "許容可能 - 現在の管理を維持",
            DetailedRiskLevel.II_A: "低リスク - 定期的に監視",
            DetailedRiskLevel.II_B: "中リスク - 改善を検討",
            DetailedRiskLevel.III: "対策必要 - 管理措置を実施",
            DetailedRiskLevel.IV: "直ちに対策が必要",
        }
        return actions[self]


class InhalationRisk(BaseModel):
    """
    Inhalation risk assessment result.

    Reference: CREATE-SIMPLE Design v3.1.1, Section 3 & 5
    """

    exposure_8hr: float = Field(..., description="8-hour TWA exposure max (ppm or mg/m³)")
    exposure_8hr_min: Optional[float] = Field(None, description="8-hour TWA exposure min (max * 0.1)")
    exposure_8hr_unit: str = Field(default="ppm")
    exposure_stel: Optional[float] = Field(None, description="Short-term exposure max")
    exposure_stel_min: Optional[float] = Field(None, description="Short-term exposure min (max * 0.1)")
    exposure_stel_unit: Optional[str] = None

    oel: float = Field(..., description="Occupational Exposure Limit used")
    oel_unit: str = Field(default="ppm")
    oel_source: str = Field(default="", description="Source of OEL value")

    acrmax: Optional[float] = Field(None, description="Management target concentration")
    acrmax_unit: Optional[str] = None

    rcr: float = Field(..., description="Risk Characterization Ratio (8-hour TWA)")
    risk_level: RiskLevel

    # STEL-specific assessment
    stel_oel: Optional[float] = Field(None, description="STEL OEL value (15-min)")
    stel_oel_unit: Optional[str] = None
    stel_oel_source: Optional[str] = None
    stel_rcr: Optional[float] = Field(None, description="STEL Risk Characterization Ratio")
    stel_risk_level: Optional[RiskLevel] = Field(None, description="Risk level based on STEL")

    # Explanation
    explanation: Optional[CalculationExplanation] = None

    # Minimum achievable (engineering controls only, without RPE)
    min_achievable_rcr: Optional[float] = None
    min_achievable_level: Optional[RiskLevel] = None
    min_achievable_reason: Optional[str] = Field(
        None, description="Reason for engineering limit (model_floor, ventilation_constraint)"
    )
    min_achievable_reason_ja: Optional[str] = Field(
        None, description="Japanese explanation of engineering limit reason"
    )
    limitations: List[Limitation] = Field(default_factory=list)

    # Floor tracking - shows what would be achievable without the minimum floor
    exposure_without_floor: Optional[float] = Field(
        None, description="Exposure if minimum floor was not applied"
    )
    rcr_without_floor: Optional[float] = Field(
        None, description="RCR if minimum floor was not applied"
    )
    would_achieve_target_without_floor: bool = Field(
        default=False, description="True if target level would be achieved without floor"
    )


class DermalRisk(BaseModel):
    """
    Dermal risk assessment result.

    Reference: CREATE-SIMPLE Design v3.1.1, Section 4
    Uses Potts-Guy equation for permeability calculation.
    """

    permeability_coefficient: float = Field(..., description="Kp from Potts-Guy equation (cm/hr)")
    dermal_flux: float = Field(..., description="Dermal flux (mg/cm²/hr)")
    skin_absorption: float = Field(..., description="Total absorbed dose (mg)")
    skin_area: float = Field(..., description="Exposed skin area (cm²)")

    dnel_dermal: Optional[float] = Field(None, description="DNEL for dermal (mg/kg/day)")

    rcr: float = Field(..., description="Risk Characterization Ratio")
    risk_level: RiskLevel

    # Explanation
    explanation: Optional[CalculationExplanation] = None

    # Minimum achievable
    min_achievable_rcr: Optional[float] = None
    min_achievable_level: Optional[RiskLevel] = None
    limitations: List[Limitation] = Field(default_factory=list)


class PhysicalRisk(BaseModel):
    """
    Physical hazard risk assessment result.

    Reference: CREATE-SIMPLE Design v3.1.1, Section 7
    """

    hazard_type: str = Field(..., description="Type of physical hazard")
    is_fixed_level_iv: bool = Field(
        default=False, description="True if hazard always results in Level IV"
    )

    flash_point: Optional[float] = None
    process_temperature: Optional[float] = None
    temperature_margin: Optional[float] = None

    risk_level: RiskLevel

    # Explanation
    explanation: Optional[CalculationExplanation] = None

    # Minimum achievable
    min_achievable_level: Optional[RiskLevel] = None
    limitations: List[Limitation] = Field(default_factory=list)
    level_one_achievable: bool = True


class RiskResult(BaseModel):
    """
    Complete risk assessment result.

    Contains all risk types and overall risk level.
    """

    # Individual risk assessments
    inhalation: Optional[InhalationRisk] = None
    dermal: Optional[DermalRisk] = None
    physical: Optional[PhysicalRisk] = None

    # Combined risk level (highest of all assessed)
    overall_risk_level: RiskLevel
    overall_rcr: Optional[float] = None

    # Summary
    primary_risk_type: str = Field(
        default="inhalation", description="Which risk type drives the overall level"
    )

    # Recommendations
    recommendations: List[Recommendation] = Field(default_factory=list)

    # Minimum achievable
    min_achievable_level: Optional[RiskLevel] = None
    limitations: List[Limitation] = Field(default_factory=list)
    level_one_achievable: bool = True
    level_one_path: Optional[str] = None

    def get_summary_ja(self) -> str:
        """Get Japanese summary of the result."""
        level_names = {
            RiskLevel.I: "リスクレベルⅠ",
            RiskLevel.II: "リスクレベルⅡ",
            RiskLevel.III: "リスクレベルⅢ",
            RiskLevel.IV: "リスクレベルⅣ",
        }
        return f"総合評価: {level_names[self.overall_risk_level]}"

    def get_summary_en(self) -> str:
        """Get English summary of the result."""
        return f"Overall: Risk Level {self.overall_risk_level.name}"
