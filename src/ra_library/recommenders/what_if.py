"""
What-if scenario analysis.

This module allows users to see how different control measures
would affect their risk level BEFORE implementing them.

Reference: CREATE-SIMPLE Design v3.1.1
"""

from dataclasses import dataclass, field

from ..models.assessment import (
    AssessmentInput,
    AssessmentMode,
    VentilationLevel,
    AmountLevel,
    RPEType,
    RPE_APF_VALUES,
)
from ..models.substance import Substance
from ..models.risk import RiskLevel
from ..models.recommendation import (
    ActionCategory,
    Feasibility,
)
from ..calculators.constants import VENTILATION_COEFFICIENTS


@dataclass
class WhatIfScenario:
    """A single what-if scenario with predicted outcome."""

    parameter_name: str
    current_value: str
    new_value: str
    current_rcr: float
    predicted_rcr: float
    current_level: RiskLevel
    predicted_level: RiskLevel
    reduction_percent: float
    coefficient_change: str
    description: str
    description_ja: str
    feasibility: Feasibility
    category: ActionCategory
    implementation_notes: list[str] = field(default_factory=list)


class WhatIfAnalyzer:
    """
    Analyzer for what-if scenarios.

    Calculates the effect of different control measures
    on the risk level without actually changing the assessment.
    """

    def __init__(
        self,
        assessment_input: AssessmentInput,
        substance: Substance,
        current_rcr: float,
        language: str = "en",
    ):
        """
        Initialize the analyzer.

        Args:
            assessment_input: Current assessment input
            substance: Substance being assessed
            current_rcr: Current RCR value
            language: "en" or "ja"
        """
        self.input = assessment_input
        self.substance = substance
        self.current_rcr = current_rcr
        self.current_level = RiskLevel.from_rcr(current_rcr)
        self.language = language

    def analyze_all_scenarios(self) -> list[WhatIfScenario]:
        """
        Generate all possible what-if scenarios.

        Returns:
            List of scenarios sorted by effectiveness
        """
        scenarios = []

        # Ventilation improvements
        scenarios.extend(self._analyze_ventilation_scenarios())

        # Amount reduction
        scenarios.extend(self._analyze_amount_scenarios())

        # Duration reduction
        scenarios.extend(self._analyze_duration_scenarios())

        # RPE options (Report mode only)
        if self.input.mode == AssessmentMode.REPORT:
            scenarios.extend(self._analyze_rpe_scenarios())

        # Sort by reduction percent (most effective first)
        scenarios.sort(key=lambda s: s.reduction_percent, reverse=True)

        return scenarios

    def _analyze_ventilation_scenarios(self) -> list[WhatIfScenario]:
        """Analyze ventilation improvement options."""
        scenarios = []
        current_vent = self.input.ventilation
        current_verified = self.input.control_velocity_verified

        # Define all ventilation options with their coefficients
        vent_options = [
            (VentilationLevel.NONE, False, 4.0, "No ventilation", "換気なし"),
            (VentilationLevel.BASIC, False, 3.0, "Basic ventilation", "一般換気"),
            (VentilationLevel.INDUSTRIAL, False, 1.0, "Industrial ventilation", "工業的換気"),
            (
                VentilationLevel.LOCAL_EXTERNAL,
                False,
                0.7,
                "Local exhaust (external)",
                "局所排気(外付け)",
            ),
            (
                VentilationLevel.LOCAL_EXTERNAL,
                True,
                0.1,
                "Local exhaust (external, verified)",
                "局所排気(外付け・確認済)",
            ),
            (
                VentilationLevel.LOCAL_ENCLOSED,
                False,
                0.3,
                "Local exhaust (enclosed)",
                "局所排気(囲い式)",
            ),
            (
                VentilationLevel.LOCAL_ENCLOSED,
                True,
                0.01,
                "Local exhaust (enclosed, verified)",
                "局所排気(囲い式・確認済)",
            ),
            (VentilationLevel.SEALED, False, 0.001, "Sealed system", "密閉系"),
        ]

        current_coeff = VENTILATION_COEFFICIENTS.get((current_vent.value, current_verified), 1.0)
        current_name = self._get_ventilation_name(current_vent, current_verified)

        for vent, verified, coeff, name_en, name_ja in vent_options:
            # Skip if same or worse than current
            if coeff >= current_coeff:
                continue

            # Calculate new RCR
            ratio = coeff / current_coeff
            new_rcr = self.current_rcr * ratio
            new_level = RiskLevel.from_rcr(new_rcr)
            reduction = (1 - ratio) * 100

            # Determine feasibility
            if vent == VentilationLevel.SEALED:
                feasibility = Feasibility.VERY_DIFFICULT
            elif vent in [VentilationLevel.LOCAL_ENCLOSED]:
                feasibility = Feasibility.DIFFICULT
            elif vent in [VentilationLevel.LOCAL_EXTERNAL]:
                feasibility = Feasibility.MODERATE
            else:
                feasibility = Feasibility.EASY

            scenarios.append(
                WhatIfScenario(
                    parameter_name="ventilation",
                    current_value=current_name,
                    new_value=name_en if self.language == "en" else name_ja,
                    current_rcr=self.current_rcr,
                    predicted_rcr=new_rcr,
                    current_level=self.current_level,
                    predicted_level=new_level,
                    reduction_percent=reduction,
                    coefficient_change=f"{current_coeff} → {coeff}",
                    description=f"Change ventilation to {name_en}",
                    description_ja=f"換気を{name_ja}に変更",
                    feasibility=feasibility,
                    category=ActionCategory.ENGINEERING,
                    implementation_notes=self._get_vent_implementation_notes(vent),
                )
            )

        return scenarios

    def _analyze_amount_scenarios(self) -> list[WhatIfScenario]:
        """Analyze amount reduction options."""
        scenarios = []
        current_amount = self.input.amount_level

        # Amount order from largest to smallest
        amount_order = [
            AmountLevel.LARGE,
            AmountLevel.MEDIUM,
            AmountLevel.SMALL,
            AmountLevel.MINUTE,
            AmountLevel.TRACE,
        ]

        current_idx = amount_order.index(current_amount)

        # Amount reduction factors (rough approximation)
        # Each level down typically reduces exposure by ~10x
        amount_factors = {
            AmountLevel.LARGE: 1.0,
            AmountLevel.MEDIUM: 0.1,
            AmountLevel.SMALL: 0.01,
            AmountLevel.MINUTE: 0.001,
            AmountLevel.TRACE: 0.0001,
        }

        current_factor = amount_factors[current_amount]

        for i, amount in enumerate(amount_order):
            if i <= current_idx:
                continue  # Skip same or larger amounts

            new_factor = amount_factors[amount]
            ratio = new_factor / current_factor
            new_rcr = self.current_rcr * ratio
            new_level = RiskLevel.from_rcr(new_rcr)
            reduction = (1 - ratio) * 100

            if self.language == "ja":
                amount_names = {
                    AmountLevel.LARGE: "大量",
                    AmountLevel.MEDIUM: "中量",
                    AmountLevel.SMALL: "少量",
                    AmountLevel.MINUTE: "微量",
                    AmountLevel.TRACE: "極微量",
                }
            else:
                amount_names = {
                    AmountLevel.LARGE: "Large",
                    AmountLevel.MEDIUM: "Medium",
                    AmountLevel.SMALL: "Small",
                    AmountLevel.MINUTE: "Minute",
                    AmountLevel.TRACE: "Trace",
                }

            scenarios.append(
                WhatIfScenario(
                    parameter_name="amount",
                    current_value=amount_names[current_amount],
                    new_value=amount_names[amount],
                    current_rcr=self.current_rcr,
                    predicted_rcr=new_rcr,
                    current_level=self.current_level,
                    predicted_level=new_level,
                    reduction_percent=reduction,
                    coefficient_change=f"~{current_factor:.4f} → ~{new_factor:.4f}",
                    description=f"Reduce amount to {amount_names[amount]}",
                    description_ja=f"取り扱い量を{amount_names[amount]}に削減",
                    feasibility=Feasibility.MODERATE,
                    category=ActionCategory.ADMINISTRATIVE,
                    implementation_notes=[
                        "Batch size reduction" if self.language == "en" else "バッチサイズの縮小",
                        "Just-in-time delivery"
                        if self.language == "en"
                        else "ジャストインタイム配送",
                    ],
                )
            )

        return scenarios

    def _analyze_duration_scenarios(self) -> list[WhatIfScenario]:
        """Analyze work duration reduction options."""
        scenarios = []
        current_hours = self.input.working_hours_per_day

        # Possible hour reductions
        hour_options = [8.0, 6.0, 4.0, 2.0, 1.0]

        for hours in hour_options:
            if hours >= current_hours:
                continue

            ratio = hours / current_hours
            new_rcr = self.current_rcr * ratio
            new_level = RiskLevel.from_rcr(new_rcr)
            reduction = (1 - ratio) * 100

            scenarios.append(
                WhatIfScenario(
                    parameter_name="duration",
                    current_value=f"{current_hours}h/day"
                    if self.language == "en"
                    else f"{current_hours}時間/日",
                    new_value=f"{hours}h/day" if self.language == "en" else f"{hours}時間/日",
                    current_rcr=self.current_rcr,
                    predicted_rcr=new_rcr,
                    current_level=self.current_level,
                    predicted_level=new_level,
                    reduction_percent=reduction,
                    coefficient_change=f"{current_hours / 8:.2f} → {hours / 8:.2f}",
                    description=f"Reduce work hours to {hours}h/day",
                    description_ja=f"作業時間を{hours}時間/日に短縮",
                    feasibility=Feasibility.MODERATE,
                    category=ActionCategory.ADMINISTRATIVE,
                    implementation_notes=[
                        "Job rotation" if self.language == "en" else "ジョブローテーション",
                        "Shift planning" if self.language == "en" else "シフト計画の見直し",
                    ],
                )
            )

        return scenarios

    def _analyze_rpe_scenarios(self) -> list[WhatIfScenario]:
        """Analyze RPE options (Report mode only)."""
        scenarios = []

        if self.input.mode != AssessmentMode.REPORT:
            return scenarios

        current_rpe = self.input.rpe_type or RPEType.NONE
        current_apf = RPE_APF_VALUES.get(current_rpe, 1)

        # RPE options
        rpe_options = [
            (RPEType.LOOSE_FIT_11, 11, "Loose-fit APF 11", "ルーズフィット APF 11"),
            (RPEType.LOOSE_FIT_20, 20, "Loose-fit APF 20", "ルーズフィット APF 20"),
            (RPEType.LOOSE_FIT_25, 25, "Loose-fit APF 25", "ルーズフィット APF 25"),
            (RPEType.TIGHT_FIT_10, 10, "Tight-fit APF 10", "タイトフィット APF 10"),
            (RPEType.TIGHT_FIT_50, 50, "Tight-fit APF 50", "タイトフィット APF 50"),
            (RPEType.TIGHT_FIT_100, 100, "Tight-fit APF 100", "タイトフィット APF 100"),
            (RPEType.TIGHT_FIT_1000, 1000, "Tight-fit APF 1000", "タイトフィット APF 1000"),
        ]

        for rpe, apf, name_en, name_ja in rpe_options:
            if apf <= current_apf:
                continue

            # RPE coefficient = 1/APF
            ratio = current_apf / apf
            new_rcr = self.current_rcr * ratio
            new_level = RiskLevel.from_rcr(new_rcr)
            reduction = (1 - ratio) * 100

            # Determine feasibility
            if apf >= 100:
                feasibility = Feasibility.DIFFICULT
            elif "TIGHT" in rpe.value.upper():
                feasibility = Feasibility.MODERATE
            else:
                feasibility = Feasibility.EASY

            scenarios.append(
                WhatIfScenario(
                    parameter_name="rpe",
                    current_value="None" if current_rpe == RPEType.NONE else f"APF {current_apf}",
                    new_value=name_en if self.language == "en" else name_ja,
                    current_rcr=self.current_rcr,
                    predicted_rcr=new_rcr,
                    current_level=self.current_level,
                    predicted_level=new_level,
                    reduction_percent=reduction,
                    coefficient_change=f"1/{current_apf} → 1/{apf}",
                    description=f"Use {name_en}",
                    description_ja=f"{name_ja}を使用",
                    feasibility=feasibility,
                    category=ActionCategory.PPE,
                    implementation_notes=self._get_rpe_implementation_notes(rpe),
                )
            )

        return scenarios

    def find_path_to_level(
        self,
        target_level: RiskLevel,
    ) -> list[WhatIfScenario]:
        """
        Find the combination of changes needed to achieve target level.

        Args:
            target_level: The risk level to achieve

        Returns:
            List of scenarios that together achieve the target
        """
        target_rcr = {
            RiskLevel.I: 0.1,
            RiskLevel.II: 1.0,
            RiskLevel.III: 10.0,
            RiskLevel.IV: float("inf"),
        }[target_level]

        if self.current_rcr <= target_rcr:
            return []  # Already at or below target

        # Get all scenarios and find minimum combination
        all_scenarios = self.analyze_all_scenarios()

        # Greedy approach: pick most effective until target reached
        selected = []
        cumulative_rcr = self.current_rcr

        for scenario in all_scenarios:
            if cumulative_rcr <= target_rcr:
                break

            # Calculate cumulative effect
            ratio = scenario.predicted_rcr / scenario.current_rcr
            cumulative_rcr *= ratio
            selected.append(scenario)

        return selected

    def _get_ventilation_name(self, vent: VentilationLevel, verified: bool) -> str:
        """Get display name for ventilation level."""
        if self.language == "ja":
            names = {
                VentilationLevel.NONE: "換気なし",
                VentilationLevel.BASIC: "一般換気",
                VentilationLevel.INDUSTRIAL: "工業的換気",
                VentilationLevel.LOCAL_EXTERNAL: "局所排気(外付け)",
                VentilationLevel.LOCAL_ENCLOSED: "局所排気(囲い式)",
                VentilationLevel.SEALED: "密閉系",
            }
            suffix = (
                "・確認済"
                if verified
                and vent in [VentilationLevel.LOCAL_EXTERNAL, VentilationLevel.LOCAL_ENCLOSED]
                else ""
            )
        else:
            names = {
                VentilationLevel.NONE: "No ventilation",
                VentilationLevel.BASIC: "Basic ventilation",
                VentilationLevel.INDUSTRIAL: "Industrial ventilation",
                VentilationLevel.LOCAL_EXTERNAL: "Local exhaust (external)",
                VentilationLevel.LOCAL_ENCLOSED: "Local exhaust (enclosed)",
                VentilationLevel.SEALED: "Sealed system",
            }
            suffix = (
                " - verified"
                if verified
                and vent in [VentilationLevel.LOCAL_EXTERNAL, VentilationLevel.LOCAL_ENCLOSED]
                else ""
            )

        return names.get(vent, str(vent)) + suffix

    def _get_vent_implementation_notes(self, vent: VentilationLevel) -> list[str]:
        """Get implementation notes for ventilation change."""
        if self.language == "ja":
            notes = {
                VentilationLevel.BASIC: ["窓の開放", "一般換気扇の設置"],
                VentilationLevel.INDUSTRIAL: ["工業用換気システムの導入"],
                VentilationLevel.LOCAL_EXTERNAL: ["局所排気装置の設置", "外付けフードの選定"],
                VentilationLevel.LOCAL_ENCLOSED: ["囲い式フードの設計・施工"],
                VentilationLevel.SEALED: ["密閉システムの設計", "自動化の検討"],
            }
        else:
            notes = {
                VentilationLevel.BASIC: ["Open windows", "Install general ventilation fan"],
                VentilationLevel.INDUSTRIAL: ["Install industrial ventilation system"],
                VentilationLevel.LOCAL_EXTERNAL: [
                    "Install LEV system",
                    "Select appropriate external hood",
                ],
                VentilationLevel.LOCAL_ENCLOSED: ["Design and install enclosed hood"],
                VentilationLevel.SEALED: ["Design sealed system", "Consider automation"],
            }
        return notes.get(vent, [])

    def _get_rpe_implementation_notes(self, rpe: RPEType) -> list[str]:
        """Get implementation notes for RPE selection."""
        if "TIGHT" in rpe.value.upper():
            if self.language == "ja":
                return ["フィットテストの実施", "使用者教育", "メンテナンス計画"]
            else:
                return ["Conduct fit test", "User training", "Maintenance plan"]
        else:
            if self.language == "ja":
                return ["使用者教育", "適切なサイズの選定"]
            else:
                return ["User training", "Select appropriate size"]
