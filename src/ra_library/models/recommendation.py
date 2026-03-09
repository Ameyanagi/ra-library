"""
Recommendation models for risk reduction actions.

These models provide prioritized, actionable recommendations
for reducing risk levels.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

from .reference import Reference


class ActionCategory(str, Enum):
    """Category of risk reduction action."""

    ELIMINATION = "elimination"  # 除去
    SUBSTITUTION = "substitution"  # 代替
    ENGINEERING = "engineering"  # 工学的対策
    ADMINISTRATIVE = "administrative"  # 管理的対策
    PPE = "ppe"  # 保護具


class Feasibility(str, Enum):
    """Feasibility of implementing an action."""

    EASY = "easy"  # Easy to implement, low cost
    MODERATE = "moderate"  # Moderate effort and cost
    DIFFICULT = "difficult"  # Significant effort and cost
    VERY_DIFFICULT = "very_difficult"  # Major investment required


class EffectivenessLevel(str, Enum):
    """Effectiveness of a risk reduction action."""

    HIGH = "high"  # >50% reduction
    MEDIUM = "medium"  # 20-50% reduction
    LOW = "low"  # <20% reduction


# Alias for backwards compatibility
Effectiveness = EffectivenessLevel


class Recommendation(BaseModel):
    """A single risk reduction recommendation."""

    # Basic info
    action: str  # "Install local exhaust ventilation"
    action_ja: str = ""  # Japanese description
    category: ActionCategory
    priority: int = 0  # Lower = higher priority

    # Effectiveness
    effectiveness: EffectivenessLevel
    feasibility: Feasibility

    # Risk impact
    current_risk_level: str  # "I", "II", "III", "IV"
    predicted_risk_level: str  # After action
    current_rcr: Optional[float] = None
    predicted_rcr: Optional[float] = None
    rcr_reduction_percent: float  # Percentage reduction in RCR

    # Parameter changes
    parameter_affected: str  # "ventilation"
    current_value: str  # "industrial"
    new_value: str  # "local_enclosed"
    coefficient_change: str = ""  # "1.0 → 0.01"

    # Implementation guidance
    description: str = ""  # Detailed description
    description_ja: str = ""  # Japanese description
    implementation_notes: str = ""  # How to implement
    implementation_notes_ja: str = ""  # Japanese notes
    cost_estimate: Optional[str] = None  # Cost estimate

    # References
    references: List[Reference] = Field(default_factory=list)


class RecommendationSet(BaseModel):
    """A set of recommendations for reducing risk."""

    # Current and target levels
    current_risk_level: str = ""  # "I", "II", "III", "IV"
    target_risk_level: str = "I"  # Target risk level

    # Is target achievable?
    achievable: bool = True
    best_achievable_level: Optional[str] = None

    # Recommendations sorted by priority
    recommendations: List[Recommendation] = Field(default_factory=list)

    # What if target is not achievable
    limitation_explanation: Optional[str] = None
    limitation_explanation_ja: str = ""
    alternatives: List[str] = Field(default_factory=list)

    def get_top_recommendations(self, n: int = 5) -> List[Recommendation]:
        """Get top N recommendations by effectiveness."""
        sorted_recs = sorted(self.recommendations, key=lambda r: -r.rcr_reduction_percent)
        return sorted_recs[:n]

    def get_recommendations_by_category(self, category: ActionCategory) -> List[Recommendation]:
        """Get recommendations for a specific category."""
        return [r for r in self.recommendations if r.category == category]

    def get_engineering_controls(self) -> List[Recommendation]:
        """Get engineering control recommendations."""
        return self.get_recommendations_by_category(ActionCategory.ENGINEERING)

    def get_ppe_recommendations(self) -> List[Recommendation]:
        """Get PPE recommendations (last resort)."""
        return self.get_recommendations_by_category(ActionCategory.PPE)


class Measure(BaseModel):
    """A single risk reduction measure."""

    category: ActionCategory
    action: str  # "half_mask", "local_enc", "reduce_hours"
    action_label: str  # "Use half-mask respirator"
    action_label_ja: str = ""
    reduction_percent: float  # Individual reduction
    coefficient: float = 1.0  # Multiplier (e.g., 0.1 for 90% reduction)
    feasibility: Feasibility = Feasibility.MODERATE
    cost_estimate: Optional[str] = None  # "low", "medium", "high"


class RiskReductionPath(BaseModel):
    """
    A path (single measure or combination) to reduce risk.

    This represents one way to achieve the target risk level,
    showing what measures are needed and their combined effect.
    """

    path_id: int = 0
    description: str  # "Use half-mask respirator"
    description_ja: str = ""

    # Measures in this path
    measures: List[Measure] = Field(default_factory=list)

    # Combined effect
    combined_reduction_percent: float
    predicted_rcr: float
    predicted_level: str  # "II-A"
    predicted_level_int: int = 0  # Numeric level for sorting

    # Achievement
    achieves_target: bool
    target_level: str = ""
    gap_to_target_percent: float = 0.0  # Remaining reduction needed

    # Implementation
    overall_feasibility: Feasibility = Feasibility.MODERATE
    overall_cost: str = "medium"  # "low", "medium", "high", "very_high"
    implementation_priority: int = 0  # Lower = better option

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "path_id": self.path_id,
            "description": self.description,
            "description_ja": self.description_ja,
            "measures": [
                {
                    "category": m.category.value,
                    "action": m.action,
                    "action_label": m.action_label,
                    "action_label_ja": m.action_label_ja,
                    "reduction_percent": round(m.reduction_percent, 1),
                }
                for m in self.measures
            ],
            "combined_reduction_percent": round(self.combined_reduction_percent, 1),
            "predicted_rcr": round(self.predicted_rcr, 4),
            "predicted_level": self.predicted_level,
            "achieves_target": self.achieves_target,
            "overall_feasibility": self.overall_feasibility.value,
            "overall_cost": self.overall_cost,
        }


class RiskType(str, Enum):
    """Types of risk assessed by CREATE-SIMPLE."""

    INHALATION_8HR = "inhalation_8hr"  # 吸入8時間 - 8-hour TWA
    INHALATION_STEL = "inhalation_stel"  # 吸入短時間 - STEL (15-min)
    DERMAL = "dermal"  # 経皮吸収 - Dermal absorption
    COMBINED = "combined"  # 合計（吸入+経皮） - Combined risk
    PHYSICAL = "physical"  # 危険性（爆発・火災等） - Physical hazards


# Japanese labels for risk types
RISK_TYPE_LABELS_JA = {
    RiskType.INHALATION_8HR: "吸入リスク（8時間）",
    RiskType.INHALATION_STEL: "吸入リスク（短時間）",
    RiskType.DERMAL: "経皮吸収リスク",
    RiskType.COMBINED: "合計リスク（吸入+経皮）",
    RiskType.PHYSICAL: "危険性（爆発・火災等）",
}

RISK_TYPE_LABELS_EN = {
    RiskType.INHALATION_8HR: "8-hour Inhalation Risk",
    RiskType.INHALATION_STEL: "Short-term (STEL) Inhalation Risk",
    RiskType.DERMAL: "Dermal Absorption Risk",
    RiskType.COMBINED: "Combined Risk (Inhalation + Dermal)",
    RiskType.PHYSICAL: "Physical Hazards",
}


class RiskTypeAnalysis(BaseModel):
    """
    Analysis for a single risk type.

    Each risk type (inhalation, STEL, dermal, etc.) has its own
    set of achievable paths and limitations.
    """

    risk_type: RiskType
    risk_type_label: str = ""  # Display label
    risk_type_label_ja: str = ""

    # Current state
    current_rcr: float = 0.0
    current_level: str = ""  # "III", "II-A", etc.

    # Target
    target_level: str = ""
    target_rcr: float = 0.0
    reduction_needed_percent: float = 0.0

    # Achievable paths for this risk type (sorted by hierarchy)
    achievable_paths: List[RiskReductionPath] = Field(default_factory=list)
    insufficient_paths: List[RiskReductionPath] = Field(default_factory=list)

    # Status
    has_achievable_path: bool = False
    best_achievable_level: Optional[str] = None
    needs_action: bool = True  # False if already at or below target

    # Limitations
    limitations: List[str] = Field(default_factory=list)
    limitations_ja: List[str] = Field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "risk_type": self.risk_type.value,
            "risk_type_label": self.risk_type_label,
            "risk_type_label_ja": self.risk_type_label_ja,
            "current_rcr": round(self.current_rcr, 4),
            "current_level": self.current_level,
            "target_level": self.target_level,
            "target_rcr": round(self.target_rcr, 4),
            "reduction_needed_percent": round(self.reduction_needed_percent, 1),
            "has_achievable_path": self.has_achievable_path,
            "needs_action": self.needs_action,
            "achievable_paths": [p.to_dict() for p in self.achievable_paths[:5]],
            "insufficient_paths": [p.to_dict() for p in self.insufficient_paths[:3]],
            "best_achievable_level": self.best_achievable_level,
            "limitations": self.limitations,
        }


class RiskReductionAnalysis(BaseModel):
    """
    Complete analysis of risk reduction options.

    Shows all possible paths to achieve target risk level,
    what's insufficient, and what's not possible.
    """

    # Context
    substance_cas: str = ""
    substance_name: str = ""
    current_rcr: float
    current_level: str  # "III"
    target_level: str  # "II-A"
    target_rcr: float  # 0.5
    reduction_needed_percent: float

    # Achievable paths (sorted by priority)
    achievable_paths: List[RiskReductionPath] = Field(default_factory=list)

    # Paths that help but don't achieve target alone
    insufficient_paths: List[RiskReductionPath] = Field(default_factory=list)

    # Not possible explanations
    limitations: List[str] = Field(default_factory=list)
    limitations_ja: List[str] = Field(default_factory=list)
    best_achievable_level: Optional[str] = None

    # Quick summary
    has_achievable_path: bool = False
    easiest_path: Optional[RiskReductionPath] = None
    most_effective_path: Optional[RiskReductionPath] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "substance_cas": self.substance_cas,
            "substance_name": self.substance_name,
            "current_rcr": round(self.current_rcr, 4),
            "current_level": self.current_level,
            "target_level": self.target_level,
            "target_rcr": round(self.target_rcr, 4),
            "reduction_needed_percent": round(self.reduction_needed_percent, 1),
            "has_achievable_path": self.has_achievable_path,
            "achievable_paths": [p.to_dict() for p in self.achievable_paths],
            "insufficient_paths": [p.to_dict() for p in self.insufficient_paths[:3]],
            "limitations": self.limitations,
            "limitations_ja": self.limitations_ja,
            "best_achievable_level": self.best_achievable_level,
            "easiest_path": self.easiest_path.to_dict() if self.easiest_path else None,
            "most_effective_path": self.most_effective_path.to_dict() if self.most_effective_path else None,
        }

    def _get_category_label(self, path: "RiskReductionPath", lang: str = "en") -> str:
        """Get category label for a path, marking PPE as last resort."""
        if not path.measures:
            return ""

        # Get primary category (if all same, use that; if mixed, show highest hierarchy)
        categories = {m.category for m in path.measures}

        # Category labels with hierarchy indication
        if lang == "ja":
            labels = {
                ActionCategory.ENGINEERING: "工学的対策",
                ActionCategory.ADMINISTRATIVE: "管理的対策",
                ActionCategory.PPE: "PPE - 最後の手段",  # Last resort
            }
        else:
            labels = {
                ActionCategory.ENGINEERING: "ENGINEERING",
                ActionCategory.ADMINISTRATIVE: "ADMINISTRATIVE",
                ActionCategory.PPE: "PPE - LAST RESORT",  # Marked as last resort
            }

        if len(categories) == 1:
            cat = list(categories)[0]
            return labels.get(cat, str(cat.value))
        else:
            # Mixed - show both
            parts = [labels.get(c, str(c.value)) for c in sorted(
                categories, key=lambda x: {"engineering": 0, "administrative": 1, "ppe": 2}.get(x.value, 9)
            )]
            return " + ".join(parts)

    def summary(self) -> str:
        """Get text summary of reduction options."""
        lines = []
        lines.append(f"Risk Reduction Analysis for {self.substance_name}")
        lines.append(f"Current: Level {self.current_level} (RCR={self.current_rcr:.2f})")
        lines.append(f"Target: Level {self.target_level} (RCR≤{self.target_rcr})")
        lines.append(f"Reduction needed: {self.reduction_needed_percent:.0f}%")
        lines.append("")

        if self.achievable_paths:
            lines.append("✓ ACHIEVABLE OPTIONS (by hierarchy of controls):")
            for i, path in enumerate(self.achievable_paths[:5], 1):
                feasibility_icon = {"easy": "🟢", "moderate": "🟡", "difficult": "🟠", "very_difficult": "🔴"}
                icon = feasibility_icon.get(path.overall_feasibility.value, "⚪")
                cat_label = self._get_category_label(path, "en")
                lines.append(f"  {i}. [{cat_label}] {path.description} {icon}")
                lines.append(f"     → Level {path.predicted_level} (↓{path.combined_reduction_percent:.0f}%)")
        else:
            lines.append("✗ NO SINGLE MEASURE ACHIEVES TARGET")

        if self.insufficient_paths:
            lines.append("")
            lines.append("△ HELPS BUT INSUFFICIENT ALONE:")
            for path in self.insufficient_paths[:3]:
                lines.append(f"  - {path.description} (↓{path.combined_reduction_percent:.0f}%, still Level {path.predicted_level})")

        if self.limitations:
            lines.append("")
            lines.append("⚠ LIMITATIONS:")
            for lim in self.limitations:
                lines.append(f"  - {lim}")

        return "\n".join(lines)

    def summary_ja(self) -> str:
        """Get Japanese text summary."""
        lines = []
        lines.append(f"{self.substance_name}のリスク低減分析")
        lines.append(f"現状: レベル{self.current_level} (RCR={self.current_rcr:.2f})")
        lines.append(f"目標: レベル{self.target_level} (RCR≤{self.target_rcr})")
        lines.append(f"必要な低減率: {self.reduction_needed_percent:.0f}%")
        lines.append("")

        if self.achievable_paths:
            lines.append("✓ 達成可能なオプション（管理の優先順位に従い表示）:")
            for i, path in enumerate(self.achievable_paths[:5], 1):
                feasibility_icon = {"easy": "🟢", "moderate": "🟡", "difficult": "🟠", "very_difficult": "🔴"}
                icon = feasibility_icon.get(path.overall_feasibility.value, "⚪")
                desc = path.description_ja or path.description
                cat_label = self._get_category_label(path, "ja")
                lines.append(f"  {i}. [{cat_label}] {desc} {icon}")
                lines.append(f"     → レベル{path.predicted_level} (↓{path.combined_reduction_percent:.0f}%)")
        else:
            lines.append("✗ 単独で目標達成可能な対策はありません")

        if self.insufficient_paths:
            lines.append("")
            lines.append("△ 効果はあるが単独では不十分:")
            for path in self.insufficient_paths[:3]:
                desc = path.description_ja or path.description
                lines.append(f"  - {desc} (↓{path.combined_reduction_percent:.0f}%、レベル{path.predicted_level})")

        if self.limitations_ja:
            lines.append("")
            lines.append("⚠ 制限事項:")
            for lim in self.limitations_ja:
                lines.append(f"  - {lim}")

        return "\n".join(lines)


class MultiRiskAnalysis(BaseModel):
    """
    Complete multi-risk-type analysis for a substance.

    Contains analysis for all 5 CREATE-SIMPLE risk types:
    - 吸入8時間 (8-hour TWA inhalation)
    - 吸入短時間 (STEL inhalation)
    - 経皮吸収 (Dermal absorption)
    - 合計 (Combined inhalation + dermal)
    - 危険性 (Physical hazards)

    Reference: CREATE-SIMPLE Design v3.1.1
    """

    # Context
    substance_cas: str = ""
    substance_name: str = ""

    # Per-risk-type analysis
    inhalation_8hr: Optional[RiskTypeAnalysis] = None
    inhalation_stel: Optional[RiskTypeAnalysis] = None
    dermal: Optional[RiskTypeAnalysis] = None
    combined: Optional[RiskTypeAnalysis] = None
    physical: Optional[RiskTypeAnalysis] = None

    # Overall summary
    controlling_risk_type: Optional[RiskType] = None  # Which risk drives overall level
    controlling_risk_label: str = ""
    controlling_risk_label_ja: str = ""
    overall_risk_level: str = ""  # Highest of all assessed
    overall_achievable: bool = True  # Any path achieves all targets?

    def get_risk_types_assessed(self) -> List[RiskType]:
        """Get list of risk types that were assessed."""
        assessed = []
        if self.inhalation_8hr and self.inhalation_8hr.needs_action:
            assessed.append(RiskType.INHALATION_8HR)
        if self.inhalation_stel and self.inhalation_stel.needs_action:
            assessed.append(RiskType.INHALATION_STEL)
        if self.dermal and self.dermal.needs_action:
            assessed.append(RiskType.DERMAL)
        if self.combined and self.combined.needs_action:
            assessed.append(RiskType.COMBINED)
        if self.physical and self.physical.needs_action:
            assessed.append(RiskType.PHYSICAL)
        return assessed

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "substance_cas": self.substance_cas,
            "substance_name": self.substance_name,
            "controlling_risk_type": self.controlling_risk_type.value if self.controlling_risk_type else None,
            "controlling_risk_label": self.controlling_risk_label,
            "controlling_risk_label_ja": self.controlling_risk_label_ja,
            "overall_risk_level": self.overall_risk_level,
            "overall_achievable": self.overall_achievable,
            "inhalation_8hr": self.inhalation_8hr.to_dict() if self.inhalation_8hr else None,
            "inhalation_stel": self.inhalation_stel.to_dict() if self.inhalation_stel else None,
            "dermal": self.dermal.to_dict() if self.dermal else None,
            "combined": self.combined.to_dict() if self.combined else None,
            "physical": self.physical.to_dict() if self.physical else None,
        }

    def summary(self) -> str:
        """Get text summary of all risk types."""
        lines = []
        lines.append(f"Risk Reduction Analysis for {self.substance_name}")
        lines.append(f"Overall Risk Level: {self.overall_risk_level}")
        if self.controlling_risk_type:
            lines.append(f"Controlling Risk: {self.controlling_risk_label}")
        lines.append("")

        # Show each risk type
        for risk_type, analysis in [
            (RiskType.INHALATION_8HR, self.inhalation_8hr),
            (RiskType.INHALATION_STEL, self.inhalation_stel),
            (RiskType.DERMAL, self.dermal),
            (RiskType.COMBINED, self.combined),
            (RiskType.PHYSICAL, self.physical),
        ]:
            if analysis is None:
                continue

            lines.append(f"■ {RISK_TYPE_LABELS_EN[risk_type]}")
            if not analysis.needs_action:
                lines.append(f"  Current: Level {analysis.current_level} - OK (no action needed)")
                lines.append("")
                continue

            lines.append(f"  Current: Level {analysis.current_level} (RCR={analysis.current_rcr:.2f})")
            lines.append(f"  Target: Level {analysis.target_level} (RCR≤{analysis.target_rcr})")

            if analysis.achievable_paths:
                lines.append(f"  ✓ {len(analysis.achievable_paths)} achievable options")
                for path in analysis.achievable_paths[:2]:
                    lines.append(f"    - {path.description} → Level {path.predicted_level}")
            else:
                lines.append("  ✗ No achievable paths")

            if analysis.limitations:
                for lim in analysis.limitations[:1]:
                    lines.append(f"  ⚠ {lim}")

            lines.append("")

        return "\n".join(lines)

    def summary_ja(self) -> str:
        """Get Japanese text summary of all risk types."""
        lines = []
        lines.append(f"{self.substance_name}のリスク低減分析")
        lines.append(f"総合リスクレベル: {self.overall_risk_level}")
        if self.controlling_risk_type:
            lines.append(f"支配的リスク: {self.controlling_risk_label_ja}")
        lines.append("")

        # Show each risk type
        for risk_type, analysis in [
            (RiskType.INHALATION_8HR, self.inhalation_8hr),
            (RiskType.INHALATION_STEL, self.inhalation_stel),
            (RiskType.DERMAL, self.dermal),
            (RiskType.COMBINED, self.combined),
            (RiskType.PHYSICAL, self.physical),
        ]:
            if analysis is None:
                continue

            lines.append(f"■ {RISK_TYPE_LABELS_JA[risk_type]}")
            if not analysis.needs_action:
                lines.append(f"  現状: レベル{analysis.current_level} - OK（対策不要）")
                lines.append("")
                continue

            lines.append(f"  現状: レベル{analysis.current_level} (RCR={analysis.current_rcr:.2f})")
            lines.append(f"  目標: レベル{analysis.target_level} (RCR≤{analysis.target_rcr})")

            if analysis.achievable_paths:
                lines.append(f"  ✓ {len(analysis.achievable_paths)}個の達成可能なオプション")
                for path in analysis.achievable_paths[:2]:
                    desc = path.description_ja or path.description
                    lines.append(f"    - {desc} → レベル{path.predicted_level}")
            else:
                lines.append("  ✗ 達成可能な対策なし")

            if analysis.limitations_ja:
                for lim in analysis.limitations_ja[:1]:
                    lines.append(f"  ⚠ {lim}")

            lines.append("")

        return "\n".join(lines)
