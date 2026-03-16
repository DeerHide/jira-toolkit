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

from .constants import HTTP_NOT_FOUND
from .client import JiraCloudClient


@dataclass
class MetadataCache:
    """Metadata cache. This class is used to cache the metadata for the Jira Cloud API."""

    client: JiraCloudClient
    _fields: list[dict[str, Any]] | None = field(default=None, init=False)
    _issuetypes: list[dict[str, Any]] | None = field(default=None, init=False)
    _priorities: list[dict[str, Any]] | None = field(default=None, init=False)
    _projects: dict[str, dict[str, Any] | None] = field(default_factory=dict, init=False)
    _project_components: dict[str, list[dict[str, Any]]] = field(default_factory=dict, init=False)
    _project_versions: dict[str, list[dict[str, Any]]] = field(default_factory=dict, init=False)
    _user_exists_cache: dict[str, bool] = field(default_factory=dict, init=False)

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

    def get_project(self, project_key: str) -> dict[str, Any] | None:
        """Get project by key. Returns None if project does not exist (404)."""
        if project_key in self._projects:
            return self._projects[project_key]
        resp = self.client.get(f"project/{project_key}")
        if resp.status_code == HTTP_NOT_FOUND:
            self._projects[project_key] = None  # type: ignore[assignment]
            return None
        resp.raise_for_status()
        self._projects[project_key] = resp.json()  # type: ignore[assignment]
        return self._projects[project_key]

    def get_project_components(self, project_key: str) -> list[dict[str, Any]]:
        """Get components for a project (paginated, cached)."""
        if project_key in self._project_components:
            return self._project_components[project_key]
        path = f"project/{project_key}/component"
        components = list(self.paged(path, page_size=50))
        self._project_components[project_key] = components
        return components

    def get_priorities(self) -> list[dict[str, Any]]:
        """Get priorities from the Jira Cloud API."""
        if self._priorities is None:
            resp = self.client.get("priority")
            resp.raise_for_status()
            self._priorities = resp.json()  # type: ignore[assignment]
        return self._priorities

    def get_project_versions(self, project_key: str) -> list[dict[str, Any]]:
        """Get fix versions for a project (paginated, cached)."""
        if project_key in self._project_versions:
            return self._project_versions[project_key]
        path = f"project/{project_key}/version"
        versions = list(self.paged(path, page_size=50))
        self._project_versions[project_key] = versions
        return versions

    def user_exists(self, account_id: str) -> bool:
        """Check if user exists by accountId. Returns False on 404. Cached."""
        if account_id in self._user_exists_cache:
            return self._user_exists_cache[account_id]
        resp = self.client.get("user", params={"accountId": account_id})
        exists = resp.status_code != HTTP_NOT_FOUND and resp.ok
        self._user_exists_cache[account_id] = exists
        return exists

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
            if not values:  # Stop if an empty page is returned
                break
