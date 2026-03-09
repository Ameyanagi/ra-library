"""
Scientific reference catalog.

All calculations include citations to enable users to
understand the scientific basis and regulatory requirements.
"""

from ..models.reference import Reference

REFERENCES: dict[str, Reference] = {
    # CREATE-SIMPLE Official Documentation
    "create_simple_design": Reference(
        id="create_simple_design",
        title="CREATE-SIMPLEの設計基準",
        title_ja="CREATE-SIMPLEの設計基準",
        authors=["厚生労働省労働基準局安全衛生部化学物質対策課"],
        organization="厚生労働省",
        organization_ja="厚生労働省",
        year=2025,
        version="v3.1.1",
        url="https://anzeninfo.mhlw.go.jp/user/anzen/kag/pdf/CREATE-SIMPLE_design_v3.1.1.pdf",
        description="Official design document for CREATE-SIMPLE risk assessment methodology",
        description_ja="CREATE-SIMPLEリスクアセスメント手法の設計基準書",
    ),
    "create_simple_design_2_1": Reference(
        id="create_simple_design_2_1",
        title="CREATE-SIMPLE設計基準 Section 2.1: ばく露限界値（吸入）の選定",
        section="Section 2.1",
        description="OEL selection priority order",
        description_ja="ばく露限界値の選定順序",
    ),
    "create_simple_design_3_2": Reference(
        id="create_simple_design_3_2",
        title="CREATE-SIMPLE設計基準 Section 3.2: 揮発性/飛散性の分類",
        section="Section 3.2",
        description="Volatility and dustiness classification",
        description_ja="揮発性・飛散性の分類",
    ),
    "create_simple_design_3_3_band": Reference(
        id="create_simple_design_3_3_band",
        title="CREATE-SIMPLE設計基準 Figure 10/11: 暴露バンドテーブル",
        section="Section 3.3",
        figure="Figure 10, 11",
        description="Exposure band lookup tables for liquids and solids",
        description_ja="液体・粉体の暴露バンドテーブル",
    ),
    "create_simple_design_3_3_content": Reference(
        id="create_simple_design_3_3_content",
        title="CREATE-SIMPLE設計基準 Figure 15: 含有率係数",
        section="Section 3.3",
        figure="Figure 15",
        description="Content percentage coefficient based on ECETOC TRA / Raoult's law",
        description_ja="含有率係数（ECETOC TRA / ラウールの法則に基づく）",
    ),
    "create_simple_design_3_3_spray": Reference(
        id="create_simple_design_3_3_spray",
        title="CREATE-SIMPLE設計基準: スプレー作業係数",
        section="Section 3.3",
        description="Spray operation coefficient (×10)",
        description_ja="スプレー作業係数（×10）",
    ),
    "create_simple_design_3_3_vent": Reference(
        id="create_simple_design_3_3_vent",
        title="CREATE-SIMPLE設計基準 Figure 17: 換気係数",
        section="Section 3.3",
        figure="Figure 17",
        description="Ventilation coefficients by type",
        description_ja="換気タイプ別の係数",
    ),
    "create_simple_design_3_3_floor": Reference(
        id="create_simple_design_3_3_floor",
        title="CREATE-SIMPLE設計基準 Section 3.3 注11: 最小暴露フロア",
        section="Section 3.3",
        description="Minimum exposure floor: 0.005 ppm (liquid), 0.001 mg/m³ (solid)",
        description_ja="最小暴露推定値: 液体0.005ppm、粉体0.001mg/m³",
    ),
    "create_simple_design_3_3_duration": Reference(
        id="create_simple_design_3_3_duration",
        title="CREATE-SIMPLE設計基準 Figure 18/19: 作業時間係数",
        section="Section 3.3",
        figure="Figure 18, 19",
        description="Duration and frequency coefficients",
        description_ja="作業時間・頻度係数",
    ),
    "create_simple_design_4_3": Reference(
        id="create_simple_design_4_3",
        title="CREATE-SIMPLE設計基準 Section 4.3: 経皮吸収リスク評価",
        section="Section 4.3",
        description="Dermal absorption risk assessment using Potts-Guy equation",
        description_ja="Potts-Guy式を用いた経皮吸収リスク評価",
    ),
    "create_simple_design_5_3": Reference(
        id="create_simple_design_5_3",
        title="CREATE-SIMPLE設計基準 Section 5.3: リスク判定",
        section="Section 5.3",
        description="Risk level determination from RCR",
        description_ja="RCRからのリスクレベル判定",
    ),
    "create_simple_design_5_3_acrmax": Reference(
        id="create_simple_design_5_3_acrmax",
        title="CREATE-SIMPLE設計基準 Section 5.3.3: ACRmax",
        section="Section 5.3.3",
        description="Management target concentration for carcinogens",
        description_ja="発がん性物質の管理目標濃度",
    ),
    # COSHH Essentials
    "coshh_essentials": Reference(
        id="coshh_essentials",
        title="COSHH Essentials: Easy steps to control chemicals",
        authors=["UK Health and Safety Executive"],
        organization="HSE",
        year=2003,
        url="https://www.hse.gov.uk/coshh/essentials/",
        description="Control banding methodology",
    ),
    # ECETOC TRA
    "ecetoc_tra": Reference(
        id="ecetoc_tra",
        title="ECETOC Targeted Risk Assessment",
        authors=["ECETOC"],
        organization="European Centre for Ecotoxicology and Toxicology of Chemicals",
        year=2012,
        description="Targeted Risk Assessment model for worker exposure",
    ),
    # Potts-Guy Equation
    "potts_guy": Reference(
        id="potts_guy",
        title="Predicting Skin Permeability",
        authors=["Potts, R.O.", "Guy, R.H."],
        year=1992,
        journal="Pharmaceutical Research",
        volume="9",
        pages="663-669",
        doi="10.1023/A:1015810312465",
        description="log Kp = -2.72 + 0.71 × log Kow - 0.0061 × MW",
    ),
    # Unified Hazard Banding
    "arnone_2015": Reference(
        id="arnone_2015",
        title="Hazard banding in compliance with GHS",
        authors=["Arnone, M.", "et al."],
        year=2015,
        journal="Regulatory Toxicology and Pharmacology",
        volume="73",
        pages="287-295",
        description="Unified approach to hazard banding for occupational health",
    ),
    # NIOSH Skin Notation
    "niosh_skin": Reference(
        id="niosh_skin",
        title="A Strategy for Assigning New NIOSH Skin Notations",
        authors=["NIOSH"],
        organization="DHHS (NIOSH)",
        year=2009,
        description="Publication No. 2009-152",
    ),
    # Additional design document references
    "create_simple_design_2_2": Reference(
        id="create_simple_design_2_2",
        title="CREATE-SIMPLE設計基準 Section 2.2: 管理目標濃度",
        section="Section 2.2",
        description="Management target concentration (ACRmax) for hazardous substances",
        description_ja="発がん性・変異原性物質等の管理目標濃度",
    ),
    "create_simple_design_7": Reference(
        id="create_simple_design_7",
        title="CREATE-SIMPLE設計基準 Section 7: 物理的危険性",
        section="Section 7",
        description="Physical hazard risk assessment including fixed Level IV hazards",
        description_ja="物理的危険性リスク評価（固定レベルIVハザードを含む）",
    ),
    "create_simple_vba_ra_sheet": Reference(
        id="create_simple_vba_ra_sheet",
        title="CREATE-SIMPLE VBA modRASheet.bas",
        description="RA Sheet mode implementation - RPE not available",
        description_ja="リスクアセスメントシートモード実装 - 呼吸用保護具選択不可",
    ),
}


def get_reference(ref_id: str) -> Reference:
    """Get a reference by ID."""
    if ref_id not in REFERENCES:
        raise KeyError(f"Reference '{ref_id}' not found")
    return REFERENCES[ref_id]
