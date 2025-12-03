"""Configuration-related exceptions."""

from __future__ import annotations

from typing import Any

from .base import ProcessingError
from .codes import ErrorCode


class ConfigurationError(ProcessingError):
    """Configuration file errors."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize ConfigurationError.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error details.
        """
        super().__init__(message, code=ErrorCode.CONFIG_FILE_ERROR, details=details)


class ExcelConfigurationError(ConfigurationError):
    """Excel configuration file errors."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize ExcelConfigurationError.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error details.
        """
        super().__init__(message, details=details)
