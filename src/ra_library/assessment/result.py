"""
AssessmentResult classes with multiple access patterns.

Supports:
- Property access: result.overall_risk_level
- Method access: result.get_risk_level()
- Dict-like access: result["overall_risk_level"]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..models.risk import InhalationRisk, DermalRisk, PhysicalRisk, RiskLevel, DetailedRiskLevel
from ..models.recommendation import Recommendation, EffectivenessLevel, RiskReductionAnalysis
from ..models.regulatory import RegulatoryInfo

if TYPE_CHECKING:
    from .builder import RiskAssessment
    from ..models.assessment import AssessmentInput


@dataclass
class ComponentResult:
    """Result for a single substance component."""

    cas_number: str
    name: str
    content_percent: float
    inhalation: InhalationRisk | None = None
    dermal: DermalRisk | None = None
    physical: PhysicalRisk | None = None
    regulatory_info: RegulatoryInfo | None = None
    calculation_errors: list[dict[str, str]] = field(default_factory=list)
    skipped_assessments: list[dict[str, str]] = field(default_factory=list)
    _substance: Any | None = field(default=None, repr=False)  # Substance for recommendations

    @property
    def risk_level(self) -> int:
        """Get highest risk level across all assessment types."""
        levels = []
        if self.inhalation:
            levels.append(int(self.inhalation.risk_level))
        if self.dermal:
            levels.append(int(self.dermal.risk_level))
        if self.physical:
            levels.append(int(self.physical.risk_level))
        return max(levels) if levels else 0

    @property
    def risk_label(self) -> str:
        """Get risk level label (I, II-A, II-B, III, IV)."""
        if self.inhalation:
            return RiskLevel.get_detailed_label(self.inhalation.rcr)
        if self.dermal:
            return RiskLevel.get_simple_label(self.dermal.rcr)
        if self.physical:
            return _level_to_label(int(self.physical.risk_level))
        if self.skipped_assessments:
            return "not_assessed"
        return str(self.risk_level)

    def get_inhalation_rcr(self) -> float | None:
        """Get inhalation RCR value."""
        return self.inhalation.rcr if self.inhalation else None

    def get_dermal_rcr(self) -> float | None:
        """Get dermal RCR value."""
        return self.dermal.rcr if self.dermal else None

    @property
    def stel_risk_level(self) -> int | None:
        """Get STEL risk level if available."""
        if self.inhalation and self.inhalation.stel_risk_level:
            return int(self.inhalation.stel_risk_level)
        return None

    @property
    def stel_rcr(self) -> float | None:
        """Get STEL RCR if available."""
        if self.inhalation and self.inhalation.stel_rcr:
            return self.inhalation.stel_rcr
        return None

    @property
    def has_stel_assessment(self) -> bool:
        """Check if STEL assessment was performed."""
        return self.inhalation is not None and self.inhalation.stel_rcr is not None

    def get_risk_level(self) -> int:
        """Get highest risk level."""
        return self.risk_level

    @property
    def has_skin_notation(self) -> bool:
        """Check if substance has skin notation (significant skin absorption)."""
        if self._substance is None:
            return False
        oel = getattr(self._substance, "oel", None)
        if oel is None:
            return False
        return getattr(oel, "skin_notation", False)

    @property
    def is_carcinogen(self) -> bool:
        """Check if substance is classified as carcinogenic (Category 1A, 1B, or 2)."""
        if self._substance is None:
            return False
        # Check direct is_carcinogen flag on Substance first
        if getattr(self._substance, "is_carcinogen", False):
            return True
        # Also check GHS classification
        ghs = getattr(self._substance, "ghs", None)
        if ghs is None:
            return False
        carc = getattr(ghs, "carcinogenicity", None)
        if carc is None:
            return False
        return carc in ["1A", "1B", "2", "Category 1A", "Category 1B", "Category 2"]

    @property
    def carcinogenicity_category(self) -> str | None:
        """Get carcinogenicity category if substance is carcinogenic."""
        if self._substance is None:
            return None
        ghs = getattr(self._substance, "ghs", None)
        if ghs is None:
            return None
        return getattr(ghs, "carcinogenicity", None)

    @property
    def is_mutagen(self) -> bool:
        """Check if substance is classified as mutagenic (Category 1A, 1B, or 2)."""
        if self._substance is None:
            return False
        ghs = getattr(self._substance, "ghs", None)
        if ghs is None:
            return False
        mutag = getattr(ghs, "germ_cell_mutagenicity", None)
        if mutag is None:
            return False
        return mutag in ["1A", "1B", "2", "Category 1A", "Category 1B", "Category 2"]

    @property
    def mutagenicity_category(self) -> str | None:
        """Get mutagenicity category if substance is mutagenic."""
        if self._substance is None:
            return None
        ghs = getattr(self._substance, "ghs", None)
        if ghs is None:
            return None
        return getattr(ghs, "germ_cell_mutagenicity", None)

    @property
    def warnings(self) -> list[str]:
        """Get list of important warnings for this substance."""
        warns = []
        if self.has_skin_notation:
            warns.append("SKIN NOTATION: Significant skin absorption - dermal protection required")
        if self.is_carcinogen:
            cat = self.carcinogenicity_category
            warns.append(f"CARCINOGEN (Category {cat}): Special controls required")
        if self.is_mutagen:
            cat = self.mutagenicity_category
            warns.append(f"MUTAGEN (Category {cat}): Special controls required")
        return warns

    @property
    def warnings_ja(self) -> list[str]:
        """Get list of important warnings in Japanese."""
        warns = []
        if self.has_skin_notation:
            warns.append("経皮吸収注意: 皮膚からの吸収が著しい - 皮膚保護が必要")
        if self.is_carcinogen:
            cat = self.carcinogenicity_category
            warns.append(f"発がん性物質 (区分{cat}): 特別管理が必要")
        if self.is_mutagen:
            cat = self.mutagenicity_category
            warns.append(f"変異原性物質 (区分{cat}): 特別管理が必要")
        return warns

    @property
    def has_calculation_errors(self) -> bool:
        """Check whether one or more risk-type calculations failed."""
        return len(self.calculation_errors) > 0

    @property
    def has_skipped_assessments(self) -> bool:
        """Check whether one or more risk-type assessments were intentionally skipped."""
        return len(self.skipped_assessments) > 0

    # =========================================================================
    # Per-risk-type minimum achievable levels
    # =========================================================================

    @property
    def inhalation_min_achievable_level(self) -> int | None:
        """Get minimum achievable risk level for inhalation."""
        if self.inhalation and self.inhalation.min_achievable_level is not None:
            return int(self.inhalation.min_achievable_level)
        return None

    @property
    def inhalation_min_achievable_rcr(self) -> float | None:
        """Get minimum achievable RCR for inhalation."""
        if self.inhalation and self.inhalation.min_achievable_rcr is not None:
            return self.inhalation.min_achievable_rcr
        return None

    @property
    def inhalation_level_one_achievable(self) -> bool:
        """Check if Level I is achievable for inhalation."""
        min_level = self.inhalation_min_achievable_level
        if min_level is None:
            return True
        return min_level == 1

    @property
    def dermal_min_achievable_level(self) -> int | None:
        """Get minimum achievable risk level for dermal."""
        if self.dermal and self.dermal.min_achievable_level is not None:
            return int(self.dermal.min_achievable_level)
        return None

    @property
    def dermal_min_achievable_rcr(self) -> float | None:
        """Get minimum achievable RCR for dermal."""
        if self.dermal and self.dermal.min_achievable_rcr is not None:
            return self.dermal.min_achievable_rcr
        return None

    @property
    def dermal_level_one_achievable(self) -> bool:
        """Check if Level I is achievable for dermal."""
        min_level = self.dermal_min_achievable_level
        if min_level is None:
            return True
        return min_level == 1

    @property
    def physical_min_achievable_level(self) -> int | None:
        """Get minimum achievable risk level for physical hazards."""
        if self.physical and self.physical.min_achievable_level is not None:
            return int(self.physical.min_achievable_level)
        return None

    @property
    def physical_level_one_achievable(self) -> bool:
        """Check if Level I is achievable for physical hazards."""
        if self.physical and hasattr(self.physical, 'level_one_achievable'):
            return self.physical.level_one_achievable
        min_level = self.physical_min_achievable_level
        if min_level is None:
            return True
        return min_level == 1

    # =========================================================================
    # Overall minimum achievable (worst across all risk types)
    # =========================================================================

    @property
    def min_achievable_rcr(self) -> float | None:
        """Get minimum achievable RCR (inhalation, for backwards compatibility)."""
        return self.inhalation_min_achievable_rcr

    @property
    def min_achievable_level(self) -> int | None:
        """Get minimum achievable risk level across all risk types."""
        levels = []
        if self.inhalation_min_achievable_level is not None:
            levels.append(self.inhalation_min_achievable_level)
        if self.dermal_min_achievable_level is not None:
            levels.append(self.dermal_min_achievable_level)
        if self.physical_min_achievable_level is not None:
            levels.append(self.physical_min_achievable_level)
        return max(levels) if levels else None

    @property
    def level_one_achievable(self) -> bool:
        """Check if Level I is achievable for all risk types."""
        return (
            self.inhalation_level_one_achievable
            and self.dermal_level_one_achievable
            and self.physical_level_one_achievable
        )

    @property
    def limitations(self) -> list[dict]:
        """Get list of limitations preventing better risk levels (all risk types)."""
        lims = []

        # Inhalation limitations
        if self.inhalation and self.inhalation.limitations:
            for lim in self.inhalation.limitations:
                lims.append({
                    "risk_type": "inhalation",
                    "factor": lim.factor_name,
                    "factor_ja": lim.factor_name_ja,
                    "description": lim.description,
                    "description_ja": lim.description_ja,
                    "impact": lim.impact,
                    "impact_ja": lim.impact_ja,
                })

        # Dermal limitations
        if self.dermal and self.dermal.limitations:
            for lim in self.dermal.limitations:
                lims.append({
                    "risk_type": "dermal",
                    "factor": lim.factor_name,
                    "factor_ja": lim.factor_name_ja,
                    "description": lim.description,
                    "description_ja": lim.description_ja,
                    "impact": lim.impact,
                    "impact_ja": lim.impact_ja,
                })

        # Physical limitations
        if self.physical and self.physical.limitations:
            for lim in self.physical.limitations:
                lims.append({
                    "risk_type": "physical",
                    "factor": lim.factor_name,
                    "factor_ja": lim.factor_name_ja,
                    "description": lim.description,
                    "description_ja": lim.description_ja,
                    "impact": lim.impact,
                    "impact_ja": lim.impact_ja,
                })

        return lims

    @property
    def limitations_summary(self) -> str:
        """Get summary of why Level I may not be achievable."""
        if self.level_one_achievable:
            return "Level I is achievable with proper controls"

        parts = []

        # Inhalation (8hr)
        if not self.inhalation_level_one_achievable:
            inh_level = self.inhalation_min_achievable_level
            parts.append(f"Inhalation (8hr): min Level {_level_to_label(inh_level) if inh_level else '?'}")
            if self.inhalation and self.inhalation.limitations:
                for lim in self.inhalation.limitations:
                    parts.append(f"  - {lim.factor_name}: {lim.impact}")

        # Dermal
        if not self.dermal_level_one_achievable:
            derm_level = self.dermal_min_achievable_level
            parts.append(f"Dermal: min Level {_level_to_label(derm_level) if derm_level else '?'}")
            if self.dermal and self.dermal.limitations:
                for lim in self.dermal.limitations:
                    parts.append(f"  - {lim.factor_name}: {lim.impact}")

        # Physical
        if not self.physical_level_one_achievable:
            phys_level = self.physical_min_achievable_level
            parts.append(f"Physical: min Level {_level_to_label(phys_level) if phys_level else '?'}")
            if self.physical and self.physical.limitations:
                for lim in self.physical.limitations:
                    parts.append(f"  - {lim.factor_name}: {lim.impact}")

        return "\n".join(parts)

    @property
    def limitations_summary_ja(self) -> str:
        """Get summary of why Level I may not be achievable (Japanese)."""
        if self.level_one_achievable:
            return "適切な対策によりレベルIは達成可能です"

        parts = []

        # Inhalation (8hr)
        if not self.inhalation_level_one_achievable:
            inh_level = self.inhalation_min_achievable_level
            parts.append(f"吸入 (8時間): 最小レベル {_level_to_label(inh_level) if inh_level else '?'}")
            if self.inhalation and self.inhalation.limitations:
                for lim in self.inhalation.limitations:
                    parts.append(f"  - {lim.factor_name_ja}: {lim.impact_ja}")

        # Dermal
        if not self.dermal_level_one_achievable:
            derm_level = self.dermal_min_achievable_level
            parts.append(f"経皮: 最小レベル {_level_to_label(derm_level) if derm_level else '?'}")
            if self.dermal and self.dermal.limitations:
                for lim in self.dermal.limitations:
                    parts.append(f"  - {lim.factor_name_ja}: {lim.impact_ja}")

        # Physical
        if not self.physical_level_one_achievable:
            phys_level = self.physical_min_achievable_level
            parts.append(f"物理: 最小レベル {_level_to_label(phys_level) if phys_level else '?'}")
            if self.physical and self.physical.limitations:
                for lim in self.physical.limitations:
                    parts.append(f"  - {lim.factor_name_ja}: {lim.impact_ja}")

        return "\n".join(parts)

    def __getitem__(self, key: str) -> Any:
        """Dict-like access to component data."""
        if key == "cas_number":
            return self.cas_number
        elif key == "name":
            return self.name
        elif key == "content_percent":
            return self.content_percent
        elif key == "risk_level":
            return self.risk_level
        elif key == "risk_label":
            return self.risk_label
        elif key == "inhalation":
            return self._inhalation_to_dict() if self.inhalation else None
        elif key == "dermal":
            return self._dermal_to_dict() if self.dermal else None
        elif key == "physical":
            return self._physical_to_dict() if self.physical else None
        elif key == "has_skin_notation":
            return self.has_skin_notation
        elif key == "is_carcinogen":
            return self.is_carcinogen
        elif key == "is_mutagen":
            return self.is_mutagen
        elif key == "warnings":
            return self.warnings
        elif key == "calculation_errors":
            return self.calculation_errors
        elif key == "has_calculation_errors":
            return self.has_calculation_errors
        elif key == "skipped_assessments":
            return self.skipped_assessments
        elif key == "has_skipped_assessments":
            return self.has_skipped_assessments
        elif key == "min_achievable_level":
            return self.min_achievable_level
        elif key == "min_achievable_rcr":
            return self.min_achievable_rcr
        elif key == "level_one_achievable":
            return self.level_one_achievable
        elif key == "limitations":
            return self.limitations
        elif key == "limitations_summary":
            return self.limitations_summary
        else:
            raise KeyError(f"Unknown key: {key}")

    def _inhalation_to_dict(self) -> dict:
        """Convert inhalation result to dict."""
        if not self.inhalation:
            return {}
        d = {
            "exposure_8hr": self.inhalation.exposure_8hr,
            "exposure_8hr_min": self.inhalation.exposure_8hr_min,
            "exposure_8hr_unit": self.inhalation.exposure_8hr_unit,
            "exposure_stel": self.inhalation.exposure_stel,
            "oel": self.inhalation.oel,
            "oel_unit": self.inhalation.oel_unit,
            "oel_source": self.inhalation.oel_source,
            "acrmax": self.inhalation.acrmax,
            "rcr": self.inhalation.rcr,
            "risk_level": int(self.inhalation.risk_level),
            "risk_label": RiskLevel.get_detailed_label(self.inhalation.rcr),
        }
        # Add STEL fields if available
        if self.inhalation.stel_oel is not None:
            d["stel_oel"] = self.inhalation.stel_oel
            d["stel_oel_unit"] = self.inhalation.stel_oel_unit
            d["stel_oel_source"] = self.inhalation.stel_oel_source
        if self.inhalation.stel_rcr is not None:
            d["stel_rcr"] = self.inhalation.stel_rcr
            d["stel_risk_level"] = int(self.inhalation.stel_risk_level) if self.inhalation.stel_risk_level else None
            d["stel_risk_label"] = RiskLevel.get_simple_label(self.inhalation.stel_rcr)
        return d

    def _dermal_to_dict(self) -> dict:
        """Convert dermal result to dict."""
        if not self.dermal:
            return {}
        return {
            "permeability_coefficient": self.dermal.permeability_coefficient,
            "dermal_flux": self.dermal.dermal_flux,
            "skin_absorption": self.dermal.skin_absorption,
            "rcr": self.dermal.rcr,
            "risk_level": int(self.dermal.risk_level),
            "risk_label": RiskLevel.get_simple_label(self.dermal.rcr),
        }

    def _physical_to_dict(self) -> dict:
        """Convert physical result to dict."""
        if not self.physical:
            return {}
        # Physical uses simple I/II/III/IV scale (not RCR-based)
        level_labels = {1: "I", 2: "II", 3: "III", 4: "IV"}
        return {
            "hazard_type": self.physical.hazard_type,
            "is_fixed_level_iv": self.physical.is_fixed_level_iv,
            "flash_point": self.physical.flash_point,
            "process_temperature": self.physical.process_temperature,
            "temperature_margin": self.physical.temperature_margin,
            "risk_level": int(self.physical.risk_level),
            "risk_label": level_labels.get(int(self.physical.risk_level), "IV"),
        }

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        d = {
            "cas_number": self.cas_number,
            "name": self.name,
            "content_percent": self.content_percent,
            "risk_level": self.risk_level,
            "risk_label": self.risk_label,
            "inhalation": self._inhalation_to_dict() if self.inhalation else None,
            "dermal": self._dermal_to_dict() if self.dermal else None,
            "physical": self._physical_to_dict() if self.physical else None,
            "has_skin_notation": self.has_skin_notation,
            "is_carcinogen": self.is_carcinogen,
            "is_mutagen": self.is_mutagen,
            "warnings": self.warnings,
            "calculation_errors": self.calculation_errors,
            "has_calculation_errors": self.has_calculation_errors,
            "skipped_assessments": self.skipped_assessments,
            "has_skipped_assessments": self.has_skipped_assessments,
            "level_one_achievable": self.level_one_achievable,
        }
        # Add achievability info if Level I is not achievable
        if not self.level_one_achievable:
            d["min_achievable_level"] = self.min_achievable_level
            d["min_achievable_rcr"] = self.min_achievable_rcr
            d["limitations"] = self.limitations
        return d


@dataclass
class AssessmentResult:
    """
    Result of risk assessment with multiple access patterns.

    Supports:
    - Property access: result.overall_risk_level
    - Method access: result.get_risk_level()
    - Dict-like access: result["overall_risk_level"]
    """

    components: dict[str, ComponentResult]
    assessment_input: AssessmentInput
    builder: RiskAssessment | None = None
    diagnostic_warnings: list[str] = field(default_factory=list, repr=False)
    _recommendations: list[Recommendation] | None = field(default=None, repr=False)
    # Target levels for recommendations (using DetailedRiskLevel)
    target_inhalation: DetailedRiskLevel = field(default=DetailedRiskLevel.I, repr=False)
    target_dermal: DetailedRiskLevel = field(default=DetailedRiskLevel.I, repr=False)
    target_physical: DetailedRiskLevel = field(default=DetailedRiskLevel.I, repr=False)

    @property
    def overall_risk_level(self) -> int:
        """Get overall risk level (highest among all components and mixed exposure)."""
        levels = [comp.risk_level for comp in self.components.values()]
        # Also consider mixed exposure levels
        if self.mixed_inhalation_risk_level is not None:
            levels.append(self.mixed_inhalation_risk_level)
        if self.mixed_dermal_risk_level is not None:
            levels.append(self.mixed_dermal_risk_level)
        return max(levels) if levels else 0

    @property
    def overall_risk_label(self) -> str:
        """Get overall risk level label with detailed II-A/II-B distinction for health risks."""
        # First check if physical hazard is the dominant risk
        max_physical_level = 0
        max_health_level = 0
        max_health_rcr = 0.0

        for comp in self.components.values():
            if comp.physical:
                max_physical_level = max(max_physical_level, int(comp.physical.risk_level))
            if comp.inhalation:
                inh_level = int(comp.inhalation.risk_level)
                max_health_level = max(max_health_level, inh_level)
                max_health_rcr = max(max_health_rcr, comp.inhalation.rcr)
                # Also consider STEL RCR
                if comp.inhalation.stel_rcr is not None:
                    max_health_rcr = max(max_health_rcr, comp.inhalation.stel_rcr)
            if comp.dermal:
                derm_level = int(comp.dermal.risk_level)
                max_health_level = max(max_health_level, derm_level)
                max_health_rcr = max(max_health_rcr, comp.dermal.rcr)

        # Also consider mixed exposure RCR
        if self.mixed_inhalation_rcr is not None:
            max_health_rcr = max(max_health_rcr, self.mixed_inhalation_rcr)
        if self.mixed_dermal_rcr is not None:
            max_health_rcr = max(max_health_rcr, self.mixed_dermal_rcr)

        # If physical hazard is dominant, use basic level label
        if max_physical_level > max_health_level:
            # But also check if mixed exposure exceeds physical level
            mixed_level = self.mixed_inhalation_risk_level or 0
            if mixed_level > max_physical_level:
                return RiskLevel.get_detailed_label(max_health_rcr)
            return _level_to_label(max_physical_level)

        # For health risks, use detailed label from RCR
        if max_health_rcr > 0:
            return RiskLevel.get_detailed_label(max_health_rcr)

        return _level_to_label(self.overall_risk_level)

    @property
    def recommendations(self) -> list[Recommendation]:
        """Get ranked improvement recommendations."""
        if self._recommendations is None:
            self._recommendations = self._generate_recommendations()
        return self._recommendations

    @property
    def mixed_inhalation_rcr(self) -> float | None:
        """
        Calculate mixed exposure RCR for inhalation (additive effect).

        Formula: Mixed RCR = Σ (Exposure_i / OEL_i) for all substances
        Reference: CREATE-SIMPLE Design v3.1.1, Section 5.4

        Returns:
            Sum of all individual inhalation RCRs, or None if no inhalation data
        """
        rcrs = []
        for comp in self.components.values():
            if comp.inhalation and comp.inhalation.rcr is not None:
                rcrs.append(comp.inhalation.rcr)
        return sum(rcrs) if rcrs else None

    @property
    def mixed_dermal_rcr(self) -> float | None:
        """
        Calculate mixed exposure RCR for dermal (additive effect).

        Formula: Mixed RCR = Σ (Exposure_i / DNEL_i) for all substances
        Reference: CREATE-SIMPLE Design v3.1.1, Section 5.4

        Returns:
            Sum of all individual dermal RCRs, or None if no dermal data
        """
        rcrs = []
        for comp in self.components.values():
            if comp.dermal and comp.dermal.rcr is not None:
                rcrs.append(comp.dermal.rcr)
        return sum(rcrs) if rcrs else None

    @property
    def mixed_inhalation_risk_level(self) -> int | None:
        """Get risk level for mixed inhalation exposure."""
        if self.mixed_inhalation_rcr is None:
            return None
        return int(RiskLevel.from_rcr(self.mixed_inhalation_rcr))

    @property
    def mixed_dermal_risk_level(self) -> int | None:
        """Get risk level for mixed dermal exposure."""
        if self.mixed_dermal_rcr is None:
            return None
        return int(RiskLevel.from_rcr(self.mixed_dermal_rcr))

    @property
    def has_mixed_exposure_concern(self) -> bool:
        """
        Check if mixed exposure is higher than any individual exposure.

        This flag indicates when additive effects may pose a greater risk
        than any single substance alone.
        """
        if len(self.components) < 2:
            return False

        # Check inhalation
        if self.mixed_inhalation_rcr is not None:
            max_individual = max(
                (comp.inhalation.rcr for comp in self.components.values() if comp.inhalation),
                default=0,
            )
            if self.mixed_inhalation_rcr > max_individual * 1.1:  # 10% threshold
                return True

        # Check dermal
        if self.mixed_dermal_rcr is not None:
            max_individual = max(
                (comp.dermal.rcr for comp in self.components.values() if comp.dermal),
                default=0,
            )
            if self.mixed_dermal_rcr > max_individual * 1.1:
                return True

        return False

    @property
    def level_one_achievable(self) -> bool:
        """Check if Level I is achievable for all components."""
        for comp in self.components.values():
            if not comp.level_one_achievable:
                return False
        return True

    @property
    def min_achievable_level(self) -> int:
        """Get the minimum achievable level across all components."""
        min_levels = []
        for comp in self.components.values():
            if comp.min_achievable_level is not None:
                min_levels.append(comp.min_achievable_level)
        return max(min_levels) if min_levels else 1

    @property
    def all_limitations(self) -> list[dict]:
        """Get all limitations from all components."""
        all_lims = []
        for cas, comp in self.components.items():
            for lim in comp.limitations:
                lim_with_cas = lim.copy()
                lim_with_cas["cas_number"] = cas
                lim_with_cas["substance_name"] = comp.name
                all_lims.append(lim_with_cas)
        return all_lims

    @property
    def limitations_summary(self) -> str:
        """Get summary of why Level I may not be achievable."""
        if self.level_one_achievable:
            return "Level I is achievable for all substances with proper controls"

        parts = ["Level I is NOT achievable for some substances:"]
        for cas, comp in self.components.items():
            if not comp.level_one_achievable:
                min_level = comp.min_achievable_level
                level_label = _level_to_label(min_level) if min_level else "Unknown"
                parts.append(f"\n{comp.name} ({cas}):")
                parts.append(f"  Minimum achievable level: {level_label}")
                if comp.inhalation and comp.inhalation.limitations:
                    for lim in comp.inhalation.limitations:
                        parts.append(f"  - {lim.factor_name}: {lim.impact}")

        return "\n".join(parts)

    @property
    def limitations_summary_ja(self) -> str:
        """Get summary of why Level I may not be achievable (Japanese)."""
        if self.level_one_achievable:
            return "適切な対策により全物質でレベルIは達成可能です"

        parts = ["一部の物質でレベルIは達成できません:"]
        for cas, comp in self.components.items():
            if not comp.level_one_achievable:
                min_level = comp.min_achievable_level
                level_label = _level_to_label(min_level) if min_level else "不明"
                parts.append(f"\n{comp.name} ({cas}):")
                parts.append(f"  到達可能な最小レベル: {level_label}")
                if comp.inhalation and comp.inhalation.limitations:
                    for lim in comp.inhalation.limitations:
                        parts.append(f"  - {lim.factor_name_ja}: {lim.impact_ja}")

        return "\n".join(parts)

    @property
    def errors(self) -> list[dict[str, str]]:
        """Get all calculation errors collected during assessment execution."""
        collected: list[dict[str, str]] = []
        for cas, comp in self.components.items():
            for error in comp.calculation_errors:
                collected.append({
                    "cas_number": cas,
                    "substance_name": comp.name,
                    "risk_type": error.get("risk_type", "unknown"),
                    "error_type": error.get("error_type", "Exception"),
                    "message": error.get("message", ""),
                })
        return collected

    @property
    def warnings(self) -> list[str]:
        """Get top-level warning summary including calculation diagnostics."""
        warnings = list(self.diagnostic_warnings)
        if not warnings and self.errors:
            for error in self.errors:
                warnings.append(
                    f"{error['cas_number']}: {error['risk_type']} failed "
                    f"({error['error_type']}: {error['message']})"
                )
        return warnings

    @property
    def regulations(self) -> list[str]:
        """Get list of applicable regulations."""
        from ..data import get_database

        all_regulations = []
        db = get_database()

        for cas in self.components.keys():
            regs = db.check_regulations(cas)
            if regs:
                if regs.get("tokka", {}).get("applies"):
                    tokka_class = regs["tokka"]["class"]
                    all_regulations.append(f"特定化学物質 第{tokka_class}類 ({cas})")
                if regs.get("organic_solvent", {}).get("applies"):
                    org_class = regs["organic_solvent"]["class"]
                    all_regulations.append(f"有機溶剤 第{org_class}種 ({cas})")
                if regs.get("skin_hazard"):
                    all_regulations.append(f"皮膚等障害化学物質 ({cas})")
                if regs.get("carcinogen"):
                    all_regulations.append(f"がん原性物質 ({cas})")

        return list(set(all_regulations))

    @property
    def critical_substance(self) -> tuple[str, ComponentResult] | None:
        """
        Get the critical substance (highest risk) and its component result.

        Returns:
            Tuple of (CAS number, ComponentResult) for the highest risk substance,
            or None if no components.
        """
        if not self.components:
            return None

        # Find substance with highest risk level, tie-break with highest RCR
        critical = None
        critical_cas = None
        max_risk = 0
        max_rcr = 0.0

        for cas, comp in self.components.items():
            comp_risk = comp.risk_level or 0
            comp_rcr = comp.inhalation.rcr if comp.inhalation else 0.0

            if comp_risk > max_risk or (comp_risk == max_risk and comp_rcr > max_rcr):
                max_risk = comp_risk
                max_rcr = comp_rcr
                critical = comp
                critical_cas = cas

        return (critical_cas, critical) if critical else None

    @property
    def critical_substance_name(self) -> str | None:
        """Get the name of the critical substance."""
        crit = self.critical_substance
        return crit[1].name if crit else None

    @property
    def risk_drivers(self) -> list[tuple[str, ComponentResult]]:
        """
        Get substances ordered by risk contribution (highest first).

        Returns:
            List of (CAS number, ComponentResult) tuples sorted by risk.
        """
        sorted_comps = sorted(
            self.components.items(),
            key=lambda x: (
                -(x[1].risk_level or 0),  # Higher risk first
                -(x[1].inhalation.rcr if x[1].inhalation else 0.0),  # Higher RCR first
            ),
        )
        return sorted_comps

    def get_recommendations_for_substance(self, cas: str) -> list[Recommendation]:
        """
        Get recommendations specific to a substance.

        Args:
            cas: CAS number of the substance

        Returns:
            List of recommendations that apply to this substance
        """
        return [
            rec for rec in self.recommendations
            if f"[{cas}]" in rec.action
        ]

    def get_risk_level(self) -> int:
        """Get overall risk level."""
        return self.overall_risk_level

    def get_risk_label(self) -> str:
        """Get overall risk level label."""
        return self.overall_risk_label

    def get_component(self, cas: str) -> ComponentResult | None:
        """Get result for a specific component."""
        return self.components.get(cas)

    def get_recommendations(self, top_n: int = 5) -> list[Recommendation]:
        """Get top N recommendations."""
        return self.recommendations[:top_n]

    def get_reduction_paths(
        self,
        cas: str | None = None,
        include_combinations: bool = True,
    ) -> dict[str, "RiskReductionAnalysis"]:
        """
        Get risk reduction path analysis for each substance.

        Shows achievable paths (single measures or combinations) to reach
        target risk levels, as well as insufficient measures and limitations.

        Args:
            cas: Optional CAS number to get paths for specific substance only
            include_combinations: Whether to include 2-measure combinations

        Returns:
            Dict mapping CAS numbers to RiskReductionAnalysis objects

        Example:
            paths = result.get_reduction_paths()
            for cas, analysis in paths.items():
                print(analysis.summary())  # Text summary
                print(analysis.summary_ja())  # Japanese summary
                # Or use structured data:
                for path in analysis.achievable_paths:
                    print(f"{path.description}: ↓{path.combined_reduction_percent}%")
        """
        from ..recommenders.paths import calculate_reduction_paths
        from ..models.recommendation import RiskReductionAnalysis

        result: dict[str, RiskReductionAnalysis] = {}

        for substance_cas, comp in self.components.items():
            if cas is not None and substance_cas != cas:
                continue

            if not comp.inhalation or not comp._substance:
                continue

            analysis = calculate_reduction_paths(
                assessment_input=self.assessment_input,
                substance=comp._substance,
                risk=comp.inhalation,
                target_level=self.target_inhalation,
                include_combinations=include_combinations,
                constraints=self.builder._constraints if self.builder else None,
            )
            result[substance_cas] = analysis

        return result

    def get_reduction_paths_summary(self, language: str = "en") -> str:
        """
        Get text summary of all reduction paths.

        Args:
            language: "en" for English, "ja" for Japanese

        Returns:
            Multi-line text summary of reduction options for all substances
        """
        paths = self.get_reduction_paths()
        summaries = []

        for cas, analysis in paths.items():
            if language == "ja":
                summaries.append(analysis.summary_ja())
            else:
                summaries.append(analysis.summary())

        return "\n\n".join(summaries)

    def to_toml(self) -> str:
        """
        Export assessment assumptions as TOML format.

        Returns structured data for reproducibility and documentation.

        Returns:
            TOML-formatted string of assessment inputs and constraints

        Example:
            toml_str = result.to_toml()
            with open("assessment.toml", "w") as f:
                f.write(toml_str)
        """
        from datetime import datetime

        lines = []
        lines.append("# CREATE-SIMPLE Risk Assessment Assumptions")
        lines.append(f"# Generated: {datetime.now().isoformat()}")
        lines.append("")

        # Meta section
        lines.append("[meta]")
        lines.append('version = "1.0"')
        lines.append(f'generated_at = "{datetime.now().isoformat()}"')
        lines.append(f'mode = "{self.assessment_input.mode.value}"')
        lines.append("")

        # Substances section
        for cas, comp in self.components.items():
            safe_cas = cas.replace("-", "_")
            lines.append(f"[substances.cas_{safe_cas}]")
            lines.append(f'cas_number = "{cas}"')
            lines.append(f'name = "{comp.name}"')
            lines.append(f"content_percent = {comp.content_percent}")
            if comp._substance:
                hl = comp._substance.get_hazard_level()
                lines.append(f'hazard_level = "{hl}"')
            lines.append("")

        # Conditions section
        inp = self.assessment_input
        lines.append("[conditions]")
        lines.append(f'property_type = "{inp.product_property.value}"')
        lines.append(f'amount = "{inp.amount_level.value}"')
        lines.append(f'ventilation = "{inp.ventilation.value}"')
        lines.append(f"control_velocity_verified = {str(inp.control_velocity_verified).lower()}")
        if self.builder and getattr(self.builder, '_control_velocity_auto_enabled', False):
            lines.append("control_velocity_auto_enabled = true")
        lines.append(f"is_spray = {str(inp.is_spray_operation).lower()}")
        lines.append(f'exposure_variation = "{inp.exposure_variation.value}"')
        lines.append("")

        # Duration section
        lines.append("[duration]")
        lines.append(f"working_hours = {inp.working_hours_per_day}")
        lines.append(f'frequency_type = "{inp.frequency_type}"')
        lines.append(f"frequency_value = {inp.frequency_value}")
        lines.append("")

        # Protection section
        lines.append("[protection]")
        rpe_val = inp.rpe_type.value if inp.rpe_type else "none"
        lines.append(f'rpe_type = "{rpe_val}"')
        lines.append(f"rpe_fit_tested = {str(inp.rpe_fit_tested).lower()}")
        glove_val = inp.glove_type.value if inp.glove_type else "none"
        lines.append(f'glove_type = "{glove_val}"')
        lines.append(f"glove_training = {str(inp.glove_training).lower()}")
        lines.append("")

        # Targets section
        lines.append("[targets]")
        lines.append(f'inhalation = "{self.target_inhalation.get_label()}"')
        lines.append(f'dermal = "{self.target_dermal.get_label()}"')
        lines.append(f'physical = "{self.target_physical.get_label()}"')
        lines.append("")

        # Constraints section (if any)
        if self.builder and self.builder._constraints:
            c = self.builder._constraints
            lines.append("[constraints]")
            if c.max_ventilation:
                lines.append(f'max_ventilation = "{c.max_ventilation.value}"')
            if c.min_frequency:
                lines.append(f'min_frequency_days = {c.min_frequency.get("days", 1)}')
                lines.append(f'min_frequency_period = "{c.min_frequency.get("period", "month")}"')
            if c.excluded_measures:
                excl_str = ", ".join(f'"{m}"' for m in c.excluded_measures)
                lines.append(f"excluded_measures = [{excl_str}]")
            if c.excluded_rpe:
                excl_str = ", ".join(f'"{r}"' for r in c.excluded_rpe)
                lines.append(f"excluded_rpe = [{excl_str}]")
            if c.max_rpe_apf:
                lines.append(f"max_rpe_apf = {c.max_rpe_apf}")
            if c.engineering_only:
                lines.append("engineering_only = true")
            if c.no_ppe:
                lines.append("no_ppe = true")
            if c.no_admin:
                lines.append("no_admin = true")
            lines.append("")

        return "\n".join(lines)

    def get_multi_risk_analysis(
        self,
        cas: str | None = None,
    ) -> dict[str, "MultiRiskAnalysis"]:
        """
        Get comprehensive multi-risk-type analysis for each substance.

        Shows analysis for all 5 CREATE-SIMPLE risk types:
        - 吸入8時間 (8-hour TWA inhalation)
        - 吸入短時間 (STEL inhalation)
        - 経皮吸収 (Dermal absorption)
        - 合計 (Combined inhalation + dermal)
        - 危険性 (Physical hazards)

        Args:
            cas: Optional CAS number to get analysis for specific substance only

        Returns:
            Dict mapping CAS numbers to MultiRiskAnalysis objects

        Example:
            analysis = result.get_multi_risk_analysis()
            for cas, multi in analysis.items():
                print(multi.summary_ja())  # Japanese summary
                if multi.controlling_risk_type:
                    print(f"Controlling: {multi.controlling_risk_label_ja}")
        """
        from ..recommenders.paths import calculate_multi_risk_analysis
        from ..models.recommendation import MultiRiskAnalysis

        result: dict[str, MultiRiskAnalysis] = {}

        for substance_cas, comp in self.components.items():
            if cas is not None and substance_cas != cas:
                continue

            if not comp._substance:
                continue

            analysis = calculate_multi_risk_analysis(
                assessment_input=self.assessment_input,
                substance=comp._substance,
                inhalation_risk=comp.inhalation,
                dermal_risk=comp.dermal,
                physical_risk=comp.physical,
                target_inhalation=self.target_inhalation,
                target_dermal=self.target_dermal,
                target_physical=self.target_physical,
            )
            result[substance_cas] = analysis

        return result

    def get_multi_risk_summary(self, language: str = "ja") -> str:
        """
        Get text summary of multi-risk analysis for all substances.

        Args:
            language: "en" for English, "ja" for Japanese (default)

        Returns:
            Multi-line text summary showing all risk types and their status
        """
        analyses = self.get_multi_risk_analysis()
        summaries = []

        for cas, analysis in analyses.items():
            if language == "ja":
                summaries.append(analysis.summary_ja())
            else:
                summaries.append(analysis.summary())

        return "\n\n".join(summaries)

    def to_csv(self, include_header: bool = True) -> str:
        """
        Export result to CSV format.

        Returns:
            CSV string with assessment results
        """
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        if include_header:
            writer.writerow([
                "CAS Number",
                "Substance Name",
                "Content %",
                "Risk Level",
                "Inhalation RCR",
                "Exposure (8hr)",
                "OEL",
                "OEL Source",
                "Dermal RCR",
                "Warnings",
            ])

        for cas, comp in self.components.items():
            inh = comp.inhalation
            derm = comp.dermal
            writer.writerow([
                cas,
                comp.name,
                comp.content_percent,
                comp.risk_level or "",
                f"{inh.rcr:.4f}" if inh else "",
                f"{inh.exposure_8hr:.6f} {inh.exposure_8hr_unit}" if inh else "",
                f"{inh.oel} {inh.oel_unit}" if inh else "",
                inh.oel_source if inh else "",
                f"{derm.rcr:.4f}" if derm else "",
                "; ".join(comp.warnings),
            ])

        return output.getvalue()

    def to_csv_file(self, filepath: str) -> None:
        """
        Export result to CSV file.

        Args:
            filepath: Path to output CSV file
        """
        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            f.write(self.to_csv())

    def to_dataframe(self):
        """
        Export result to pandas DataFrame.

        Returns:
            pandas DataFrame with assessment results

        Raises:
            ImportError: If pandas is not installed
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for DataFrame export. Install with: pip install pandas")

        rows = []
        for cas, comp in self.components.items():
            inh = comp.inhalation
            derm = comp.dermal
            rows.append({
                "cas_number": cas,
                "name": comp.name,
                "content_percent": comp.content_percent,
                "risk_level": comp.risk_level,
                "risk_label": comp.risk_label,
                "inhalation_rcr": inh.rcr if inh else None,
                "exposure_8hr": inh.exposure_8hr if inh else None,
                "exposure_unit": inh.exposure_8hr_unit if inh else None,
                "oel": inh.oel if inh else None,
                "oel_unit": inh.oel_unit if inh else None,
                "oel_source": inh.oel_source if inh else None,
                "stel_rcr": inh.stel_rcr if inh else None,
                "dermal_rcr": derm.rcr if derm else None,
                "dermal_absorption": derm.skin_absorption if derm else None,
                "has_skin_notation": comp.has_skin_notation,
                "is_carcinogen": comp.is_carcinogen,
                "warnings": "; ".join(comp.warnings),
            })

        return pd.DataFrame(rows)

    def to_excel(self, filepath: str) -> None:
        """
        Export result to Excel file.

        Args:
            filepath: Path to output Excel file

        Raises:
            ImportError: If pandas or openpyxl is not installed
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for Excel export. Install with: pip install pandas openpyxl")

        df = self.to_dataframe()
        df.to_excel(filepath, index=False, sheet_name="Assessment Results")

    def __getitem__(self, key: str) -> Any:
        """Dict-like access to result data."""
        if key == "overall_risk_level":
            return self.overall_risk_level
        elif key == "overall_risk_label":
            return self.overall_risk_label
        elif key == "components":
            return {cas: comp.to_dict() for cas, comp in self.components.items()}
        elif key == "recommendations":
            return [r.to_dict() if hasattr(r, "to_dict") else r for r in self.recommendations]
        elif key == "regulations":
            return self.regulations
        elif key == "warnings":
            return self.warnings
        elif key == "errors":
            return self.errors
        elif key == "level_one_achievable":
            return self.level_one_achievable
        elif key == "min_achievable_level":
            return self.min_achievable_level
        elif key == "limitations":
            return self.all_limitations
        elif key == "limitations_summary":
            return self.limitations_summary
        else:
            raise KeyError(f"Unknown key: {key}")

    def what_if(self, **changes: Any) -> AssessmentResult:
        """
        Run what-if analysis with modified conditions.

        Args:
            **changes: Conditions to change (e.g., ventilation="sealed")

        Returns:
            New AssessmentResult with recalculated values
        """
        if self.builder is None:
            raise ValueError("What-if analysis requires builder reference")

        # Clone the builder
        new_builder = self._clone_builder()

        # Apply changes
        if "amount" in changes:
            new_builder.with_conditions(amount=changes["amount"])
        if "ventilation" in changes:
            new_builder.with_conditions(ventilation=changes["ventilation"])
        if "control_velocity_verified" in changes:
            new_builder.with_conditions(control_velocity_verified=changes["control_velocity_verified"])
        if "is_spray" in changes:
            new_builder.with_conditions(is_spray=changes["is_spray"])
        if "dustiness" in changes:
            new_builder.with_conditions(dustiness=changes["dustiness"])
        if "hours" in changes:
            new_builder.with_duration(hours=changes["hours"])
        if "days_per_week" in changes:
            new_builder.with_duration(days_per_week=changes["days_per_week"])
        if "rpe" in changes:
            new_builder.with_protection(rpe=changes["rpe"])
        if "gloves" in changes:
            new_builder.with_protection(gloves=changes["gloves"])

        return new_builder.calculate()

    def compare_to(self, other: AssessmentResult) -> dict:
        """
        Compare this result to another result.

        Useful for comparing before/after scenarios or different control options.

        Args:
            other: Another AssessmentResult to compare against

        Returns:
            Dictionary with comparison details
        """
        comparison = {
            "overall": {
                "this_level": self.overall_risk_level,
                "other_level": other.overall_risk_level,
                "level_improved": self.overall_risk_level < other.overall_risk_level,
                "level_worsened": self.overall_risk_level > other.overall_risk_level,
            },
            "components": {},
        }

        # Compare common components
        for cas in set(self.components.keys()) | set(other.components.keys()):
            this_comp = self.components.get(cas)
            other_comp = other.components.get(cas)

            if this_comp is None or other_comp is None:
                continue  # Skip if component doesn't exist in both

            comp_comparison = {
                "name": this_comp.name,
                "this_level": this_comp.risk_level,
                "other_level": other_comp.risk_level,
                "level_improved": this_comp.risk_level < other_comp.risk_level if (this_comp.risk_level and other_comp.risk_level) else None,
            }

            # Compare inhalation
            if this_comp.inhalation and other_comp.inhalation:
                this_rcr = this_comp.inhalation.rcr
                other_rcr = other_comp.inhalation.rcr
                rcr_change = other_rcr - this_rcr
                rcr_change_pct = (rcr_change / other_rcr * 100) if other_rcr != 0 else 0

                comp_comparison["inhalation"] = {
                    "this_rcr": this_rcr,
                    "other_rcr": other_rcr,
                    "rcr_change": rcr_change,
                    "rcr_change_percent": rcr_change_pct,
                    "improved": this_rcr < other_rcr,
                    "this_exposure": this_comp.inhalation.exposure_8hr,
                    "other_exposure": other_comp.inhalation.exposure_8hr,
                }

            # Compare dermal
            if this_comp.dermal and other_comp.dermal:
                this_rcr = this_comp.dermal.rcr
                other_rcr = other_comp.dermal.rcr
                rcr_change = other_rcr - this_rcr

                comp_comparison["dermal"] = {
                    "this_rcr": this_rcr,
                    "other_rcr": other_rcr,
                    "rcr_change": rcr_change,
                    "improved": this_rcr < other_rcr,
                }

            comparison["components"][cas] = comp_comparison

        # Summary
        improved_count = sum(
            1 for comp in comparison["components"].values()
            if comp.get("level_improved")
        )
        worsened_count = sum(
            1 for comp in comparison["components"].values()
            if comp.get("level_improved") is False
        )

        comparison["summary"] = {
            "components_improved": improved_count,
            "components_worsened": worsened_count,
            "net_improvement": improved_count - worsened_count,
        }

        return comparison

    def compare_summary(self, other: AssessmentResult) -> str:
        """
        Get a human-readable summary comparing this result to another.

        Args:
            other: Another AssessmentResult to compare against

        Returns:
            Summary string
        """
        comp = self.compare_to(other)
        lines = ["Comparison Summary:"]

        # Overall change
        this_level = comp["overall"]["this_level"]
        other_level = comp["overall"]["other_level"]
        if comp["overall"]["level_improved"]:
            lines.append(f"  Overall: Level {other_level} → Level {this_level} (Improved)")
        elif comp["overall"]["level_worsened"]:
            lines.append(f"  Overall: Level {other_level} → Level {this_level} (Worsened)")
        else:
            lines.append(f"  Overall: Level {this_level} (No change)")

        # Component changes
        for cas, comp_data in comp["components"].items():
            inh = comp_data.get("inhalation", {})
            if inh:
                change = inh.get("rcr_change_percent", 0)
                direction = "↓" if inh.get("improved") else "↑" if change < 0 else "="
                lines.append(f"  {comp_data['name']}: RCR {inh['other_rcr']:.4f} → {inh['this_rcr']:.4f} ({direction} {abs(change):.1f}%)")

        return "\n".join(lines)

    def compare_summary_ja(self, other: AssessmentResult) -> str:
        """
        Get a Japanese summary comparing this result to another.

        Args:
            other: Another AssessmentResult to compare against

        Returns:
            Summary string in Japanese
        """
        comp = self.compare_to(other)
        lines = ["比較結果:"]

        # Overall change
        this_level = comp["overall"]["this_level"]
        other_level = comp["overall"]["other_level"]
        if comp["overall"]["level_improved"]:
            lines.append(f"  総合: レベル{other_level} → レベル{this_level} (改善)")
        elif comp["overall"]["level_worsened"]:
            lines.append(f"  総合: レベル{other_level} → レベル{this_level} (悪化)")
        else:
            lines.append(f"  総合: レベル{this_level} (変化なし)")

        # Component changes
        for cas, comp_data in comp["components"].items():
            inh = comp_data.get("inhalation", {})
            if inh:
                change = inh.get("rcr_change_percent", 0)
                direction = "低下" if inh.get("improved") else "上昇" if change < 0 else "同じ"
                lines.append(f"  {comp_data['name']}: RCR {inh['other_rcr']:.4f} → {inh['this_rcr']:.4f} ({direction} {abs(change):.1f}%)")

        return "\n".join(lines)

    def _clone_builder(self) -> RiskAssessment:
        """Clone the builder for what-if analysis."""
        from .builder import RiskAssessment as Builder

        new_builder = Builder()
        new_builder._substances = self.builder._substances.copy()
        new_builder._property_type = self.builder._property_type
        new_builder._amount_level = self.builder._amount_level
        new_builder._ventilation = self.builder._ventilation
        new_builder._control_velocity_verified = self.builder._control_velocity_verified
        new_builder._is_spray = self.builder._is_spray
        new_builder._work_area_size = self.builder._work_area_size
        new_builder._dustiness = self.builder._dustiness
        new_builder._working_hours = self.builder._working_hours
        new_builder._frequency_type = self.builder._frequency_type
        new_builder._frequency_value = self.builder._frequency_value
        new_builder._exposure_variation = self.builder._exposure_variation
        new_builder._rpe_type = self.builder._rpe_type
        new_builder._rpe_fit_tested = self.builder._rpe_fit_tested
        new_builder._glove_type = self.builder._glove_type
        new_builder._glove_training = self.builder._glove_training
        new_builder._skin_area = self.builder._skin_area
        new_builder._assess_inhalation = self.builder._assess_inhalation
        new_builder._assess_dermal = self.builder._assess_dermal
        new_builder._mode = self.builder._mode
        new_builder._verbose = self.builder._verbose
        new_builder._target_inhalation = self.builder._target_inhalation
        new_builder._target_dermal = self.builder._target_dermal
        new_builder._target_physical = self.builder._target_physical
        # Physical hazard conditions
        new_builder._assess_physical = self.builder._assess_physical
        new_builder._process_temperature = self.builder._process_temperature
        new_builder._has_ignition_sources = self.builder._has_ignition_sources
        new_builder._has_explosive_atmosphere = self.builder._has_explosive_atmosphere
        return new_builder

    def _generate_recommendations(self) -> list[Recommendation]:
        """Generate improvement recommendations based on target levels."""
        from ..recommenders.inhalation import get_inhalation_recommendations
        from ..recommenders.dermal import get_dermal_recommendations
        from ..recommenders.physical import get_physical_recommendations

        all_recs: list[Recommendation] = []

        # Get RCR thresholds from detailed target levels
        target_inh_rcr = self.target_inhalation.get_rcr_threshold()
        target_derm_rcr = self.target_dermal.get_rcr_threshold()
        target_phys_level = self.target_physical.to_basic_level()

        for cas, comp in self.components.items():
            # Inhalation recommendations
            if comp.inhalation and comp._substance:
                # Only recommend if current RCR exceeds target threshold
                if comp.inhalation.rcr > target_inh_rcr:
                    try:
                        rec_set = get_inhalation_recommendations(
                            assessment_input=self.assessment_input,
                            substance=comp._substance,
                            risk=comp.inhalation,
                            target_level=self.target_inhalation.to_basic_level(),
                            language=self.builder._language,
                            constraints=self.builder._constraints if self.builder else None,
                        )
                        for rec in rec_set.recommendations:
                            # Copy with CAS context added to action text
                            rec_copy = Recommendation(
                                action=f"[{cas}] {rec.action}",
                                action_ja=f"[{cas}] {rec.action_ja}" if rec.action_ja else "",
                                category=rec.category,
                                priority=rec.priority,
                                effectiveness=rec.effectiveness,
                                feasibility=rec.feasibility,
                                current_risk_level=rec.current_risk_level,
                                predicted_risk_level=rec.predicted_risk_level,
                                current_rcr=rec.current_rcr,
                                predicted_rcr=rec.predicted_rcr,
                                rcr_reduction_percent=rec.rcr_reduction_percent,
                                parameter_affected=rec.parameter_affected,
                                current_value=rec.current_value,
                                new_value=rec.new_value,
                                coefficient_change=rec.coefficient_change,
                                description=rec.description,
                                description_ja=rec.description_ja,
                                implementation_notes=rec.implementation_notes,
                                implementation_notes_ja=rec.implementation_notes_ja,
                                cost_estimate=rec.cost_estimate,
                                references=rec.references,
                            )
                            all_recs.append(rec_copy)
                    except Exception:
                        pass

            # Dermal recommendations
            if comp.dermal and comp._substance:
                # Only recommend if current RCR exceeds target threshold
                if comp.dermal.rcr > target_derm_rcr:
                    try:
                        rec_set = get_dermal_recommendations(
                            assessment_input=self.assessment_input,
                            substance=comp._substance,
                            risk=comp.dermal,
                            target_level=self.target_dermal.to_basic_level(),
                            language=self.builder._language,
                            constraints=self.builder._constraints if self.builder else None,
                        )
                        for rec in rec_set.recommendations:
                            # Copy with CAS context added to action text
                            rec_copy = Recommendation(
                                action=f"[{cas}] {rec.action}",
                                action_ja=f"[{cas}] {rec.action_ja}" if rec.action_ja else "",
                                category=rec.category,
                                priority=rec.priority,
                                effectiveness=rec.effectiveness,
                                feasibility=rec.feasibility,
                                current_risk_level=rec.current_risk_level,
                                predicted_risk_level=rec.predicted_risk_level,
                                current_rcr=rec.current_rcr,
                                predicted_rcr=rec.predicted_rcr,
                                rcr_reduction_percent=rec.rcr_reduction_percent,
                                parameter_affected=rec.parameter_affected,
                                current_value=rec.current_value,
                                new_value=rec.new_value,
                                coefficient_change=rec.coefficient_change,
                                description=rec.description,
                                description_ja=rec.description_ja,
                                implementation_notes=rec.implementation_notes,
                                implementation_notes_ja=rec.implementation_notes_ja,
                                cost_estimate=rec.cost_estimate,
                                references=rec.references,
                            )
                            all_recs.append(rec_copy)
                    except Exception:
                        pass

            # Physical recommendations
            if comp.physical and comp._substance:
                # Only recommend if current level exceeds target level
                if int(comp.physical.risk_level) > int(target_phys_level):
                    try:
                        rec_set = get_physical_recommendations(
                            assessment_input=self.assessment_input,
                            substance=comp._substance,
                            risk=comp.physical,
                            language=self.builder._language,
                            constraints=self.builder._constraints if self.builder else None,
                        )
                        for rec in rec_set.recommendations:
                            # Copy with CAS context added to action text
                            rec_copy = Recommendation(
                                action=f"[{cas}] {rec.action}",
                                action_ja=f"[{cas}] {rec.action_ja}" if rec.action_ja else "",
                                category=rec.category,
                                priority=rec.priority,
                                effectiveness=rec.effectiveness,
                                feasibility=rec.feasibility,
                                current_risk_level=rec.current_risk_level,
                                predicted_risk_level=rec.predicted_risk_level,
                                current_rcr=rec.current_rcr,
                                predicted_rcr=rec.predicted_rcr,
                                rcr_reduction_percent=rec.rcr_reduction_percent,
                                parameter_affected=rec.parameter_affected,
                                current_value=rec.current_value,
                                new_value=rec.new_value,
                                coefficient_change=rec.coefficient_change,
                                description=rec.description,
                                description_ja=rec.description_ja,
                                implementation_notes=rec.implementation_notes,
                                implementation_notes_ja=rec.implementation_notes_ja,
                                cost_estimate=rec.cost_estimate,
                                references=rec.references,
                            )
                            all_recs.append(rec_copy)
                    except Exception:
                        pass

        # Sort by effectiveness and priority
        effectiveness_order = {
            EffectivenessLevel.HIGH: 0, "high": 0,
            EffectivenessLevel.MEDIUM: 1, "medium": 1,
            EffectivenessLevel.LOW: 2, "low": 2,
        }
        all_recs.sort(key=lambda r: (effectiveness_order.get(r.effectiveness, 3), r.priority))

        # Re-prioritize
        for i, rec in enumerate(all_recs):
            rec.priority = i + 1

        return all_recs

    def summary(self) -> str:
        """Get human-readable summary in English."""
        # Identify critical substance
        crit = self.critical_substance
        critical_cas = crit[0] if crit else None

        lines = [
            f"Risk Assessment Summary",
            f"=" * 40,
            f"Overall Risk Level: {self.overall_risk_label} (Level {self.overall_risk_level})",
        ]

        # Highlight critical substance
        if crit and len(self.components) > 1:
            lines.append(f"Critical Substance: {crit[1].name} ({critical_cas})")

        lines.append(f"")
        lines.append(f"Components (by risk):")

        # Show components sorted by risk (highest first)
        for cas, comp in self.risk_drivers:
            is_critical = (cas == critical_cas) and len(self.components) > 1
            marker = " ⚠ CRITICAL" if is_critical else ""
            lines.append(f"  - {comp.name} ({cas}): {comp.content_percent}%{marker}")
            if comp.inhalation:
                lines.append(f"    Inhalation (8hr): RCR={comp.inhalation.rcr:.2f}, Level {comp.risk_label}")
                # Show STEL if available
                if comp.has_stel_assessment:
                    stel_label = RiskLevel.get_simple_label(comp.stel_rcr)
                    lines.append(f"    Inhalation (STEL): RCR={comp.stel_rcr:.2f}, Level {stel_label}")
            if comp.dermal:
                lines.append(f"    Dermal: RCR={comp.dermal.rcr:.2f}")
            if comp.physical:
                phys_level = _level_to_label(int(comp.physical.risk_level))
                lines.append(f"    Physical: {comp.physical.hazard_type}, Level {phys_level}")
            # Show warnings for this component
            for warn in comp.warnings:
                lines.append(f"    ⚠ {warn}")

            # Show per-substance recommendations for high-risk substances
            if comp.risk_level >= 3:  # Level III or higher
                sub_recs = self.get_recommendations_for_substance(cas)
                if sub_recs:
                    lines.append(f"    Recommendations for this substance:")
                    for rec in sub_recs[:2]:
                        reduction = f"(↓{rec.rcr_reduction_percent:.0f}%)" if rec.rcr_reduction_percent else ""
                        # Remove CAS prefix from action for per-substance display
                        action = rec.action.replace(f"[{cas}] ", "")
                        lines.append(f"      → {action} {reduction}")

        # Show mixed exposure if multiple substances
        if len(self.components) > 1:
            if self.mixed_inhalation_rcr is not None:
                mixed_level = _level_to_label(self.mixed_inhalation_risk_level or 0)
                lines.append(f"")
                lines.append(f"Mixed Exposure (Additive Effect):")
                lines.append(f"  Inhalation: Combined RCR={self.mixed_inhalation_rcr:.2f}, Level {mixed_level}")
                if self.has_mixed_exposure_concern:
                    lines.append(f"  ⚠ Mixed exposure exceeds individual risks - consider additional controls")

        if self.warnings:
            lines.append(f"")
            lines.append(f"Calculation Warnings:")
            for warning in self.warnings:
                lines.append(f"  ⚠ {warning}")

        if self.regulations:
            lines.append(f"")
            lines.append(f"Applicable Regulations:")
            for reg in self.regulations:
                lines.append(f"  - {reg}")

        if self.recommendations:
            lines.append(f"")
            lines.append(f"Top Recommendations (All Substances):")
            for rec in self.recommendations[:5]:
                reduction = f"(↓{rec.rcr_reduction_percent:.0f}%)" if rec.rcr_reduction_percent else ""
                lines.append(f"  {rec.priority}. {rec.action} {reduction}")

        # Show achievability information (per risk type)
        if not self.level_one_achievable:
            lines.append(f"")
            lines.append(f"Achievability:")
            min_level = _level_to_label(self.min_achievable_level)
            lines.append(f"  ⚠ Level I is NOT achievable")
            lines.append(f"  Minimum achievable level: {min_level}")
            for cas, comp in self.components.items():
                if not comp.level_one_achievable:
                    # Show per-risk-type details
                    risk_details = []
                    if not comp.inhalation_level_one_achievable:
                        inh_min = _level_to_label(comp.inhalation_min_achievable_level) if comp.inhalation_min_achievable_level else "?"
                        risk_details.append(f"Inhalation (8hr): {inh_min}")
                    if not comp.dermal_level_one_achievable:
                        derm_min = _level_to_label(comp.dermal_min_achievable_level) if comp.dermal_min_achievable_level else "?"
                        risk_details.append(f"Dermal: {derm_min}")
                    if not comp.physical_level_one_achievable:
                        phys_min = _level_to_label(comp.physical_min_achievable_level) if comp.physical_min_achievable_level else "?"
                        risk_details.append(f"Physical: {phys_min}")
                    if risk_details:
                        lines.append(f"  - {comp.name}: {', '.join(risk_details)}")

        return "\n".join(lines)

    def summary_ja(self) -> str:
        """Get human-readable summary in Japanese."""
        # Identify critical substance
        crit = self.critical_substance
        critical_cas = crit[0] if crit else None

        lines = [
            f"リスクアセスメント結果",
            f"=" * 40,
            f"総合リスクレベル: {self.overall_risk_label} (レベル {self.overall_risk_level})",
        ]

        # Highlight critical substance
        if crit and len(self.components) > 1:
            lines.append(f"クリティカル物質: {crit[1].name} ({critical_cas})")

        lines.append(f"")
        lines.append(f"成分 (リスク順):")

        # Show components sorted by risk (highest first)
        for cas, comp in self.risk_drivers:
            is_critical = (cas == critical_cas) and len(self.components) > 1
            marker = " ⚠ クリティカル" if is_critical else ""
            lines.append(f"  - {comp.name} ({cas}): {comp.content_percent}%{marker}")
            if comp.inhalation:
                lines.append(f"    吸入 (8時間): RCR={comp.inhalation.rcr:.2f}, レベル {comp.risk_label}")
                # Show STEL if available
                if comp.has_stel_assessment:
                    stel_label = RiskLevel.get_simple_label(comp.stel_rcr)
                    lines.append(f"    吸入 (短時間): RCR={comp.stel_rcr:.2f}, レベル {stel_label}")
            if comp.dermal:
                lines.append(f"    経皮: RCR={comp.dermal.rcr:.2f}")
            if comp.physical:
                phys_level = _level_to_label(int(comp.physical.risk_level))
                lines.append(f"    物理的危険性: {comp.physical.hazard_type}, レベル {phys_level}")
            # Show warnings for this component
            for warn in comp.warnings_ja:
                lines.append(f"    ⚠ {warn}")

            # Show per-substance recommendations for high-risk substances
            if comp.risk_level >= 3:  # Level III or higher
                sub_recs = self.get_recommendations_for_substance(cas)
                if sub_recs:
                    lines.append(f"    この物質への推奨対策:")
                    for rec in sub_recs[:2]:
                        reduction = f"(↓{rec.rcr_reduction_percent:.0f}%)" if rec.rcr_reduction_percent else ""
                        # Remove CAS prefix from action for per-substance display
                        action_ja = rec.action_ja.replace(f"[{cas}] ", "") if rec.action_ja else rec.action.replace(f"[{cas}] ", "")
                        lines.append(f"      → {action_ja} {reduction}")

        # Show mixed exposure if multiple substances
        if len(self.components) > 1:
            if self.mixed_inhalation_rcr is not None:
                mixed_level = _level_to_label(self.mixed_inhalation_risk_level or 0)
                lines.append(f"")
                lines.append(f"混合暴露（相加効果）:")
                lines.append(f"  吸入: 合計RCR={self.mixed_inhalation_rcr:.2f}, レベル {mixed_level}")
                if self.has_mixed_exposure_concern:
                    lines.append(f"  ⚠ 混合暴露が個別リスクを上回っています - 追加対策を検討してください")

        if self.warnings:
            lines.append(f"")
            lines.append(f"計算時の警告:")
            for warning in self.warnings:
                lines.append(f"  ⚠ {warning}")

        if self.regulations:
            lines.append(f"")
            lines.append(f"適用される規制:")
            for reg in self.regulations:
                lines.append(f"  - {reg}")

        if self.recommendations:
            lines.append(f"")
            lines.append(f"推奨対策 (全物質):")
            for rec in self.recommendations[:5]:
                reduction = f"(↓{rec.rcr_reduction_percent:.0f}%)" if rec.rcr_reduction_percent else ""
                action_ja = rec.action_ja if rec.action_ja else rec.action
                lines.append(f"  {rec.priority}. {action_ja} {reduction}")

        # Show achievability information (per risk type)
        if not self.level_one_achievable:
            lines.append(f"")
            lines.append(f"到達可能性:")
            min_level = _level_to_label(self.min_achievable_level)
            lines.append(f"  ⚠ レベルIは達成できません")
            lines.append(f"  到達可能な最小レベル: {min_level}")
            for cas, comp in self.components.items():
                if not comp.level_one_achievable:
                    # Show per-risk-type details
                    risk_details = []
                    if not comp.inhalation_level_one_achievable:
                        inh_min = _level_to_label(comp.inhalation_min_achievable_level) if comp.inhalation_min_achievable_level else "?"
                        risk_details.append(f"吸入 (8時間): {inh_min}")
                    if not comp.dermal_level_one_achievable:
                        derm_min = _level_to_label(comp.dermal_min_achievable_level) if comp.dermal_min_achievable_level else "?"
                        risk_details.append(f"経皮: {derm_min}")
                    if not comp.physical_level_one_achievable:
                        phys_min = _level_to_label(comp.physical_min_achievable_level) if comp.physical_min_achievable_level else "?"
                        risk_details.append(f"物理: {phys_min}")
                    if risk_details:
                        lines.append(f"  - {comp.name}: {', '.join(risk_details)}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        d = {
            "overall_risk_level": self.overall_risk_level,
            "overall_risk_label": self.overall_risk_label,
            "components": {cas: comp.to_dict() for cas, comp in self.components.items()},
            "regulations": self.regulations,
            "warnings": self.warnings,
            "errors": self.errors,
            "recommendations": [
                {
                    "priority": r.priority,
                    "action": r.action,
                    "action_ja": r.action_ja,
                    "category": str(r.category.value) if hasattr(r.category, 'value') else str(r.category),
                    "effectiveness": str(r.effectiveness.value) if hasattr(r.effectiveness, 'value') else str(r.effectiveness),
                    "rcr_reduction_percent": r.rcr_reduction_percent,
                    "predicted_risk_level": r.predicted_risk_level,
                }
                for r in self.recommendations
            ],
        }
        # Add mixed exposure if multiple components
        if len(self.components) > 1:
            d["mixed_exposure"] = {
                "inhalation_rcr": self.mixed_inhalation_rcr,
                "inhalation_risk_level": self.mixed_inhalation_risk_level,
                "dermal_rcr": self.mixed_dermal_rcr,
                "dermal_risk_level": self.mixed_dermal_risk_level,
                "has_concern": self.has_mixed_exposure_concern,
            }
        # Add achievability information
        d["achievability"] = {
            "level_one_achievable": self.level_one_achievable,
            "min_achievable_level": self.min_achievable_level,
        }
        if not self.level_one_achievable:
            d["achievability"]["limitations"] = self.all_limitations
        return d

    def to_json(self) -> str:
        """Convert to JSON string."""
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def full_report(self, language: str = "ja") -> str:
        """
        Generate comprehensive assessment report with all risk types,
        recommendations, and analysis.

        This is the standard output format for CREATE-SIMPLE risk assessment.

        Args:
            language: "ja" for Japanese (default), "en" for English

        Returns:
            Complete formatted assessment report
        """
        if language == "ja":
            return self._full_report_ja()
        else:
            return self._full_report_en()

    def _full_report_ja(self) -> str:
        """Generate Japanese full report."""
        lines = []
        sep = "=" * 60
        inp = self.assessment_input

        # === HEADER ===
        lines.append(sep)
        lines.append("CREATE-SIMPLE リスクアセスメント結果")
        lines.append(sep)
        lines.append("")

        # === 1. OVERALL ASSESSMENT (結論を最初に) ===
        lines.append("■ 総合評価")
        lines.append(sep)
        target_label = self._detailed_level_label(self.target_inhalation)
        level_indicator = self._risk_indicator(self.overall_risk_level)
        lines.append(f"  現状リスクレベル: {self.overall_risk_label} {level_indicator}")
        lines.append(f"  目標リスクレベル: {target_label}")
        # Check if target is achieved
        if self.overall_risk_level <= self.target_inhalation:
            lines.append(f"  判定: ✓ 目標達成 - {self._risk_judgment_ja(RiskLevel(self.overall_risk_level))}")
        else:
            lines.append(f"  判定: ✗ 目標未達 - {self._risk_judgment_ja(RiskLevel(self.overall_risk_level))}")
        lines.append("")

        # === 2. QUICK RECOMMENDATION SUMMARY (推奨対策を2番目に) ===
        paths_by_cas = self.get_reduction_paths()

        lines.append("■ 推奨対策")
        lines.append(sep)

        for cas, comp in self.components.items():
            lines.append(f"  【{comp.name}】")

            # Show current risk status for all assessed risk types
            lines.append("  〈現状リスク〉")
            if comp.inhalation:
                inh = comp.inhalation
                # 8-hour TWA uses detailed level (I, II-A, II-B, III, IV)
                detailed_level = RiskLevel.get_detailed_label(inh.rcr)
                ind = self._risk_indicator(inh.risk_level.value)
                lines.append(f"    吸入(8hr): レベル{detailed_level} {ind} (RCR={inh.rcr:.2f})")
                # STEL if available
                if inh.stel_rcr is not None and inh.stel_risk_level is not None:
                    stel_ind = self._risk_indicator(inh.stel_risk_level.value)
                    lines.append(f"    吸入(短時間): レベル{inh.stel_risk_level.name} {stel_ind} (RCR={inh.stel_rcr:.2f})")
            if comp.dermal:
                derm = comp.dermal
                ind = self._risk_indicator(derm.risk_level.value)
                # Dermal uses detailed level (I, II-A, II-B, III, IV)
                detailed_derm = RiskLevel.get_detailed_label(derm.rcr)
                lines.append(f"    経皮: レベル{detailed_derm} {ind} (RCR={derm.rcr:.2f})")
            if comp.physical:
                phys = comp.physical
                ind = self._risk_indicator(phys.risk_level.value)
                lines.append(f"    危険性: レベル{phys.risk_level.name} {ind}")
            lines.append("")

            # Inhalation recommendations
            analysis = paths_by_cas.get(cas)
            if analysis and comp.inhalation:
                if not analysis.has_achievable_path:
                    lines.append("  〈吸入リスク対策〉")
                    lines.append(f"    ⚠ 現在の条件では目標達成不可")
                    if analysis.best_achievable_level:
                        lines.append(f"      到達可能な最良レベル: {analysis.best_achievable_level}")
                else:
                    lines.append("  〈吸入リスク対策〉")
                    # Find best engineering option
                    eng_paths = [p for p in analysis.achievable_paths
                                if len(p.measures) == 1 and p.measures[0].category.value == "engineering"]
                    # Find best PPE option
                    ppe_paths = [p for p in analysis.achievable_paths
                                if len(p.measures) == 1 and p.measures[0].category.value == "ppe"]

                    if eng_paths:
                        best_eng = eng_paths[0]
                        status = "✓" if best_eng.achieves_target else "△"
                        lines.append(f"    {status} 工学的: {best_eng.description_ja} → レベル{best_eng.predicted_level}")

                    if ppe_paths:
                        best_ppe = ppe_paths[0]
                        lines.append(f"    ✓ PPE: {best_ppe.description_ja} → レベル{best_ppe.predicted_level}")

                    # Show limitation if engineering alone doesn't achieve target
                    if analysis.limitations_ja:
                        main_lim = analysis.limitations_ja[0].split(";")[0] if ";" in analysis.limitations_ja[0] else analysis.limitations_ja[0]
                        lines.append(f"    ⚠ {main_lim}")
                lines.append("")

            # Dermal recommendations
            if comp.dermal:
                lines.append("  〈経皮リスク対策〉")
                if comp.dermal.risk_level.value <= 2:  # Level I or II
                    lines.append(f"    ✓ 現状で目標達成")
                else:
                    lines.append(f"    → 耐透過性手袋の着用を推奨")
                lines.append("")

            # Physical recommendations
            if comp.physical:
                lines.append("  〈危険性対策〉")
                if comp.physical.risk_level.value <= 2:  # Level I or II
                    lines.append(f"    ✓ 現状で目標達成")
                else:
                    lines.append(f"    → 着火源の管理、換気の確保を推奨")
                lines.append("")

        # === 3. ASSESSMENT CONDITIONS (評価条件) ===
        lines.append("■ 評価条件")
        lines.append("-" * 40)
        # Show preset if used
        if self.builder and getattr(self.builder, '_preset_name', None):
            from ..presets import get_preset
            preset = get_preset(self.builder._preset_name)
            lines.append(f"  プリセット: {preset.description}")
        product_form_ja = {"liquid": "液体", "solid": "固体", "gas": "気体"}.get(inp.product_property.value, inp.product_property.value)
        lines.append(f"  製品形態: {product_form_ja}")
        lines.append(f"  取扱量: {self._amount_label_ja(inp.amount_level.value)}")
        lines.append(f"  換気条件: {self._vent_label_ja(inp.ventilation.value)}")
        if inp.control_velocity_verified:
            auto_note = ""
            if self.builder and getattr(self.builder, '_control_velocity_auto_enabled', False):
                auto_note = "（局所排気のため自動適用）"
            lines.append(f"  制御風速: 確認済み{auto_note}")
        hours = inp.working_hours_per_day
        hours_str = str(int(hours)) if hours == int(hours) else f"{hours:.1f}"
        lines.append(f"  作業時間: {hours_str}時間/日")
        if inp.frequency_type == "weekly":
            lines.append(f"  作業頻度: {inp.frequency_value}日/週")
        else:
            lines.append(f"  作業頻度: {inp.frequency_value}日/月（週未満）")
        lines.append(f"  暴露変動: {self._variation_label_ja(inp.exposure_variation.value)}")
        if inp.rpe_type and inp.rpe_type.value != "none":
            lines.append(f"  呼吸用保護具: {self._rpe_label_ja(inp.rpe_type.value)}")
        lines.append(f"  評価モード: {'実施レポート' if inp.mode.value == 'report' else 'RAシート'}")
        lines.append("")

        # === 4. SUBSTANCE DETAILS (物質詳細) ===
        for cas, comp in self.components.items():
            lines.append(sep)
            lines.append(f"■ 物質詳細: {comp.name} (CAS: {cas})")
            lines.append(f"  含有率: {comp.content_percent}%")
            if comp._substance:
                hl = comp._substance.get_hazard_level()
                if hl:
                    lines.append(f"  {self._hazard_level_label_ja(hl)}")
            lines.append(sep)
            lines.append("")

            # --- INHALATION 8HR ---
            if comp.inhalation:
                inh = comp.inhalation
                lines.append("【吸入リスク（8時間TWA）】")
                lines.append("-" * 40)
                lines.append(f"  暴露推定値: {inh.exposure_8hr:.4f} {inh.exposure_8hr_unit}")
                if inh.exposure_8hr_min:
                    lines.append(f"  暴露範囲: {inh.exposure_8hr_min:.4f} - {inh.exposure_8hr:.4f} {inh.exposure_8hr_unit}")
                lines.append(f"  OEL: {inh.oel} {inh.oel_unit} ({inh.oel_source})")
                if inh.acrmax:
                    lines.append(f"  ACRmax: {inh.acrmax} {inh.acrmax_unit} (管理目標濃度)")
                lines.append(f"  {self._rcr_basis_ja(inh.oel, inh.acrmax, inh.oel_unit)}")
                lines.append(f"  RCR: {inh.rcr:.4f}")
                # 8-hour TWA uses detailed level (I, II-A, II-B, III, IV)
                detailed_level = RiskLevel.get_detailed_label(inh.rcr)
                level_indicator = self._risk_indicator(inh.risk_level.value)
                lines.append(f"  リスクレベル: {detailed_level} {level_indicator}")
                lines.append(f"  判定: {self._risk_judgment_ja(inh.risk_level)}")
                lines.append("")

                # Show engineering control limit with contextual explanation
                if inh.min_achievable_rcr and inh.min_achievable_rcr > 0.1:
                    lines.extend(self._format_engineering_limit_ja(
                        current_rcr=inh.rcr,
                        min_achievable_rcr=inh.min_achievable_rcr,
                        min_achievable_reason_ja=getattr(inh, 'min_achievable_reason_ja', None),
                        target_rcr=self.target_inhalation.get_rcr_threshold() if self.target_inhalation else 0.1,
                    ))

            # --- INHALATION STEL ---
            if comp.inhalation and comp.inhalation.stel_rcr is not None:
                inh = comp.inhalation
                lines.append("【吸入リスク（短時間暴露）】")
                lines.append("-" * 40)
                if inh.exposure_stel:
                    lines.append(f"  短時間暴露推定値: {inh.exposure_stel:.4f} {inh.exposure_stel_unit}")
                if inh.stel_oel:
                    lines.append(f"  STEL OEL: {inh.stel_oel} {inh.stel_oel_unit} ({inh.stel_oel_source})")
                lines.append(f"  STEL RCR: {inh.stel_rcr:.4f}")
                if inh.stel_risk_level:
                    lines.append(f"  リスクレベル: {inh.stel_risk_level.name}")
                lines.append("")

            # --- DERMAL ---
            if comp.dermal:
                derm = comp.dermal
                lines.append("【経皮吸収リスク】")
                lines.append("-" * 40)
                lines.append(f"  経皮吸収フラックス: {derm.dermal_flux:.6f} mg/cm²/hr")
                lines.append(f"  RCR: {derm.rcr:.4f}")
                # Dermal uses detailed level (I, II-A, II-B, III, IV)
                detailed_derm = RiskLevel.get_detailed_label(derm.rcr)
                lines.append(f"  リスクレベル: {detailed_derm}")
                lines.append(f"  判定: {self._risk_judgment_ja(derm.risk_level)}")
                lines.append("")

            # --- COMBINED ---
            if comp.inhalation and comp.dermal:
                combined_rcr = comp.inhalation.rcr + comp.dermal.rcr
                combined_level = RiskLevel.from_rcr(combined_rcr)
                dominant = "吸入" if comp.inhalation.rcr > comp.dermal.rcr else "経皮吸収"
                lines.append("【合計リスク（吸入＋経皮）】")
                lines.append("-" * 40)
                lines.append(f"  合計RCR: {combined_rcr:.4f}")
                # Combined uses detailed level (I, II-A, II-B, III, IV)
                detailed_combined = RiskLevel.get_detailed_label(combined_rcr)
                lines.append(f"  リスクレベル: {detailed_combined}")
                lines.append(f"  支配的リスク: {dominant}")
                lines.append("")

            # --- PHYSICAL ---
            if comp.physical:
                phys = comp.physical
                lines.append("【危険性（爆発・火災等）】")
                lines.append("-" * 40)
                lines.append(f"  リスクレベル: {phys.risk_level.name}")
                lines.append(f"  判定: {self._risk_judgment_ja(phys.risk_level)}")
                lines.append("")

        # === MINIMUM MEASURES PER LEVEL ===
        from ..recommenders.paths import get_minimum_measures_summary

        lines.append(sep)
        lines.append("■ レベル別 最小対策")
        lines.append(sep)
        lines.append("")

        for cas, analysis in paths_by_cas.items():
            comp = self.components.get(cas)
            current_indicator = self._risk_indicator_from_label(analysis.current_level)
            lines.append(f"【{comp.name if comp else cas}】")
            lines.append(f"現状: レベル{analysis.current_level} {current_indicator} (RCR={analysis.current_rcr:.2f})")
            lines.append("")

            # Get minimum measures for each level
            summary = get_minimum_measures_summary(analysis)

            # Category labels
            cat_labels = {
                "engineering": "工学的",
                "administrative": "管理的",
                "ppe": "PPE",
                "combination": "組合せ",
            }

            for item in summary:
                level = item["level"]
                path = item["path"]
                cat = item["category_type"]
                rcr = item["rcr"]
                desc = item["description_ja"]

                # Mark if this is the target level
                is_target = level == analysis.target_level
                target_mark = " ← 目標" if is_target else ""

                # Level indicator
                level_ind = self._risk_indicator_from_label(level)

                lines.append(f"〈レベル{level}{target_mark}〉")
                lines.append(f"  最小対策: {desc}")
                lines.append(f"  種別: {cat_labels.get(cat, cat)}, RCR={rcr:.2f} {level_ind}")
                lines.append("")

            # Limitations
            if analysis.limitations_ja:
                lines.append("〈制限事項〉")
                for i, lim in enumerate(analysis.limitations_ja):
                    if i == 0:
                        lines.append(f"  ⚠ {lim}")
                    else:
                        clean_lim = lim.replace("  → ", "").replace("     ", "")
                        lines.append(f"    {clean_lim}")
                lines.append("")

        # Show constraint exclusions if any
        if self.builder and self.builder._constraints:
            exclusions = self.builder._constraints.get_excluded_summary()
            if exclusions:
                lines.append("〈制約による除外〉")
                for excl in exclusions:
                    lines.append(f"  • {excl}")
                lines.append("")

        # === REGULATORY NOTES ===
        if self.regulations:
            lines.append(sep)
            lines.append("■ 法規制情報")
            lines.append(sep)
            for reg in self.regulations:
                lines.append(f"  • {reg}")
                # Add context for common regulations
                context = self._regulation_context_ja(reg)
                if context:
                    lines.append(f"    {context}")
            lines.append("")

        # === FOOTER ===
        lines.append(sep)
        lines.append("※ この結果はCREATE-SIMPLE手法による推定値です。")
        lines.append("※ 実際の暴露濃度は作業環境測定により確認してください。")
        lines.append(sep)

        return "\n".join(lines)

    def _full_report_en(self) -> str:
        """Generate English full report."""
        lines = []
        sep = "=" * 60

        # === HEADER ===
        lines.append(sep)
        lines.append("CREATE-SIMPLE Risk Assessment Report")
        lines.append(sep)
        lines.append("")

        # === ASSESSMENT CONDITIONS ===
        lines.append("■ Assessment Conditions")
        lines.append("-" * 40)
        inp = self.assessment_input
        # Show preset if used
        if self.builder and getattr(self.builder, '_preset_name', None):
            from ..presets import get_preset
            preset = get_preset(self.builder._preset_name)
            lines.append(f"  Preset: {preset.description_en}")
        product_form_en = {"liquid": "Liquid", "solid": "Solid", "gas": "Gas"}.get(inp.product_property.value, inp.product_property.value)
        lines.append(f"  Product form: {product_form_en}")
        lines.append(f"  Amount: {inp.amount_level.value}")
        lines.append(f"  Ventilation: {inp.ventilation.value}")
        if inp.control_velocity_verified:
            lines.append(f"  Control velocity: Verified")
        lines.append(f"  Working hours: {inp.working_hours_per_day} hours/day")
        if inp.frequency_type == "weekly":
            lines.append(f"  Frequency: {inp.frequency_value} days/week")
        else:
            lines.append(f"  Frequency: {inp.frequency_value} days/month")
        lines.append(f"  Exposure variation: {inp.exposure_variation.value}")
        if inp.rpe_type and inp.rpe_type.value != "none":
            lines.append(f"  RPE: {inp.rpe_type.value}")
        lines.append(f"  Mode: {'Report' if inp.mode.value == 'report' else 'RA Sheet'}")
        lines.append("")

        # === FOR EACH SUBSTANCE ===
        for cas, comp in self.components.items():
            lines.append(sep)
            lines.append(f"■ Substance: {comp.name} (CAS: {cas})")
            lines.append(f"  Content: {comp.content_percent}%")
            lines.append(sep)
            lines.append("")

            # --- INHALATION 8HR ---
            if comp.inhalation:
                inh = comp.inhalation
                lines.append("[Inhalation Risk (8-hour TWA)]")
                lines.append("-" * 40)
                lines.append(f"  Exposure estimate: {inh.exposure_8hr:.4f} {inh.exposure_8hr_unit}")
                lines.append(f"  OEL: {inh.oel} {inh.oel_unit} ({inh.oel_source})")
                if inh.acrmax:
                    lines.append(f"  ACRmax: {inh.acrmax} {inh.acrmax_unit}")
                lines.append(f"  RCR: {inh.rcr:.4f}")
                lines.append(f"  Risk Level: {inh.risk_level.name}")
                lines.append(f"  Judgment: {self._risk_judgment_en(inh.risk_level)}")
                lines.append("")

                if inh.min_achievable_rcr and inh.min_achievable_rcr > 0.1:
                    lines.append(f"  * Minimum achievable RCR: {inh.min_achievable_rcr:.4f}")
                    lines.append(f"    Minimum achievable level: {inh.min_achievable_level.name}")
                    lines.append("")

            # --- INHALATION STEL ---
            if comp.inhalation and comp.inhalation.stel_rcr is not None:
                inh = comp.inhalation
                lines.append("[Inhalation Risk (STEL)]")
                lines.append("-" * 40)
                if inh.exposure_stel:
                    lines.append(f"  STEL exposure: {inh.exposure_stel:.4f} {inh.exposure_stel_unit}")
                if inh.stel_oel:
                    lines.append(f"  STEL OEL: {inh.stel_oel} {inh.stel_oel_unit}")
                lines.append(f"  STEL RCR: {inh.stel_rcr:.4f}")
                if inh.stel_risk_level:
                    lines.append(f"  Risk Level: {inh.stel_risk_level.name}")
                lines.append("")

            # --- DERMAL ---
            if comp.dermal:
                derm = comp.dermal
                lines.append("[Dermal Absorption Risk]")
                lines.append("-" * 40)
                lines.append(f"  Dermal flux: {derm.dermal_flux:.6f} mg/cm²/hr")
                lines.append(f"  RCR: {derm.rcr:.4f}")
                lines.append(f"  Risk Level: {derm.risk_level.name}")
                lines.append("")

            # --- COMBINED ---
            if comp.inhalation and comp.dermal:
                combined_rcr = comp.inhalation.rcr + comp.dermal.rcr
                combined_level = RiskLevel.from_rcr(combined_rcr)
                dominant = "inhalation" if comp.inhalation.rcr > comp.dermal.rcr else "dermal"
                lines.append("[Combined Risk (Inhalation + Dermal)]")
                lines.append("-" * 40)
                lines.append(f"  Combined RCR: {combined_rcr:.4f}")
                lines.append(f"  Risk Level: {combined_level.name}")
                lines.append(f"  Dominant risk: {dominant}")
                lines.append("")

            # --- PHYSICAL ---
            if comp.physical:
                phys = comp.physical
                lines.append("[Physical Hazards]")
                lines.append("-" * 40)
                lines.append(f"  Risk Level: {phys.risk_level.name}")
                lines.append("")

            lines.append("[Substance Overall]")
            lines.append("-" * 40)
            lines.append(f"  Overall Risk Level: {comp.risk_label}")
            lines.append("")

        # === OVERALL ===
        lines.append(sep)
        lines.append("■ Overall Assessment")
        lines.append(sep)
        lines.append(f"  Overall Risk Level: {self.overall_risk_label}")
        lines.append(f"  Judgment: {self._risk_judgment_en(RiskLevel(self.overall_risk_level))}")
        lines.append("")

        # === RECOMMENDATIONS ===
        lines.append(sep)
        lines.append("■ Risk Reduction Options")
        lines.append(sep)
        lines.append("")

        paths_by_cas = self.get_reduction_paths()
        for cas, analysis in paths_by_cas.items():
            comp = self.components.get(cas)
            lines.append(f"[{comp.name if comp else cas}]")
            lines.append(f"Current: Level {analysis.current_level} (RCR={analysis.current_rcr:.2f})")
            lines.append(f"Target: Level {analysis.target_level} (RCR≤{analysis.target_rcr})")
            lines.append("")

            if analysis.achievable_paths:
                lines.append("<Achievable Options (by Hierarchy of Controls)>")
                for i, p in enumerate(analysis.achievable_paths[:5]):
                    cat = p.measures[0].category.value if p.measures else "N/A"
                    lines.append(f"  {i+1}. [{cat}] {p.description}")
                    lines.append(f"     → Level {p.predicted_level} (RCR={p.predicted_rcr:.4f})")
                lines.append("")

            if analysis.limitations:
                lines.append("<Limitations>")
                for lim in analysis.limitations:
                    lines.append(f"  ⚠ {lim}")
                lines.append("")

        # === FOOTER ===
        lines.append(sep)
        lines.append("* This result is an estimate based on CREATE-SIMPLE methodology.")
        lines.append("* Actual exposure should be confirmed by workplace monitoring.")
        lines.append(sep)

        return "\n".join(lines)

    def _vent_label_ja(self, vent: str) -> str:
        """Get Japanese ventilation label."""
        labels = {
            "none": "無換気",
            "basic": "一般換気",
            "industrial": "工業的換気/屋外",
            "local_ext": "局所排気（外付け式）",
            "local_enc": "局所排気（囲い式）",
            "sealed": "密閉系",
        }
        return labels.get(vent, vent)

    def _variation_label_ja(self, var: str) -> str:
        """Get Japanese exposure variation label."""
        labels = {
            "constant": "常時",
            "intermittent": "間欠",
            "brief": "短時間",
        }
        return labels.get(var, var)

    def _risk_judgment_ja(self, level: "RiskLevel") -> str:
        """Get Japanese risk judgment."""
        judgments = {
            1: "許容範囲（追加対策不要）",
            2: "許容範囲（ただし管理継続）",
            3: "対策必要（リスク低減措置を講じること）",
            4: "直ちに対策必要（作業中止を含む）",
        }
        return judgments.get(int(level), "不明")

    def _risk_judgment_en(self, level: "RiskLevel") -> str:
        """Get English risk judgment."""
        judgments = {
            1: "Acceptable (no additional action required)",
            2: "Acceptable (continue monitoring)",
            3: "Action required (implement risk reduction measures)",
            4: "Immediate action required (including work suspension)",
        }
        return judgments.get(int(level), "Unknown")

    def _amount_label_ja(self, amount: str) -> str:
        """Get Japanese amount label."""
        labels = {
            "large": "大量",
            "medium": "中量",
            "small": "少量",
            "minute": "微量",
            "trace": "極微量",
        }
        return labels.get(amount, amount)

    def _rpe_label_ja(self, rpe: str) -> str:
        """Get Japanese RPE label."""
        labels = {
            "none": "なし",
            "loose_fit_11": "ルーズフィット型（APF11）",
            "loose_fit_20": "ルーズフィット型（APF20）",
            "loose_fit_25": "ルーズフィット型（APF25）",
            "tight_fit_10": "半面形（APF10）",
            "tight_fit_50": "全面形（APF50）",
            "tight_fit_100": "電動ファン付き（APF100）",
            "tight_fit_1000": "送気マスク（APF1000）",
            "tight_fit_10000": "自給式空気呼吸器（APF10000）",
        }
        return labels.get(rpe, rpe)

    def _detailed_level_label(self, level: "DetailedRiskLevel") -> str:
        """Get detailed level label (I, II-A, II-B, III, IV)."""
        from ..models.risk import DetailedRiskLevel
        if isinstance(level, DetailedRiskLevel):
            return level.get_label()
        # Fallback for int (shouldn't happen but just in case)
        labels = {1: "I", 2: "II-A", 3: "II-B", 4: "III", 5: "IV"}
        return labels.get(level, str(level))

    def _risk_indicator(self, level: int) -> str:
        """Get risk level emoji indicator."""
        indicators = {
            1: "🟢",  # Green - acceptable
            2: "🟡",  # Yellow - monitor
            3: "🟠",  # Orange - action required
            4: "🔴",  # Red - immediate action
        }
        return indicators.get(level, "")

    def _risk_indicator_from_label(self, label: str) -> str:
        """Get risk level emoji from label string."""
        if label.startswith("I") and not label.startswith("II") and not label.startswith("IV"):
            return "🟢"
        elif label.startswith("II"):
            return "🟡"
        elif label.startswith("III"):
            return "🟠"
        elif label.startswith("IV"):
            return "🔴"
        return ""

    def _format_engineering_limit_ja(
        self,
        current_rcr: float,
        min_achievable_rcr: float,
        min_achievable_reason_ja: str | None,
        target_rcr: float = 0.1,
    ) -> list[str]:
        """
        Format engineering control limit explanation with context.

        Shows different messages based on:
        - Whether current RCR is at the engineering limit or can be improved
        - Why the limit exists (model floor vs constraint)
        - What to do next (RPE needed for target)
        """
        lines = []
        min_detailed = RiskLevel.get_detailed_label(min_achievable_rcr)

        # Tolerance for comparing floats
        tolerance = 0.01
        at_limit = abs(current_rcr - min_achievable_rcr) < tolerance * min_achievable_rcr or current_rcr <= min_achievable_rcr

        lines.append("  ※ 工学的対策の限界:")

        if at_limit:
            # Already at engineering limit
            lines.append(f"     現在のRCR ({current_rcr:.2f}) は工学的対策として最適化済み")
        else:
            # Room for engineering improvement
            lines.append(f"     換気改善により RCR {min_achievable_rcr:.2f} (レベル{min_detailed}) まで低減可能")
            lines.append(f"     現在: {current_rcr:.2f} → 改善後: {min_achievable_rcr:.2f}")

        # Explain why (use reason_ja if available, else default)
        if min_achievable_reason_ja:
            lines.append(f"     理由: {min_achievable_reason_ja}")
        else:
            lines.append(f"     到達可能な最良レベル: {min_detailed}")

        # What to do next
        if min_achievable_rcr > target_rcr:
            lines.append(f"     → 目標レベル達成には呼吸用保護具（RPE）が必要です")

        lines.append("")
        return lines

    def _category_label_ja(self, category: str) -> str:
        """Get Japanese category label."""
        labels = {
            "engineering": "工学的",
            "administrative": "管理的",
            "ppe": "PPE",
        }
        return labels.get(category, category)

    def _regulation_context_ja(self, reg: str) -> str:
        """Get context explanation for regulation in Japanese."""
        if "皮膚等障害化学物質" in reg:
            return "→ 保護手袋の使用が義務付けられています"
        elif "特定化学物質" in reg:
            return "→ 特別管理物質として管理が必要です"
        elif "有機溶剤" in reg:
            return "→ 有機溶剤作業主任者の選任が必要です"
        elif "発がん性" in reg or "発がん物質" in reg:
            return "→ 特別な管理措置が必要です"
        elif "変異原性" in reg:
            return "→ 遺伝毒性への対策が必要です"
        elif "生殖毒性" in reg:
            return "→ 女性労働者への配慮が必要です"
        return ""

    def _format_reduction(self, reduction: float) -> str:
        """Format reduction percentage with appropriate precision."""
        if reduction >= 99.95:
            return ">99.9%"
        elif reduction >= 99.0:
            return f"{reduction:.1f}%"
        elif reduction >= 10.0:
            return f"{reduction:.0f}%"
        else:
            return f"{reduction:.1f}%"

    def _rcr_basis_ja(self, oel: float, acrmax: float | None, oel_unit: str) -> str:
        """Explain which value is used for RCR calculation."""
        if acrmax is None:
            return f"RCR基準: OEL ({oel} {oel_unit})"
        elif acrmax < oel:
            return f"RCR基準: ACRmax（OEL {oel}より低いため）"
        else:
            return f"RCR基準: OEL（ACRmax {acrmax}より低いため）"

    def _dustiness_label_ja(self, dustiness: str) -> str:
        """Get Japanese dustiness label."""
        labels = {
            "high": "高",
            "medium": "中",
            "low": "低",
        }
        return labels.get(dustiness, dustiness)

    def _volatility_label_ja(self, volatility: str) -> str:
        """Get Japanese volatility label."""
        labels = {
            "very_high": "極高",
            "high": "高",
            "medium": "中",
            "low": "低",
            "very_low": "極低",
        }
        return labels.get(volatility, volatility)

    def _hazard_level_label_ja(self, hl: str) -> str:
        """Get Japanese hazard level description."""
        descriptions = {
            "HL1": "HL1（低有害性）",
            "HL2": "HL2",
            "HL3": "HL3",
            "HL4": "HL4（変異原性）",
            "HL5": "HL5（発がん性）",
        }
        return descriptions.get(hl, hl)


def _level_to_label(level: int) -> str:
    """Convert numeric level to label."""
    labels = {1: "I", 2: "II", 3: "III", 4: "IV"}
    return labels.get(level, str(level))
