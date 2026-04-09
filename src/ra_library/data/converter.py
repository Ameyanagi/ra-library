"""
Substance model converter module.

Converts SubstanceData (database format) to Substance (model format)
for use in risk assessment calculations.
"""

from typing import Optional
from .substance_db import SubstanceData
from ..models.substance import (
    Substance,
    PropertyType,
    GHSClassification,
    OccupationalExposureLimits,
    PhysicochemicalProperties,
)


def to_ghs_classification(data: SubstanceData) -> GHSClassification:
    """
    Convert SubstanceData GHS fields to GHSClassification model.

    Args:
        data: SubstanceData from database

    Returns:
        GHSClassification model
    """
    return GHSClassification(
        # Physical hazards
        explosives=data.ghs_explosives,
        flammable_gases=data.ghs_flam_gas,
        flammable_aerosols=data.ghs_aerosol,
        oxidizing_gases=data.ghs_ox_gas,
        gases_under_pressure=data.ghs_gases_pressure,
        flammable_liquids=data.ghs_flam_liq,
        flammable_solids=data.ghs_flam_sol,
        self_reactive=data.ghs_self_react,
        pyrophoric_liquids=data.ghs_pyr_liq,
        pyrophoric_solids=data.ghs_pyr_sol,
        self_heating=data.ghs_self_heat,
        water_reactive=data.ghs_water_react,
        oxidizing_liquids=data.ghs_ox_liq,
        oxidizing_solids=data.ghs_ox_sol,
        organic_peroxides=data.ghs_org_perox,
        corrosive_to_metals=data.ghs_met_corr,
        # Health hazards
        acute_toxicity_oral=data.ghs_acute_oral,
        acute_toxicity_dermal=data.ghs_acute_dermal,
        acute_toxicity_inhalation_gas=data.ghs_acute_inhal_gas,
        acute_toxicity_inhalation_vapor=data.ghs_acute_inhal_vapor,
        acute_toxicity_inhalation_dust=data.ghs_acute_inhal_dust,
        skin_corrosion=data.ghs_skin_corr,
        eye_damage=data.ghs_eye_damage,
        respiratory_sensitization=data.ghs_resp_sens,
        skin_sensitization=data.ghs_skin_sens,
        germ_cell_mutagenicity=data.ghs_mutagenicity,
        carcinogenicity=data.ghs_carcinogenicity,
        reproductive_toxicity=data.ghs_reproductive,
        stot_single=data.ghs_stot_se,
        stot_repeated=data.ghs_stot_re,
        aspiration_hazard=data.ghs_aspiration,
    )


def to_oel_limits(
    data: SubstanceData,
    property_type: PropertyType,
) -> OccupationalExposureLimits:
    """
    Convert SubstanceData OEL fields to OccupationalExposureLimits model.

    Selects appropriate units based on property type:
    - SOLID: Uses mg/m³ values
    - LIQUID/GAS: Uses ppm values

    Note: The OccupationalExposureLimits model does not include jsoh_ceiling
    or acgih_tlv_c fields. These are stored in other_stel if available.

    Args:
        data: SubstanceData from database
        property_type: The property type of the substance

    Returns:
        OccupationalExposureLimits model
    """
    if property_type == PropertyType.SOLID:
        return OccupationalExposureLimits(
            concentration_standard_8hr=data.conc_standard_8hr_mgm3,
            concentration_standard_8hr_unit="mg/m³",
            concentration_standard_stel=data.conc_standard_stel_mgm3,
            concentration_standard_stel_unit="mg/m³",
            jsoh_8hr=data.jsoh_8hr_mgm3,
            jsoh_8hr_unit="mg/m³",
            acgih_tlv_twa=data.acgih_tlv_twa_mgm3,
            acgih_tlv_twa_unit="mg/m³",
            acgih_tlv_stel=data.acgih_tlv_stel_mgm3,
            acgih_tlv_stel_unit="mg/m³",
            dfg_mak=data.dfg_mak_mgm3,
            dfg_mak_unit="mg/m³" if data.dfg_mak_mgm3 else None,
            # Use other fields for ceiling values if available
            other_stel=data.jsoh_ceiling_mgm3 or data.acgih_tlv_c_mgm3,
            other_stel_unit="mg/m³" if (data.jsoh_ceiling_mgm3 or data.acgih_tlv_c_mgm3) else None,
        )
    else:
        # LIQUID and GAS both use ppm-based OELs in workbook metadata.
        return OccupationalExposureLimits(
            concentration_standard_8hr=data.conc_standard_8hr_ppm,
            concentration_standard_8hr_unit="ppm",
            concentration_standard_stel=data.conc_standard_stel_ppm,
            concentration_standard_stel_unit="ppm",
            jsoh_8hr=data.jsoh_8hr_ppm,
            jsoh_8hr_unit="ppm",
            acgih_tlv_twa=data.acgih_tlv_twa_ppm,
            acgih_tlv_twa_unit="ppm",
            acgih_tlv_stel=data.acgih_tlv_stel_ppm,
            acgih_tlv_stel_unit="ppm",
            dfg_mak=data.dfg_mak_ppm,
            dfg_mak_unit="ppm" if data.dfg_mak_ppm else None,
            # Use other fields for ceiling values if available
            other_stel=data.jsoh_ceiling_ppm or data.acgih_tlv_c_ppm,
            other_stel_unit="ppm" if (data.jsoh_ceiling_ppm or data.acgih_tlv_c_ppm) else None,
        )


def to_physical_properties(data: SubstanceData) -> PhysicochemicalProperties:
    """
    Convert SubstanceData physical properties to PhysicochemicalProperties model.

    Args:
        data: SubstanceData from database

    Returns:
        PhysicochemicalProperties model
    """
    return PhysicochemicalProperties(
        molecular_weight=data.molecular_weight,
        boiling_point=data.boiling_point,
        flash_point=data.flash_point,
        vapor_pressure=data.vapor_pressure,
        log_kow=data.log_kow,
    )


def _determine_property_type(data: SubstanceData) -> PropertyType:
    """
    Determine the property type for a substance.

    Mapping:
    - 1 → LIQUID
    - 2 → SOLID
    - 3 → GAS
    - None/other → SOLID (default)

    Args:
        data: SubstanceData from database

    Returns:
        PropertyType enum value
    """
    if data.property_type == 1:
        return PropertyType.LIQUID
    elif data.property_type == 2:
        return PropertyType.SOLID
    elif data.property_type == 3:
        return PropertyType.GAS
    else:
        # Default to solid for unknown types
        return PropertyType.SOLID


def _is_carcinogen(data: SubstanceData) -> bool:
    """
    Determine if substance is a carcinogen.

    Args:
        data: SubstanceData from database

    Returns:
        True if carcinogen, False otherwise
    """
    if data.is_carcinogen:
        return True
    if data.ghs_carcinogenicity is not None:
        return True
    return False


def to_substance_model(data: SubstanceData) -> Substance:
    """
    Convert SubstanceData to full Substance model.

    This is the main conversion function that creates a complete
    Substance model ready for use in risk assessment calculations.

    Args:
        data: SubstanceData from database

    Returns:
        Substance model with all fields populated
    """
    property_type = _determine_property_type(data)

    return Substance(
        cas_number=data.cas_number,
        name_ja=data.name_ja,
        name_en=data.name_en,
        property_type=property_type,
        ghs=to_ghs_classification(data),
        oel=to_oel_limits(data, property_type),
        properties=to_physical_properties(data),
        is_concentration_standard_substance=data.is_conc_standard,
        is_skin_hazard_substance=(
            data.skin_hazard_flag_code == "1"
            if data.skin_hazard_flag_code is not None
            else data.is_skin_hazard
        ),
        is_carcinogen=_is_carcinogen(data),
    )
