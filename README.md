# RA Library

Chemical risk assessment library built from publicly documented methodology references.

## Overview

This library implements an independent risk assessment workflow with detailed explanations, recommendations, and optional bundled SQLite reference data.

## Features

- **Verbose Calculations**: Every step is explained with references
- **What-If Analysis**: Simulate different control measures
- **Recommendation Engine**: Prioritized risk reduction actions
- **Limitation Transparency**: Explains when Level I is impossible

## Installation

```bash
uv add "ra-library @ git+https://github.com/Ameyanagi/ra-library.git"
```

## Usage

```python
from ra_library import AssessmentInput, Substance
from ra_library.calculators import calculate_inhalation_risk

# Create assessment input
input = AssessmentInput(
    title="Toluene handling",
    product_property=PropertyType.LIQUID,
    amount_level=AmountLevel.MEDIUM,
    ventilation=VentilationLevel.INDUSTRIAL,
)

# Calculate risk
result = calculate_inhalation_risk(input, substance)
print(f"Risk Level: {result.risk_level.name}")
print(f"RCR: {result.rcr:.4f}")
```

## Notes

- The packaged reference data is bundled as SQLite databases, not the original source workbook files.
- This is an independent implementation and is not an official MHLW distribution.
- Public methodology documents may be cited for interoperability and validation, but official workbook assets are not redistributed here.

## References

- Public CREATE-SIMPLE design and manual documents
- HSE COSHH Essentials
- ECETOC TRA
- Potts-Guy Equation for dermal absorption
