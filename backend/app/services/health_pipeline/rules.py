"""Normalize parsed report fields into structured clinical findings."""

from typing import Any


def normalize_findings(raw_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert parsed report fields into normalized findings with severity and action hints."""
    return raw_items  # V1: pass-through; V2 will add structured normalization
