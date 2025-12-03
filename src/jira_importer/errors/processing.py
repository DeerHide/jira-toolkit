"""Processing-related exceptions."""

from __future__ import annotations

from typing import Any

from .base import ProcessingError
from .codes import ErrorCode


class ValidationError(ProcessingError):
    """Validation failures."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize ValidationError.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error details.
        """
        super().__init__(message, code=ErrorCode.VALIDATION_FAILED, details=details)


class ValidationSetupError(ProcessingError):
    """Validation setup failures."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize ValidationSetupError.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error details.
        """
        super().__init__(message, code=ErrorCode.INTERNAL_ERROR, details=details)


class RowProcessingError(ProcessingError):
    """Row processing failures."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize RowProcessingError.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error details.
        """
        super().__init__(message, code=ErrorCode.INTERNAL_ERROR, details=details)


class MetadataWriteError(ProcessingError):
    """Excel metadata write failures."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize MetadataWriteError.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error details.
        """
        super().__init__(message, code=ErrorCode.INTERNAL_ERROR, details=details)
