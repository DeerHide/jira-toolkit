"""Bulk operation utilities for Jira Cloud API.

This module provides helpers for building bulk operation payloads and
managing batch sizes for efficient API usage.

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
    """Split issues into chunks with a maximum size."""
    chunks = []
    current_chunk = []

    for issue in issues:
        current_chunk.append(issue)
        if len(current_chunk) >= batch_size:
            chunks.append(current_chunk)
            current_chunk = []

    if current_chunk:
        chunks.append(current_chunk)

    return chunks
