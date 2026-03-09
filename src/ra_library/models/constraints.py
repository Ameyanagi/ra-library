"""
Assessment constraints for recommendation generation.

Constraints allow users to specify what measures are physically possible
for their workplace, excluding recommendations that cannot be implemented.
"""

from dataclasses import dataclass, field
from typing import Optional

from .assessment import VentilationLevel


# Ventilation hierarchy (higher = more enclosed/better)
VENTILATION_HIERARCHY: dict[VentilationLevel, int] = {
    VentilationLevel.NONE: 0,
    VentilationLevel.BASIC: 1,
    VentilationLevel.INDUSTRIAL: 2,
    VentilationLevel.LOCAL_EXTERNAL: 3,
    VentilationLevel.LOCAL_ENCLOSED: 4,
    VentilationLevel.SEALED: 5,
}


@dataclass
class AssessmentConstraints:
    """
    Constraints for recommendation generation.

    These constraints filter out measures that are physically impossible
    or undesirable for a specific workplace.

    Attributes:
        max_ventilation: Maximum ventilation level achievable.
            E.g., "local_enclosed" means sealed system is not possible.
        min_frequency: Minimum work frequency allowed.
            E.g., {"days": 1, "period": "week"} means cannot reduce below 1 day/week.
        excluded_measures: List of specific measure IDs to exclude.
            E.g., ["sealed_system", "scba"]
        excluded_rpe: List of RPE types to exclude.
            E.g., ["scba", "airline"] for workplaces where these aren't feasible.
        max_rpe_apf: Maximum RPE APF allowed.
            E.g., 100 means exclude SCBA (APF 10000) and other high-APF options.
        engineering_only: Only suggest engineering controls (no PPE).
        no_ppe: Exclude all PPE recommendations.
        no_admin: Exclude administrative controls (frequency reduction).
    """

    max_ventilation: Optional[VentilationLevel] = None
    min_frequency: Optional[dict] = None  # {"days": 1, "period": "week"|"month"}
    excluded_measures: list[str] = field(default_factory=list)
    excluded_rpe: list[str] = field(default_factory=list)
    max_rpe_apf: Optional[int] = None
    engineering_only: bool = False
    no_ppe: bool = False
    no_admin: bool = False

    def allows_ventilation(self, level: VentilationLevel) -> bool:
        """
        Check if a ventilation level is allowed.

        Args:
            level: The ventilation level to check.

        Returns:
            True if the level is at or below max_ventilation.
        """
        if self.max_ventilation is None:
            return True

        max_rank = VENTILATION_HIERARCHY.get(self.max_ventilation, 5)
        level_rank = VENTILATION_HIERARCHY.get(level, 0)

        return level_rank <= max_rank

    def allows_rpe(self, rpe_type: str, apf: int) -> bool:
        """
        Check if an RPE type is allowed.

        Args:
            rpe_type: The RPE type identifier (e.g., "scba", "half_mask").
            apf: The Assigned Protection Factor.

        Returns:
            True if the RPE is allowed by all constraints.
        """
        if self.no_ppe or self.engineering_only:
            return False

        # Check excluded RPE types
        rpe_lower = rpe_type.lower()
        for excluded in self.excluded_rpe:
            if excluded.lower() in rpe_lower or rpe_lower in excluded.lower():
                return False

        # Check APF limit
        if self.max_rpe_apf is not None and apf > self.max_rpe_apf:
            return False

        return True

    def allows_measure(self, measure_id: str) -> bool:
        """
        Check if a specific measure is allowed.

        Args:
            measure_id: The measure identifier.

        Returns:
            True if the measure is not in the excluded list.
        """
        measure_lower = measure_id.lower()
        for excluded in self.excluded_measures:
            if excluded.lower() in measure_lower or measure_lower in excluded.lower():
                return False
        return True

    def allows_frequency_reduction(self, target_days: int, target_period: str) -> bool:
        """
        Check if a frequency reduction is allowed.

        Args:
            target_days: Target days per period.
            target_period: "week" or "month".

        Returns:
            True if the reduction is at or above minimum frequency.
        """
        if self.no_admin:
            return False

        if self.min_frequency is None:
            return True

        # Convert to monthly equivalent for comparison
        def to_monthly(days: int, period: str) -> float:
            if period == "week":
                return days * 4.0  # Approximate weeks per month
            return float(days)

        target_monthly = to_monthly(target_days, target_period)
        min_monthly = to_monthly(
            self.min_frequency.get("days", 1),
            self.min_frequency.get("period", "month"),
        )

        return target_monthly >= min_monthly

    def allows_admin_controls(self) -> bool:
        """Check if administrative controls are allowed."""
        return not self.no_admin and not self.engineering_only

    def allows_ppe_controls(self) -> bool:
        """Check if PPE controls are allowed."""
        return not self.no_ppe and not self.engineering_only

    def get_excluded_summary(self) -> list[str]:
        """
        Get a summary of what is excluded by these constraints.

        Returns:
            List of human-readable exclusion descriptions.
        """
        exclusions = []

        if self.max_ventilation is not None:
            vent_names = {
                VentilationLevel.LOCAL_ENCLOSED: "密閉系システム",
                VentilationLevel.LOCAL_EXTERNAL: "密閉系システム、囲い式局所排気",
                VentilationLevel.INDUSTRIAL: "密閉系システム、局所排気装置",
            }
            excluded = vent_names.get(self.max_ventilation)
            if excluded:
                exclusions.append(f"{excluded}（max_ventilation={self.max_ventilation.value}）")

        if self.excluded_rpe:
            rpe_names = {
                "scba": "自給式空気呼吸器",
                "airline": "エアラインマスク",
                "papr": "電動ファン付き呼吸用保護具",
                "half_mask": "半面形マスク",
                "full_mask": "全面形マスク",
            }
            for rpe in self.excluded_rpe:
                name = rpe_names.get(rpe.lower(), rpe)
                exclusions.append(f"{name}（excluded_rpe）")

        if self.max_rpe_apf:
            exclusions.append(f"APF {self.max_rpe_apf}超のRPE（max_rpe_apf）")

        if self.engineering_only:
            exclusions.append("PPE・管理的対策（engineering_only=True）")
        elif self.no_ppe:
            exclusions.append("全てのPPE（no_ppe=True）")

        if self.no_admin:
            exclusions.append("頻度削減等の管理的対策（no_admin=True）")

        if self.min_frequency:
            days = self.min_frequency.get("days", 1)
            period = self.min_frequency.get("period", "month")
            period_ja = "週" if period == "week" else "月"
            exclusions.append(f"{days}日/{period_ja}未満への頻度削減（min_frequency）")

        if self.excluded_measures:
            for measure in self.excluded_measures:
                exclusions.append(f"{measure}（excluded_measures）")

        return exclusions
