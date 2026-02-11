"""Utility helpers for the import pipeline.

Author:
    Julien (@tom4897)
"""

from __future__ import annotations

from typing import Any


def split_multi_value_cell(raw: Any, sep: str = ";") -> list[str]:
    """Split a raw cell value into trimmed, non-empty parts.

    This is used for fields that can contain multiple values in a single cell,
    such as Components or Labels, using a semicolon-delimited format:

    - "A;B"        -> ["A", "B"]
    - "A; B ; ; C" -> ["A", "B", "C"]
    - "" / None    -> []

    Args:
        raw: Cell value as read from the source row.
        sep: Delimiter used to separate values (default: ";").

    Returns:
        List of trimmed, non-empty value strings.
    """
    if raw is None:
        return []

    text = str(raw).strip()
    if not text:
        return []

    return [part.strip() for part in text.split(sep) if part.strip()]

