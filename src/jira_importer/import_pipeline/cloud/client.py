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
    verify: bool | str = True
    max_response_size: int | None = None

    def _headers(self) -> dict[str, str]:
        """Get request headers with auth."""
        headers = DEFAULT_HEADERS.copy()
        headers.update(self.auth_provider.get_auth_header())
        return headers

    def _request_with_retries(
        self, method: str, url: str, *, params: Mapping[str, Any] | None = None, json: Any | None = None
    ) -> requests.Response:
        """Make request with retries for transient errors.

        Notes:
            - SSL/TLS verification is controlled via self.verify (bool or path to CA bundle).
            - Optional response size guard uses Content-Length when available.
        """
        backoff = BACKOFF_INITIAL_SECONDS

        for attempt in range(1, RETRY_MAX_ATTEMPTS + 1):
            resp = requests.request(
                method,
                url,
                headers=self._headers(),
                params=params,
                json=json,
                timeout=self.timeout_seconds,
                verify=self.verify,
            )

            # Optional response size limiting when Content-Length is present
            if self.max_response_size is not None:
                content_length = resp.headers.get("Content-Length")
                if content_length:
                    try:
                        length_int = int(content_length)
                    except ValueError:
                        length_int = None
                    if length_int is not None and length_int > self.max_response_size:
                        # Do not attempt to parse or process oversized responses
                        from ...errors import JiraApiError  # pylint: disable=import-outside-toplevel

                        raise JiraApiError(
                            f"Jira API response too large ({length_int} bytes, "
                            f"limit is {self.max_response_size} bytes).",
                            status_code=resp.status_code,
                            details={"content_length": length_int, "max_response_size": self.max_response_size},
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

    def put(self, path: str, *, json: Any | None = None) -> requests.Response:
        """PUT request."""
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        return self._request_with_retries("PUT", url, json=json)
