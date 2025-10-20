"""Authentication providers for Jira Cloud API.

Supports Basic Auth (email + API token) and OAuth 2.0 (3LO) with PKCE.
TODO: OAuth 2.0 (3LO) with PKCE and refresh token.
Only minimal scaffolding is provided at this step.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

import base64
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class AuthProvider(ABC):
    """Base class for authentication providers."""

    @abstractmethod
    def get_auth_header(self) -> dict[str, str]:
        """Return headers for authentication."""


@dataclass
class BasicAuthProvider(AuthProvider):
    """Basic authentication using email and API token."""

    email: str
    api_token: str = field(repr=False)

    def get_auth_header(self) -> dict[str, str]:
        """Return Basic auth header."""
        credentials = f"{self.email}:{self.api_token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}


@dataclass
class OAuthSessionManager(AuthProvider):  # pylint: disable=too-many-instance-attributes
    """Manages OAuth 2.0 (3LO) tokens, including refresh and persistence."""

    client_id: str
    client_secret: str = field(repr=False)
    refresh_token: str | None = field(default=None, repr=False)
    access_token: str | None = field(default=None, repr=False)
    expires_at: float = 0.0  # Unix timestamp
    token_url: str = "https://auth.atlassian.com/oauth/token"
    keyring_service: str = "jira-toolkit-oauth"
    keyring_username: str = "default"

    def _should_refresh(self) -> bool:
        """Check if token needs refresh."""
        return self.access_token is None or time.time() >= self.expires_at - 60

    def ensure_access_token(self) -> str:
        """Ensure we have a valid access token, refreshing if needed."""
        if not self._should_refresh():
            return self.access_token or ""

        # OAuth refresh flow not yet implemented
        # For now, return empty string to indicate not implemented
        return ""

    def get_auth_header(self) -> dict[str, str]:
        """Return OAuth Bearer header."""
        token = self.ensure_access_token()
        return {"Authorization": f"Bearer {token}"}
