"""Service helpers for risk-assessment workflows."""

from typing import Any

from .. import RiskAssessment
from ..calculators import (
    MIN_EXPOSURE_LIQUID,
    MIN_EXPOSURE_SOLID,
)
from ..calculators.version_comparison import compare_versions
from ..models.risk import RiskLevel
from .common import ServiceError, ServiceResult
from .conditions import format_conditions_used

# Version metadata
VERSION_INFO = {
    "v3.1.2": {
        "name_en": "CREATE-SIMPLE v3.1.2",
        "name_ja": "CREATE-SIMPLE v3.1.2 (2024年版)",
        "is_recommended": True,
        "exposure_floor": {
            "enabled": True,
            "liquid_ppm": MIN_EXPOSURE_LIQUID,  # 0.005
            "solid_mg_m3": MIN_EXPOSURE_SOLID,  # 0.001
        },
        "features_en": [
            "Exposure floor (minimum exposure limit)",
            "Expanded hazard-data coverage",
            "GHS-based skin hazard detection",
            "Cutoff thresholds for hazard labels",
        ],
        "features_ja": [
            "ばく露下限値（最小ばく露量）",
            "有害性データの拡張カバレッジ",
            "GHS分類による皮膚障害検出",
            "有害性ラベルの裾切値適用",
        ],
        "note_en": "Recommended version. Exposure floor prevents unrealistically low estimates.",
        "note_ja": "推奨バージョン。ばく露下限値により非現実的に低い推定値を防止。",
    },
    "v3.0.2": {
        "name_en": "CREATE-SIMPLE v3.0.2",
        "name_ja": "CREATE-SIMPLE v3.0.2 (2023年版)",
        "is_recommended": False,
        "exposure_floor": {
            "enabled": False,
            "liquid_ppm": None,
            "solid_mg_m3": None,
        },
        "features_en": [
            "No exposure floor (can calculate any low value)",
            "Legacy hazard-data coverage",
            "Database-only skin hazard detection",
        ],
        "features_ja": [
            "ばく露下限値なし（任意の低い値を計算可能）",
            "旧版の有害性データカバレッジ",
            "データベースのみの皮膚障害検出",
        ],
        "note_en": "Older version without exposure floor. May give unrealistically low estimates for well-controlled scenarios.",
        "note_ja": "ばく露下限値のない旧バージョン。管理の良い作業条件で非現実的に低い推定値になる可能性あり。",
    },
}


# Risk level string to int mapping
RISK_LEVEL_MAP = {
    "I": 1,
    "II-A": 2,
    "II-B": 3,
    "III": 4,
    "IV": 5,
}


def _append_warning(
    warnings: list[dict[str, Any]],
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Append a structured warning entry."""
    warning: dict[str, Any] = {"code": code, "message": message}
    if details:
        warning["details"] = details
    warnings.append(warning)


def _parse_risk_level(level: str | int) -> int:
    """Convert risk level string or int to integer for comparison."""
    if isinstance(level, int):
        return level
    return RISK_LEVEL_MAP.get(level.upper(), 5)


def _generate_methodology_info(version: str, language: str) -> dict:
    """Generate methodology information section for output."""
    info = VERSION_INFO.get(version, VERSION_INFO["v3.1.2"])
    lang_suffix = "ja" if language == "ja" else "en"

    return {
        "version": version,
        "version_name": info[f"name_{lang_suffix}"],
        "is_recommended": info["is_recommended"],
        "exposure_floor": info["exposure_floor"],
        "features": info[f"features_{lang_suffix}"],
        "note": info[f"note_{lang_suffix}"],
    }


def _calculate_version_alternative(
    result,
    current_version: str,
    target_level: str,
    language: str,
    floor_manually_disabled: bool = False,
    warnings: list[dict[str, Any]] | None = None,
) -> dict | None:
    """
    Calculate what the alternative version would produce.

    When using v3.1.2 and floor is applied, show what v3.0.2 would calculate.
    When using v3.0.2, show what v3.1.2 would calculate.
    When floor is manually disabled with v3.1.2, warn user about non-standard behavior.
    """
    try:
        # Check if any component has floor applied (for v3.1.2 -> v3.0.2 comparison)
        floor_applied_any = False
        target_would_be_achieved = False

        for cas, comp in result.components.items():
            if not comp.inhalation:
                continue

            # Check if floor was applied and affected result
            if hasattr(comp.inhalation, "would_achieve_target_without_floor"):
                if comp.inhalation.would_achieve_target_without_floor:
                    floor_applied_any = True
                    # Check if removing floor would achieve target
                    rcr_without = comp.inhalation.rcr_without_floor
                    if rcr_without is not None:
                        target_level_int = _parse_risk_level(target_level)
                        alt_risk_level = RiskLevel.get_detailed_label(rcr_without)
                        alt_level_int = _parse_risk_level(alt_risk_level)
                        if alt_level_int <= target_level_int:
                            target_would_be_achieved = True

        # Case 1: v3.1.2 with floor manually disabled (non-standard usage)
        if current_version == "v3.1.2" and floor_manually_disabled:
            alt_info = {
                "alternative_version": "v3.1.2 (標準設定)",
                "current_behavior": "v3.0.2相当（下限値無効）",
                "floor_manually_disabled": True,
                "is_non_standard": True,
            }

            if language == "ja":
                alt_info["warning"] = (
                    "⚠️ ばく露下限値が手動で無効化されています。"
                    "これはv3.0.2と同等の動作であり、v3.1.2の標準動作ではありません。"
                )
                alt_info["recommendation"] = (
                    "公式な評価には、ignore_minimum_floorを無効（false）にするか、"
                    "methodology_version='v3.0.2'を明示的に指定することを推奨します。"
                )
                alt_info["note"] = (
                    "v3.1.2のばく露下限値は非現実的に低いばく露推定を防ぐために設計されています。"
                    "下限値を無効にすると、特に管理の良い条件下で過度に楽観的な結果が得られる可能性があります。"
                )
            else:
                alt_info["warning"] = (
                    "⚠️ Exposure floor is manually disabled. "
                    "This behaves like v3.0.2, not standard v3.1.2."
                )
                alt_info["recommendation"] = (
                    "For official assessments, either enable the floor (ignore_minimum_floor=false) "
                    "or explicitly use methodology_version='v3.0.2'."
                )
                alt_info["note"] = (
                    "The v3.1.2 exposure floor prevents unrealistically low estimates. "
                    "Disabling it may give overly optimistic results in well-controlled conditions."
                )

            return alt_info

        # Case 2: v3.1.2 with floor applied and limiting
        if current_version == "v3.1.2" and floor_applied_any:
            alt_info = {
                "alternative_version": "v3.0.2",
                "would_differ": True,
                "floor_is_limiting_factor": True,
                "target_achievable_without_floor": target_would_be_achieved,
            }

            if language == "ja":
                alt_info["reason"] = "v3.1.2のばく露下限値が適用されています"
                if target_would_be_achieved:
                    alt_info["note"] = (
                        "v3.0.2ではばく露下限値がないため目標リスクレベルを達成できますが、"
                        "v3.1.2の使用を推奨します（厚生労働省推奨の最新版）。"
                        "下限値は非現実的に低いばく露推定を防ぐために設定されています。"
                    )
                else:
                    alt_info["note"] = (
                        "v3.0.2ではより低いばく露値が計算されますが、v3.1.2の使用を推奨します。"
                    )
            else:
                alt_info["reason"] = "Exposure floor from v3.1.2 is applied"
                if target_would_be_achieved:
                    alt_info["note"] = (
                        "v3.0.2 (without floor) would achieve target risk level, but "
                        "v3.1.2 is recommended (MHLW latest version). "
                        "The floor prevents unrealistically low exposure estimates."
                    )
                else:
                    alt_info["note"] = (
                        "v3.0.2 would calculate lower exposure, but v3.1.2 is recommended."
                    )

            return alt_info

        # Case 3: v3.0.2 -> always show v3.1.2 recommendation
        elif current_version == "v3.0.2":
            alt_info = {
                "alternative_version": "v3.1.2",
                "is_recommended_version": True,
            }

            if language == "ja":
                alt_info["note"] = (
                    "v3.1.2（推奨版）にはばく露下限値があり、より保守的な推定値を提供します。"
                    "公式な評価にはv3.1.2の使用を推奨します。"
                )
            else:
                alt_info["note"] = (
                    "v3.1.2 (recommended) includes exposure floor for more conservative estimates. "
                    "Use v3.1.2 for official assessments."
                )

            return alt_info

        return None

    except Exception as exc:
        if warnings is not None:
            _append_warning(
                warnings,
                code="VERSION_ALTERNATIVE_UNAVAILABLE",
                message=(
                    "Unable to compute version alternative comparison"
                    if language == "en"
                    else "バージョン比較情報を生成できませんでした"
                ),
                details={"error_type": type(exc).__name__, "error": str(exc)},
            )
        return None


def calculate_risk(
    substances: list[dict[str, Any]],
    preset: str | None = None,
    conditions: dict[str, Any] | None = None,
    duration: dict[str, Any] | None = None,
    protection: dict[str, Any] | None = None,
    assess_inhalation: bool = True,
    assess_dermal: bool = True,
    assess_physical: bool = True,
    target_level: str = "II-A",
    include_recommendations: str = "auto",
    include_explanation: bool = False,
    include_v2_comparison: bool = False,
    methodology_version: str = "v3.1.2",
    language: str = "en",
) -> ServiceResult:
    """Calculate a chemical risk assessment payload."""
    if not substances:
        raise ServiceError("MISSING_SUBSTANCES", "At least one substance is required")

    valid_versions = ["v3.1.2", "v3.0.2"]
    if methodology_version not in valid_versions:
        raise ServiceError(
            "INVALID_METHODOLOGY_VERSION",
            f"Invalid methodology_version. Must be one of: {valid_versions}",
        )

    use_v302 = methodology_version == "v3.0.2"

    assessment = RiskAssessment()

    if include_explanation:
        assessment = assessment.verbose(True)

    if preset:
        try:
            assessment = assessment.use_preset(preset)
        except ValueError as exc:
            raise ServiceError("INVALID_PRESET", str(exc)) from exc

    for sub in substances:
        cas = sub.get("cas_number")
        content = sub.get("content_percent", 100.0)
        if not cas:
            raise ServiceError("MISSING_CAS_NUMBER", "Each substance must have a cas_number")
        try:
            assessment = assessment.add_substance(cas, content=content)
        except ValueError as exc:
            raise ServiceError("SUBSTANCE_LOOKUP_FAILED", f"Substance lookup failed for {cas}: {exc}") from exc

    ignore_floor = conditions.get("ignore_minimum_floor") if conditions else None
    if use_v302:
        ignore_floor = True

    if conditions:
        assessment = assessment.with_conditions(
            property_type=conditions.get("property_type"),
            amount=conditions.get("amount"),
            ventilation=conditions.get("ventilation"),
            control_velocity_verified=conditions.get("control_velocity_verified"),
            is_spray=conditions.get("is_spray"),
            dustiness=conditions.get("dustiness"),
            work_area_size=conditions.get("work_area_size"),
            ignore_minimum_floor=ignore_floor,
        )
    elif use_v302:
        assessment = assessment.with_conditions(ignore_minimum_floor=True)

    if duration:
        assessment = assessment.with_duration(
            hours=duration.get("hours"),
            days_per_week=duration.get("days_per_week"),
            days_per_month=duration.get("days_per_month"),
        )

    if protection:
        assessment = assessment.with_protection(
            rpe=protection.get("rpe"),
            rpe_fit_tested=protection.get("rpe_fit_tested"),
            gloves=protection.get("gloves"),
            glove_training=protection.get("glove_training"),
            skin_area=protection.get("skin_area"),
        )

    assessment = assessment.with_assessments(
        inhalation=assess_inhalation,
        dermal=assess_dermal,
        physical=assess_physical,
    )

    assessment = assessment.with_target_levels(inhalation=target_level)
    assessment = assessment.with_language(language)

    try:
        result = assessment.calculate()
    except ValueError as exc:
        raise ServiceError("CALCULATION_FAILED", f"Calculation failed: {exc}") from exc

    floor_manually_disabled = (
        methodology_version == "v3.1.2"
        and conditions is not None
        and conditions.get("ignore_minimum_floor") is True
    )

    payload = _format_result(
        result,
        language,
        include_recommendations=include_recommendations,
        include_explanation=include_explanation,
        include_v2_comparison=include_v2_comparison,
        target_level=target_level,
        methodology_version=methodology_version,
        floor_manually_disabled=floor_manually_disabled,
    )
    warnings = payload.pop("warnings", [])
    return ServiceResult(data=payload, warnings=warnings)


def _extract_conditions_info(
    result,
    language: str,
    warnings: list[dict[str, Any]] | None = None,
) -> dict | None:
    """Extract and format conditions with human-readable labels."""
    try:
        assessment_input = result.assessment_input
        builder = result.builder

        # Determine volatility/dustiness and physical properties
        volatility = None
        dustiness = None
        volatility_source = None
        flash_point = None
        boiling_point = None

        # Get from builder if available
        if builder:
            dustiness = builder._dustiness

            # Get substance properties from first substance
            if builder._substances:
                try:
                    substance, _ = builder._substances[0]
                    if substance and substance.properties:
                        props = substance.properties
                        # Get physical properties
                        flash_point = props.flash_point
                        boiling_point = props.boiling_point

                        # For liquids, get volatility
                        if assessment_input.product_property.value == "liquid":
                            vol_level = props.get_volatility_level()
                            volatility = vol_level.value if vol_level else None
                            # Determine volatility source
                            if props.vapor_pressure is not None:
                                volatility_source = f"vapor_pressure: {props.vapor_pressure}Pa"
                            elif props.boiling_point is not None:
                                volatility_source = f"boiling_point: {props.boiling_point}°C"
                except (IndexError, AttributeError):
                    pass

        return format_conditions_used(
            assessment_input=assessment_input,
            language=language,
            volatility=volatility,
            dustiness=dustiness,
            volatility_source=volatility_source,
            flash_point=flash_point,
            boiling_point=boiling_point,
        )
    except Exception as exc:
        # Don't fail the whole response if formatting fails
        if warnings is not None:
            _append_warning(
                warnings,
                code="CONDITIONS_FORMAT_UNAVAILABLE",
                message=(
                    "Unable to format assessment conditions"
                    if language == "en"
                    else "評価条件の整形に失敗しました"
                ),
                details={"error_type": type(exc).__name__, "error": str(exc)},
            )
        return None


def _format_result(
    result,
    language: str,
    include_recommendations: str = "auto",
    include_explanation: bool = False,
    include_v2_comparison: bool = False,
    target_level: str = "I",
    methodology_version: str = "v3.1.2",
    floor_manually_disabled: bool = False,
) -> dict:
    """Format AssessmentResult for MCP response."""
    structured_warnings: list[dict[str, Any]] = []
    output: dict[str, Any] = {
        "methodology": {
            "version": methodology_version,
            "details": _generate_methodology_info(methodology_version, language),
        },
        "overall_risk": {
            "level": result.overall_risk_level,
            "label": result.overall_risk_label,
        },
        "components": {},
    }

    # Bubble up assessment-level warnings/errors from ra-library.
    for warning in getattr(result, "warnings", []):
        _append_warning(
            structured_warnings,
            code="ASSESSMENT_PARTIAL_FAILURE",
            message=warning,
        )
    if getattr(result, "errors", None):
        output["assessment_errors"] = result.errors
        _append_warning(
            structured_warnings,
            code="ASSESSMENT_ERRORS_REPORTED",
            message=(
                "Assessment returned component-level errors"
                if language == "en"
                else "評価処理で成分別エラーが返されました"
            ),
            details={"errors": result.errors},
        )

    # Add conditions_used with human-readable labels
    conditions_info = _extract_conditions_info(result, language, warnings=structured_warnings)
    if conditions_info:
        output["conditions_used"] = conditions_info

    # Add version alternative info (shows what other version would calculate)
    version_alt = _calculate_version_alternative(
        result,
        methodology_version,
        target_level,
        language,
        floor_manually_disabled,
        warnings=structured_warnings,
    )
    if version_alt:
        output["version_alternative"] = version_alt

    for cas, comp in result.components.items():
        comp_data = {
            "cas_number": comp.cas_number,
            "name": comp.name,
            "content_percent": comp.content_percent,
            "risk_level": comp.risk_level,
            "risk_label": comp.risk_label,
        }

        # Inhalation results
        if comp.inhalation:
            inh_data = {
                "rcr": round(comp.inhalation.rcr, 4),
                "risk_level": int(comp.inhalation.risk_level),
                "risk_label": RiskLevel.get_detailed_label(comp.inhalation.rcr),
                "exposure_8hr": comp.inhalation.exposure_8hr,
                "exposure_unit": comp.inhalation.exposure_8hr_unit,
                "oel": comp.inhalation.oel,
                "oel_source": comp.inhalation.oel_source,
            }
            # Add STEL if available
            if comp.inhalation.stel_rcr is not None:
                inh_data["stel_rcr"] = round(comp.inhalation.stel_rcr, 4)
                inh_data["stel_risk_level"] = (
                    int(comp.inhalation.stel_risk_level)
                    if comp.inhalation.stel_risk_level
                    else None
                )
                inh_data["stel_risk_label"] = RiskLevel.get_simple_label(
                    comp.inhalation.stel_rcr
                )
            # Add floor tracking info
            if comp.inhalation.would_achieve_target_without_floor:
                inh_data["would_achieve_target_without_floor"] = True
                inh_data["rcr_without_floor"] = (
                    round(comp.inhalation.rcr_without_floor, 4)
                    if comp.inhalation.rcr_without_floor is not None
                    else None
                )
            comp_data["inhalation"] = inh_data

            # Add explanation if requested
            if include_explanation:
                explanation = getattr(comp.inhalation, "explanation", None)
                if explanation:
                    comp_data["inhalation"]["explanation"] = _format_explanation(
                        explanation, language
                    )

        # Dermal results (uses simple I/II/III/IV scale per VBA)
        if comp.dermal:
            comp_data["dermal"] = {
                "rcr": round(comp.dermal.rcr, 4),
                "risk_level": int(comp.dermal.risk_level),
                "risk_label": RiskLevel.get_simple_label(comp.dermal.rcr),
            }

        # Physical results (verbose output)
        if comp.physical:
            phys = comp.physical
            phys_data: dict[str, Any] = {
                "risk_level": int(phys.risk_level),
                "hazard_type": phys.hazard_type,
            }

            # Add labels from PHYSICAL_HAZARD_LABELS
            from ..i18n.labels import PHYSICAL_HAZARD_LABELS

            hazard_key = phys.hazard_type
            if hazard_key in PHYSICAL_HAZARD_LABELS:
                hazard_info = PHYSICAL_HAZARD_LABELS[hazard_key]
                # Get localized hazard label
                phys_data["hazard_label"] = hazard_info.get(language, hazard_info.get("en", hazard_key))
                # Get warnings
                phys_data["warnings"] = hazard_info.get("warnings", {}).get(language, [])
            else:
                # Fallback if hazard type not in labels
                phys_data["hazard_label"] = phys.hazard_type

            # Add flash point if available (from PhysicalRisk or substance)
            if phys.flash_point is not None:
                phys_data["flash_point_celsius"] = phys.flash_point
            elif hasattr(comp, "_substance") and comp._substance:
                sub = comp._substance
                if hasattr(sub, "properties") and sub.properties:
                    if sub.properties.flash_point is not None:
                        phys_data["flash_point_celsius"] = sub.properties.flash_point

            comp_data["physical"] = phys_data

        # Add warnings based on language
        if language == "ja":
            comp_data["warnings"] = comp.warnings_ja
        else:
            comp_data["warnings"] = comp.warnings
        if comp.calculation_errors:
            comp_data["calculation_errors"] = comp.calculation_errors

        output["components"][cas] = comp_data

    # Add mixed exposure info if multiple substances
    if len(result.components) > 1:
        if result.mixed_inhalation_rcr is not None:
            output["mixed_exposure"] = {
                "inhalation_rcr": round(result.mixed_inhalation_rcr, 4),
                "inhalation_risk_level": result.mixed_inhalation_risk_level,
            }
            if result.mixed_dermal_rcr is not None:
                output["mixed_exposure"]["dermal_rcr"] = round(result.mixed_dermal_rcr, 4)
                output["mixed_exposure"]["dermal_risk_level"] = result.mixed_dermal_risk_level

    # Add v2 comparison if requested
    if include_v2_comparison:
        v2_comparisons = _generate_v2_comparison(result, language, warnings=structured_warnings)
        if v2_comparisons:
            output["version_comparison"] = v2_comparisons

    # Add recommendations if requested
    should_include_recs = False
    if include_recommendations == "always":
        should_include_recs = True
    elif include_recommendations == "auto":
        # Include if overall risk level exceeds target
        current_level_int = _parse_risk_level(result.overall_risk_level)
        target_level_int = _parse_risk_level(target_level)
        should_include_recs = current_level_int > target_level_int
    # "never" = don't include

    if should_include_recs:
        recs = result.get_recommendations(top_n=5)
        if recs:
            output["recommendations"] = _format_recommendations(recs, language)
            output["recommendations_meta"] = {
                "target_level": target_level,
                "current_level": result.overall_risk_level,
                "level_achievable": result.level_one_achievable if target_level == "I" else None,
            }

        # Add version-based recommendation if floor is limiting factor
        if methodology_version == "v3.1.2" and version_alt:
            if version_alt.get("target_achievable_without_floor"):
                version_rec = _create_version_recommendation(
                    target_level, result.overall_risk_level, language
                )
                if version_rec:
                    if "recommendations" not in output:
                        output["recommendations"] = []
                    output["recommendations"].append(version_rec)

    if structured_warnings:
        output["warnings"] = structured_warnings

    return output


def _create_version_recommendation(
    target_level: str,
    current_level: str,
    language: str,
) -> dict:
    """Create a special recommendation about trying alternative version."""
    if language == "ja":
        return {
            "priority": 99,  # Low priority (informational)
            "category": "methodology",
            "action": (
                f"参考情報: v3.0.2（ばく露下限値なし）では目標リスクレベル{target_level}を"
                "達成可能ですが、v3.1.2の使用を推奨します"
            ),
            "effectiveness": "informational",
            "feasibility": "immediate",
            "current_level": current_level,
            "predicted_level": target_level,
            "rcr_reduction_percent": 0,
            "notes": (
                "v3.1.2のばく露下限値は、非現実的に低いばく露推定を防ぐために設定されています。"
                "現在の作業条件では十分にリスクが管理されていると考えられますが、"
                "公式な評価にはv3.1.2の結果を使用してください。"
                "v3.0.2での計算は参考値としてのみ使用してください。"
            ),
            "is_version_suggestion": True,
            "suggested_version": "v3.0.2",
        }
    else:
        return {
            "priority": 99,  # Low priority (informational)
            "category": "methodology",
            "action": (
                f"For reference: v3.0.2 (no exposure floor) would achieve target level {target_level}, "
                "but v3.1.2 is recommended"
            ),
            "effectiveness": "informational",
            "feasibility": "immediate",
            "current_level": current_level,
            "predicted_level": target_level,
            "rcr_reduction_percent": 0,
            "notes": (
                "The v3.1.2 exposure floor prevents unrealistically low exposure estimates. "
                "Current conditions indicate well-controlled exposure, but use v3.1.2 results "
                "for official assessments. v3.0.2 calculations are for reference only."
            ),
            "is_version_suggestion": True,
            "suggested_version": "v3.0.2",
        }


def _generate_v2_comparison(
    result,
    language: str,
    warnings: list[dict[str, Any]] | None = None,
) -> dict | None:
    """Generate v2.x methodology comparison for the assessment."""
    try:
        # Get assessment input and builder
        assessment_input = result.assessment_input
        builder = result.builder
        if not assessment_input or not builder:
            return None

        comparisons = {}

        # Get property type
        property_type = assessment_input.product_property.value
        if property_type not in ("liquid", "solid"):
            return None

        # Get amount level
        amount_level = assessment_input.amount.value if assessment_input.amount else "medium"

        # Get ventilation
        ventilation = assessment_input.ventilation.value if assessment_input.ventilation else "industrial"

        # Get working conditions
        is_spray = assessment_input.is_spray if hasattr(assessment_input, "is_spray") else False
        working_hours = assessment_input.working_hours if hasattr(assessment_input, "working_hours") else 8.0
        days_per_week = assessment_input.days_per_week if hasattr(assessment_input, "days_per_week") else 5

        # Get volatility/dustiness from builder
        volatility_or_dustiness = builder._dustiness if property_type == "solid" else None
        if property_type == "liquid" and builder._substances:
            try:
                substance, _ = builder._substances[0]
                if substance and substance.properties:
                    vol_level = substance.properties.get_volatility_level()
                    volatility_or_dustiness = vol_level.value if vol_level else "medium"
            except (IndexError, AttributeError):
                volatility_or_dustiness = "medium"
        if not volatility_or_dustiness:
            volatility_or_dustiness = "medium"

        # Generate comparison for each component
        for cas, comp in result.components.items():
            if not comp.inhalation:
                continue

            # Get v3 values
            v3_exposure = comp.inhalation.exposure_8hr
            v3_rcr = comp.inhalation.rcr
            v3_risk_level = RiskLevel.get_detailed_label(v3_rcr)
            oel = comp.inhalation.oel if comp.inhalation.oel else 0

            # Get content percent
            content_percent = comp.content_percent

            # Get ACRmax if available (for fallback if no OEL)
            acrmax = None
            if hasattr(comp, "_acrmax"):
                acrmax = comp._acrmax

            # Generate comparison
            comparison = compare_versions(
                property_type=property_type,
                volatility_or_dustiness=volatility_or_dustiness,
                amount_level=amount_level,
                oel=oel,
                v3_exposure=v3_exposure,
                v3_rcr=v3_rcr,
                v3_risk_level=v3_risk_level,
                content_percent=content_percent,
                ventilation=ventilation,
                is_spray=is_spray,
                working_hours=working_hours,
                days_per_week=days_per_week,
                acrmax=acrmax,
            )

            comparisons[cas] = comparison

        # Add summary
        if comparisons:
            summary = {
                "note": "v3.1.2 is recommended (latest methodology with STEL, dermal, and physical hazard assessment)" if language == "en" else "v3.1.2を推奨 (STEL、経皮吸収、物理的危険性を含む最新の評価手法)",
                "v3_features": ["8-hour TWA", "STEL", "Dermal absorption", "Physical hazards"] if language == "en" else ["8時間TWA", "短時間STEL", "経皮吸収", "物理的危険性"],
                "v2_features": ["8-hour TWA only"] if language == "en" else ["8時間TWAのみ"],
            }
            return {
                "substances": comparisons,
                "summary": summary,
            }

        return None
    except Exception as exc:
        # Don't fail the whole response if v2 comparison fails
        if warnings is not None:
            _append_warning(
                warnings,
                code="VERSION_COMPARISON_UNAVAILABLE",
                message=(
                    "Unable to generate v2 comparison"
                    if language == "en"
                    else "v2比較情報を生成できませんでした"
                ),
                details={"error_type": type(exc).__name__, "error": str(exc)},
            )
        return None


def _format_recommendations(recs: list, language: str) -> list[dict]:
    """Format recommendations for output."""
    formatted = []
    for rec in recs:
        rec_data = {
            "priority": rec.priority,
            "category": rec.category.value,
            "action": rec.action_ja if language == "ja" and rec.action_ja else rec.action,
            "effectiveness": rec.effectiveness.value,
            "feasibility": rec.feasibility.value,
            "current_level": rec.current_risk_level,
            "predicted_level": rec.predicted_risk_level,
            "rcr_reduction_percent": round(rec.rcr_reduction_percent, 1),
        }
        # Add parameter change info
        if rec.parameter_affected:
            rec_data["parameter_change"] = {
                "parameter": rec.parameter_affected,
                "from": rec.current_value,
                "to": rec.new_value,
            }
            if rec.coefficient_change:
                rec_data["parameter_change"]["coefficient"] = rec.coefficient_change
        # Add implementation notes if available
        if language == "ja" and rec.implementation_notes_ja:
            rec_data["notes"] = rec.implementation_notes_ja
        elif rec.implementation_notes:
            rec_data["notes"] = rec.implementation_notes
        formatted.append(rec_data)
    return formatted


def _format_explanation(explanation, language: str) -> dict:
    """Format calculation explanation for output."""
    output: dict[str, Any] = {
        "steps": [],
        "factors": [],
        "limitations": [],
    }

    # Add calculation steps
    steps = getattr(explanation, "steps", [])
    for step in steps:
        step_data = {
            "step": getattr(step, "step_number", None),
            "description": (
                getattr(step, "description_ja", step.description)
                if language == "ja"
                else step.description
            ),
            "formula": getattr(step, "formula", None),
            "inputs": getattr(step, "input_values", {}),
            "output": f"{getattr(step, 'output_value', '')} {getattr(step, 'output_unit', '')}".strip(),
        }
        step_explanation = (
            getattr(step, "explanation_ja", getattr(step, "explanation", ""))
            if language == "ja"
            else getattr(step, "explanation", "")
        )
        if step_explanation:
            step_data["explanation"] = step_explanation
        output["steps"].append(step_data)

    # Add contributing factors
    factors = getattr(explanation, "factors", [])
    for factor in factors:
        factor_data = {
            "name": (
                getattr(factor, "factor_name_ja", factor.factor_name)
                if language == "ja"
                else factor.factor_name
            ),
            "value": getattr(factor, "factor_value", None),
            "coefficient": getattr(factor, "coefficient", None),
            "contribution_percent": round(getattr(factor, "contribution_percent", 0), 1),
            "is_beneficial": getattr(factor, "is_beneficial", False),
            "can_improve": getattr(factor, "can_be_improved", False),
        }
        improvement_options = getattr(factor, "improvement_options", None)
        if improvement_options:
            factor_data["improvement_options"] = improvement_options
        output["factors"].append(factor_data)

    # Add limitations
    limitations = getattr(explanation, "limitations", [])
    for lim in limitations:
        lim_data = {
            "factor": (
                getattr(lim, "factor_name_ja", lim.factor_name)
                if language == "ja"
                else lim.factor_name
            ),
            "description": (
                getattr(lim, "description_ja", lim.description)
                if language == "ja"
                else lim.description
            ),
        }
        impact = (
            getattr(lim, "impact_ja", getattr(lim, "impact", ""))
            if language == "ja"
            else getattr(lim, "impact", "")
        )
        if impact:
            lim_data["impact"] = impact
        alternatives = getattr(lim, "alternatives", None)
        if alternatives:
            lim_data["alternatives"] = alternatives
        output["limitations"].append(lim_data)

    # Add summary
    summary = (
        getattr(explanation, "summary_ja", None)
        if language == "ja"
        else getattr(explanation, "summary", None)
    )
    if summary:
        output["summary"] = summary

    return output
