# RA Library

<p align="center">
  <img src="assets/logo.png" alt="RA Suite logo" width="180">
</p>

Chemical risk assessment library built from publicly documented methodology references.

## Overview

This library implements an independent risk assessment workflow with detailed explanations, recommendations, and optional bundled SQLite reference data.

## Features

- **Verbose Calculations**: Every step is explained with references
- **Verified Scenario Analysis**: Recalculate bounded control ranges and explicit batches
- **Auditable Recommendations**: Preserve mixture, method version, risk domains, and baseline fingerprint
- **Limitation Transparency**: Explains when Level I is impossible
- **Official Japanese Terminology**: v3.2.1 workbook labels with sheet/cell and SHA-256 provenance

## Installation

```bash
uv add "ra-library @ https://github.com/Ameyanagi/ra-library/archive/refs/tags/v0.4.0.zip"
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

Verified control ranges are available from the service layer:

```python
from ra_library.services import calculate_risk

result = calculate_risk(
    substances=[{"cas_number": "108-88-3", "content_percent": 100}],
    preset="lab_organic",
    include_recommendations="verified",
    recommendation_scope={
        "ventilation": ["local_enclosed", "sealed"],
        "hours": [4, 2, 1],
        "max_combination_size": 2,
        "max_scenarios": 30,
    },
    language="ja",
)
print(result.data["recommendation_analysis"])
```

## Development

```bash
uv sync --group dev
uv run pre-commit install
uv run pre-commit run --all-files
uv run pytest -q
```

## Release

A matching `v*` tag builds and attaches distributions to a GitHub Release.
The workflow does not publish to PyPI or another package registry.

## Notes

- The package includes extracted terminology and provenance, not the original XLSM workbook.
- This is an independent implementation and is not an official MHLW distribution.
- Public methodology documents may be cited for interoperability and validation, but official workbook assets are not redistributed here.

## References

- Public CREATE-SIMPLE design and manual documents
- HSE COSHH Essentials
- ECETOC TRA
- Potts-Guy Equation for dermal absorption
