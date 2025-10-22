"""Shared helper functions for formatting and data normalisation in the GUI."""
from __future__ import annotations

from typing import Any, Mapping, Optional


def resolve_cost(record: Mapping[str, Any]) -> Optional[float]:
    """Return the best cost value for an inventory record.

    The database may expose the purchase amount under a variety of keys
    (``purchase_cost``, ``cost`` or ``purchase_price``).  This helper selects the
    first meaningful value and coerces it to ``float`` when possible so callers
    can safely perform calculations.
    """

    for key in ("purchase_cost", "cost", "purchase_price"):
        value = record.get(key)
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def format_currency(value: Optional[float], default: str = "N/A") -> str:
    """Format a numeric value as currency, returning ``default`` when missing."""

    if value is None:
        return default
    try:
        return f"${float(value):.2f}"
    except (TypeError, ValueError):
        return default
