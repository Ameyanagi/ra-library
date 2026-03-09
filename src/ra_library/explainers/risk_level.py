"""
Risk level explanation generator.

Explains WHY the risk level is what it is in plain language.

Reference: CREATE-SIMPLE Design v3.1.1, Section 5
"""

from ..models.risk import RiskLevel, RiskResult, InhalationRisk, DermalRisk, PhysicalRisk


def explain_risk_level(result: RiskResult, language: str = "en") -> str:
    """
    Generate a plain-language explanation of why the risk level is what it is.

    Args:
        result: The complete risk assessment result
        language: "en" for English, "ja" for Japanese

    Returns:
        Human-readable explanation string
    """
    explanations = []

    # Overall risk level
    level = result.overall_risk_level
    explanations.append(_explain_overall_level(level, language))

    # Inhalation risk
    if result.inhalation:
        explanations.append(_explain_inhalation(result.inhalation, language))

    # Dermal risk
    if result.dermal:
        explanations.append(_explain_dermal(result.dermal, language))

    # Physical risk
    if result.physical:
        explanations.append(_explain_physical(result.physical, language))

    return "\n\n".join(explanations)


def _explain_overall_level(level: RiskLevel, language: str) -> str:
    """Explain the overall risk level."""
    if language == "ja":
        level_names = {
            RiskLevel.I: "レベルI（リスクは十分に低い）",
            RiskLevel.II: "レベルII（リスクはあるが許容範囲内）",
            RiskLevel.III: "レベルIII（追加対策が必要）",
            RiskLevel.IV: "レベルIV（直ちに対策が必要）",
        }
        template = "総合リスクレベル: {level}\n{description}"
        descriptions = {
            RiskLevel.I: "ばく露量がばく露限界値の10%以下であり、現在の管理措置で十分です。",
            RiskLevel.II: "ばく露量がばく露限界値以下ですが、管理措置の維持・確認が必要です。",
            RiskLevel.III: "ばく露量がばく露限界値を超えています。追加の管理措置を検討してください。",
            RiskLevel.IV: "ばく露量がばく露限界値の10倍を超えています。直ちに作業を中止し、対策を講じてください。",
        }
    else:
        level_names = {
            RiskLevel.I: "Level I (Risk is sufficiently low)",
            RiskLevel.II: "Level II (Risk is within acceptable limits)",
            RiskLevel.III: "Level III (Additional controls needed)",
            RiskLevel.IV: "Level IV (Immediate action required)",
        }
        template = "Overall Risk Level: {level}\n{description}"
        descriptions = {
            RiskLevel.I: "Exposure is less than 10% of the occupational exposure limit. Current controls are adequate.",
            RiskLevel.II: "Exposure is below the limit but controls must be maintained and verified.",
            RiskLevel.III: "Exposure exceeds the limit. Additional control measures should be implemented.",
            RiskLevel.IV: "Exposure exceeds 10x the limit. Stop work immediately and implement controls.",
        }

    return template.format(level=level_names[level], description=descriptions[level])


def _explain_inhalation(risk: InhalationRisk, language: str) -> str:
    """Explain inhalation risk in detail."""
    if language == "ja":
        template = """吸入リスク: レベル{level}
RCR (リスク特性比): {rcr:.4f}
推定ばく露濃度: {exposure:.4f} {unit}
ばく露限界値 (OEL): {oel:.4f} {unit}
{acr_note}

計算式: RCR = ばく露濃度 / OEL = {exposure:.4f} / {oel:.4f} = {rcr:.4f}

リスクレベル判定基準:
- レベルI: RCR ≤ 0.1
- レベルII: 0.1 < RCR ≤ 1.0
- レベルIII: 1.0 < RCR ≤ 10.0
- レベルIV: RCR > 10.0"""
    else:
        template = """Inhalation Risk: Level {level}
RCR (Risk Characterization Ratio): {rcr:.4f}
Estimated Exposure: {exposure:.4f} {unit}
Occupational Exposure Limit (OEL): {oel:.4f} {unit}
{acr_note}

Formula: RCR = Exposure / OEL = {exposure:.4f} / {oel:.4f} = {rcr:.4f}

Risk Level Thresholds:
- Level I: RCR ≤ 0.1
- Level II: 0.1 < RCR ≤ 1.0
- Level III: 1.0 < RCR ≤ 10.0
- Level IV: RCR > 10.0"""

    # ACR note for carcinogens
    acr_note = ""
    if risk.acrmax is not None:
        if language == "ja":
            acr_note = f"※ 管理目標濃度 (ACRmax): {risk.acrmax:.4f} {risk.oel_unit} がOELの代わりに使用されています"
        else:
            acr_note = f"Note: ACRmax of {risk.acrmax:.4f} {risk.oel_unit} is used instead of OEL"

    return template.format(
        level=risk.risk_level.name,
        rcr=risk.rcr,
        exposure=risk.estimated_exposure,
        oel=risk.effective_oel,
        unit=risk.oel_unit,
        acr_note=acr_note,
    )


def _explain_dermal(risk: DermalRisk, language: str) -> str:
    """Explain dermal risk in detail."""
    if language == "ja":
        template = """経皮リスク: レベル{level}
吸収量: {absorption:.6f} mg/kg/day
皮膚透過係数 (Kp): {kp:.6e} cm/hr

ポッツ-ガイ式による計算:
log(Kp) = -2.7 + 0.71 × log(Kow) - 0.0061 × MW

リスク判定根拠: {reason}"""
    else:
        template = """Dermal Risk: Level {level}
Absorption Rate: {absorption:.6f} mg/kg/day
Skin Permeability Coefficient (Kp): {kp:.6e} cm/hr

Calculated using Potts-Guy equation:
log(Kp) = -2.7 + 0.71 × log(Kow) - 0.0061 × MW

Risk Assessment Basis: {reason}"""

    # Determine reason for risk level
    if risk.is_skin_hazard_substance:
        reason = (
            "Classified as skin hazard substance"
            if language == "en"
            else "皮膚等障害化学物質に指定"
        )
    elif risk.ghs_skin_hazard:
        reason = (
            f"GHS skin classification: {risk.ghs_skin_hazard}"
            if language == "en"
            else f"GHS皮膚有害性分類: {risk.ghs_skin_hazard}"
        )
    else:
        reason = (
            "Based on Potts-Guy permeability calculation"
            if language == "en"
            else "ポッツ-ガイ式による透過性計算に基づく"
        )

    return template.format(
        level=risk.risk_level.name,
        absorption=risk.absorption_rate or 0,
        kp=risk.kp or 0,
        reason=reason,
    )


def _explain_physical(risk: PhysicalRisk, language: str) -> str:
    """Explain physical hazard risk in detail."""
    if language == "ja":
        if risk.is_fixed_level_iv:
            return f"""物理的危険性: レベルIV（固定）
危険性種類: {risk.hazard_type}

この物質は{risk.hazard_type}に分類されており、本質的にレベルIVとなります。
いかなる管理措置によってもリスクを低減することはできません。
物質の代替または工程の根本的な見直しが必要です。"""
        else:
            template = """物理的危険性: レベル{level}
主要危険性: {hazard_type}
{flash_point_note}

リスク判定根拠: GHS分類に基づく評価"""
    else:
        if risk.is_fixed_level_iv:
            return f"""Physical Hazard: Level IV (Fixed)
Hazard Type: {risk.hazard_type}

This substance is classified as {risk.hazard_type} and is inherently Level IV.
No control measures can reduce this risk.
Substitution or fundamental process redesign is required."""
        else:
            template = """Physical Hazard: Level {level}
Primary Hazard: {hazard_type}
{flash_point_note}

Risk Assessment Basis: Evaluation based on GHS classification"""

    # Flash point note for flammables
    flash_point_note = ""
    if risk.flash_point is not None and risk.process_temperature is not None:
        margin = risk.temperature_margin
        if language == "ja":
            flash_point_note = f"引火点: {risk.flash_point}°C、作業温度: {risk.process_temperature}°C、マージン: {margin:.1f}°C"
        else:
            flash_point_note = f"Flash point: {risk.flash_point}°C, Process temp: {risk.process_temperature}°C, Margin: {margin:.1f}°C"

    return template.format(
        level=risk.risk_level.name, hazard_type=risk.hazard_type, flash_point_note=flash_point_note
    )


def get_level_boundary_explanation(rcr: float, language: str = "en") -> str:
    """
    Explain where the current RCR sits relative to level boundaries.

    Args:
        rcr: Risk Characterization Ratio
        language: "en" or "ja"

    Returns:
        Explanation of proximity to boundaries
    """
    level = RiskLevel.from_rcr(rcr)

    if language == "ja":
        if level == RiskLevel.I:
            headroom = (0.1 - rcr) / 0.1 * 100
            return f"現在RCR {rcr:.4f}はレベルI上限(0.1)から{headroom:.1f}%の余裕があります。"
        elif level == RiskLevel.II:
            to_level_i = (rcr - 0.1) / rcr * 100
            to_level_iii = (1.0 - rcr) / 1.0 * 100
            return f"レベルIまであと{to_level_i:.1f}%削減が必要。レベルIIIまで{to_level_iii:.1f}%の余裕。"
        elif level == RiskLevel.III:
            to_level_ii = (rcr - 1.0) / rcr * 100
            return f"レベルIIまであと{to_level_ii:.1f}%削減が必要です。"
        else:
            to_level_iii = (rcr - 10.0) / rcr * 100
            return f"レベルIIIまであと{to_level_iii:.1f}%削減が必要です。緊急対策が必要です。"
    else:
        if level == RiskLevel.I:
            headroom = (0.1 - rcr) / 0.1 * 100
            return f"RCR of {rcr:.4f} is {headroom:.1f}% below Level I threshold (0.1)."
        elif level == RiskLevel.II:
            to_level_i = (rcr - 0.1) / rcr * 100
            to_level_iii = (1.0 - rcr) / 1.0 * 100
            return f"Need {to_level_i:.1f}% reduction for Level I. {to_level_iii:.1f}% margin to Level III."
        elif level == RiskLevel.III:
            to_level_ii = (rcr - 1.0) / rcr * 100
            return f"Need {to_level_ii:.1f}% reduction to reach Level II."
        else:
            to_level_iii = (rcr - 10.0) / rcr * 100
            return f"Need {to_level_iii:.1f}% reduction to reach Level III. Urgent action required."
