"""
Dermal risk assessment calculation.

Uses the Potts-Guy equation for skin permeability.

Reference:
- CREATE-SIMPLE Design v3.1.1, Section 4
- Potts & Guy (1992) Pharmaceutical Research 9:663-669
- VBA: modCalc.bas lines 2-79 (CalculateDermalAbsorption)
- VBA: modCalc.bas lines 278-311 (CalculateOELDermal)
"""

import math
from typing import Optional

from ..models.substance import Substance
from ..models.assessment import AssessmentInput, SkinArea, GloveType, SKIN_AREA_VALUES
from ..models.risk import RiskLevel, DermalRisk
from ..models.explanation import CalculationExplanation, CalculationStep
from ..references.catalog import REFERENCES
from .constants import GLOVE_COEFFICIENTS, GLOVE_TRAINING_COEFFICIENT


def calculate_oel_dermal(
    oel_8hr: Optional[float],
    property_type: str,
    molecular_weight: float,
    acrmax: Optional[float] = None,
) -> float:
    """
    Calculate dermal OEL from inhalation OEL.

    VBA Reference: modCalc.bas lines 278-311 (CalculateOELDermal)

    Formula:
    - Liquid: OEL_dermal = MW / (22.41 × 298.15/273.15) × OEL8hr × 0.75 × 10
    - Solid: OEL_dermal = OEL8hr × 0.75 × 10

    Args:
        oel_8hr: 8-hour inhalation OEL (ppm for liquid, mg/m³ for solid)
        property_type: "liquid" or "solid"
        molecular_weight: Molecular weight in g/mol
        acrmax: ACRmax value (used if OEL not available)

    Returns:
        Dermal OEL in mg
    """
    # Use OEL if available, otherwise ACRmax
    evaluation_standard = oel_8hr if oel_8hr is not None and oel_8hr > 0 else acrmax

    if evaluation_standard is None or evaluation_standard <= 0:
        raise ValueError("No valid OEL or ACRmax for dermal calculation")

    if property_type == "liquid":
        # Convert ppm to mg/m³ basis, then to dermal
        # Temperature correction: 298.15K / 273.15K = 1.0917
        temp_correction = 298.15 / 273.15
        molar_volume = 22.41 * temp_correction  # ~24.465 L/mol at 25°C
        oel_dermal = (molecular_weight / molar_volume) * evaluation_standard * 0.75 * 10
    else:  # solid
        oel_dermal = evaluation_standard * 0.75 * 10

    return oel_dermal


def calculate_dermal_kp_detailed(
    molecular_weight: float,
    log_kow: float,
) -> float:
    """
    Calculate skin permeability coefficient using detailed VBA formula.

    VBA Reference: modCalc.bas lines 2-50

    Uses the detailed formula with KpSc, KPol, and KAq components:
    - LogKpSc = -1.326 + 0.6097 × logKow - 0.1786 × √MW
    - KpSc = 10^LogKpSc
    - KPol = 0.0001519 / √MW
    - KAq = 2.5 / √MW
    - Kp = 1 / ((1 / (KpSc + KPol)) + 1 / KAq)

    Args:
        molecular_weight: Molecular weight in g/mol
        log_kow: Log octanol-water partition coefficient

    Returns:
        Kp in cm/hr
    """
    sqrt_mw = math.sqrt(molecular_weight)

    # Stratum corneum permeability
    log_kp_sc = -1.326 + 0.6097 * log_kow - 0.1786 * sqrt_mw
    kp_sc = 10 ** log_kp_sc

    # Polar route permeability
    k_pol = 0.0001519 / sqrt_mw

    # Aqueous route permeability
    k_aq = 2.5 / sqrt_mw

    # Combined permeability (parallel pathways)
    # Kp = 1 / ((1 / (KpSc + KPol)) + 1 / KAq)
    kp = 1 / ((1 / (kp_sc + k_pol)) + (1 / k_aq))

    return kp


def calculate_skin_retention_time(
    absorption_rate: float,
    evaporation_rate: float,
    property_type: str,
) -> float:
    """
    Calculate skin retention time.

    VBA Reference: modCalc.bas lines 51-60

    Formula:
    - Liquid: 7 / (absorption_rate + evaporation_rate)
    - Solid: 3 / (absorption_rate + evaporation_rate)

    Args:
        absorption_rate: Absorption rate
        evaporation_rate: Evaporation rate
        property_type: "liquid" or "solid"

    Returns:
        Skin retention time in hours (capped at reasonable maximum)
    """
    total_rate = absorption_rate + evaporation_rate

    # Avoid division by zero
    if total_rate <= 0:
        return 100.0  # Cap at reasonable maximum

    if property_type == "liquid":
        retention_time = 7 / total_rate
    else:  # solid
        retention_time = 3 / total_rate

    # Cap at reasonable maximum
    return min(retention_time, 100.0)


def calculate_total_skin_exposure_time(
    working_hours: float,
    skin_retention_time: float,
) -> float:
    """
    Calculate total skin exposure time.

    VBA Reference: modCalc.bas lines 61-70

    Total exposure = working_hours + skin_retention_time, capped at 10 hours.

    Args:
        working_hours: Hours worked per day
        skin_retention_time: Skin retention time in hours

    Returns:
        Total exposure time in hours (max 10)
    """
    total_time = working_hours + skin_retention_time
    return min(total_time, 10.0)


def calculate_evaporation_rate(
    vapor_pressure: float,
    molecular_weight: float,
) -> float:
    """
    Calculate evaporation rate from skin surface.

    VBA Reference: modCalc.bas lines 47-49

    Uses the detailed VBA formula with BetaCoefficient:
    - MolecularDiffusivity = 0.06 * (76 / MW) ^ 0.5
    - BetaCoefficient = (0.0111 * AirVelocity^0.96 * MolecularDiffusivity^0.19) /
                        (KinematicViscosity^0.15 * EvaporationAreaLength^0.04)
    - EvaporationRate = (BetaCoefficient * VP * MW) / (R * T * 10)

    Constants (VBA modCalc.bas lines 21-26):
    - GasConstant = 8.314 Pa*m³/mol/K
    - AirVelocity = 1080 m/h
    - KinematicViscosity = 0.054 m²/h
    - EvaporationAreaLength = 0.1 m
    - Temperature = 293 K (20°C)

    Args:
        vapor_pressure: Vapor pressure in Pa
        molecular_weight: Molecular weight in g/mol

    Returns:
        Evaporation rate in mg/cm²/hr
    """
    if vapor_pressure <= 0:
        return 0.0

    # Constants from VBA modCalc.bas lines 21-26
    GAS_CONSTANT = 8.314  # Pa*m³/mol/K
    AIR_VELOCITY = 1080  # m/h
    KINEMATIC_VISCOSITY = 0.054  # m²/h
    EVAPORATION_AREA_LENGTH = 0.1  # m
    TEMPERATURE = 293  # K (20°C, per VBA)

    # Calculate molecular diffusivity (VBA line 47)
    molecular_diffusivity = 0.06 * (76 / molecular_weight) ** 0.5

    # Calculate beta coefficient (VBA line 48)
    beta_coefficient = (
        (0.0111 * (AIR_VELOCITY ** 0.96) * (molecular_diffusivity ** 0.19))
        / ((KINEMATIC_VISCOSITY ** 0.15) * (EVAPORATION_AREA_LENGTH ** 0.04))
    )

    # Calculate evaporation rate (VBA line 49)
    evaporation_rate = (
        (beta_coefficient * vapor_pressure * molecular_weight)
        / (GAS_CONSTANT * TEMPERATURE * 10)
    )

    return evaporation_rate


def calculate_absorption_rate_vba(
    kp: float,
    water_solubility: float,
) -> float:
    """
    Calculate absorption rate using VBA formula.

    VBA Reference: modCalc.bas lines 35-40

    Formula: Absorption rate = Kp × water_solubility

    Args:
        kp: Permeability coefficient (cm/hr)
        water_solubility: Water solubility (mg/L = mg/1000cm³)

    Returns:
        Absorption rate in mg/cm²/hr
    """
    # Convert water solubility from mg/L to mg/cm³
    # 1 L = 1000 cm³, so mg/L = mg/1000cm³
    concentration = water_solubility / 1000.0

    return kp * concentration


def calculate_potts_guy_kp(
    log_kow: float,
    molecular_weight: float,
) -> float:
    """
    Calculate skin permeability coefficient using simplified Potts-Guy equation.

    Formula: log Kp = -2.72 + 0.71 × log Kow - 0.0061 × MW

    Reference: Potts & Guy (1992) Pharmaceutical Research 9:663-669

    Note: For VBA parity, use calculate_dermal_kp_detailed() instead.

    Args:
        log_kow: Log octanol-water partition coefficient
        molecular_weight: Molecular weight in g/mol

    Returns:
        Kp in cm/hr
    """
    log_kp = -2.72 + 0.71 * log_kow - 0.0061 * molecular_weight
    return 10**log_kp


def calculate_dermal_flux(
    kp: float,
    concentration: float,
) -> float:
    """
    Calculate dermal flux (absorption rate).

    Formula: Flux = Kp × C

    Args:
        kp: Permeability coefficient (cm/hr)
        concentration: Concentration on skin (mg/cm³)

    Returns:
        Flux in mg/cm²/hr
    """
    return kp * concentration


def calculate_dermal_absorption(
    flux: float,
    skin_area: float,
    exposure_duration: float,
    glove_coefficient: float = 1.0,
) -> float:
    """
    Calculate total dermal absorption.

    Formula: Absorption = Flux × Area × Duration × Glove_coeff

    Args:
        flux: Dermal flux (mg/cm²/hr)
        skin_area: Exposed skin area (cm²)
        exposure_duration: Duration of exposure (hours)
        glove_coefficient: Glove protection coefficient

    Returns:
        Total absorbed dose in mg
    """
    return flux * skin_area * exposure_duration * glove_coefficient


def calculate_dermal_risk(
    assessment_input: AssessmentInput,
    substance: Substance,
    content_percent: float = 100.0,
    verbose: bool = True,
    use_vba_method: bool = True,
) -> Optional[DermalRisk]:
    """
    Calculate dermal risk for a substance.

    Uses the VBA detailed formula by default for CREATE-SIMPLE parity:
    - Detailed Kp with KpSc, KPol, KAq components
    - Absorption rate = Kp × water_solubility
    - Evaporation rate from vapor pressure
    - Skin retention time calculation
    - Total exposure = working_hours + retention_time (capped at 10h)

    Reference: CREATE-SIMPLE Design v3.1.1, Section 4
    VBA Reference: modCalc.bas lines 2-79 (CalculateDermalAbsorption)

    Args:
        assessment_input: Assessment input parameters
        substance: Substance data
        content_percent: Content percentage of the substance
        verbose: Whether to generate detailed explanation
        use_vba_method: Use VBA detailed formula (default True for parity)

    Returns:
        DermalRisk result, or None if dermal assessment not requested
    """
    if not assessment_input.assess_dermal:
        return None

    props = substance.properties

    # Check required properties
    if props.log_kow is None:
        raise ValueError("log Kow is required for dermal assessment")
    if props.molecular_weight is None:
        raise ValueError("Molecular weight is required for dermal assessment")

    steps = []
    step_num = 1

    # Determine property type for retention time calculation
    property_type = substance.property_type.value

    if use_vba_method:
        # VBA Method: Detailed Kp formula with retention time
        # Step 1: Calculate Kp using detailed VBA formula
        kp = calculate_dermal_kp_detailed(props.molecular_weight, props.log_kow)

        if verbose:
            steps.append(
                CalculationStep(
                    step_number=step_num,
                    description="Calculate permeability coefficient (VBA detailed)",
                    description_ja="透過係数を計算（VBA詳細式）",
                    formula="Kp = 1/((1/(KpSc + KPol)) + 1/KAq)",
                    input_values={
                        "log_kow": props.log_kow,
                        "molecular_weight": props.molecular_weight,
                    },
                    output_value=kp,
                    output_unit="cm/hr",
                    explanation="Detailed Kp with stratum corneum, polar, and aqueous routes",
                    explanation_ja="角質層、極性、水性経路を考慮した詳細透過係数",
                    reference=REFERENCES.get("create_simple"),
                )
            )
            step_num += 1

        # Step 2: Calculate absorption rate using water solubility
        water_solubility = props.water_solubility or 1000.0  # Default 1000 mg/L if unknown
        absorption_rate = calculate_absorption_rate_vba(kp, water_solubility)

        # Adjust for content percentage
        absorption_rate *= (content_percent / 100)

        if verbose:
            steps.append(
                CalculationStep(
                    step_number=step_num,
                    description="Calculate absorption rate",
                    description_ja="吸収速度を計算",
                    formula="Absorption rate = Kp × (water_solubility/1000) × content%",
                    input_values={
                        "kp": kp,
                        "water_solubility": water_solubility,
                        "content_percent": content_percent,
                    },
                    output_value=absorption_rate,
                    output_unit="mg/cm²/hr",
                    explanation="Rate of substance absorption through skin",
                    explanation_ja="物質の経皮吸収速度",
                )
            )
            step_num += 1

        # Step 3: Calculate evaporation rate
        vapor_pressure = props.vapor_pressure or 0.0
        evaporation_rate = calculate_evaporation_rate(vapor_pressure, props.molecular_weight)

        if verbose:
            steps.append(
                CalculationStep(
                    step_number=step_num,
                    description="Calculate evaporation rate",
                    description_ja="蒸発速度を計算",
                    formula="Evap = VP × MW / (R × T × 3600)",
                    input_values={
                        "vapor_pressure": vapor_pressure,
                        "molecular_weight": props.molecular_weight,
                    },
                    output_value=evaporation_rate,
                    output_unit="mg/cm²/hr",
                    explanation="Rate of evaporation from skin surface at 30°C",
                    explanation_ja="皮膚表面からの蒸発速度（30°C）",
                )
            )
            step_num += 1

        # Step 4: Calculate skin retention time
        retention_time = calculate_skin_retention_time(
            absorption_rate, evaporation_rate, property_type
        )

        if verbose:
            numerator = 7 if property_type == "liquid" else 3
            steps.append(
                CalculationStep(
                    step_number=step_num,
                    description="Calculate skin retention time",
                    description_ja="皮膚残留時間を計算",
                    formula=f"Retention = {numerator} / (absorption_rate + evaporation_rate)",
                    input_values={
                        "absorption_rate": absorption_rate,
                        "evaporation_rate": evaporation_rate,
                        "property_type": property_type,
                    },
                    output_value=retention_time,
                    output_unit="hr",
                    explanation=f"Time substance remains on skin ({numerator} for {property_type})",
                    explanation_ja=f"物質が皮膚に残留する時間（{property_type}の場合{numerator}）",
                )
            )
            step_num += 1

        # Step 5: Calculate total exposure time (capped at 10h)
        working_hours = assessment_input.working_hours_per_day
        total_exposure_time = calculate_total_skin_exposure_time(working_hours, retention_time)

        if verbose:
            steps.append(
                CalculationStep(
                    step_number=step_num,
                    description="Calculate total exposure time",
                    description_ja="総曝露時間を計算",
                    formula="Total time = min(working_hours + retention_time, 10)",
                    input_values={
                        "working_hours": working_hours,
                        "retention_time": retention_time,
                    },
                    output_value=total_exposure_time,
                    output_unit="hr",
                    explanation="Total skin exposure time (capped at 10 hours)",
                    explanation_ja="総皮膚曝露時間（最大10時間）",
                )
            )
            step_num += 1

        # Use absorption_rate as flux for the rest of the calculation
        flux = absorption_rate
        exposure_duration = total_exposure_time

    else:
        # Simplified Potts-Guy method (legacy)
        kp = calculate_potts_guy_kp(props.log_kow, props.molecular_weight)

        if verbose:
            steps.append(
                CalculationStep(
                    step_number=step_num,
                    description="Calculate permeability coefficient (Potts-Guy)",
                    description_ja="透過係数を計算（Potts-Guy式）",
                    formula="log Kp = -2.72 + 0.71 × log Kow - 0.0061 × MW",
                    input_values={
                        "log_kow": props.log_kow,
                        "molecular_weight": props.molecular_weight,
                    },
                    output_value=kp,
                    output_unit="cm/hr",
                    explanation=f"Kp = 10^(-2.72 + 0.71 × {props.log_kow} - 0.0061 × {props.molecular_weight})",
                    reference=REFERENCES["potts_guy"],
                )
            )
            step_num += 1

        # Estimate concentration on skin
        density = props.density or 1.0
        concentration = density * (content_percent / 100) * 1000

        if verbose:
            steps.append(
                CalculationStep(
                    step_number=step_num,
                    description="Estimate concentration on skin",
                    description_ja="皮膚上の濃度を推定",
                    formula="C = density × content% × 1000",
                    input_values={
                        "density": density,
                        "content_percent": content_percent,
                    },
                    output_value=concentration,
                    output_unit="mg/cm³",
                    explanation="Concentration of substance in contact with skin",
                )
            )
            step_num += 1

        flux = calculate_dermal_flux(kp, concentration)

        if verbose:
            steps.append(
                CalculationStep(
                    step_number=step_num,
                    description="Calculate dermal flux",
                    description_ja="経皮フラックスを計算",
                    formula="Flux = Kp × C",
                    input_values={"kp": kp, "concentration": concentration},
                    output_value=flux,
                    output_unit="mg/cm²/hr",
                    explanation="Rate of absorption through skin",
                )
            )
            step_num += 1

        exposure_duration = assessment_input.working_hours_per_day

    # Get skin area
    skin_area_type = assessment_input.exposed_skin_area or SkinArea.HANDS_BOTH
    skin_area = SKIN_AREA_VALUES.get(skin_area_type, 840)

    # Get glove coefficient
    glove_type = assessment_input.glove_type or GloveType.NONE
    glove_coeff = GLOVE_COEFFICIENTS.get(glove_type.value, 1.0)

    # Apply glove training effect if applicable
    training_coeff = 1.0
    if assessment_input.glove_training and glove_type != GloveType.NONE:
        training_coeff = GLOVE_TRAINING_COEFFICIENT
        if verbose:
            steps.append(
                CalculationStep(
                    step_number=step_num,
                    description="Apply glove training coefficient",
                    description_ja="手袋訓練係数を適用",
                    formula="Training coefficient = 0.5",
                    input_values={"glove_training": True},
                    output_value=training_coeff,
                    output_unit="",
                    explanation="Trained workers use gloves more effectively: 50% reduction",
                    explanation_ja="訓練を受けた作業者は手袋をより効果的に使用: 50%低減",
                )
            )
            step_num += 1

    # Combined glove effect
    combined_glove_coeff = glove_coeff * training_coeff

    # Calculate total absorption
    total_absorption = calculate_dermal_absorption(
        flux=flux,
        skin_area=skin_area,
        exposure_duration=exposure_duration,
        glove_coefficient=combined_glove_coeff,
    )

    if verbose:
        training_text = " × Training" if training_coeff < 1.0 else ""
        steps.append(
            CalculationStep(
                step_number=step_num,
                description="Calculate total dermal absorption",
                description_ja="総経皮吸収量を計算",
                formula=f"Absorption = Rate × Area × Duration × Glove_coeff{training_text}",
                input_values={
                    "flux": flux,
                    "skin_area": skin_area,
                    "duration": exposure_duration,
                    "glove_coeff": glove_coeff,
                    "training_coeff": training_coeff if training_coeff < 1.0 else None,
                    "combined_coeff": combined_glove_coeff,
                },
                output_value=total_absorption,
                output_unit="mg",
                explanation=f"Total absorbed over {exposure_duration:.1f} hours with {skin_area} cm² exposed",
            )
        )
        step_num += 1

    # Calculate dermal OEL from inhalation OEL per CREATE-SIMPLE methodology
    # VBA Reference: modCalc.bas lines 278-311 (CalculateOELDermal)
    from .oel import select_oel
    from .acr import get_acrmax

    oel_value, oel_unit, oel_source = select_oel(substance.oel)
    # Get ACRmax only for carcinogens/mutagens, not reproductive toxicity
    acrmax_hazard_level = substance.ghs.get_acrmax_hazard_level()
    acrmax = get_acrmax(acrmax_hazard_level, property_type)

    dermal_oel = None
    try:
        dermal_oel = calculate_oel_dermal(
            oel_8hr=oel_value,
            property_type=property_type,
            molecular_weight=props.molecular_weight,
            acrmax=acrmax,
        )
        # RCR = absorbed amount / dermal OEL
        rcr = total_absorption / dermal_oel

        if verbose:
            steps.append(
                CalculationStep(
                    step_number=step_num,
                    description="Calculate dermal RCR",
                    description_ja="経皮RCRを計算",
                    formula="RCR = Total absorption / Dermal OEL",
                    input_values={
                        "total_absorption": total_absorption,
                        "dermal_oel": dermal_oel,
                        "oel_source": oel_source,
                        "acrmax": acrmax,
                    },
                    output_value=rcr,
                    output_unit="",
                    explanation=f"Dermal OEL = {dermal_oel:.2f} mg derived from {oel_source}",
                    explanation_ja=f"経皮OEL = {dermal_oel:.2f} mg（{oel_source}から算出）",
                )
            )
            step_num += 1
    except ValueError:
        # No valid OEL available - cannot calculate RCR accurately
        # Use very conservative estimate
        rcr = 1.0  # Default to Level III boundary
        dermal_oel = None

    risk_level = RiskLevel.from_rcr(rcr)

    # Build explanation
    explanation = None
    if verbose:
        method_name = "VBA detailed" if use_vba_method else "Potts-Guy"
        main_formula = (
            "Absorption = (Kp × solubility × content%) × Area × (work_hours + retention) × Glove"
            if use_vba_method
            else "Absorption = Kp × C × Area × Duration × Glove"
        )
        explanation = CalculationExplanation(
            steps=steps,
            summary=f"Dermal absorption ({method_name}): {total_absorption:.4f} mg over {exposure_duration:.1f} hours",
            summary_ja=f"経皮吸収量（{method_name}）: {total_absorption:.4f} mg ({exposure_duration:.1f}時間)",
            main_formula=main_formula,
        )

    return DermalRisk(
        permeability_coefficient=kp,
        dermal_flux=flux,
        skin_absorption=total_absorption,
        skin_area=skin_area,
        dnel_dermal=dermal_oel,  # Use calculated dermal OEL
        rcr=rcr,
        risk_level=risk_level,
        explanation=explanation,
    )
