"""
Example: Risk Assessment for Supported Metal Catalysts

This example demonstrates how to perform risk assessment for:
- 5wt% Pt/SiO2 (Platinum on Silica)
- 5wt% Rh/SiO2 (Rhodium on Silica)

These are common heterogeneous catalysts used in hydrogenation reactions.

CAS Numbers used:
- Platinum: 7440-06-4 (OEL: JSOH 0.001 mg/m³, ACGIH 1.0 mg/m³)
- Rhodium: 7440-16-6 (OEL: JSOH 0.001 mg/m³, ACGIH 1.0 mg/m³)
- Silica: 7631-86-9 (Note: Database includes both crystalline and amorphous)

Note: The database uses a combined silica entry (7631-86-9) that includes
crystalline silica (carcinogen 1A). For pure amorphous silica supports,
consider creating a custom Substance with appropriate OEL (10 mg/m³).
"""

from ra_library import RiskAssessment


# CAS numbers for database lookup
CAS_PLATINUM = "7440-06-4"
CAS_RHODIUM = "7440-16-6"
CAS_SILICA = "7631-86-9"


def assess_pt_sio2_catalyst():
    """
    Assess 5wt% Pt/SiO2 catalyst handling.

    Scenario: Laboratory-scale catalyst preparation/handling
    - Small amount (100g-1kg)
    - High dustiness (fine powder) - 高飛散性
    - Enclosed fume hood (囲い式ドラフト) - local_enc
    """
    print("=" * 60)
    print("5wt% Pt/SiO2 Catalyst Risk Assessment")
    print("=" * 60)

    # Perform assessment using CAS numbers (auto-lookup from database)
    result = (
        RiskAssessment()
        .add_substance(CAS_PLATINUM, content=5.0)   # 5wt% Pt
        .add_substance(CAS_SILICA, content=95.0)    # 95wt% SiO2
        .with_conditions(
            property_type="solid",
            amount="small",              # 100g-1kg laboratory scale
            dustiness="high",            # 高飛散性 (fine powder)
            ventilation="local_enc",     # 囲い式ドラフト (enclosed fume hood)
            control_velocity_verified=True,
        )
        .with_duration(
            hours=4.0,                   # 4 hours of handling
            days_per_week=3,             # 3 days per week
        )
        .with_protection(
            rpe="half_mask",             # N95 or similar
            gloves="resistant",          # Chemical-resistant gloves
            glove_training=True,         # Workers are trained
        )
        .calculate()
    )

    # Print results
    print(result.summary())
    print("\n" + "-" * 40)
    print("Detailed component results:")
    for cas, comp in result.components.items():
        print(f"\n{comp.name} ({comp.content_percent}%):")
        rcr = comp.get_inhalation_rcr()
        print(f"  Inhalation RCR: {rcr:.4f}" if rcr else "  Inhalation RCR: N/A")
        print(f"  Risk Level: {comp.risk_level}")

    print("\n" + "-" * 40)
    mixed_rcr = result.mixed_inhalation_rcr
    print(f"Mixed exposure RCR: {mixed_rcr:.4f}" if mixed_rcr else "Mixed exposure RCR: N/A")
    print(f"Overall risk level: {result.overall_risk_level}")

    return result


def assess_rh_sio2_catalyst():
    """
    Assess 5wt% Rh/SiO2 catalyst handling.

    Scenario: Same as Pt/SiO2 for comparison
    - High dustiness (高飛散性)
    - Enclosed fume hood (囲い式ドラフト)
    """
    print("\n" + "=" * 60)
    print("5wt% Rh/SiO2 Catalyst Risk Assessment")
    print("=" * 60)

    result = (
        RiskAssessment()
        .add_substance(CAS_RHODIUM, content=5.0)
        .add_substance(CAS_SILICA, content=95.0)
        .with_conditions(
            property_type="solid",
            amount="small",
            dustiness="high",            # 高飛散性
            ventilation="local_enc",     # 囲い式ドラフト
            control_velocity_verified=True,
        )
        .with_duration(hours=4.0, days_per_week=3)
        .with_protection(
            rpe="half_mask",
            gloves="resistant",
            glove_training=True,
        )
        .calculate()
    )

    print(result.summary())
    print(f"\nOverall risk level: {result.overall_risk_level}")

    return result


def compare_with_without_protection():
    """
    Compare risk levels with and without PPE.

    Demonstrates the what_if() analysis feature.
    """
    print("\n" + "=" * 60)
    print("What-If Analysis: PPE Impact")
    print("=" * 60)

    # Assessment with protection
    protected = (
        RiskAssessment()
        .add_substance(CAS_PLATINUM, content=5.0)
        .add_substance(CAS_SILICA, content=95.0)
        .with_conditions(
            property_type="solid",
            amount="small",
            dustiness="high",
            ventilation="local_enc",
            control_velocity_verified=True,
        )
        .with_duration(hours=4.0, days_per_week=3)
        .with_protection(rpe="half_mask", gloves="resistant")
        .calculate()
    )

    # What-if: No RPE
    unprotected = protected.what_if(rpe="none")

    # Compare
    comparison = protected.compare_to(unprotected)
    print(f"\nWith RPE (half mask):")
    print(f"  Mixed RCR: {protected.mixed_inhalation_rcr:.4f}")
    print(f"  Risk Level: {protected.overall_risk_level}")

    print(f"\nWithout RPE:")
    print(f"  Mixed RCR: {unprotected.mixed_inhalation_rcr:.4f}")
    print(f"  Risk Level: {unprotected.overall_risk_level}")

    print(f"\n{protected.compare_summary(unprotected)}")


def export_results():
    """
    Export assessment results to CSV.
    """
    print("\n" + "=" * 60)
    print("Export to CSV")
    print("=" * 60)

    # Pt/SiO2
    pt_result = (
        RiskAssessment()
        .add_substance(CAS_PLATINUM, content=5.0)
        .add_substance(CAS_SILICA, content=95.0)
        .with_conditions(
            property_type="solid",
            amount="small",
            dustiness="high",
            ventilation="local_enc",
        )
        .with_duration(hours=4.0)
        .with_protection(rpe="half_mask")
        .calculate()
    )

    # Rh/SiO2
    rh_result = (
        RiskAssessment()
        .add_substance(CAS_RHODIUM, content=5.0)
        .add_substance(CAS_SILICA, content=95.0)
        .with_conditions(
            property_type="solid",
            amount="small",
            dustiness="high",
            ventilation="local_enc",
        )
        .with_duration(hours=4.0)
        .with_protection(rpe="half_mask")
        .calculate()
    )

    # Export
    print("\nPt/SiO2 CSV:")
    print(pt_result.to_csv())

    print("\nRh/SiO2 CSV:")
    print(rh_result.to_csv(include_header=False))


def simple_example():
    """
    Simplest possible example for 5wt% Pt/SiO2.

    Just uses CAS numbers - substances are automatically looked up from database.
    """
    print("\n" + "=" * 60)
    print("Simple Example: 5wt% Pt/SiO2")
    print("=" * 60)

    # Simple assessment with high dustiness in enclosed fume hood
    result = (
        RiskAssessment()
        .add_substance(CAS_PLATINUM, content=5.0)   # Auto-lookup
        .add_substance(CAS_SILICA, content=95.0)    # Auto-lookup
        .with_conditions(
            property_type="solid",
            amount="small",
            dustiness="high",         # 高飛散性
            ventilation="local_enc",  # 囲い式ドラフト
        )
        .calculate()
    )

    print(f"Overall Risk Level: {result.overall_risk_level}")
    print(f"Mixed RCR: {result.mixed_inhalation_rcr:.4f}")


if __name__ == "__main__":
    # Simple example first
    simple_example()

    # Detailed assessments
    pt_result = assess_pt_sio2_catalyst()
    rh_result = assess_rh_sio2_catalyst()

    # Compare with/without protection
    compare_with_without_protection()

    # Export results
    export_results()

    print("\n" + "=" * 60)
    print("Assessment Complete")
    print("=" * 60)
