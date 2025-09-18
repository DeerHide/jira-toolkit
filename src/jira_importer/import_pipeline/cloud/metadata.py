"""Metadata helpers for Jira Cloud.

This module provides simple cached fetchers for fields, projects, and issue types.
Detailed pagination and expansion will be implemented in later steps.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from .client import JiraCloudClient


@dataclass
class MetadataCache:
    """Metadata cache. This class is used to cache the metadata for the Jira Cloud API."""

    client: JiraCloudClient
    _fields: list[dict[str, Any]] | None = field(default=None, init=False)
    _issuetypes: list[dict[str, Any]] | None = field(default=None, init=False)

    def get_fields(self) -> list[dict[str, Any]]:
        """Get the fields from the Jira Cloud API."""
        if self._fields is None:
            resp = self.client.get("field")
            resp.raise_for_status()
            self._fields = resp.json()  # type: ignore[assignment]
        return self._fields

    def get_issuetypes(self) -> list[dict[str, Any]]:
        """Get the issue types from the Jira Cloud API."""
        if self._issuetypes is None:
            resp = self.client.get("issuetype")
            resp.raise_for_status()
            self._issuetypes = resp.json()  # type: ignore[assignment]
        return self._issuetypes

    def paged(
        self, path: str, *, params: dict[str, Any] | None = None, page_size: int = 50
    ) -> Iterator[dict[str, Any]]:
        """Generic paginator for paginated endpoints (yields items across pages)."""
        start_at = 0
        params = dict(params or {})
        while True:
            params.update({"startAt": start_at, "maxResults": page_size})
            resp = self.client.get(path, params=params)
            resp.raise_for_status()
            data = resp.json()
            values = data.get("values") or data.get("issues") or []
            yield from values
            is_last = data.get("isLast")
            total = data.get("total")
            if is_last or (total is not None and start_at + page_size >= int(total)):
                break
            start_at += page_size
