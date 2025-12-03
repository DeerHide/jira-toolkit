"""File I/O related exceptions."""

from __future__ import annotations

from typing import Any

from .base import ProcessingError
from .codes import ErrorCode


class FileReadError(ProcessingError):
    """File reading failures."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize FileReadError.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error details.
        """
        super().__init__(message, code=ErrorCode.INVALID_INPUT, details=details)


class FileWriteError(ProcessingError):
    """File writing failures."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize FileWriteError.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error details.
        """
        super().__init__(message, code=ErrorCode.INVALID_INPUT, details=details)


class InputFileError(ProcessingError):
    """Input file validation failures.

    Raised when the input file fails validation checks (e.g., file doesn't exist,
    is not a file, or is invalid for processing).
    """

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize InputFileError.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error details.
        """
        super().__init__(message, code=ErrorCode.INPUT_FILE_ERROR, details=details)
