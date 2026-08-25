"""Internationalization module for CREATE-SIMPLE labels."""

from .labels import get_label, get_labels, LABELS
from .official import (
    get_official_named_text,
    get_official_option_list,
    get_official_terminology,
    get_terminology_source,
)

__all__ = [
    "get_label",
    "get_labels",
    "LABELS",
    "get_official_named_text",
    "get_official_option_list",
    "get_official_terminology",
    "get_terminology_source",
]
