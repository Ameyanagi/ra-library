"""Shared service-layer result and error types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ServiceResult:
    """Structured service result returned to thin transport layers."""

    data: dict[str, Any]
    warnings: list[dict[str, Any]] = field(default_factory=list)


class ServiceError(Exception):
    """Machine-readable service error for transport wrappers."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


def warning_item(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a machine-readable warning entry."""
    item: dict[str, Any] = {"code": code, "message": message}
    if details:
        item["details"] = details
    return item
