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
pip install ra-library
```

```bash
uv add ra-library
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

## Development

```bash
uv sync --group dev
uv run pre-commit install
uv run pre-commit run --all-files
uv run pytest -q
```

## Release

PyPI publishing is handled by GitHub Actions only when a matching `v*` tag is
pushed. See [docs/release.md](docs/release.md) for the cleanup and release
checklist.

## Notes

- The packaged reference data is bundled as SQLite databases, not the original source workbook files.
- This is an independent implementation and is not an official MHLW distribution.
- Public methodology documents may be cited for interoperability and validation, but official workbook assets are not redistributed here.

## References

- Public CREATE-SIMPLE design and manual documents
- HSE COSHH Essentials
- ECETOC TRA
- Potts-Guy Equation for dermal absorption
