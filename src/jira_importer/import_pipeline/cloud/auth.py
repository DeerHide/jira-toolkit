"""Authentication helpers for Jira Cloud.

This module defines abstractions for OAuth 2.0 (3LO) and basic auth.
Only minimal scaffolding is provided at this step.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

import time
from base64 import b64encode
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import import_module
from typing import Any, Protocol


class AuthProvider(Protocol):
    """Protocol for objects that can provide HTTP Authorization headers."""

    def get_auth_header(self) -> dict[str, str]:
        """Return authorization headers to attach to HTTP requests."""


@dataclass
class BasicAuthProvider:
    """Basic auth provider scaffold (email + API token)."""

    email: str
    api_token: str

    def get_auth_header(self) -> dict[str, str]:
        """Return authorization headers to attach to HTTP requests."""
        token = b64encode(f"{self.email}:{self.api_token}".encode()).decode("ascii")
        return {"Authorization": f"Basic {token}"}


@dataclass
class OAuthToken:
    """OAuth 2.0 (3LO) token."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"


@dataclass
class OAuthProvider:
    """OAuth 2.0 (3LO) provider scaffold using pre-provisioned tokens.

    Full PKCE flow and refresh handling will be implemented in a later step.
    """

    token: OAuthToken

    def get_auth_header(self) -> dict[str, str]:
        """Return authorization headers to attach to HTTP requests."""
        return {"Authorization": f"Bearer {self.token.access_token}"}


@dataclass
class OAuthSessionManager:
    """Minimal refresh-capable OAuth session manager (refresh-token flow only).

    Notes:
        - Expects client_id/client_secret and a refresh_token in config/keyring.
        - Uses Atlassian OAuth token endpoint. PKCE/device code are out of scope here.
    """

    token_endpoint: str
    client_id: str
    client_secret: str
    refresh_token: str
    access_token: str | None = None
    access_token_expiry_epoch: int | None = None

    def _now(self) -> int:
        return int(time.time())

    def _should_refresh(self) -> bool:
        if not self.access_token or not self.access_token_expiry_epoch:
            return True
        # Refresh a bit early (skew)
        return self._now() >= (self.access_token_expiry_epoch - 30)

    def _http_post_form(self, url: str, data: Mapping[str, Any]) -> dict[str, Any]:
        try:
            requests = import_module("requests")  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("requests is required for OAuthSessionManager") from exc
        resp = requests.post(url, data=data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def ensure_access_token(self) -> str:
        """Ensure an access token is available or return an empty string."""
        if not self._should_refresh():
            return self.access_token or ""

        payload = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
        }
        data = self._http_post_form(self.token_endpoint, payload)
        self.access_token = data.get("access_token")
        expires_in = int(data.get("expires_in", 3600))
        self.access_token_expiry_epoch = self._now() + expires_in
        # Optionally update refresh token if rotated
        new_refresh = data.get("refresh_token")
        if isinstance(new_refresh, str) and new_refresh:
            self.refresh_token = new_refresh
        return self.access_token or ""

    def get_auth_header(self) -> dict[str, str]:
        """Return authorization headers to attach to HTTP requests."""
        token = self.ensure_access_token()
        return {"Authorization": f"Bearer {token}"}
