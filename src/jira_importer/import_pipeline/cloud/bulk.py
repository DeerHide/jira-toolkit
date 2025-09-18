"""Helpers to build bulk operation payloads (scaffold)."""

from __future__ import annotations

from typing import Any


def build_bulk_create_payload(issues: list[dict[str, Any]]) -> dict[str, Any]:
    """Return payload for POST /rest/api/3/issue/bulk."""
    return {"issueUpdates": issues}
