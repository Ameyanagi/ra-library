"""
Work scenario presets for risk assessment.

Common workplace scenarios with pre-configured conditions, duration,
protection, and constraints.

Usage:
    from ra_library import RiskAssessment

    # Use a preset
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
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class WorkPreset:
    """
    A pre-configured work scenario.

    Attributes:
        name: Preset identifier (e.g., "lab_organic")
        description: Japanese description
        description_en: English description

        # Conditions
        property_type: "liquid", "solid", or "gas"
        amount: Amount level
        ventilation: Ventilation level
        control_velocity_verified: Whether control velocity is verified
        dustiness: Dustiness level (for solids)
        work_area_size: Work area size (for liquids)
        is_spray: Whether spray operation
        process_temperature: Process temperature in °C (for physical hazard)

        # Duration
        hours: Working hours per day
        days_per_week: Days per week (if weekly)
        days_per_month: Days per month (if less than weekly)

        # Protection
        gloves: Glove type
        glove_training: Whether workers are trained
        rpe: RPE type (None = no RPE in RA sheet mode)

        # Constraints
        max_ventilation: Maximum ventilation level
        excluded_rpe: List of excluded RPE types
        no_admin: Whether to exclude frequency reduction
    """
    name: str
    description: str
    description_en: str

    # Conditions
    property_type: str = "liquid"
    amount: str = "small"
    ventilation: str = "local_enc"
    control_velocity_verified: bool = True
    dustiness: Optional[str] = None
    work_area_size: Optional[str] = None
    is_spray: bool = False
    process_temperature: Optional[float] = None

    # Duration
    hours: float = 4.0
    days_per_week: Optional[int] = 5
    days_per_month: Optional[int] = None

    # Protection
    gloves: str = "resistant"
    glove_training: bool = True
    rpe: Optional[str] = None

    # Constraints
    max_ventilation: Optional[str] = None
    excluded_rpe: list[str] = field(default_factory=list)
    no_admin: bool = False


# =============================================================================
# Laboratory Presets (研究室)
# =============================================================================

LAB_ORGANIC = WorkPreset(
    name="lab_organic",
    description="有機合成研究室（液体・少量・ドラフト使用）",
    description_en="Organic chemistry lab (liquid, small amount, fume hood)",
    property_type="liquid",
    amount="small",
    ventilation="local_enc",
    control_velocity_verified=True,
    # work_area_size not set - matches CREATE-SIMPLE standard methodology
    hours=4.0,
    days_per_week=5,
    gloves="resistant",
    glove_training=True,
    max_ventilation="local_enc",  # Labs typically cannot install sealed systems
)

LAB_ORGANIC_MINUTE = WorkPreset(
    name="lab_organic_minute",
    description="有機合成研究室（液体・微量・ドラフト使用）",
    description_en="Organic chemistry lab (liquid, minute amount, fume hood)",
    property_type="liquid",
    amount="minute",
    ventilation="local_enc",
    control_velocity_verified=True,
    hours=2.0,
    days_per_week=3,
    gloves="resistant",
    glove_training=True,
    max_ventilation="local_enc",
)

LAB_POWDER = WorkPreset(
    name="lab_powder",
    description="粉体取扱い研究室（固体・少量・ドラフト・手袋使用）",
    description_en="Powder handling lab (solid, small amount, fume hood, gloves)",
    property_type="solid",
    amount="small",
    dustiness="high",  # Fine powders in lab
    ventilation="local_enc",
    control_velocity_verified=True,
    hours=4.0,
    days_per_week=3,
    gloves="resistant",
    glove_training=True,
    rpe=None,  # No RPE in lab (RA sheet mode)
    max_ventilation="local_enc",
)

LAB_CATALYST = WorkPreset(
    name="lab_catalyst",
    description="触媒取扱い研究室（固体・少量・ドラフト・手袋使用）",
    description_en="Catalyst handling lab (solid, small amount, fume hood, gloves)",
    property_type="solid",
    amount="small",
    dustiness="high",
    ventilation="local_enc",
    control_velocity_verified=True,
    hours=4.0,
    days_per_week=3,
    gloves="resistant",
    glove_training=True,
    rpe=None,  # No RPE in lab (RA sheet mode)
    max_ventilation="local_enc",
)

LAB_ANALYTICAL = WorkPreset(
    name="lab_analytical",
    description="分析研究室（液体・微量・ドラフト使用）",
    description_en="Analytical lab (liquid, trace/minute amount, fume hood)",
    property_type="liquid",
    amount="trace",
    ventilation="local_enc",
    control_velocity_verified=True,
    hours=2.0,
    days_per_week=5,
    gloves="resistant",
    glove_training=True,
    max_ventilation="local_enc",
)

LAB_GAS = WorkPreset(
    name="lab_gas",
    description="研究室でのガス取扱い（気体・少量・ドラフト使用）",
    description_en="Laboratory gas handling (gas, small amount band, fume hood/local enclosure)",
    property_type="gas",
    amount="small",
    ventilation="local_enc",
    control_velocity_verified=True,
    hours=1.0,
    days_per_week=5,
    gloves="none",
    glove_training=False,
    max_ventilation="local_enc",
)


# =============================================================================
# Production Presets (製造)
# =============================================================================

PRODUCTION_BATCH = WorkPreset(
    name="production_batch",
    description="バッチ製造（液体・中量・局所排気）",
    description_en="Batch production (liquid, medium amount, local exhaust)",
    property_type="liquid",
    amount="medium",
    ventilation="local_ext",
    control_velocity_verified=True,
    work_area_size="medium",
    hours=8.0,
    days_per_week=5,
    gloves="resistant",
    glove_training=True,
)

PRODUCTION_BATCH_ENCLOSED = WorkPreset(
    name="production_batch_enclosed",
    description="バッチ製造（液体・中量・囲い式局所排気）",
    description_en="Batch production (liquid, medium amount, enclosed local exhaust)",
    property_type="liquid",
    amount="medium",
    ventilation="local_enc",
    control_velocity_verified=True,
    work_area_size="medium",
    hours=8.0,
    days_per_week=5,
    gloves="resistant",
    glove_training=True,
)

PRODUCTION_CONTINUOUS = WorkPreset(
    name="production_continuous",
    description="連続製造（液体・大量・密閉系）",
    description_en="Continuous production (liquid, large amount, sealed system)",
    property_type="liquid",
    amount="large",
    ventilation="sealed",
    hours=8.0,
    days_per_week=5,
    gloves="resistant",
    glove_training=True,
)

PRODUCTION_POWDER = WorkPreset(
    name="production_powder",
    description="粉体製造（固体・中量・局所排気・RPE着用）",
    description_en="Powder production (solid, medium amount, local exhaust, with RPE)",
    property_type="solid",
    amount="medium",
    dustiness="high",
    ventilation="local_ext",
    control_velocity_verified=True,
    hours=8.0,
    days_per_week=5,
    gloves="resistant",
    glove_training=True,
    rpe="half_mask",
)

PRODUCTION_PACKAGING = WorkPreset(
    name="production_packaging",
    description="包装作業（固体・中量・局所排気）",
    description_en="Packaging operation (solid, medium amount, local exhaust)",
    property_type="solid",
    amount="medium",
    dustiness="medium",  # Typically granular/crystalline
    ventilation="local_ext",
    control_velocity_verified=True,
    hours=8.0,
    days_per_week=5,
    gloves="resistant",
    glove_training=True,
)


# =============================================================================
# Maintenance Presets (保全)
# =============================================================================

MAINTENANCE_CLEANING = WorkPreset(
    name="maintenance_cleaning",
    description="清掃作業（液体・少量・一般換気・短時間）",
    description_en="Cleaning operation (liquid, small amount, basic ventilation, short duration)",
    property_type="liquid",
    amount="small",
    ventilation="basic",
    hours=2.0,
    days_per_week=2,
    gloves="resistant",
    glove_training=True,
    rpe="half_mask",
)

MAINTENANCE_CLEANING_ENCLOSED = WorkPreset(
    name="maintenance_cleaning_enclosed",
    description="清掃作業（液体・少量・局所排気・短時間）",
    description_en="Cleaning with local exhaust (liquid, small amount, local exhaust, short duration)",
    property_type="liquid",
    amount="small",
    ventilation="local_enc",
    control_velocity_verified=True,
    hours=2.0,
    days_per_week=2,
    gloves="resistant",
    glove_training=True,
)

MAINTENANCE_TANK = WorkPreset(
    name="maintenance_tank",
    description="タンク内作業（液体・中量・換気なし・RPE必須）",
    description_en="Tank entry (liquid, medium amount, no ventilation, RPE required)",
    property_type="liquid",
    amount="medium",
    ventilation="none",
    hours=2.0,
    days_per_month=2,  # Infrequent
    gloves="resistant",
    glove_training=True,
    rpe="full_mask",  # Required for confined space
    excluded_rpe=["half_mask", "loose_fit"],  # Only tight-fit full-face
)


# =============================================================================
# Spray Operation Presets (スプレー作業)
# =============================================================================

SPRAY_PAINTING = WorkPreset(
    name="spray_painting",
    description="スプレー塗装（液体・少量・局所排気・スプレー作業）",
    description_en="Spray painting (liquid, small amount, local exhaust, spray operation)",
    property_type="liquid",
    amount="small",
    ventilation="local_ext",
    control_velocity_verified=True,
    is_spray=True,
    hours=4.0,
    days_per_week=5,
    gloves="resistant",
    glove_training=True,
    rpe="half_mask",  # Required for spray
)

SPRAY_COATING = WorkPreset(
    name="spray_coating",
    description="スプレーコーティング（液体・中量・局所排気・スプレー作業）",
    description_en="Spray coating (liquid, medium amount, local exhaust, spray operation)",
    property_type="liquid",
    amount="medium",
    ventilation="local_enc",
    control_velocity_verified=True,
    is_spray=True,
    hours=6.0,
    days_per_week=5,
    gloves="resistant",
    glove_training=True,
    rpe="papr",  # PAPR for extended spray work
)


# =============================================================================
# Preset Registry
# =============================================================================

PRESETS: dict[str, WorkPreset] = {
    # Laboratory
    "lab_organic": LAB_ORGANIC,
    "lab_organic_minute": LAB_ORGANIC_MINUTE,
    "lab_powder": LAB_POWDER,
    "lab_catalyst": LAB_CATALYST,
    "lab_analytical": LAB_ANALYTICAL,
    "lab_gas": LAB_GAS,
    # Production
    "production_batch": PRODUCTION_BATCH,
    "production_batch_enclosed": PRODUCTION_BATCH_ENCLOSED,
    "production_continuous": PRODUCTION_CONTINUOUS,
    "production_powder": PRODUCTION_POWDER,
    "production_packaging": PRODUCTION_PACKAGING,
    # Maintenance
    "maintenance_cleaning": MAINTENANCE_CLEANING,
    "maintenance_cleaning_enclosed": MAINTENANCE_CLEANING_ENCLOSED,
    "maintenance_tank": MAINTENANCE_TANK,
    # Spray
    "spray_painting": SPRAY_PAINTING,
    "spray_coating": SPRAY_COATING,
}

# Japanese aliases
PRESETS_JA: dict[str, str] = {
    "有機合成": "lab_organic",
    "有機合成研究室": "lab_organic",
    "粉体研究室": "lab_powder",
    "触媒研究室": "lab_catalyst",
    "分析研究室": "lab_analytical",
    "ガス研究室": "lab_gas",
    "バッチ製造": "production_batch",
    "連続製造": "production_continuous",
    "粉体製造": "production_powder",
    "包装作業": "production_packaging",
    "清掃作業": "maintenance_cleaning",
    "タンク内作業": "maintenance_tank",
    "スプレー塗装": "spray_painting",
}


def get_preset(name: str) -> WorkPreset:
    """
    Get a preset by name.

    Args:
        name: Preset name (English or Japanese alias)

    Returns:
        WorkPreset object

    Raises:
        ValueError: If preset not found
    """
    # Check Japanese alias first
    if name in PRESETS_JA:
        name = PRESETS_JA[name]

    if name not in PRESETS:
        available = ", ".join(sorted(PRESETS.keys()))
        raise ValueError(
            f"Unknown preset: {name}. Available presets: {available}"
        )

    return PRESETS[name]


def list_presets() -> list[tuple[str, str, str]]:
    """
    List all available presets.

    Returns:
        List of (name, description_ja, description_en) tuples
    """
    return [
        (name, preset.description, preset.description_en)
        for name, preset in PRESETS.items()
    ]


def print_presets():
    """Print all available presets in a readable format."""
    categories = {
        "Laboratory (研究室)": ["lab_organic", "lab_organic_minute", "lab_powder", "lab_catalyst", "lab_analytical", "lab_gas"],
        "Production (製造)": ["production_batch", "production_batch_enclosed", "production_continuous", "production_powder", "production_packaging"],
        "Maintenance (保全)": ["maintenance_cleaning", "maintenance_cleaning_enclosed", "maintenance_tank"],
        "Spray (スプレー)": ["spray_painting", "spray_coating"],
    }

    print("=" * 60)
    print("Available Presets")
    print("=" * 60)

    for category, preset_names in categories.items():
        print(f"\n{category}:")
        print("-" * 40)
        for name in preset_names:
            preset = PRESETS[name]
            print(f"  {name}")
            print(f"    {preset.description}")
            print(f"    {preset.description_en}")
