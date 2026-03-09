"""
Human-readable labels for CREATE-SIMPLE assessment options.

Based on VBA SelectList.csv and CREATE-SIMPLE Design v3.1.1.
"""

from typing import Optional, Literal

Language = Literal["ja", "en"]
PropertyType = Literal["liquid", "solid"]


# Amount level labels (Q1)
AMOUNT_LABELS = {
    "large": {
        "liquid": {
            "ja": "大量 (1kL以上)",
            "en": "Large (≥1kL)",
            "range": "≥1000L",
        },
        "solid": {
            "ja": "大量 (1t以上)",
            "en": "Large (≥1ton)",
            "range": "≥1000kg",
        },
    },
    "medium": {
        "liquid": {
            "ja": "中量 (1L～1kL)",
            "en": "Medium (1L-1kL)",
            "range": "1-1000L",
        },
        "solid": {
            "ja": "中量 (1kg～1t)",
            "en": "Medium (1kg-1ton)",
            "range": "1-1000kg",
        },
    },
    "small": {
        "liquid": {
            "ja": "少量 (100mL～1L)",
            "en": "Small (100mL-1L)",
            "range": "100-1000mL",
        },
        "solid": {
            "ja": "少量 (100g～1kg)",
            "en": "Small (100g-1kg)",
            "range": "100-1000g",
        },
    },
    "minute": {
        "liquid": {
            "ja": "微量 (10mL～100mL)",
            "en": "Minute (10-100mL)",
            "range": "10-100mL",
        },
        "solid": {
            "ja": "微量 (10g～100g)",
            "en": "Minute (10-100g)",
            "range": "10-100g",
        },
    },
    "trace": {
        "liquid": {
            "ja": "極微量 (10mL未満)",
            "en": "Trace (<10mL)",
            "range": "<10mL",
        },
        "solid": {
            "ja": "極微量 (10g未満)",
            "en": "Trace (<10g)",
            "range": "<10g",
        },
    },
}


# Volatility labels (for liquids)
# Keys match what volatility.py calculate_volatility_from_boiling_point() returns
# Reference: CREATE-SIMPLE Design v3.1.1, VBA SelectList.csv
VOLATILITY_LABELS = {
    # BP < 50°C → "high" from volatility.py
    "high": {
        "ja": "高揮発性（沸点：50℃未満）",
        "en": "High volatility (BP < 50°C)",
        "condition_ja": "沸点 50℃未満",
        "condition_en": "Boiling point < 50°C",
    },
    # 50°C ≤ BP < 150°C → "medium" from volatility.py
    "medium": {
        "ja": "中揮発性（沸点：50℃以上～150℃未満）",
        "en": "Medium volatility (BP 50-150°C)",
        "condition_ja": "沸点 50℃以上～150℃未満",
        "condition_en": "Boiling point 50-150°C",
    },
    # BP ≥ 150°C → "low" from volatility.py
    "low": {
        "ja": "低揮発性（沸点：150℃以上）",
        "en": "Low volatility (BP ≥ 150°C)",
        "condition_ja": "沸点 150℃以上",
        "condition_en": "Boiling point ≥ 150°C",
    },
    # VP < 0.5 Pa → "very_low" from volatility.py (overrides BP-based)
    "very_low": {
        "ja": "極低揮発性（蒸気圧：0.5 Pa未満）",
        "en": "Very low volatility (VP < 0.5 Pa)",
        "condition_ja": "蒸気圧 0.5 Pa未満",
        "condition_en": "Vapor pressure < 0.5 Pa",
    },
}


# Dustiness labels (for solids)
DUSTINESS_LABELS = {
    "high": {
        "ja": "高飛散性（微細な軽い粉体）",
        "en": "High dustiness (fine, light powder)",
        "examples_ja": "セメント、カーボンブラックなど",
        "examples_en": "e.g., cement, carbon black",
        "description_ja": "空気中に容易に飛散する微細な粉体",
        "description_en": "Fine powder that easily becomes airborne",
    },
    "medium": {
        "ja": "中飛散性（結晶状・顆粒状）",
        "en": "Medium dustiness (crystalline, granular)",
        "examples_ja": "衣類用洗剤など",
        "examples_en": "e.g., laundry detergent",
        "description_ja": "結晶や顆粒状の物質",
        "description_en": "Crystalline or granular solids",
    },
    "low": {
        "ja": "低飛散性（壊れないペレット）",
        "en": "Low dustiness (non-friable pellets)",
        "examples_ja": "錠剤、PVCペレットなど",
        "examples_en": "e.g., tablets, PVC pellets",
        "description_ja": "ペレット状や塊状の物質",
        "description_en": "Pellet-like or lumpy solids",
    },
}


# Ventilation labels (Q4)
VENTILATION_LABELS = {
    "none": {
        "ja": "換気レベルA（特に換気のない部屋）",
        "en": "Level A (no ventilation)",
        "coefficient": 4.0,
        "description_ja": "密閉された部屋、換気設備なし",
        "description_en": "Enclosed room with no ventilation",
    },
    "basic": {
        "ja": "換気レベルB（全体換気）",
        "en": "Level B (general ventilation)",
        "coefficient": 3.0,
        "description_ja": "窓や扇風機による一般的な換気",
        "description_en": "General ventilation via windows or fans",
    },
    "industrial": {
        "ja": "換気レベルC（工業的な全体換気、屋外作業）",
        "en": "Level C (industrial ventilation, outdoor)",
        "coefficient": 1.0,
        "description_ja": "工場の全体換気システム、または屋外作業",
        "description_en": "Industrial ventilation system or outdoor work",
    },
    "local_ext": {
        "ja": "換気レベルD（外付け式局所排気装置）",
        "en": "Level D (local exhaust - external type)",
        "coefficient_unverified": 0.5,
        "coefficient_verified": 0.1,
        "description_ja": "外付け式フード（制御風速確認なし: 0.5、確認済: 0.1）",
        "description_en": "External hood (unverified: 0.5, verified: 0.1)",
    },
    "local_enc": {
        "ja": "換気レベルE（囲い式局所排気装置）",
        "en": "Level E (local exhaust - enclosed type)",
        "coefficient_unverified": 0.1,
        "coefficient_verified": 0.01,
        "description_ja": "囲い式フード・ドラフト（制御風速確認なし: 0.1、確認済: 0.01）",
        "description_en": "Enclosed hood/fume cupboard (unverified: 0.1, verified: 0.01)",
    },
    "sealed": {
        "ja": "換気レベルF（密閉容器内での取扱い）",
        "en": "Level F (sealed system)",
        "coefficient": 0.001,
        "description_ja": "完全に密閉されたシステム内での取扱い",
        "description_en": "Handling within completely sealed system",
    },
}


# Skin area labels (Q8)
# Based on CREATE-SIMPLE SelectList.csv Q8_Exposure_area
SKIN_AREA_LABELS = {
    "coin_splash": {
        "ja": "大きなコインのサイズ、小さな飛沫",
        "en": "Coin-sized area, small splashes",
        "area_cm2": 10,
    },
    "palm_one": {
        "ja": "片手の手のひら付着",
        "en": "One palm exposure",
        "area_cm2": 240,
    },
    "palm_both": {
        "ja": "両手の手のひらに付着",
        "en": "Both palms exposure",
        "area_cm2": 480,
    },
    "hands_both": {
        "ja": "両手全体に付着",
        "en": "Both full hands exposure",
        "area_cm2": 960,
    },
    "wrists": {
        "ja": "両手及び手首",
        "en": "Hands and wrists exposure",
        "area_cm2": 1500,
    },
    "forearms": {
        "ja": "両手の肘から下全体",
        "en": "Hands and forearms (elbow down)",
        "area_cm2": 1980,
    },
}


# Glove type labels (Q9)
GLOVE_LABELS = {
    "none": {
        "ja": "手袋を着用していない",
        "en": "No gloves",
        "coefficient": 1.0,
    },
    "non_resistant": {
        "ja": "取扱物質に関する情報のない手袋を使用",
        "en": "Gloves without permeation data",
        "coefficient": 1.0,
    },
    "resistant": {
        "ja": "耐透過性・耐浸透性の手袋を着用",
        "en": "Chemical-resistant gloves",
        "coefficient": 0.2,
    },
}


# RPE type labels
RPE_LABELS = {
    "half_mask": {
        "ja": "防毒マスク（半面形面体）",
        "en": "Half-mask respirator",
        "apf": 10,
    },
    "full_mask": {
        "ja": "防毒マスク（全面形面体）",
        "en": "Full-face respirator",
        "apf": 50,
    },
    "papr_loose": {
        "ja": "電動ファン付き呼吸用保護具（ルーズフィット形）",
        "en": "PAPR (loose-fitting)",
        "apf": 25,
    },
    "papr_half": {
        "ja": "電動ファン付き呼吸用保護具（半面形面体）",
        "en": "PAPR (half-mask)",
        "apf": 50,
    },
    "papr_full": {
        "ja": "電動ファン付き呼吸用保護具（全面形面体）",
        "en": "PAPR (full-face)",
        "apf": 1000,
    },
}


# Work area size labels (Q3 - for liquids)
WORK_AREA_LABELS = {
    "small": {
        "ja": "狭い作業スペース",
        "en": "Small work area",
        "coefficient": 1.5,
        "description_ja": "狭い・密閉された作業エリア（濃度上昇）",
        "description_en": "Confined/enclosed work area (higher concentration)",
    },
    "medium": {
        "ja": "標準的な作業スペース",
        "en": "Medium work area",
        "coefficient": 1.0,
        "description_ja": "標準的な作業エリア",
        "description_en": "Standard work area",
    },
    "large": {
        "ja": "広い作業スペース",
        "en": "Large work area",
        "coefficient": 0.5,
        "description_ja": "広い・開放的な作業エリア（希釈効果）",
        "description_en": "Large/open work area (dilution effect)",
    },
}


# Exposure variation labels (Q7)
# Based on CREATE-SIMPLE Q7_ExposureVariation
EXPOSURE_VARIATION_LABELS = {
    "small": {
        "ja": "ばく露濃度の変動が小さい作業",
        "en": "Low exposure variation",
        "stel_multiplier": 4.0,
        "description_ja": "定常的な作業、STEL = 8hr TWA × 4",
        "description_en": "Steady work, STEL = 8hr TWA × 4",
    },
    "large": {
        "ja": "ばく露濃度の変動が大きい作業",
        "en": "High exposure variation",
        "stel_multiplier": 6.0,
        "description_ja": "間欠的・変動のある作業、STEL = 8hr TWA × 6",
        "description_en": "Intermittent work, STEL = 8hr TWA × 6",
    },
    # Legacy values (mapped to small in ExposureVariation enum)
    "constant": {
        "ja": "ばく露濃度の変動が小さい作業（定常）",
        "en": "Low exposure variation (steady)",
        "stel_multiplier": 4.0,
    },
    "intermittent": {
        "ja": "ばく露濃度の変動が小さい作業（間欠）",
        "en": "Low exposure variation (intermittent)",
        "stel_multiplier": 4.0,
    },
    "brief": {
        "ja": "ばく露濃度の変動が小さい作業（短時間）",
        "en": "Low exposure variation (brief)",
        "stel_multiplier": 4.0,
    },
}


# Content coefficient labels
CONTENT_LABELS = {
    "high": {
        "ja": "25%以上",
        "en": "≥25%",
        "coefficient": 1.0,
        "range": "≥25%",
    },
    "medium_high": {
        "ja": "5%～25%",
        "en": "5-25%",
        "coefficient": 0.6,
        "range": "5-25%",
    },
    "medium_low": {
        "ja": "1%～5%",
        "en": "1-5%",
        "coefficient": 0.2,
        "range": "1-5%",
    },
    "low": {
        "ja": "1%未満",
        "en": "<1%",
        "coefficient": 0.1,
        "range": "<1%",
    },
}


# Physical hazard labels (GHS categories)
# Based on CREATE-SIMPLE and GHS Rev.9
PHYSICAL_HAZARD_LABELS = {
    "flammable_liquid": {
        "ja": "引火性液体",
        "en": "Flammable liquid",
        "categories": {
            "1": {"ja": "区分1（引火点 < 23℃、沸点 ≤ 35℃）", "en": "Category 1 (FP < 23°C, BP ≤ 35°C)"},
            "2": {"ja": "区分2（引火点 < 23℃、沸点 > 35℃）", "en": "Category 2 (FP < 23°C, BP > 35°C)"},
            "3": {"ja": "区分3（23℃ ≤ 引火点 ≤ 60℃）", "en": "Category 3 (23°C ≤ FP ≤ 60°C)"},
            "4": {"ja": "区分4（60℃ < 引火点 ≤ 93℃）", "en": "Category 4 (60°C < FP ≤ 93°C)"},
        },
        "warnings": {
            "ja": ["着火源から離して保管", "静電気対策が必要", "適切な換気を確保"],
            "en": ["Keep away from ignition sources", "Anti-static measures required", "Ensure adequate ventilation"],
        },
    },
    "flammable_solid": {
        "ja": "可燃性固体",
        "en": "Flammable solid",
        "categories": {
            "1": {"ja": "区分1（急速燃焼）", "en": "Category 1 (rapid burning)"},
            "2": {"ja": "区分2（燃焼持続）", "en": "Category 2 (sustained burning)"},
        },
        "warnings": {
            "ja": ["着火源から離して保管", "粉塵爆発に注意"],
            "en": ["Keep away from ignition sources", "Beware of dust explosion"],
        },
    },
    "flammable_gas": {
        "ja": "可燃性ガス",
        "en": "Flammable gas",
        "categories": {
            "1": {"ja": "区分1（爆発限界濃度範囲が広い）", "en": "Category 1 (wide flammability range)"},
            "2": {"ja": "区分2（爆発限界濃度範囲が狭い）", "en": "Category 2 (narrow flammability range)"},
        },
        "warnings": {
            "ja": ["漏洩検知器を設置", "換気を確保", "着火源厳禁"],
            "en": ["Install leak detectors", "Ensure ventilation", "No ignition sources"],
        },
    },
    "oxidizing_liquid": {
        "ja": "酸化性液体",
        "en": "Oxidizing liquid",
        "categories": {
            "1": {"ja": "区分1（強酸化性）", "en": "Category 1 (strong oxidizer)"},
            "2": {"ja": "区分2（酸化性）", "en": "Category 2 (oxidizer)"},
            "3": {"ja": "区分3（弱酸化性）", "en": "Category 3 (weak oxidizer)"},
        },
        "warnings": {
            "ja": ["可燃物・有機物から隔離", "火災時の対応に注意"],
            "en": ["Keep away from combustibles/organics", "Special fire response required"],
        },
    },
    "oxidizing_solid": {
        "ja": "酸化性固体",
        "en": "Oxidizing solid",
        "categories": {
            "1": {"ja": "区分1（強酸化性）", "en": "Category 1 (strong oxidizer)"},
            "2": {"ja": "区分2（酸化性）", "en": "Category 2 (oxidizer)"},
            "3": {"ja": "区分3（弱酸化性）", "en": "Category 3 (weak oxidizer)"},
        },
        "warnings": {
            "ja": ["可燃物・有機物から隔離", "火災時の対応に注意"],
            "en": ["Keep away from combustibles/organics", "Special fire response required"],
        },
    },
    "self_reactive": {
        "ja": "自己反応性化学品",
        "en": "Self-reactive substance",
        "categories": {
            "A": {"ja": "タイプA（爆轟・急速爆発）", "en": "Type A (detonation/rapid deflagration)"},
            "B": {"ja": "タイプB（爆発性）", "en": "Type B (explosive)"},
            "C": {"ja": "タイプC（急速反応）", "en": "Type C (rapid effect)"},
            "D": {"ja": "タイプD（中程度の反応）", "en": "Type D (medium effect)"},
            "E": {"ja": "タイプE（弱い反応）", "en": "Type E (low effect)"},
            "F": {"ja": "タイプF（弱い反応、発熱）", "en": "Type F (low effect with heat)"},
            "G": {"ja": "タイプG（反応性なし）", "en": "Type G (no reaction)"},
        },
        "warnings": {
            "ja": ["温度管理が必要", "衝撃・摩擦を避ける"],
            "en": ["Temperature control required", "Avoid shock/friction"],
        },
    },
    "organic_peroxide": {
        "ja": "有機過酸化物",
        "en": "Organic peroxide",
        "categories": {
            "A": {"ja": "タイプA（爆轟性）", "en": "Type A (detonation)"},
            "B": {"ja": "タイプB（爆発性）", "en": "Type B (explosive)"},
            "C": {"ja": "タイプC（急速反応）", "en": "Type C (rapid effect)"},
            "D": {"ja": "タイプD（中程度の反応）", "en": "Type D (medium effect)"},
            "E": {"ja": "タイプE（弱い反応）", "en": "Type E (low effect)"},
            "F": {"ja": "タイプF（弱い反応）", "en": "Type F (low effect)"},
            "G": {"ja": "タイプG（反応性なし）", "en": "Type G (no reaction)"},
        },
        "warnings": {
            "ja": ["冷蔵保管", "温度管理厳守", "衝撃・摩擦を避ける"],
            "en": ["Refrigerated storage", "Strict temperature control", "Avoid shock/friction"],
        },
    },
    "pyrophoric_liquid": {
        "ja": "自然発火性液体",
        "en": "Pyrophoric liquid",
        "categories": {
            "1": {"ja": "区分1（空気に触れると発火）", "en": "Category 1 (ignites on air contact)"},
        },
        "warnings": {
            "ja": ["空気との接触を完全に遮断", "不活性ガス下で取扱い", "消火時は水を使用しない"],
            "en": ["Complete air exclusion required", "Handle under inert gas", "Do not use water for fire"],
        },
    },
    "pyrophoric_solid": {
        "ja": "自然発火性固体",
        "en": "Pyrophoric solid",
        "categories": {
            "1": {"ja": "区分1（空気に触れると発火）", "en": "Category 1 (ignites on air contact)"},
        },
        "warnings": {
            "ja": ["空気との接触を完全に遮断", "不活性ガス下で取扱い", "消火時は水を使用しない"],
            "en": ["Complete air exclusion required", "Handle under inert gas", "Do not use water for fire"],
        },
    },
    "self_heating": {
        "ja": "自己発熱性化学品",
        "en": "Self-heating substance",
        "categories": {
            "1": {"ja": "区分1（大量で自己発熱）", "en": "Category 1 (self-heating in bulk)"},
            "2": {"ja": "区分2（少量で自己発熱）", "en": "Category 2 (self-heating in small amounts)"},
        },
        "warnings": {
            "ja": ["通気を確保", "蓄熱を避ける", "温度監視"],
            "en": ["Ensure ventilation", "Avoid heat accumulation", "Temperature monitoring"],
        },
    },
    "water_reactive": {
        "ja": "水反応可燃性化学品",
        "en": "Water-reactive substance",
        "categories": {
            "1": {"ja": "区分1（水と激しく反応）", "en": "Category 1 (violent reaction with water)"},
            "2": {"ja": "区分2（水と反応）", "en": "Category 2 (reacts with water)"},
            "3": {"ja": "区分3（水と緩やかに反応）", "en": "Category 3 (slow reaction with water)"},
        },
        "warnings": {
            "ja": ["水分との接触を避ける", "乾燥状態で保管", "消火時は水を使用しない"],
            "en": ["Avoid moisture contact", "Store dry", "Do not use water for fire"],
        },
    },
    "explosives": {
        "ja": "爆発物",
        "en": "Explosives",
        "categories": {
            "unstable": {"ja": "不安定爆発物", "en": "Unstable explosive"},
            "1.1": {"ja": "等級1.1（大量爆発危険性）", "en": "Division 1.1 (mass explosion hazard)"},
            "1.2": {"ja": "等級1.2（飛散危険性）", "en": "Division 1.2 (projection hazard)"},
            "1.3": {"ja": "等級1.3（火災・軽度爆発）", "en": "Division 1.3 (fire/minor blast)"},
            "1.4": {"ja": "等級1.4（軽微な危険性）", "en": "Division 1.4 (minor hazard)"},
            "1.5": {"ja": "等級1.5（鈍感爆発物）", "en": "Division 1.5 (insensitive)"},
            "1.6": {"ja": "等級1.6（非常に鈍感）", "en": "Division 1.6 (extremely insensitive)"},
        },
        "warnings": {
            "ja": ["衝撃・摩擦・火気厳禁", "専門知識者のみ取扱い", "法規制を遵守"],
            "en": ["No shock/friction/fire", "Trained personnel only", "Follow regulations"],
        },
    },
    "corrosive_to_metals": {
        "ja": "金属腐食性物質",
        "en": "Corrosive to metals",
        "categories": {
            "1": {"ja": "区分1（金属を腐食する）", "en": "Category 1 (corrodes metals)"},
        },
        "warnings": {
            "ja": ["耐食性容器を使用", "金属との接触を避ける"],
            "en": ["Use corrosion-resistant containers", "Avoid metal contact"],
        },
    },
}


# Consolidated LABELS dict for easy access
LABELS = {
    "amount": AMOUNT_LABELS,
    "volatility": VOLATILITY_LABELS,
    "dustiness": DUSTINESS_LABELS,
    "ventilation": VENTILATION_LABELS,
    "skin_area": SKIN_AREA_LABELS,
    "gloves": GLOVE_LABELS,
    "rpe": RPE_LABELS,
    "work_area": WORK_AREA_LABELS,
    "exposure_variation": EXPOSURE_VARIATION_LABELS,
    "content": CONTENT_LABELS,
}


def get_label(
    category: str,
    key: str,
    language: Language = "ja",
    property_type: Optional[PropertyType] = None,
) -> str:
    """
    Get human-readable label for a given option.

    Args:
        category: Option category (amount, volatility, dustiness, etc.)
        key: Option key (large, medium, small, etc.)
        language: Output language (ja/en)
        property_type: Required for amount (liquid/solid)

    Returns:
        Human-readable label string
    """
    if category not in LABELS:
        return key

    labels = LABELS[category]

    if key not in labels:
        return key

    label_data = labels[key]

    # Handle property-type-specific labels (amount)
    if category == "amount" and property_type:
        if property_type in label_data:
            return label_data[property_type].get(language, key)
        return key

    # Standard label lookup
    return label_data.get(language, key)


def get_labels(
    category: str,
    key: str,
    language: Language = "ja",
    property_type: Optional[PropertyType] = None,
) -> dict:
    """
    Get full label data including description and examples.

    Args:
        category: Option category
        key: Option key
        language: Output language
        property_type: Required for amount

    Returns:
        Dict with label, description, examples, coefficient, etc.
    """
    if category not in LABELS or key not in LABELS[category]:
        return {"key": key, "label": key}

    label_data = LABELS[category][key]

    # Handle property-type-specific (amount)
    if category == "amount" and property_type and property_type in label_data:
        data = label_data[property_type]
        return {
            "key": key,
            "label": data.get(language, key),
            "range": data.get("range"),
        }

    result = {
        "key": key,
        "label": label_data.get(language, key),
    }

    # Add optional fields based on language
    suffix = "_ja" if language == "ja" else "_en"
    for field in ["description", "examples", "condition"]:
        field_key = f"{field}{suffix}"
        if field_key in label_data:
            result[field] = label_data[field_key]

    # Add numeric fields
    for field in ["coefficient", "coefficient_verified", "coefficient_unverified",
                  "area_cm2", "apf", "stel_multiplier", "range"]:
        if field in label_data:
            result[field] = label_data[field]

    return result
