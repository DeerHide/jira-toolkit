"""HTTP client scaffold for Jira Cloud REST API v3.

Provides a minimal interface to make requests; resilience will be added later.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

from collections.abc import Mapping

# pyright: reportMissingTypeStubs=false, reportMissingImports=false
from dataclasses import dataclass
from typing import Any

import requests  # type: ignore  # pyright: ignore[reportMissingTypeStubs]

from .auth import AuthProvider


@dataclass
class JiraCloudClient:
    """This class is used to make requests to the Jira Cloud API."""

    base_url: str
    auth_provider: AuthProvider
    timeout_seconds: float = 30.0

    def _headers(self, extra: Mapping[str, str] | None = None) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        headers.update(self.auth_provider.get_auth_header())
        if extra:
            headers.update(extra)
        return headers

    def get(self, path: str, params: Mapping[str, Any] | None = None) -> Any:
        """Make a GET request to the Jira Cloud API."""
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        return requests.get(url, headers=self._headers(), params=params, timeout=self.timeout_seconds)

    def post(self, path: str, json: Any | None = None) -> Any:
        """Make a POST request to the Jira Cloud API."""
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        return requests.post(url, headers=self._headers(), json=json, timeout=self.timeout_seconds)
