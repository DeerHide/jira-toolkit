"""Metadata helpers for Jira Cloud.

This module provides simple cached fetchers for fields, projects, and issue types.
Detailed pagination and expansion will be implemented in later steps.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

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
