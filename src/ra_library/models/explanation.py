"""
Explanation models for verbose output.

These models provide detailed breakdowns of calculations
so users understand WHY results are what they are.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Any

from .reference import Reference


class CalculationStep(BaseModel):
    """A single step in a calculation."""

    step_number: int
    description: str  # "Apply ventilation coefficient"
    description_ja: str = ""  # Japanese description
    formula: str  # "exposure = base × ventilation_coeff"
    input_values: dict[str, Any] = Field(default_factory=dict)
    output_value: float
    output_unit: str  # "ppm"
    explanation: str  # "Local exhaust reduces exposure by 90%"
    explanation_ja: str = ""  # Japanese explanation
    reference: Optional[Reference] = None


class FactorContribution(BaseModel):
    """How much a single factor contributes to the result."""

    factor_name: str  # "Ventilation"
    factor_name_ja: str = ""  # Japanese name
    factor_value: str  # "Local exhaust (enclosed)"
    coefficient: float  # 0.01
    contribution_percent: float  # Percentage of total exposure from this factor
    is_beneficial: bool  # True = reduces risk
    can_be_improved: bool  # True = user can change this
    improvement_options: List[str] = Field(default_factory=list)


class Limitation(BaseModel):
    """
    A factor that limits how low the risk can go.

    This is key to explaining WHY Level I might be impossible.
    """

    factor_name: str  # "Minimum exposure floor"
    factor_name_ja: str = ""  # Japanese name
    description: str  # "CREATE-SIMPLE cannot estimate below 0.005 ppm"
    description_ja: str = ""  # Japanese description
    current_value: float
    limiting_value: float
    impact: str  # "Sets minimum RCR at 0.1 for this substance"
    impact_ja: str = ""  # Japanese impact
    reference: Optional[Reference] = None
    alternatives: List[str] = Field(default_factory=list)


class CalculationExplanation(BaseModel):
    """
    Complete explanation of a calculation.

    Contains all steps, factors, and any limitations that
    affect the result.
    """

    # The calculation steps
    steps: List[CalculationStep] = Field(default_factory=list)

    # What factors contribute to the result
    factors: List[FactorContribution] = Field(default_factory=list)

    # Any limitations that prevent achieving a lower risk level
    limitations: List[Limitation] = Field(default_factory=list)

    # Summary text
    summary: str = ""
    summary_ja: str = ""

    # Key formula used
    main_formula: str = ""
    main_formula_description: str = ""

    def get_limiting_factors_summary(self) -> str:
        """Get a summary of all limiting factors."""
        if not self.limitations:
            return "No limiting factors - Level I may be achievable"

        factors = [lim.factor_name for lim in self.limitations]
        return f"Limited by: {', '.join(factors)}"

    def get_dominant_factor(self) -> Optional[FactorContribution]:
        """Get the factor with the highest contribution."""
        if not self.factors:
            return None
        return max(self.factors, key=lambda f: f.contribution_percent)


class MinimumAchievableResult(BaseModel):
    """
    Result showing the minimum achievable risk level.

    Explains what the best possible outcome is and why.
    """

    best_possible_rcr: float
    best_possible_level: int  # 1-4
    limiting_factors: List[Limitation] = Field(default_factory=list)
    explanation: str
    explanation_ja: str = ""

    # What changes are needed to achieve minimum
    required_changes: List[str] = Field(default_factory=list)

    # Alternative approaches if current limit is too high
    alternatives: List[str] = Field(default_factory=list)
