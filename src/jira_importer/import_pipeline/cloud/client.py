"""HTTP client scaffold for Jira Cloud REST API v3.

Provides a minimal interface to make requests; resilience will be added later.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

from collections.abc import Mapping

# pyright: reportMissingTypeStubs=false, reportMissingImports=false
from dataclasses import dataclass
from time import sleep
from typing import Any

import requests  # type: ignore  # pyright: ignore[reportMissingTypeStubs]

from .auth import AuthProvider
from .constants import (
    BACKOFF_INITIAL_SECONDS,
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
    """This class is used to make requests to the Jira Cloud API."""

    base_url: str
    auth_provider: AuthProvider
    timeout_seconds: float = 30.0

    def _headers(self, extra: Mapping[str, str] | None = None) -> dict[str, str]:
        headers = dict(DEFAULT_HEADERS)
        headers.update(self.auth_provider.get_auth_header())
        if extra:
            headers.update(extra)
        return headers

    def get(self, path: str, params: Mapping[str, Any] | None = None) -> Any:
        """Make a GET request to the Jira Cloud API."""
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        return self._request_with_retries("GET", url, params=params)

    def post(self, path: str, json: Any | None = None) -> Any:
        """Make a POST request to the Jira Cloud API."""
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        return self._request_with_retries("POST", url, json=json)

    def _request_with_retries(
        self, method: str, url: str, *, params: Mapping[str, Any] | None = None, json: Any | None = None
    ) -> Any:
        max_attempts = RETRY_MAX_ATTEMPTS
        backoff = BACKOFF_INITIAL_SECONDS
        for attempt in range(1, max_attempts + 1):
            resp = requests.request(
                method, url, headers=self._headers(), params=params, json=json, timeout=self.timeout_seconds
            )  # type: ignore
            if HTTP_SUCCESS_MIN <= resp.status_code <= HTTP_SUCCESS_MAX:
                return resp
            if resp.status_code == STATUS_TOO_MANY_REQUESTS:
                retry_after = resp.headers.get("Retry-After")
                try:
                    delay = float(retry_after) if retry_after else backoff
                except Exception:
                    delay = backoff
                sleep(delay)
                backoff = min(backoff * BACKOFF_MULTIPLIER, BACKOFF_INITIAL_SECONDS * (BACKOFF_MULTIPLIER**4))
                continue
            if HTTP_SERVER_ERROR_MIN <= resp.status_code <= HTTP_SERVER_ERROR_MAX and attempt < max_attempts:
                sleep(backoff)
                backoff = min(backoff * BACKOFF_MULTIPLIER, BACKOFF_INITIAL_SECONDS * (BACKOFF_MULTIPLIER**4))
                continue
            return resp
        return resp
