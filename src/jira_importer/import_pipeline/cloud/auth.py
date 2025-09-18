"""Authentication helpers for Jira Cloud.

This module defines abstractions for OAuth 2.0 (3LO) and basic auth.
Only minimal scaffolding is provided at this step.
"""

from __future__ import annotations

from base64 import b64encode
from dataclasses import dataclass
from typing import Protocol


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
