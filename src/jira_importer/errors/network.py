"""Network/connection related exceptions."""

from __future__ import annotations

from typing import Any

from .base import ProcessingError
from .codes import ErrorCode


class NetworkError(ProcessingError):
    """Network/connection errors."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize NetworkError.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error details.
        """
        super().__init__(message, code=ErrorCode.INTERNAL_ERROR, details=details)
