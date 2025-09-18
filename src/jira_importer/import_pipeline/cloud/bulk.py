"""Helpers to build bulk operation payloads (scaffold).

author:
    Julien (@tom4897)
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .constants import BATCH_SIZE


def build_bulk_create_payload(issues: list[dict[str, Any]]) -> dict[str, Any]:
    """Return payload for POST /rest/api/3/issue/bulk."""
    return {"issueUpdates": issues}


def chunk_issues(issues: Iterable[dict[str, Any]], *, batch_size: int = BATCH_SIZE) -> list[list[dict[str, Any]]]:
    """Split issues into chunks with a maximum size (default BATCH_SIZE, defined in constants.py)."""
    batch: list[dict[str, Any]] = []
    batches: list[list[dict[str, Any]]] = []
    for issue in issues:
        batch.append(issue)
        if len(batch) >= batch_size:
            batches.append(batch)
            batch = []
    if batch:
        batches.append(batch)
    return batches
