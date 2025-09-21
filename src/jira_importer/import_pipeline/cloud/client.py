"""HTTP client scaffold for Jira Cloud REST API v3.

Provides a minimal interface to make requests; resilience will be added later.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import requests  # pyright: ignore[reportMissingTypeStubs, reportMissingImports]

from .auth import AuthProvider
from .constants import (
    BACKOFF_INITIAL_SECONDS,
    BACKOFF_MAX_SECONDS,
    BACKOFF_MULTIPLIER,
    DEFAULT_HEADERS,
    HTTP_SERVER_ERROR_MAX,
    HTTP_SERVER_ERROR_MIN,
    HTTP_SUCCESS_MAX,
    HTTP_SUCCESS_MIN,
    RETRY_MAX_ATTEMPTS,
    STATUS_TOO_MANY_REQUESTS,
)


@dataclass
class JiraCloudClient:
    """HTTP client for Jira Cloud REST API v3."""

    base_url: str
    auth_provider: AuthProvider
    timeout_seconds: int = 30

    def _headers(self) -> dict[str, str]:
        """Get request headers with auth."""
        headers = DEFAULT_HEADERS.copy()
        headers.update(self.auth_provider.get_auth_header())
        return headers

    def _request_with_retries(
        self, method: str, url: str, *, params: Mapping[str, Any] | None = None, json: Any | None = None
    ) -> requests.Response:
        """Make request with retries for transient errors."""
        backoff = BACKOFF_INITIAL_SECONDS

        for attempt in range(1, RETRY_MAX_ATTEMPTS + 1):
            resp = requests.request(
                method, url, headers=self._headers(), params=params, json=json, timeout=self.timeout_seconds
            )

            # Success
            if HTTP_SUCCESS_MIN <= resp.status_code <= HTTP_SUCCESS_MAX:
                return resp

            # Rate limited - retry with backoff
            if resp.status_code == STATUS_TOO_MANY_REQUESTS:
                delay = float(resp.headers.get("Retry-After", backoff)) if resp.headers.get("Retry-After") else backoff
                time.sleep(delay)
                backoff = min(backoff * BACKOFF_MULTIPLIER, BACKOFF_MAX_SECONDS)
                continue

            # Server error - retry with backoff
            if HTTP_SERVER_ERROR_MIN <= resp.status_code <= HTTP_SERVER_ERROR_MAX and attempt < RETRY_MAX_ATTEMPTS:
                time.sleep(backoff)
                backoff = min(backoff * BACKOFF_MULTIPLIER, BACKOFF_MAX_SECONDS)
                continue

            # Client error or max retries reached
            return resp

        return resp

    def get(self, path: str, *, params: Mapping[str, Any] | None = None) -> requests.Response:
        """GET request."""
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        return self._request_with_retries("GET", url, params=params)

    def post(self, path: str, *, json: Any | None = None) -> requests.Response:
        """POST request."""
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        return self._request_with_retries("POST", url, json=json)
