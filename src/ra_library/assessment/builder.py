"""
RiskAssessment builder class with fluent interface.

Provides a chainable API for constructing and executing chemical risk assessments.
"""

from __future__ import annotations

import logging
from typing import Any

from ..models.substance import Substance, PropertyType
from ..models.assessment import (
    AssessmentInput,
    AmountLevel,
    VentilationLevel,
    ExposureVariation,
    SkinArea,
    GloveType,
    RPEType,
    AssessmentMode,
)
from ..models.risk import DetailedRiskLevel
from ..models.constraints import AssessmentConstraints
from ..data import get_database, lookup_substance, to_substance_model, get_regulatory_info
from ..presets import get_preset, WorkPreset, PRESETS
from .result import AssessmentResult, ComponentResult

logger = logging.getLogger(__name__)


class RiskAssessment:
    """
    Fluent builder for chemical risk assessment.

    Example:
        result = (
            RiskAssessment()
            .add_substance("7440-06-4", content=50.0)
            .add_substance("50-00-0", content=10.0)
            .with_conditions(
                property_type="solid",
                amount="medium",
                ventilation="local_external",
            )
            .with_duration(hours=6.0, days_per_week=5)
            .with_protection(rpe="half_mask", gloves="nitrile")
            .calculate()
        )
    """

    def __init__(self) -> None:
        """Initialize empty assessment builder."""
        self._substances: list[tuple[Substance, float]] = []
        self._property_type: PropertyType = PropertyType.SOLID
        self._amount_level: AmountLevel = AmountLevel.MEDIUM
        self._ventilation: VentilationLevel = VentilationLevel.INDUSTRIAL
        self._control_velocity_verified: bool = False
        self._control_velocity_auto_enabled: bool = False  # Track if auto-enabled for draft
        self._is_spray: bool = False
        self._work_area_size: str | None = None  # Only for liquids
        self._dustiness: str | None = None  # Only for solids: high, medium, low
        self._working_hours: float = 8.0
        self._frequency_type: str = "weekly"
        self._frequency_value: int = 5
        self._exposure_variation: ExposureVariation = ExposureVariation.CONSTANT
        self._rpe_type: RPEType | None = None
        self._rpe_fit_tested: bool = False
        self._glove_type: GloveType | None = None
        self._glove_training: bool = False
        self._skin_area: SkinArea = SkinArea.HANDS_BOTH
        self._assess_inhalation: bool = True
        self._assess_dermal: bool = True  # Calculate all risk types by default
        self._assess_physical: bool = False  # Physical requires explicit opt-in
        self._mode: AssessmentMode = AssessmentMode.RA_SHEET
        self._verbose: bool = True
        # Physical hazard conditions
        self._process_temperature: float | None = None
        self._has_ignition_sources: bool = False
        self._has_explosive_atmosphere: bool = False
        self._has_organic_matter: bool = False
        self._has_air_water_contact: bool = False
        # Target levels for recommendations (using DetailedRiskLevel)
        self._target_inhalation: DetailedRiskLevel = DetailedRiskLevel.I
        self._target_dermal: DetailedRiskLevel = DetailedRiskLevel.I
        self._target_physical: DetailedRiskLevel = DetailedRiskLevel.I
        # Constraints for recommendations
        self._constraints: AssessmentConstraints | None = None
        # Preset tracking
        self._preset_name: str | None = None
        # Exposure calculation options
        self._ignore_minimum_floor: bool = False
        # Output language for recommendations
        self._language: str = "en"

    def use_preset(
        self,
        preset_name: str | WorkPreset,
    ) -> RiskAssessment:
        """
        Apply a work scenario preset.

        Presets provide pre-configured conditions, duration, protection,
        and constraints for common work scenarios.

        Available presets:
        - Laboratory: lab_organic, lab_organic_minute, lab_powder, lab_catalyst, lab_analytical
        - Production: production_batch, production_batch_enclosed, production_continuous,
                      production_powder, production_packaging
        - Maintenance: maintenance_cleaning, maintenance_cleaning_enclosed, maintenance_tank
        - Spray: spray_painting, spray_coating

        Japanese aliases also supported:
        - 有機合成研究室, 粉体研究室, 触媒研究室, 分析研究室
        - バッチ製造, 連続製造, 粉体製造, 包装作業
        - 清掃作業, タンク内作業, スプレー塗装

        Example:
            result = (
                RiskAssessment()
                .use_preset("lab_organic")
                .add_substance("108-88-3", content=100.0)
                .calculate()
            )

            # Override specific values after preset
            result = (
                RiskAssessment()
                .use_preset("lab_organic")
                .add_substance("108-88-3", content=50.0)
                .with_duration(hours=2.0)  # Override preset's 4 hours
                .calculate()
            )

        Args:
            preset_name: Preset name string or WorkPreset object

        Returns:
            Self for chaining
        """
        if isinstance(preset_name, str):
            preset = get_preset(preset_name)
        else:
            preset = preset_name

        self._preset_name = preset.name

        # Apply conditions
        self._property_type = _parse_property_type(preset.property_type)
        self._amount_level = _parse_amount_level(preset.amount)
        self._ventilation = _parse_ventilation(preset.ventilation)
        self._control_velocity_verified = preset.control_velocity_verified

        if preset.dustiness:
            self._dustiness = preset.dustiness
        if preset.work_area_size:
            self._work_area_size = preset.work_area_size
        if preset.is_spray:
            self._is_spray = preset.is_spray
        if preset.process_temperature is not None:
            self._process_temperature = preset.process_temperature

        # Apply duration
        self._working_hours = preset.hours
        if preset.days_per_week is not None:
            self._frequency_type = "weekly"
            self._frequency_value = preset.days_per_week
        elif preset.days_per_month is not None:
            self._frequency_type = "monthly"
            self._frequency_value = preset.days_per_month

        # Apply protection
        if preset.gloves:
            self._glove_type = _parse_glove_type(preset.gloves)
        self._glove_training = preset.glove_training
        if preset.rpe:
            self._rpe_type = _parse_rpe_type(preset.rpe)

        # Apply constraints
        if preset.max_ventilation or preset.excluded_rpe or preset.no_admin:
            max_vent = None
            if preset.max_ventilation:
                max_vent = _parse_ventilation(preset.max_ventilation)

            self._constraints = AssessmentConstraints(
                max_ventilation=max_vent,
                excluded_rpe=preset.excluded_rpe,
                no_admin=preset.no_admin,
            )

        return self

    def add_substance(
        self,
        substance: str | Substance,
        content: float,
    ) -> RiskAssessment:
        """
        Add a substance to the assessment.

        Args:
            substance: CAS number (auto-lookup) or Substance object
            content: Content percentage (0-100)

        Returns:
            Self for chaining
        """
        if isinstance(substance, str):
            # Auto-lookup from database
            db = get_database()
            sub_model = db.get_as_model(substance)
            if sub_model is None:
                raise ValueError(f"Substance not found in database: {substance}")
            self._substances.append((sub_model, content))
        else:
            # Custom substance object
            self._substances.append((substance, content))

        return self

    def with_conditions(
        self,
        property_type: str | PropertyType | None = None,
        amount: str | AmountLevel | None = None,
        ventilation: str | VentilationLevel | None = None,
        control_velocity_verified: bool | None = None,
        is_spray: bool | None = None,
        exposure_variation: str | ExposureVariation | None = None,
        work_area_size: str | None = None,
        dustiness: str | None = None,
        ignore_minimum_floor: bool | None = None,
    ) -> RiskAssessment:
        """
        Set working conditions.

        Args:
            property_type: "solid", "liquid", or PropertyType enum
            amount: Usage amount level:
                - "large": ≥1kL (liquid) or ≥1ton (solid) - Large batch processing
                - "medium": 1L-1kL or 1kg-1ton - Standard operations
                - "small": 100mL-1L or 100g-1kg - Laboratory scale
                - "minute": 10mL-100mL or 10g-100g - Small tests
                - "trace": <10mL or <10g - Minimal quantities
            ventilation: Ventilation level:
                - "none": No ventilation (coefficient: 4.0)
                - "basic": Basic/general ventilation (coefficient: 3.0)
                - "industrial": Industrial ventilation/outdoor (coefficient: 1.0)
                - "local_external" or "local_ext": Local exhaust - external type (coefficient: 0.7 or 0.1 if verified)
                - "local_enclosed" or "local_enc": Local exhaust - enclosed type (coefficient: 0.3 or 0.01 if verified)
                - "sealed": Sealed/enclosed system (coefficient: 0.001)
            control_velocity_verified: Whether local exhaust control velocity is verified
            is_spray: Whether this is a spray operation (increases exposure 10x)
            exposure_variation: "constant", "intermittent", "brief"
            work_area_size: Work area size for liquids (affects air dilution):
                - "small": Confined/small work area (coefficient: 1.5 - higher concentration)
                - "medium": Standard work area (coefficient: 1.0 - baseline)
                - "large": Large/open work area (coefficient: 0.5 - better dilution)
            dustiness: Dustiness level for solids (affects airborne concentration):
                - "high": Fine powder, easily airborne (飛散性高)
                - "medium": Crystalline, granular (飛散性中)
                - "low": Pellets, flakes, waxy (飛散性低)
            ignore_minimum_floor: Disable the minimum exposure floor (0.001 mg/m³ for solids,
                0.005 ppm for liquids). Useful for theoretical calculations when
                administrative controls achieve very low exposure. Default: False.

        Returns:
            Self for chaining
        """
        if property_type is not None:
            if isinstance(property_type, str):
                self._property_type = _parse_property_type(property_type)
            else:
                self._property_type = property_type

        if amount is not None:
            if isinstance(amount, str):
                self._amount_level = _parse_amount_level(amount)
            else:
                self._amount_level = amount

        if ventilation is not None:
            if isinstance(ventilation, str):
                self._ventilation = _parse_ventilation(ventilation)
            else:
                self._ventilation = ventilation

            # Auto-enable control velocity verification for enclosed local exhaust (draft)
            # This reflects standard practice: drafts are typically verified
            # User can explicitly set control_velocity_verified=False to override
            if self._ventilation in (VentilationLevel.LOCAL_ENCLOSED, VentilationLevel.LOCAL_EXTERNAL):
                if control_velocity_verified is None:
                    self._control_velocity_verified = True
                    self._control_velocity_auto_enabled = True

        if control_velocity_verified is not None:
            self._control_velocity_verified = control_velocity_verified
            self._control_velocity_auto_enabled = False  # User explicitly set

        if is_spray is not None:
            self._is_spray = is_spray

        if exposure_variation is not None:
            if isinstance(exposure_variation, str):
                self._exposure_variation = _parse_exposure_variation(exposure_variation)
            else:
                self._exposure_variation = exposure_variation

        if work_area_size is not None:
            if work_area_size not in ("small", "medium", "large"):
                raise ValueError(f"Invalid work area size: {work_area_size}. Must be 'small', 'medium', or 'large'")
            self._work_area_size = work_area_size

        if dustiness is not None:
            if dustiness not in ("high", "medium", "low"):
                raise ValueError(f"Invalid dustiness: {dustiness}. Must be 'high', 'medium', or 'low'")
            self._dustiness = dustiness

        if ignore_minimum_floor is not None:
            self._ignore_minimum_floor = ignore_minimum_floor

        return self

    def with_duration(
        self,
        hours: float | None = None,
        days_per_week: int | None = None,
        days_per_month: int | None = None,
    ) -> RiskAssessment:
        """
        Set duration and frequency.

        Args:
            hours: Working hours per day
            days_per_week: Days per week (for weekly frequency)
            days_per_month: Days per month (for less-than-weekly frequency)

        Returns:
            Self for chaining
        """
        if hours is not None:
            self._working_hours = hours

        if days_per_week is not None:
            self._frequency_type = "weekly"
            self._frequency_value = days_per_week
        elif days_per_month is not None:
            self._frequency_type = "monthly"
            self._frequency_value = days_per_month

        return self

    def with_protection(
        self,
        rpe: str | RPEType | None = None,
        rpe_fit_tested: bool | None = None,
        gloves: str | GloveType | None = None,
        glove_training: bool | None = None,
        skin_area: str | SkinArea | None = None,
    ) -> RiskAssessment:
        """
        Set protection measures (PPE).

        Args:
            rpe: RPE type string or RPEType enum
            rpe_fit_tested: Whether RPE is fit tested
            gloves: Glove type string or GloveType enum
            glove_training: Whether workers are trained in proper glove use
            skin_area: Exposed skin area

        Returns:
            Self for chaining
        """
        if rpe is not None:
            if isinstance(rpe, str):
                self._rpe_type = _parse_rpe_type(rpe)
            else:
                self._rpe_type = rpe

        if rpe_fit_tested is not None:
            self._rpe_fit_tested = rpe_fit_tested

        if gloves is not None:
            if isinstance(gloves, str):
                self._glove_type = _parse_glove_type(gloves)
            else:
                self._glove_type = gloves

        if glove_training is not None:
            self._glove_training = glove_training

        if skin_area is not None:
            if isinstance(skin_area, str):
                self._skin_area = _parse_skin_area(skin_area)
            else:
                self._skin_area = skin_area

        return self

    def with_assessments(
        self,
        inhalation: bool | None = None,
        dermal: bool | None = None,
        physical: bool | None = None,
    ) -> RiskAssessment:
        """
        Configure which risk assessments to run.

        By default, inhalation and dermal assessments are enabled.
        Physical assessment requires explicit opt-in.

        Args:
            inhalation: Whether to assess inhalation risk
            dermal: Whether to assess dermal risk
            physical: Whether to assess physical hazards

        Returns:
            Self for chaining
        """
        if inhalation is not None:
            self._assess_inhalation = inhalation
        if dermal is not None:
            self._assess_dermal = dermal
        if physical is not None:
            self._assess_physical = physical
        return self

    def with_physical_conditions(
        self,
        process_temperature: float | None = None,
        has_ignition_sources: bool | None = None,
        has_explosive_atmosphere: bool | None = None,
        has_organic_matter: bool | None = None,
        has_air_water_contact: bool | None = None,
    ) -> RiskAssessment:
        """
        Set physical hazard conditions and enable physical assessment.

        Calling this method automatically enables physical hazard assessment.

        Reference: CREATE-SIMPLE Design v3.1.1, Section 7

        Args:
            process_temperature: Process temperature in °C (for flash point comparison).
                Note: A 10°C safety margin is applied per CREATE-SIMPLE methodology.
            has_ignition_sources: Whether ignition sources are present.
                If False (controlled), reduces provisional risk level by 1 for
                flammable gases, aerosols, liquids, solids, and water-reactive substances.
            has_explosive_atmosphere: Whether explosive atmosphere may form.
                If False (prevented), reduces provisional risk level by 1 for
                flammable gases, aerosols, liquids, and solids.
            has_organic_matter: Whether organic matter or metals are handled nearby.
                If False, reduces provisional risk level by 1 for oxidizing liquids/solids.
            has_air_water_contact: Whether substance contacts air or water.
                If False (prevented), reduces provisional risk level by 1 for
                self-heating and water-reactive substances.

        Returns:
            Self for chaining
        """
        # Enable physical assessment when conditions are set
        self._assess_physical = True

        if process_temperature is not None:
            self._process_temperature = process_temperature
        if has_ignition_sources is not None:
            self._has_ignition_sources = has_ignition_sources
        if has_explosive_atmosphere is not None:
            self._has_explosive_atmosphere = has_explosive_atmosphere
        if has_organic_matter is not None:
            self._has_organic_matter = has_organic_matter
        if has_air_water_contact is not None:
            self._has_air_water_contact = has_air_water_contact
        return self

    def with_dermal_assessment(self, enabled: bool = True) -> RiskAssessment:
        """
        Enable or disable dermal assessment.

        Note: Dermal assessment is enabled by default.

        Args:
            enabled: Whether to assess dermal risk

        Returns:
            Self for chaining
        """
        self._assess_dermal = enabled
        return self

    def with_target_levels(
        self,
        inhalation: str | DetailedRiskLevel | None = None,
        dermal: str | DetailedRiskLevel | None = None,
        physical: str | DetailedRiskLevel | None = None,
    ) -> RiskAssessment:
        """
        Set target risk levels for recommendations.

        Recommendations will suggest controls to achieve these target levels.
        Default is Level I (lowest risk) for all risk types.

        Args:
            inhalation: Target level - DetailedRiskLevel or string ("I", "II-A", "II-B", "III", "IV")
            dermal: Target level - DetailedRiskLevel or string
            physical: Target level - DetailedRiskLevel or string

        Returns:
            Self for chaining

        Example:
            .with_target_levels(inhalation=DetailedRiskLevel.II_A, dermal="II-B")
        """
        if inhalation is not None:
            self._target_inhalation = _parse_detailed_level(inhalation)
        if dermal is not None:
            self._target_dermal = _parse_detailed_level(dermal)
        if physical is not None:
            self._target_physical = _parse_detailed_level(physical)
        return self

    def with_constraints(
        self,
        max_ventilation: str | VentilationLevel | None = None,
        min_frequency: dict | None = None,
        excluded_measures: list[str] | None = None,
        excluded_rpe: list[str] | None = None,
        max_rpe_apf: int | None = None,
        engineering_only: bool = False,
        no_ppe: bool = False,
        no_admin: bool = False,
    ) -> RiskAssessment:
        """
        Set constraints for recommendation generation.

        Constraints filter out measures that are physically impossible
        or undesirable for a specific workplace.

        Args:
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
            engineering_only: Only suggest engineering controls (no PPE or admin).
            no_ppe: Exclude all PPE recommendations.
            no_admin: Exclude administrative controls (frequency reduction).

        Returns:
            Self for chaining

        Example:
            .with_constraints(
                max_ventilation='local_enclosed',  # Can't seal the process
                excluded_rpe=['scba', 'airline'],  # Not feasible for routine work
                min_frequency={'days': 1, 'period': 'week'},  # Can't reduce below 1/week
            )
        """
        # Parse ventilation if string
        parsed_max_vent = None
        if max_ventilation is not None:
            if isinstance(max_ventilation, str):
                parsed_max_vent = _parse_ventilation(max_ventilation)
            else:
                parsed_max_vent = max_ventilation

        self._constraints = AssessmentConstraints(
            max_ventilation=parsed_max_vent,
            min_frequency=min_frequency,
            excluded_measures=excluded_measures or [],
            excluded_rpe=excluded_rpe or [],
            max_rpe_apf=max_rpe_apf,
            engineering_only=engineering_only,
            no_ppe=no_ppe,
            no_admin=no_admin,
        )
        return self

    def with_mode(
        self,
        mode: str | AssessmentMode,
    ) -> RiskAssessment:
        """
        Set the assessment mode.

        Args:
            mode: Assessment mode - "ra_sheet" or "report"
                - "ra_sheet": RA Sheet mode (default) - baseline risk without PPE reduction
                - "report": Report mode (実施レポート) - includes PPE effects and recommendations

        Returns:
            Self for chaining
        """
        if isinstance(mode, str):
            mode_lower = mode.lower()
            if mode_lower in ("ra_sheet", "sheet"):
                self._mode = AssessmentMode.RA_SHEET
            elif mode_lower in ("report", "implementation"):
                self._mode = AssessmentMode.REPORT
            else:
                raise ValueError(f"Invalid mode: {mode}. Use 'ra_sheet' or 'report'")
        else:
            self._mode = mode
        return self

    def verbose(self, enabled: bool = True) -> RiskAssessment:
        """
        Enable or disable verbose output with explanations.

        Args:
            enabled: Whether to include detailed explanations

        Returns:
            Self for chaining
        """
        self._verbose = enabled
        return self

    def with_language(self, language: str = "en") -> RiskAssessment:
        """
        Set output language for recommendations and explanations.

        Args:
            language: "en" for English, "ja" for Japanese

        Returns:
            Self for chaining
        """
        if language not in ("en", "ja"):
            raise ValueError(f"Unsupported language: {language}. Use 'en' or 'ja'.")
        self._language = language
        return self

    def validate(self) -> list[str]:
        """
        Validate the assessment configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not self._substances:
            errors.append("At least one substance is required")

        for sub, content in self._substances:
            if content < 0 or content > 100:
                errors.append(f"Content must be 0-100%: {sub.cas_number} has {content}%")

        total_content = sum(content for _, content in self._substances)
        if total_content > 100:
            errors.append(f"Total content exceeds 100%: {total_content}%")

        if self._working_hours <= 0 or self._working_hours > 24:
            errors.append(f"Invalid working hours: {self._working_hours}")

        return errors

    def is_valid(self) -> bool:
        """Check if the assessment configuration is valid."""
        return len(self.validate()) == 0

    def plan(self) -> AssessmentResult:
        """
        Run assessment in planning mode (without PPE reduction).

        This is useful for understanding the baseline risk before controls.

        Returns:
            AssessmentResult without PPE applied
        """
        # Temporarily disable PPE
        saved_rpe = self._rpe_type
        saved_glove = self._glove_type
        self._rpe_type = None
        self._glove_type = None
        self._mode = AssessmentMode.RA_SHEET

        try:
            return self.calculate()
        finally:
            # Restore PPE settings
            self._rpe_type = saved_rpe
            self._glove_type = saved_glove

    def calculate(self) -> AssessmentResult:
        """
        Run the full risk assessment.

        Returns:
            AssessmentResult with all calculations

        Raises:
            ValueError: If assessment configuration is invalid
        """
        errors = self.validate()
        if errors:
            raise ValueError(f"Invalid assessment: {'; '.join(errors)}")

        # Build assessment input
        assessment_input = AssessmentInput(
            product_property=self._property_type,
            amount_level=self._amount_level,
            ventilation=self._ventilation,
            control_velocity_verified=self._control_velocity_verified,
            is_spray_operation=self._is_spray,
            work_area_size=self._work_area_size,
            volatility_or_dustiness=self._dustiness,  # Override for dustiness
            working_hours_per_day=self._working_hours,
            frequency_type=self._frequency_type,
            frequency_value=self._frequency_value,
            exposure_variation=self._exposure_variation,
            rpe_type=self._rpe_type,
            rpe_fit_tested=self._rpe_fit_tested,
            glove_type=self._glove_type,
            glove_training=self._glove_training,
            exposed_skin_area=self._skin_area,
            assess_dermal=self._assess_dermal,
            assess_physical=self._assess_physical,
            process_temperature=self._process_temperature,
            has_ignition_sources=self._has_ignition_sources,
            has_explosive_atmosphere=self._has_explosive_atmosphere,
            has_organic_matter=self._has_organic_matter,
            has_air_water_contact=self._has_air_water_contact,
            mode=self._mode,
            ignore_minimum_floor=self._ignore_minimum_floor,
        )

        # Calculate risk for each substance
        from ..calculators.inhalation import calculate_inhalation_risk
        from ..calculators.dermal import calculate_dermal_risk
        from ..calculators.physical import calculate_physical_risk

        component_results: dict[str, ComponentResult] = {}
        assessment_warnings: list[str] = []

        def _record_component_error(
            *,
            errors: list[dict[str, str]],
            warnings: list[str],
            risk_type: str,
            cas_number: str,
            exc: Exception,
        ) -> None:
            """Capture recoverable calculation errors without aborting the assessment."""
            error_entry = {
                "risk_type": risk_type,
                "error_type": type(exc).__name__,
                "message": str(exc) or type(exc).__name__,
            }
            errors.append(error_entry)
            warning = (
                f"{cas_number}: {risk_type} calculation failed "
                f"({error_entry['error_type']}: {error_entry['message']})"
            )
            warnings.append(warning)
            logger.warning(warning)

        for substance, content in self._substances:
            inhalation_result = None
            dermal_result = None
            physical_result = None
            component_errors: list[dict[str, str]] = []

            if self._assess_inhalation:
                try:
                    inhalation_result = calculate_inhalation_risk(
                        assessment_input=assessment_input,
                        substance=substance,
                        content_percent=content,
                        verbose=self._verbose,
                    )
                except Exception as exc:
                    _record_component_error(
                        errors=component_errors,
                        warnings=assessment_warnings,
                        risk_type="inhalation",
                        cas_number=substance.cas_number,
                        exc=exc,
                    )

            if self._assess_dermal:
                try:
                    dermal_result = calculate_dermal_risk(
                        assessment_input=assessment_input,
                        substance=substance,
                        content_percent=content,
                        verbose=self._verbose,
                    )
                except Exception as exc:
                    _record_component_error(
                        errors=component_errors,
                        warnings=assessment_warnings,
                        risk_type="dermal",
                        cas_number=substance.cas_number,
                        exc=exc,
                    )

            if self._assess_physical:
                try:
                    physical_result = calculate_physical_risk(
                        assessment_input=assessment_input,
                        substance=substance,
                        verbose=self._verbose,
                    )
                except Exception as exc:
                    _record_component_error(
                        errors=component_errors,
                        warnings=assessment_warnings,
                        risk_type="physical",
                        cas_number=substance.cas_number,
                        exc=exc,
                    )

            # Lookup regulatory info for this substance
            regulatory_info = get_regulatory_info(substance.cas_number)

            component_results[substance.cas_number] = ComponentResult(
                cas_number=substance.cas_number,
                name=substance.name_ja or substance.name_en or substance.cas_number,
                content_percent=content,
                inhalation=inhalation_result,
                dermal=dermal_result,
                physical=physical_result,
                regulatory_info=regulatory_info,
                calculation_errors=component_errors,
                _substance=substance,  # Store for recommendations
            )

        return AssessmentResult(
            components=component_results,
            assessment_input=assessment_input,
            builder=self,
            diagnostic_warnings=assessment_warnings,
            target_inhalation=self._target_inhalation,
            target_dermal=self._target_dermal,
            target_physical=self._target_physical,
        )


# Helper functions for parsing string inputs

def _parse_property_type(value: str) -> PropertyType:
    """Parse property type from string."""
    mapping = {
        "solid": PropertyType.SOLID,
        "liquid": PropertyType.LIQUID,
        # Gas is treated as liquid for CREATE-SIMPLE calculations
        "gas": PropertyType.LIQUID,
    }
    value_lower = value.lower()
    if value_lower in mapping:
        return mapping[value_lower]
    raise ValueError(f"Invalid property type: {value}")


def _parse_amount_level(value: str) -> AmountLevel:
    """Parse amount level from string."""
    mapping = {
        "large": AmountLevel.LARGE,
        "medium": AmountLevel.MEDIUM,
        "small": AmountLevel.SMALL,
        "minute": AmountLevel.MINUTE,
        "trace": AmountLevel.TRACE,
    }
    value_lower = value.lower()
    if value_lower in mapping:
        return mapping[value_lower]
    raise ValueError(f"Invalid amount level: {value}")


def _parse_ventilation(value: str) -> VentilationLevel:
    """Parse ventilation level from string."""
    mapping = {
        "none": VentilationLevel.NONE,
        "basic": VentilationLevel.BASIC,
        "industrial": VentilationLevel.INDUSTRIAL,
        "local_external": VentilationLevel.LOCAL_EXTERNAL,
        "local_ext": VentilationLevel.LOCAL_EXTERNAL,
        "local_enclosed": VentilationLevel.LOCAL_ENCLOSED,
        "local_enc": VentilationLevel.LOCAL_ENCLOSED,
        "sealed": VentilationLevel.SEALED,
    }
    value_lower = value.lower()
    if value_lower in mapping:
        return mapping[value_lower]
    raise ValueError(f"Invalid ventilation level: {value}")


def _parse_exposure_variation(value: str) -> ExposureVariation:
    """Parse exposure variation from string."""
    mapping = {
        "constant": ExposureVariation.CONSTANT,
        "intermittent": ExposureVariation.INTERMITTENT,
        "brief": ExposureVariation.BRIEF,
    }
    value_lower = value.lower()
    if value_lower in mapping:
        return mapping[value_lower]
    raise ValueError(f"Invalid exposure variation: {value}")


def _parse_rpe_type(value: str) -> RPEType:
    """Parse RPE type from string."""
    # Direct enum value mapping
    mapping = {
        "none": RPEType.NONE,
        # Loose-fit types (no fit test required)
        "loose_fit_11": RPEType.LOOSE_FIT_11,
        "loose_fit_20": RPEType.LOOSE_FIT_20,
        "loose_fit_25": RPEType.LOOSE_FIT_25,
        # Tight-fit types (fit test required)
        "tight_fit_10": RPEType.TIGHT_FIT_10,
        "tight_fit_50": RPEType.TIGHT_FIT_50,
        "tight_fit_100": RPEType.TIGHT_FIT_100,
        "tight_fit_1000": RPEType.TIGHT_FIT_1000,
        "tight_fit_10000": RPEType.TIGHT_FIT_10000,
        # User-friendly aliases
        "half_mask": RPEType.TIGHT_FIT_10,  # Typical half-mask APF
        "full_mask": RPEType.TIGHT_FIT_50,  # Typical full-face mask APF
        "papr": RPEType.LOOSE_FIT_25,  # PAPR with loose hood
        "scba": RPEType.TIGHT_FIT_10000,  # SCBA highest protection
    }
    value_lower = value.lower()
    if value_lower in mapping:
        return mapping[value_lower]
    raise ValueError(f"Invalid RPE type: {value}. Valid values: {list(mapping.keys())}")


def _parse_glove_type(value: str) -> GloveType:
    """Parse glove type from string."""
    mapping = {
        "none": GloveType.NONE,
        "non_resistant": GloveType.NON_RESISTANT,
        "resistant": GloveType.RESISTANT,
        # User-friendly aliases
        "nitrile": GloveType.RESISTANT,  # Nitrile is typically resistant
        "butyl": GloveType.RESISTANT,  # Butyl is typically resistant
        "latex": GloveType.NON_RESISTANT,  # Basic latex may not be resistant
    }
    value_lower = value.lower()
    if value_lower in mapping:
        return mapping[value_lower]
    raise ValueError(f"Invalid glove type: {value}. Valid values: none, non_resistant, resistant")


def _parse_skin_area(value: str) -> SkinArea:
    """Parse skin area from string.

    Matches CREATE-SIMPLE Q8_Exposure_area options.
    """
    mapping = {
        "coin_splash": SkinArea.COIN_SPLASH,
        "palm_one": SkinArea.PALM_ONE,
        "palm_both": SkinArea.PALM_BOTH,
        "hands_both": SkinArea.HANDS_BOTH,
        "wrists": SkinArea.WRISTS,
        "forearms": SkinArea.FOREARMS,
    }
    value_lower = value.lower()
    if value_lower in mapping:
        return mapping[value_lower]
    valid = ", ".join(mapping.keys())
    raise ValueError(f"Invalid skin area: {value}. Valid values: {valid}")


def _parse_detailed_level(value: str | DetailedRiskLevel) -> DetailedRiskLevel:
    """Parse detailed risk level from string or enum."""
    if isinstance(value, DetailedRiskLevel):
        return value

    mapping = {
        "i": DetailedRiskLevel.I,
        "1": DetailedRiskLevel.I,
        "ii-a": DetailedRiskLevel.II_A,
        "ii_a": DetailedRiskLevel.II_A,
        "iia": DetailedRiskLevel.II_A,
        "2a": DetailedRiskLevel.II_A,
        "2": DetailedRiskLevel.II_A,  # Default II to II-A (stricter)
        "ii-b": DetailedRiskLevel.II_B,
        "ii_b": DetailedRiskLevel.II_B,
        "iib": DetailedRiskLevel.II_B,
        "2b": DetailedRiskLevel.II_B,
        "iii": DetailedRiskLevel.III,
        "3": DetailedRiskLevel.III,
        "iv": DetailedRiskLevel.IV,
        "4": DetailedRiskLevel.IV,
    }
    value_lower = str(value).lower().strip()
    if value_lower in mapping:
        return mapping[value_lower]
    raise ValueError(
        f"Invalid risk level: {value}. "
        f"Valid values: I, II-A, II-B, III, IV (or 1, 2, 2a, 2b, 3, 4)"
    )
