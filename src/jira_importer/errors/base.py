"""Base exception classes for the error hierarchy."""

from __future__ import annotations

from typing import Any

from .codes import ErrorCode


class ProcessingError(Exception):
    """Base exception for processing errors.

    All domain exceptions inherit from this class.
    """

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize ProcessingError.

        Args:
            message: Human-readable error message.
            code: Error code enum value. Defaults to INTERNAL_ERROR.
            details: Optional dictionary with additional error details.
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
