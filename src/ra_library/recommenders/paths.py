"""
Risk reduction path calculation.

Calculates all possible paths (single measures or combinations)
to achieve target risk levels.

IMPORTANT: This module uses actual CREATE-SIMPLE recalculation for each
suggested measure, NOT simple multiplication. This ensures:
- Minimum exposure floors are properly applied (0.005 ppm liquid, 0.001 mg/m³ solid)
- ACRmax is correctly considered for carcinogens
- Risk levels that cannot be achieved are accurately reported
"""

from typing import Optional
from copy import deepcopy
from itertools import combinations

from ..models.assessment import (
    AssessmentInput,
    VentilationLevel,
    ExposureVariation,
    RPEType,
    AssessmentMode,
)
from ..models.risk import RiskLevel, DetailedRiskLevel, InhalationRisk, DermalRisk, PhysicalRisk
from ..models.recommendation import (
    ActionCategory,
    Feasibility,
    Measure,
    RiskReductionPath,
    RiskReductionAnalysis,
    RiskType,
    RiskTypeAnalysis,
    MultiRiskAnalysis,
    RISK_TYPE_LABELS_EN,
    RISK_TYPE_LABELS_JA,
)
from ..models.substance import Substance
from ..models.constraints import AssessmentConstraints
from ..calculators.inhalation import calculate_inhalation_risk


# Define available measures with their coefficients
VENTILATION_MEASURES = [
    {
        "action": "local_external",
        "label": "Install local exhaust ventilation (external hood)",
        "label_ja": "局所排気装置（外付け式）の設置",
        "coefficient": 0.7,  # Without verification
        "coefficient_verified": 0.1,  # With verification
        "feasibility": Feasibility.DIFFICULT,
        "cost": "high",
        "from_levels": [VentilationLevel.NONE, VentilationLevel.BASIC, VentilationLevel.INDUSTRIAL],
    },
    {
        "action": "local_enclosed",
        "label": "Install enclosed local exhaust ventilation",
        "label_ja": "局所排気装置（囲い式）の設置",
        "coefficient": 0.3,  # Without verification
        "coefficient_verified": 0.01,  # With verification
        "feasibility": Feasibility.DIFFICULT,
        "cost": "high",
        "from_levels": [VentilationLevel.NONE, VentilationLevel.BASIC, VentilationLevel.INDUSTRIAL, VentilationLevel.LOCAL_EXTERNAL],
    },
    {
        "action": "sealed",
        "label": "Implement sealed/enclosed system",
        "label_ja": "密閉系システムの導入",
        "coefficient": 0.001,
        "feasibility": Feasibility.VERY_DIFFICULT,
        "cost": "very_high",
        "from_levels": [VentilationLevel.NONE, VentilationLevel.BASIC, VentilationLevel.INDUSTRIAL, VentilationLevel.LOCAL_EXTERNAL, VentilationLevel.LOCAL_ENCLOSED],
    },
    {
        "action": "verify_control_velocity",
        "label": "Verify and document control velocity",
        "label_ja": "制御風速の確認・記録",
        "coefficient": None,  # Special - improves existing local exhaust
        "feasibility": Feasibility.EASY,
        "cost": "low",
        "from_levels": [VentilationLevel.LOCAL_EXTERNAL, VentilationLevel.LOCAL_ENCLOSED],
        "requires_local_exhaust": True,
    },
]

RPE_MEASURES = [
    {
        "action": "half_mask",
        "label": "Use half-mask respirator (APF 10)",
        "label_ja": "半面形マスク着用 (APF 10)",
        "apf": 10,
        "coefficient": 0.1,
        "feasibility": Feasibility.EASY,
        "cost": "low",
    },
    {
        "action": "full_mask",
        "label": "Use full-face respirator (APF 50)",
        "label_ja": "全面形マスク着用 (APF 50)",
        "apf": 50,
        "coefficient": 0.02,
        "feasibility": Feasibility.MODERATE,
        "cost": "medium",
    },
    {
        "action": "papr",
        "label": "Use PAPR (APF 25-1000)",
        "label_ja": "電動ファン付き呼吸用保護具着用",
        "apf": 100,
        "coefficient": 0.01,
        "feasibility": Feasibility.MODERATE,
        "cost": "medium",
    },
    {
        "action": "scba",
        "label": "Use SCBA/supplied air (APF 10000)",
        "label_ja": "自給式空気呼吸器/エアライン着用",
        "apf": 10000,
        "coefficient": 0.0001,
        "feasibility": Feasibility.DIFFICULT,
        "cost": "high",
    },
]

# CREATE-SIMPLE Discrete Administrative Options
# Reference: CREATE-SIMPLE Design v3.1.1, Figure 18, 19

# Working hours options (from constants.py)
WORKING_HOURS_OPTIONS = {
    8: 1.0,
    6: 0.75,
    4: 0.5,
    2: 0.25,
    1: 0.125,
}

# Weekly frequency options (days/week)
FREQUENCY_WEEKLY_OPTIONS = {
    5: 1.0,
    4: 0.8,
    3: 0.6,
    2: 0.4,
    1: 0.2,
}

# Monthly frequency options (days/month)
FREQUENCY_MONTHLY_OPTIONS = {
    4: 0.2,
    3: 0.15,
    2: 0.1,
    1: 0.05,
}

# Exposure variation options
EXPOSURE_VARIATION_OPTIONS = {
    "constant": 1.0,
    "intermittent": 0.5,
    "brief": 0.1,
}


def _get_admin_measures(assessment_input: AssessmentInput) -> list[dict]:
    """
    Generate administrative measures based on current assessment input.

    Uses only CREATE-SIMPLE discrete options (not arbitrary values).
    """
    measures = []
    current_hours = assessment_input.working_hours_per_day
    current_freq_type = assessment_input.frequency_type
    current_freq_value = assessment_input.frequency_value
    current_variation = assessment_input.exposure_variation.value

    # Get current coefficients
    current_hours_coeff = WORKING_HOURS_OPTIONS.get(int(current_hours), 1.0)
    if current_freq_type == "weekly":
        current_freq_coeff = FREQUENCY_WEEKLY_OPTIONS.get(current_freq_value, 1.0)
    else:
        current_freq_coeff = FREQUENCY_MONTHLY_OPTIONS.get(current_freq_value, 0.2)
    current_var_coeff = EXPOSURE_VARIATION_OPTIONS.get(current_variation, 1.0)

    # === Working Hours Reduction Options ===
    # Only suggest options that are LOWER than current
    for hours, coeff in sorted(WORKING_HOURS_OPTIONS.items(), reverse=True):
        if hours < current_hours:
            # Calculate relative reduction from current
            relative_coeff = coeff / current_hours_coeff if current_hours_coeff > 0 else coeff
            feasibility = Feasibility.EASY if hours >= 4 else Feasibility.MODERATE if hours >= 2 else Feasibility.DIFFICULT
            measures.append({
                "action": f"hours_{hours}",
                "label": f"Reduce working hours to {hours}h/day",
                "label_ja": f"作業時間を{hours}時間/日に短縮",
                "coefficient": relative_coeff,
                "feasibility": feasibility,
                "cost": "low",
                "parameter": "working_hours_per_day",
                "new_value": hours,
            })

    # === Frequency Reduction Options ===
    if current_freq_type == "weekly":
        # Weekly frequency: suggest reducing days/week
        for days, coeff in sorted(FREQUENCY_WEEKLY_OPTIONS.items(), reverse=True):
            if days < current_freq_value:
                relative_coeff = coeff / current_freq_coeff if current_freq_coeff > 0 else coeff
                feasibility = Feasibility.EASY if days >= 3 else Feasibility.MODERATE if days >= 2 else Feasibility.DIFFICULT
                measures.append({
                    "action": f"freq_weekly_{days}",
                    "label": f"Reduce frequency to {days} days/week",
                    "label_ja": f"頻度を{days}日/週に削減",
                    "coefficient": relative_coeff,
                    "feasibility": feasibility,
                    "cost": "low",
                    "parameter": "frequency_value",
                    "new_value": days,
                })

        # Also suggest switching to monthly (less than weekly)
        # Monthly options are more restrictive
        for days, coeff in sorted(FREQUENCY_MONTHLY_OPTIONS.items(), reverse=True):
            # Compare with current weekly coefficient
            relative_coeff = coeff / current_freq_coeff if current_freq_coeff > 0 else coeff
            if relative_coeff < 1.0:  # Only if it reduces exposure
                feasibility = Feasibility.MODERATE if days >= 2 else Feasibility.DIFFICULT
                measures.append({
                    "action": f"freq_monthly_{days}",
                    "label": f"Reduce to {days} days/month (less than weekly)",
                    "label_ja": f"頻度を{days}日/月に削減（週未満作業）",
                    "coefficient": relative_coeff,
                    "feasibility": feasibility,
                    "cost": "low",
                    "parameter": "frequency_type",
                    "new_value": f"monthly_{days}",
                })
    else:
        # Already monthly: suggest reducing days/month
        for days, coeff in sorted(FREQUENCY_MONTHLY_OPTIONS.items(), reverse=True):
            if days < current_freq_value:
                relative_coeff = coeff / current_freq_coeff if current_freq_coeff > 0 else coeff
                feasibility = Feasibility.EASY if days >= 2 else Feasibility.MODERATE
                measures.append({
                    "action": f"freq_monthly_{days}",
                    "label": f"Reduce frequency to {days} days/month",
                    "label_ja": f"頻度を{days}日/月に削減",
                    "coefficient": relative_coeff,
                    "feasibility": feasibility,
                    "cost": "low",
                    "parameter": "frequency_value",
                    "new_value": days,
                })

    # === Exposure Variation Options ===
    if current_variation == "constant":
        # Suggest intermittent or brief
        measures.append({
            "action": "variation_intermittent",
            "label": "Change to intermittent exposure",
            "label_ja": "暴露を間欠的に変更",
            "coefficient": 0.5 / current_var_coeff,
            "feasibility": Feasibility.MODERATE,
            "cost": "low",
            "parameter": "exposure_variation",
            "new_value": "intermittent",
        })
        measures.append({
            "action": "variation_brief",
            "label": "Change to brief exposure",
            "label_ja": "暴露を短時間に変更",
            "coefficient": 0.1 / current_var_coeff,
            "feasibility": Feasibility.DIFFICULT,
            "cost": "low",
            "parameter": "exposure_variation",
            "new_value": "brief",
        })
    elif current_variation == "intermittent":
        # Suggest brief only
        measures.append({
            "action": "variation_brief",
            "label": "Change to brief exposure",
            "label_ja": "暴露を短時間に変更",
            "coefficient": 0.1 / current_var_coeff,
            "feasibility": Feasibility.MODERATE,
            "cost": "low",
            "parameter": "exposure_variation",
            "new_value": "brief",
        })

    return measures


def _action_to_ventilation_level(action: str) -> VentilationLevel | None:
    """Convert action string to VentilationLevel."""
    mapping = {
        "local_external": VentilationLevel.LOCAL_EXTERNAL,
        "local_enclosed": VentilationLevel.LOCAL_ENCLOSED,
        "sealed": VentilationLevel.SEALED,
    }
    return mapping.get(action)


def _get_current_ventilation_coefficient(
    assessment_input: AssessmentInput,
) -> float:
    """Get the current ventilation coefficient."""
    from ..calculators.constants import VENTILATION_COEFFICIENTS

    vent = assessment_input.ventilation
    verified = assessment_input.control_velocity_verified

    if vent in (VentilationLevel.LOCAL_EXTERNAL, VentilationLevel.LOCAL_ENCLOSED):
        if verified:
            return VENTILATION_COEFFICIENTS.get(f"{vent.value}_verified", 1.0)
    return VENTILATION_COEFFICIENTS.get(vent.value, 1.0)


def _get_target_rcr(target_level: DetailedRiskLevel) -> float:
    """Get the target RCR threshold for a detailed risk level."""
    return target_level.get_rcr_threshold()


def _rcr_to_level_label(rcr: float) -> str:
    """Convert RCR to detailed level label."""
    return RiskLevel.get_detailed_label(rcr)


def _calculate_reduction_percent(current_coeff: float, new_coeff: float) -> float:
    """Calculate reduction percentage from coefficient change."""
    if current_coeff <= 0:
        return 0.0
    reduction = (current_coeff - new_coeff) / current_coeff * 100
    return max(0.0, min(100.0, reduction))


def _recalculate_inhalation_risk(
    base_input: AssessmentInput,
    substance: Substance,
    content_percent: float,
    modifications: dict,
) -> InhalationRisk:
    """
    Recalculate inhalation risk with modified assessment input.

    This uses the actual CREATE-SIMPLE calculation to ensure:
    - Minimum exposure floors are applied
    - ACRmax is correctly considered
    - All factor interactions are handled properly

    Args:
        base_input: Original assessment input
        substance: Substance being assessed
        content_percent: Content percentage
        modifications: Dict of parameter -> new_value to apply

    Returns:
        Recalculated InhalationRisk
    """
    # Create a deep copy of the input to avoid modifying the original
    modified_input = deepcopy(base_input)

    # Map action names to enum values for ventilation
    VENTILATION_ACTION_TO_ENUM = {
        "local_external": "local_ext",
        "local_enclosed": "local_enc",
        "sealed": "sealed",
    }

    # Map RPE action names to enum values
    # half_mask (APF 10) -> tight_fit_10
    # full_mask (APF 50) -> tight_fit_50
    # papr (APF 100) -> tight_fit_100
    # scba (APF 10000) -> tight_fit_10000
    RPE_ACTION_TO_ENUM = {
        "half_mask": "tight_fit_10",
        "full_mask": "tight_fit_50",
        "papr": "tight_fit_100",
        "scba": "tight_fit_10000",
    }

    # Apply modifications
    for param, value in modifications.items():
        if param == "ventilation":
            # Map action name to enum value if needed
            enum_value = VENTILATION_ACTION_TO_ENUM.get(value, value)
            modified_input.ventilation = VentilationLevel(enum_value)
        elif param == "control_velocity_verified":
            modified_input.control_velocity_verified = value
        elif param == "working_hours_per_day":
            modified_input.working_hours_per_day = value
        elif param == "frequency_value":
            modified_input.frequency_value = value
        elif param == "frequency_type":
            # Handle switching from weekly to monthly
            if isinstance(value, str) and value.startswith("monthly_"):
                days = int(value.split("_")[1])
                modified_input.frequency_type = "monthly"
                modified_input.frequency_value = days
            else:
                modified_input.frequency_type = value
        elif param == "exposure_variation":
            modified_input.exposure_variation = ExposureVariation(value)
        elif param == "rpe_type":
            # Map RPE action name to enum value
            enum_value = RPE_ACTION_TO_ENUM.get(value, value)
            modified_input.rpe_type = RPEType(enum_value) if enum_value else None
            # Switch to report mode for RPE to take effect
            if modified_input.rpe_type and modified_input.rpe_type != RPEType.NONE:
                modified_input.mode = AssessmentMode.REPORT

    # Recalculate using CREATE-SIMPLE methodology
    return calculate_inhalation_risk(
        assessment_input=modified_input,
        substance=substance,
        content_percent=content_percent,
        verbose=False,  # Skip verbose output for efficiency
    )


def calculate_reduction_paths(
    assessment_input: AssessmentInput,
    substance: Substance,
    risk: InhalationRisk,
    target_level: DetailedRiskLevel,
    include_combinations: bool = True,
    constraints: AssessmentConstraints | None = None,
) -> RiskReductionAnalysis:
    """
    Calculate all possible risk reduction paths for a substance.

    Args:
        assessment_input: Current assessment input
        substance: Substance being assessed
        risk: Current inhalation risk result
        target_level: Target risk level
        include_combinations: Whether to include 2-measure combinations
        constraints: Optional constraints to filter out impossible measures

    Returns:
        RiskReductionAnalysis with all achievable and insufficient paths
    """
    current_rcr = risk.rcr
    target_rcr = _get_target_rcr(target_level)
    current_level = RiskLevel.get_detailed_label(current_rcr)
    reduction_needed = (1 - target_rcr / current_rcr) * 100 if current_rcr > 0 else 0

    achievable_paths: list[RiskReductionPath] = []
    insufficient_paths: list[RiskReductionPath] = []
    all_measures: list[Measure] = []

    # Get current coefficients
    current_vent_coeff = _get_current_ventilation_coefficient(assessment_input)
    current_rpe_coeff = 1.0  # Assume no RPE currently
    if assessment_input.rpe_type and assessment_input.rpe_type != RPEType.NONE:
        # Already has RPE - can still upgrade
        pass

    # === Build list of available measures ===

    # === Build measures with modification info for recalculation ===
    # Each measure includes the parameters to modify for recalculation

    # Ventilation upgrades
    current_vent = assessment_input.ventilation
    is_velocity_verified = assessment_input.control_velocity_verified

    # Store (measure, modifications) pairs for recalculation
    measures_with_mods: list[tuple[Measure, dict]] = []

    for vent in VENTILATION_MEASURES:
        if current_vent in vent.get("from_levels", []):
            if vent.get("requires_local_exhaust") and current_vent not in (
                VentilationLevel.LOCAL_EXTERNAL, VentilationLevel.LOCAL_ENCLOSED
            ):
                continue

            # Build modification dict for recalculation
            if vent["action"] == "verify_control_velocity":
                # Skip if already verified
                if is_velocity_verified:
                    continue
                modifications = {"control_velocity_verified": True}
                new_coeff = 0.1 if current_vent == VentilationLevel.LOCAL_EXTERNAL else 0.01
            else:
                # Check constraints for ventilation upgrades
                target_vent_level = _action_to_ventilation_level(vent["action"])
                if constraints and target_vent_level:
                    if not constraints.allows_ventilation(target_vent_level):
                        continue
                    if not constraints.allows_measure(vent["action"]):
                        continue

                modifications = {"ventilation": vent["action"]}
                new_coeff = vent.get("coefficient_verified", vent["coefficient"])

            reduction = _calculate_reduction_percent(current_vent_coeff, new_coeff)
            if reduction > 0:
                measure = Measure(
                    category=ActionCategory.ENGINEERING,
                    action=vent["action"],
                    action_label=vent["label"],
                    action_label_ja=vent["label_ja"],
                    reduction_percent=reduction,
                    coefficient=new_coeff / current_vent_coeff if current_vent_coeff > 0 else 1.0,
                    feasibility=vent["feasibility"],
                    cost_estimate=vent["cost"],
                )
                measures_with_mods.append((measure, modifications))
                all_measures.append(measure)

    # RPE measures
    for rpe in RPE_MEASURES:
        # Check constraints for RPE
        if constraints:
            if not constraints.allows_ppe_controls():
                continue
            if not constraints.allows_rpe(rpe["action"], rpe["apf"]):
                continue
            if not constraints.allows_measure(rpe["action"]):
                continue

        reduction = (1 - rpe["coefficient"]) * 100
        modifications = {"rpe_type": rpe["action"]}
        measure = Measure(
            category=ActionCategory.PPE,
            action=rpe["action"],
            action_label=rpe["label"],
            action_label_ja=rpe["label_ja"],
            reduction_percent=reduction,
            coefficient=rpe["coefficient"],
            feasibility=rpe["feasibility"],
            cost_estimate=rpe["cost"],
        )
        measures_with_mods.append((measure, modifications))
        all_measures.append(measure)

    # Administrative measures - context-aware based on current assessment
    if not constraints or constraints.allows_admin_controls():
        admin_measures = _get_admin_measures(assessment_input)
        for admin in admin_measures:
            # Check frequency constraints
            if constraints and admin.get("parameter") in ("frequency_type", "frequency_value"):
                # Get target frequency from admin measure
                if admin["parameter"] == "frequency_value":
                    freq_type = admin.get("frequency_type", assessment_input.frequency_type)
                    period = "month" if freq_type == "monthly" else "week"
                    if not constraints.allows_frequency_reduction(admin["new_value"], period):
                        continue

            if constraints and not constraints.allows_measure(admin["action"]):
                continue

            reduction = (1 - admin["coefficient"]) * 100
            modifications = {admin["parameter"]: admin["new_value"]}
            measure = Measure(
                category=ActionCategory.ADMINISTRATIVE,
                action=admin["action"],
                action_label=admin["label"],
                action_label_ja=admin["label_ja"],
                reduction_percent=reduction,
                coefficient=admin["coefficient"],
                feasibility=admin["feasibility"],
                cost_estimate=admin["cost"],
            )
            measures_with_mods.append((measure, modifications))
            all_measures.append(measure)

    # === Evaluate single measures using actual CREATE-SIMPLE recalculation ===
    # IMPORTANT: We recalculate instead of simple multiplication to ensure:
    # - Minimum exposure floors are applied
    # - ACRmax is correctly considered for carcinogens
    # - All factor interactions are handled properly
    path_id = 0
    content_percent = 100.0  # Default content percentage

    for measure, modifications in measures_with_mods:
        # Recalculate risk with modified input
        recalc_risk = _recalculate_inhalation_risk(
            base_input=assessment_input,
            substance=substance,
            content_percent=content_percent,
            modifications=modifications,
        )
        new_rcr = recalc_risk.rcr
        new_level = _rcr_to_level_label(new_rcr)
        achieves = new_rcr <= target_rcr

        # Calculate actual reduction from recalculation
        actual_reduction = (1 - new_rcr / current_rcr) * 100 if current_rcr > 0 else 0

        path = RiskReductionPath(
            path_id=path_id,
            description=measure.action_label,
            description_ja=measure.action_label_ja,
            measures=[measure],
            combined_reduction_percent=max(0, actual_reduction),
            predicted_rcr=new_rcr,
            predicted_level=new_level,
            achieves_target=achieves,
            target_level=target_level.get_label(),
            gap_to_target_percent=(1 - target_rcr / new_rcr) * 100 if new_rcr > target_rcr else 0,
            overall_feasibility=measure.feasibility,
            overall_cost=measure.cost_estimate or "medium",
        )

        if achieves:
            achievable_paths.append(path)
        else:
            insufficient_paths.append(path)

        path_id += 1

    # === Evaluate 2-measure combinations ===
    if include_combinations:
        # Build a lookup from measure action to modifications
        measure_to_mods = {m.action: mods for m, mods in measures_with_mods}

        # Calculate useful combinations (especially when single measures are insufficient)
        # Build map of sufficient measures and their achieved RCR
        insufficient_actions = {p.measures[0].action for p in insufficient_paths}
        sufficient_measure_rcr: dict[str, float] = {}
        for p in achievable_paths:
            if len(p.measures) == 1:
                sufficient_measure_rcr[p.measures[0].action] = p.predicted_rcr

        for m1, m2 in combinations(all_measures, 2):
            # Skip if same category (can't use two RPE at once, etc.)
            if m1.category == m2.category:
                continue

            # Only consider combinations where at least one measure is insufficient alone
            # This avoids redundant combinations of two already-sufficient measures
            m1_sufficient = m1.action not in insufficient_actions
            m2_sufficient = m2.action not in insufficient_actions
            if m1_sufficient and m2_sufficient:
                continue  # Both already work alone, combination not needed

            # Combine modifications from both measures
            combined_mods = {}
            if m1.action in measure_to_mods:
                combined_mods.update(measure_to_mods[m1.action])
            if m2.action in measure_to_mods:
                combined_mods.update(measure_to_mods[m2.action])

            # Recalculate with combined modifications
            recalc_risk = _recalculate_inhalation_risk(
                base_input=assessment_input,
                substance=substance,
                content_percent=content_percent,
                modifications=combined_mods,
            )
            new_rcr = recalc_risk.rcr
            new_level = _rcr_to_level_label(new_rcr)
            combined_reduction = (1 - new_rcr / current_rcr) * 100 if current_rcr > 0 else 0
            achieves = new_rcr <= target_rcr

            # Skip combinations that include a measure that already achieves target alone
            # Principle: recommend the LEAST amount of measures needed
            # If one measure already achieves the target, don't show combinations with it
            skip_redundant = False
            for action in sufficient_measure_rcr.keys():
                if action in (m1.action, m2.action):
                    # This combination includes a measure that already achieves target alone
                    # Skip this combination - simpler single measure is sufficient
                    skip_redundant = True
                    break
            if skip_redundant:
                continue

            # Determine overall feasibility (worst of two)
            feasibility_order = [Feasibility.EASY, Feasibility.MODERATE, Feasibility.DIFFICULT, Feasibility.VERY_DIFFICULT]
            f1_idx = feasibility_order.index(m1.feasibility)
            f2_idx = feasibility_order.index(m2.feasibility)
            overall_feas = feasibility_order[max(f1_idx, f2_idx)]

            path = RiskReductionPath(
                path_id=path_id,
                description=f"{m1.action_label} + {m2.action_label}",
                description_ja=f"{m1.action_label_ja or m1.action_label} + {m2.action_label_ja or m2.action_label}",
                measures=[m1, m2],
                combined_reduction_percent=max(0, combined_reduction),
                predicted_rcr=new_rcr,
                predicted_level=new_level,
                achieves_target=achieves,
                target_level=target_level.get_label(),
                gap_to_target_percent=(1 - target_rcr / new_rcr) * 100 if new_rcr > target_rcr else 0,
                overall_feasibility=overall_feas,
                overall_cost="high" if overall_feas in (Feasibility.DIFFICULT, Feasibility.VERY_DIFFICULT) else "medium",
            )

            if achieves:
                achievable_paths.append(path)

            path_id += 1

    # === Sort paths ===
    # Sort by Hierarchy of Controls (管理の優先順位):
    # 1. Engineering controls first (工学的対策)
    # 2. Administrative controls second (管理的対策)
    # 3. PPE last - 最後の手段 (保護具)
    # Within same hierarchy level, sort by feasibility then reduction
    hierarchy_order = {
        ActionCategory.ENGINEERING: 0,
        ActionCategory.ADMINISTRATIVE: 1,
        ActionCategory.PPE: 2,  # Last resort
    }
    feasibility_order = {
        Feasibility.EASY: 0,
        Feasibility.MODERATE: 1,
        Feasibility.DIFFICULT: 2,
        Feasibility.VERY_DIFFICULT: 3,
    }

    def _get_path_hierarchy(path: RiskReductionPath) -> int:
        """Get hierarchy order for a path (lowest = highest priority)."""
        if not path.measures:
            return 999
        # For single measure: use its category
        # For combinations: use the LOWEST hierarchy (PPE demotes the whole path)
        return max(hierarchy_order.get(m.category, 999) for m in path.measures)

    def _is_combination(path: RiskReductionPath) -> int:
        """Return 1 for combinations, 0 for single measures (sort singles first)."""
        return 1 if len(path.measures) > 1 else 0

    achievable_paths.sort(key=lambda p: (
        _get_path_hierarchy(p),  # Hierarchy of controls first
        _is_combination(p),  # Single measures before combinations
        feasibility_order[p.overall_feasibility],  # Then by feasibility
        -p.combined_reduction_percent,  # Then by reduction (highest first)
    ))

    # Insufficient: sort by reduction (highest first)
    insufficient_paths.sort(key=lambda p: -p.combined_reduction_percent)

    # Assign priority
    for i, path in enumerate(achievable_paths):
        path.implementation_priority = i + 1
        path.path_id = i + 1

    # === Determine limitations ===
    # Include detailed explanations for WHY certain levels cannot be achieved
    # Note: Limitation is about engineering controls - RPE can still achieve lower levels
    limitations = []
    limitations_ja = []
    best_achievable = None

    if risk.min_achievable_rcr is not None:
        min_level = _rcr_to_level_label(risk.min_achievable_rcr)
        if risk.min_achievable_rcr > target_rcr:
            # Check if any achievable path reaches target WITHOUT RPE
            non_rpe_achievable = any(
                p.achieves_target and all(m.category != ActionCategory.PPE for m in p.measures)
                for p in achievable_paths
            )

            if non_rpe_achievable:
                # Target is achievable with engineering/admin controls - no limitation
                pass
            else:
                # Target requires RPE or is not achievable at all
                rpe_achievable = any(p.achieves_target for p in achievable_paths)

                # Check if current is at the engineering limit
                tolerance = 0.01
                at_limit = (
                    abs(current_rcr - risk.min_achievable_rcr) < tolerance * risk.min_achievable_rcr
                    or current_rcr <= risk.min_achievable_rcr
                )

                # Get reason from risk object if available
                reason_ja = getattr(risk, 'min_achievable_reason_ja', None)

                if rpe_achievable:
                    # Achievable with RPE but not without
                    if at_limit:
                        limitations.append(
                            f"Engineering controls optimized (at model floor); "
                            f"Level {min_level} is the engineering limit"
                        )
                        limitations_ja.append(
                            f"工学的対策は最適化済み（モデル下限に到達）; "
                            f"工学的対策のみではレベル{min_level}が限界"
                        )
                    else:
                        limitations.append(
                            f"Target level {target_level.get_label()} requires RPE; "
                            f"engineering controls alone can improve to Level {min_level}"
                        )
                        limitations_ja.append(
                            f"換気改善でレベル{min_level}まで低減可能; "
                            f"目標達成にはRPEも必要"
                        )
                else:
                    # Not achievable at all
                    limitations.append(
                        f"Target level {target_level.get_label()} not achievable; "
                        f"best possible is Level {min_level}"
                    )
                    limitations_ja.append(
                        f"目標レベル{target_level.get_label()}は達成不可; "
                        f"最良はレベル{min_level}"
                    )

                best_achievable = min_level

                # Add reason explanation if available
                if reason_ja:
                    limitations_ja.append(f"  → 理由: {reason_ja}")

                # Add detailed explanations from the risk object's limitations
                # These explain WHY the engineering limit exists (e.g., minimum floor)
                for lim in risk.limitations:
                    if lim.factor_name == "Minimum exposure floor":
                        if lim.description:
                            limitations.append(f"  → {lim.description}")
                        if lim.description_ja and not reason_ja:
                            # Only add if reason_ja not already provided
                            limitations_ja.append(f"  → {lim.description_ja}")
                        if lim.impact:
                            limitations.append(f"     {lim.impact}")
                        if lim.impact_ja:
                            limitations_ja.append(f"     {lim.impact_ja}")

    # === Build result ===
    easiest = achievable_paths[0] if achievable_paths else None
    most_effective = max(achievable_paths, key=lambda p: p.combined_reduction_percent) if achievable_paths else None

    return RiskReductionAnalysis(
        substance_cas=substance.cas_number,
        substance_name=substance.name_ja or substance.name_en or substance.cas_number,
        current_rcr=current_rcr,
        current_level=current_level,
        target_level=target_level.get_label(),
        target_rcr=target_rcr,
        reduction_needed_percent=reduction_needed,
        achievable_paths=achievable_paths,
        insufficient_paths=insufficient_paths[:5],  # Limit to top 5
        limitations=limitations,
        limitations_ja=limitations_ja,
        best_achievable_level=best_achievable,
        has_achievable_path=len(achievable_paths) > 0,
        easiest_path=easiest,
        most_effective_path=most_effective,
    )


def _calculate_minimality_score(path: RiskReductionPath) -> tuple:
    """
    Calculate minimality score for a path. Lower score = more minimal/preferred.

    Ranking criteria:
    1. Number of measures (fewer is better)
    2. Category priority following hierarchy of controls (engineering > admin > PPE)
    3. Total cost (lower is better)
    """
    num_measures = len(path.measures)

    # Category priority (lower = better per hierarchy of controls)
    category_priority = {
        ActionCategory.ENGINEERING: 1,
        ActionCategory.ADMINISTRATIVE: 2,
        ActionCategory.PPE: 3,
    }

    # Use the "worst" (highest) category in the path
    worst_category = max(
        (category_priority.get(m.category, 99) for m in path.measures),
        default=99
    )

    # Cost ranking
    cost_rank = {
        "low": 1,
        "medium": 2,
        "high": 3,
        "very_high": 4,
    }
    total_cost = sum(cost_rank.get(m.cost_estimate, 99) for m in path.measures)

    return (num_measures, worst_category, total_cost)


def get_minimum_measures_by_level(analysis: RiskReductionAnalysis) -> dict[str, RiskReductionPath]:
    """
    Get the minimum necessary measure for each achievable risk level.

    For each risk level that can be achieved, returns the "minimum" path
    based on: fewer measures, hierarchy of controls, and lower cost.

    Args:
        analysis: RiskReductionAnalysis from calculate_reduction_paths

    Returns:
        Dict mapping level label (e.g., "II-B", "II-A", "I") to minimum path
    """
    from collections import defaultdict

    # Group all paths by achieved level
    paths_by_level: dict[str, list[RiskReductionPath]] = defaultdict(list)

    for path in analysis.achievable_paths:
        paths_by_level[path.predicted_level].append(path)

    # For insufficient paths, also track what level they achieve
    for path in analysis.insufficient_paths:
        paths_by_level[path.predicted_level].append(path)

    # For each level, select the minimum path
    result = {}
    for level, paths in paths_by_level.items():
        # Sort by minimality score (lower is better)
        paths.sort(key=_calculate_minimality_score)
        result[level] = paths[0] if paths else None

    return result


def get_minimum_measures_summary(analysis: RiskReductionAnalysis) -> list[dict]:
    """
    Get a summary of minimum measures needed for each achievable level.

    Returns a list ordered from best level (I) to worst, showing only
    the minimum measure needed to achieve each level.

    Returns:
        List of dicts with level, path, and category info
    """
    minimum_by_level = get_minimum_measures_by_level(analysis)

    # Order levels from best to worst
    level_order = ["I", "II-A", "II-B", "III", "IV"]

    summary = []
    for level in level_order:
        if level in minimum_by_level:
            path = minimum_by_level[level]
            # Determine primary category
            categories = [m.category.value for m in path.measures]
            if len(path.measures) == 1:
                category_type = categories[0]
            else:
                category_type = "combination"

            summary.append({
                "level": level,
                "path": path,
                "category_type": category_type,
                "num_measures": len(path.measures),
                "description_ja": path.description_ja,
                "rcr": path.predicted_rcr,
            })

    return summary


def calculate_multi_risk_analysis(
    assessment_input: AssessmentInput,
    substance: Substance,
    inhalation_risk: Optional[InhalationRisk] = None,
    dermal_risk: Optional[DermalRisk] = None,
    physical_risk: Optional[PhysicalRisk] = None,
    target_inhalation: DetailedRiskLevel = DetailedRiskLevel.II_A,
    target_dermal: DetailedRiskLevel = DetailedRiskLevel.II_B,  # Level II-B for dermal
    target_physical: DetailedRiskLevel = DetailedRiskLevel.I,
    include_combinations: bool = True,
) -> MultiRiskAnalysis:
    """
    Calculate comprehensive risk reduction analysis for all risk types.

    Analyzes all 5 CREATE-SIMPLE risk types:
    - 吸入8時間 (8-hour TWA inhalation)
    - 吸入短時間 (STEL inhalation)
    - 経皮吸収 (Dermal absorption)
    - 合計 (Combined inhalation + dermal)
    - 危険性 (Physical hazards)

    Args:
        assessment_input: Current assessment input
        substance: Substance being assessed
        inhalation_risk: Inhalation risk result (includes STEL if available)
        dermal_risk: Dermal risk result
        physical_risk: Physical hazard risk result
        target_inhalation: Target level for inhalation risk
        target_dermal: Target level for dermal risk
        target_physical: Target level for physical risk
        include_combinations: Whether to include 2-measure combinations

    Returns:
        MultiRiskAnalysis with per-risk-type analysis
    """
    substance_name = substance.name_ja or substance.name_en or substance.cas_number

    # Track which risk type has the highest level
    controlling_risk_type: Optional[RiskType] = None
    max_risk_level = 0

    # === 1. Inhalation 8-hour TWA ===
    inhalation_8hr_analysis = None
    if inhalation_risk:
        current_level = RiskLevel.get_detailed_label(inhalation_risk.rcr)
        target_rcr = target_inhalation.get_rcr_threshold()
        needs_action = inhalation_risk.rcr > target_rcr

        if needs_action:
            # Use existing path calculation
            analysis = calculate_reduction_paths(
                assessment_input=assessment_input,
                substance=substance,
                risk=inhalation_risk,
                target_level=target_inhalation,
                include_combinations=include_combinations,
            )
            inhalation_8hr_analysis = RiskTypeAnalysis(
                risk_type=RiskType.INHALATION_8HR,
                risk_type_label=RISK_TYPE_LABELS_EN[RiskType.INHALATION_8HR],
                risk_type_label_ja=RISK_TYPE_LABELS_JA[RiskType.INHALATION_8HR],
                current_rcr=inhalation_risk.rcr,
                current_level=current_level,
                target_level=target_inhalation.get_label(),
                target_rcr=target_rcr,
                reduction_needed_percent=(1 - target_rcr / inhalation_risk.rcr) * 100 if inhalation_risk.rcr > 0 else 0,
                achievable_paths=analysis.achievable_paths,
                insufficient_paths=analysis.insufficient_paths,
                has_achievable_path=analysis.has_achievable_path,
                best_achievable_level=analysis.best_achievable_level,
                needs_action=True,
                limitations=analysis.limitations,
                limitations_ja=analysis.limitations_ja,
            )
        else:
            inhalation_8hr_analysis = RiskTypeAnalysis(
                risk_type=RiskType.INHALATION_8HR,
                risk_type_label=RISK_TYPE_LABELS_EN[RiskType.INHALATION_8HR],
                risk_type_label_ja=RISK_TYPE_LABELS_JA[RiskType.INHALATION_8HR],
                current_rcr=inhalation_risk.rcr,
                current_level=current_level,
                target_level=target_inhalation.get_label(),
                target_rcr=target_rcr,
                needs_action=False,
            )

        if inhalation_risk.risk_level > max_risk_level:
            max_risk_level = inhalation_risk.risk_level
            controlling_risk_type = RiskType.INHALATION_8HR

    # === 2. Inhalation STEL ===
    inhalation_stel_analysis = None
    if inhalation_risk and inhalation_risk.stel_rcr is not None:
        current_level = RiskLevel.get_simple_label(inhalation_risk.stel_rcr)
        target_rcr = target_inhalation.get_rcr_threshold()
        needs_action = inhalation_risk.stel_rcr > target_rcr

        if needs_action:
            # STEL uses same engineering controls but different exposure calculation
            # For now, show same paths with a note that STEL focuses on peak exposure
            inhalation_stel_analysis = RiskTypeAnalysis(
                risk_type=RiskType.INHALATION_STEL,
                risk_type_label=RISK_TYPE_LABELS_EN[RiskType.INHALATION_STEL],
                risk_type_label_ja=RISK_TYPE_LABELS_JA[RiskType.INHALATION_STEL],
                current_rcr=inhalation_risk.stel_rcr,
                current_level=current_level,
                target_level=target_inhalation.get_label(),
                target_rcr=target_rcr,
                reduction_needed_percent=(1 - target_rcr / inhalation_risk.stel_rcr) * 100 if inhalation_risk.stel_rcr > 0 else 0,
                needs_action=True,
                limitations=["STEL risk focuses on peak exposure; engineering controls most effective"],
                limitations_ja=["短時間暴露リスクはピーク暴露に焦点；工学的対策が最も効果的"],
            )
        else:
            inhalation_stel_analysis = RiskTypeAnalysis(
                risk_type=RiskType.INHALATION_STEL,
                risk_type_label=RISK_TYPE_LABELS_EN[RiskType.INHALATION_STEL],
                risk_type_label_ja=RISK_TYPE_LABELS_JA[RiskType.INHALATION_STEL],
                current_rcr=inhalation_risk.stel_rcr,
                current_level=current_level,
                target_level=target_inhalation.get_label(),
                target_rcr=target_rcr,
                needs_action=False,
            )

        if inhalation_risk.stel_risk_level and inhalation_risk.stel_risk_level > max_risk_level:
            max_risk_level = inhalation_risk.stel_risk_level
            controlling_risk_type = RiskType.INHALATION_STEL

    # === 3. Dermal Risk ===
    dermal_analysis = None
    if dermal_risk:
        current_level = RiskLevel.get_simple_label(dermal_risk.rcr)
        target_rcr = target_dermal.get_rcr_threshold()
        needs_action = dermal_risk.rcr > target_rcr

        # Dermal has specific control measures (gloves, protective clothing)
        dermal_measures = _get_dermal_measures(assessment_input, dermal_risk)

        if needs_action and dermal_measures:
            achievable_paths = []
            insufficient_paths = []
            path_id = 0

            for measure in dermal_measures:
                new_rcr = dermal_risk.rcr * measure["coefficient"]
                new_level = _rcr_to_level_label(new_rcr)
                achieves = new_rcr <= target_rcr

                path = RiskReductionPath(
                    path_id=path_id,
                    description=measure["label"],
                    description_ja=measure["label_ja"],
                    measures=[Measure(
                        category=measure["category"],
                        action=measure["action"],
                        action_label=measure["label"],
                        action_label_ja=measure["label_ja"],
                        reduction_percent=(1 - measure["coefficient"]) * 100,
                        coefficient=measure["coefficient"],
                        feasibility=measure["feasibility"],
                        cost_estimate=measure.get("cost", "low"),
                    )],
                    combined_reduction_percent=(1 - measure["coefficient"]) * 100,
                    predicted_rcr=new_rcr,
                    predicted_level=new_level,
                    achieves_target=achieves,
                    target_level=target_dermal.get_label(),
                    overall_feasibility=measure["feasibility"],
                    overall_cost=measure.get("cost", "low"),
                )

                if achieves:
                    achievable_paths.append(path)
                else:
                    insufficient_paths.append(path)
                path_id += 1

            dermal_analysis = RiskTypeAnalysis(
                risk_type=RiskType.DERMAL,
                risk_type_label=RISK_TYPE_LABELS_EN[RiskType.DERMAL],
                risk_type_label_ja=RISK_TYPE_LABELS_JA[RiskType.DERMAL],
                current_rcr=dermal_risk.rcr,
                current_level=current_level,
                target_level=target_dermal.get_label(),
                target_rcr=target_rcr,
                reduction_needed_percent=(1 - target_rcr / dermal_risk.rcr) * 100 if dermal_risk.rcr > 0 else 0,
                achievable_paths=achievable_paths,
                insufficient_paths=insufficient_paths,
                has_achievable_path=len(achievable_paths) > 0,
                needs_action=True,
            )
        else:
            dermal_analysis = RiskTypeAnalysis(
                risk_type=RiskType.DERMAL,
                risk_type_label=RISK_TYPE_LABELS_EN[RiskType.DERMAL],
                risk_type_label_ja=RISK_TYPE_LABELS_JA[RiskType.DERMAL],
                current_rcr=dermal_risk.rcr,
                current_level=current_level,
                target_level=target_dermal.get_label(),
                target_rcr=target_rcr,
                needs_action=needs_action,
            )

        if dermal_risk.risk_level > max_risk_level:
            max_risk_level = dermal_risk.risk_level
            controlling_risk_type = RiskType.DERMAL

    # === 4. Combined Risk (Inhalation + Dermal) ===
    combined_analysis = None
    if inhalation_risk and dermal_risk:
        combined_rcr = inhalation_risk.rcr + dermal_risk.rcr
        current_level = RiskLevel.get_detailed_label(combined_rcr)
        target_rcr = target_inhalation.get_rcr_threshold()  # Use inhalation target
        needs_action = combined_rcr > target_rcr

        # Determine which risk dominates
        dominant_risk = "inhalation" if inhalation_risk.rcr > dermal_risk.rcr else "dermal"
        dominant_percent = max(inhalation_risk.rcr, dermal_risk.rcr) / combined_rcr * 100

        limitations = [f"Combined risk dominated by {dominant_risk} ({dominant_percent:.0f}%)"]
        limitations_ja = [f"合計リスクは{('吸入' if dominant_risk == 'inhalation' else '経皮吸収')}が支配的（{dominant_percent:.0f}%）"]

        combined_analysis = RiskTypeAnalysis(
            risk_type=RiskType.COMBINED,
            risk_type_label=RISK_TYPE_LABELS_EN[RiskType.COMBINED],
            risk_type_label_ja=RISK_TYPE_LABELS_JA[RiskType.COMBINED],
            current_rcr=combined_rcr,
            current_level=current_level,
            target_level=target_inhalation.get_label(),
            target_rcr=target_rcr,
            reduction_needed_percent=(1 - target_rcr / combined_rcr) * 100 if combined_rcr > 0 else 0,
            needs_action=needs_action,
            limitations=limitations,
            limitations_ja=limitations_ja,
        )

        # Combined risk level
        combined_risk_level = RiskLevel.from_rcr(combined_rcr)
        if combined_risk_level > max_risk_level:
            max_risk_level = combined_risk_level
            controlling_risk_type = RiskType.COMBINED

    # === 5. Physical Risk ===
    physical_analysis = None
    if physical_risk:
        current_level = str(physical_risk.risk_level)
        needs_action = physical_risk.risk_level > target_physical

        # Physical risk doesn't use RCR - it's based on hazard conditions
        physical_analysis = RiskTypeAnalysis(
            risk_type=RiskType.PHYSICAL,
            risk_type_label=RISK_TYPE_LABELS_EN[RiskType.PHYSICAL],
            risk_type_label_ja=RISK_TYPE_LABELS_JA[RiskType.PHYSICAL],
            current_rcr=0.0,  # Not applicable for physical
            current_level=f"Level {physical_risk.risk_level.name}",
            target_level=f"Level {target_physical.name}",
            target_rcr=0.0,  # Not applicable
            needs_action=needs_action,
            limitations=["Physical hazard risk based on process conditions, not exposure"] if needs_action else [],
            limitations_ja=["危険性は暴露ではなく工程条件に基づく"] if needs_action else [],
        )

        if physical_risk.risk_level > max_risk_level:
            max_risk_level = physical_risk.risk_level
            controlling_risk_type = RiskType.PHYSICAL

    # === Build overall result ===
    overall_level = RiskLevel.get_detailed_label(max_risk_level) if max_risk_level else "I"
    overall_achievable = all([
        inhalation_8hr_analysis is None or not inhalation_8hr_analysis.needs_action or inhalation_8hr_analysis.has_achievable_path,
        dermal_analysis is None or not dermal_analysis.needs_action or dermal_analysis.has_achievable_path,
    ])

    return MultiRiskAnalysis(
        substance_cas=substance.cas_number,
        substance_name=substance_name,
        inhalation_8hr=inhalation_8hr_analysis,
        inhalation_stel=inhalation_stel_analysis,
        dermal=dermal_analysis,
        combined=combined_analysis,
        physical=physical_analysis,
        controlling_risk_type=controlling_risk_type,
        controlling_risk_label=RISK_TYPE_LABELS_EN.get(controlling_risk_type, "") if controlling_risk_type else "",
        controlling_risk_label_ja=RISK_TYPE_LABELS_JA.get(controlling_risk_type, "") if controlling_risk_type else "",
        overall_risk_level=overall_level,
        overall_achievable=overall_achievable,
    )


def _get_dermal_measures(assessment_input: AssessmentInput, dermal_risk: DermalRisk) -> list[dict]:
    """Get available dermal protection measures."""
    from ..models.assessment import GloveType

    measures = []
    current_glove = assessment_input.glove_type or GloveType.NONE

    # Glove upgrade
    if current_glove == GloveType.NONE:
        measures.append({
            "action": "gloves_resistant",
            "label": "Use chemical-resistant gloves",
            "label_ja": "耐透過性手袋の着用",
            "coefficient": 0.2,  # 80% reduction
            "category": ActionCategory.PPE,
            "feasibility": Feasibility.EASY,
            "cost": "low",
        })
    elif current_glove == GloveType.NON_RESISTANT:
        measures.append({
            "action": "gloves_upgrade",
            "label": "Switch to chemical-resistant gloves",
            "label_ja": "耐透過性手袋への変更",
            "coefficient": 0.2,
            "category": ActionCategory.PPE,
            "feasibility": Feasibility.EASY,
            "cost": "low",
        })

    # Glove training
    if not assessment_input.glove_training:
        measures.append({
            "action": "glove_training",
            "label": "Implement glove use training",
            "label_ja": "手袋使用教育の実施",
            "coefficient": 0.5,  # 50% reduction with proper training
            "category": ActionCategory.ADMINISTRATIVE,
            "feasibility": Feasibility.EASY,
            "cost": "low",
        })

    # Protective clothing
    measures.append({
        "action": "protective_clothing",
        "label": "Use protective clothing (long sleeves)",
        "label_ja": "保護衣の着用（長袖）",
        "coefficient": 0.7,  # 30% reduction by reducing exposed area
        "category": ActionCategory.PPE,
        "feasibility": Feasibility.EASY,
        "cost": "low",
    })

    return measures
