"""Jira API related exceptions."""

from __future__ import annotations

from typing import Any

from .base import ProcessingError
from .codes import ErrorCode


class JiraAuthError(ProcessingError):
    """Jira authentication/authorization errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize JiraAuthError.

        Args:
            message: Human-readable error message.
            status_code: Optional HTTP status code (e.g., 401, 403).
            details: Optional dictionary with additional error details.
        """
        super().__init__(message, code=ErrorCode.JIRA_AUTH_ERROR, details=details)
        self.status_code = status_code


class JiraApiError(ProcessingError):
    """Jira API errors (non-auth)."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize JiraApiError.

        Args:
            message: Human-readable error message.
            status_code: Optional HTTP status code (e.g., 404, 429, 500).
            details: Optional dictionary with additional error details.
        """
        super().__init__(message, code=ErrorCode.JIRA_API_ERROR, details=details)
        self.status_code = status_code
