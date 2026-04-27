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


class MissingConfigElementError(ConfigurationError):
    """Missing required configuration element errors."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize MissingConfigElementError.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error details.
        """
        ProcessingError.__init__(
            self,
            message,
            code=ErrorCode.CONFIG_MISSING_REQUIRED,
            details=details,
        )


class ConfigValidationPolicy:
    """Canonical config validation messaging policy.

    Keep this policy in errors/config.py so Phase 2 can tighten
    enforcement without moving call sites again.
    """

    @staticmethod
    def version_warning(cfg_req: int) -> str:
        """Build a standardized warning for unsupported config versions."""
        return (
            "Configuration version is missing, invalid, or below the supported minimum "
            f"({cfg_req}). Processing continues for backward compatibility, but a valid "
            "configuration version will be required in a future release."
        )

    @staticmethod
    def type_mismatch_message(key: str, expected_type: type[Any], actual_value: Any) -> str:
        """Build a standardized type mismatch message for config keys."""
        return f"Config key '{key}' expected {expected_type.__name__}, got {type(actual_value).__name__}"

    @staticmethod
    def type_mismatch_details(key: str, expected_type: type[Any], actual_value: Any) -> dict[str, str]:
        """Build standardized details payload for config type mismatches."""
        return {
            "key": key,
            "expected_type": expected_type.__name__,
            "actual_type": type(actual_value).__name__,
        }
