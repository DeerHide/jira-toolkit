"""Error mapping and formatting utilities."""

from __future__ import annotations

import logging
from typing import Any

from .base import ProcessingError
from .codes import ErrorCode
from .jira import JiraApiError, JiraAuthError


def map_exception_to_code(exc: Exception) -> ErrorCode:
    """Map an exception to an ErrorCode.

    Used by both main app and MCP server to determine error codes
    from exceptions.

    Args:
        exc: The exception to map.

    Returns:
        The corresponding ErrorCode.
    """
    if isinstance(exc, ProcessingError):
        return exc.code

    # Map standard exceptions
    if isinstance(exc, (ValueError, TypeError, KeyError)):
        return ErrorCode.INVALID_INPUT
    if isinstance(exc, (FileNotFoundError, PermissionError, OSError)):
        return ErrorCode.INVALID_INPUT

    # Default to internal error
    return ErrorCode.INTERNAL_ERROR


def get_error_details(exc: Exception) -> dict[str, Any]:
    """Extract error details from an exception.

    Used by both main app and MCP server to extract structured
    error details from exceptions.

    Args:
        exc: The exception to extract details from.

    Returns:
        Dictionary of error details.
    """
    if isinstance(exc, ProcessingError):
        details = exc.details.copy()
        if isinstance(exc, (JiraAuthError, JiraApiError)) and exc.status_code:
            details["status_code"] = exc.status_code
        return details

    return {"exception_type": type(exc).__name__}


def format_error_for_display(exc: Exception) -> str:
    """Format error for user display with both string and numeric codes.

    Example:
        "INVALID_INPUT (1001): File not found: /path/to/file"

    Args:
        exc: The exception to format.

    Returns:
        Formatted error string with code and message.
    """
    if isinstance(exc, ProcessingError):
        code_display = exc.code.display()  # "INVALID_INPUT (1001)"
        return f"{code_display}: {exc.message}"
    return str(exc)


def log_exception(
    logger: logging.Logger, exc: Exception, level: int = logging.ERROR, context: str | None = None
) -> None:
    """Log an exception with error code and structured details.

    This function logs exceptions with their error codes and details,
    making it easier to debug and track issues. It automatically includes:
    - Error code (both string and numeric)
    - Error message
    - Structured details (if available)
    - Full traceback (via exc_info)

    Args:
        logger: The logger instance to use.
        exc: The exception to log.
        level: Logging level (default: logging.ERROR).
        context: Optional context string to include in the log message.

    Example:
        >>> logger = logging.getLogger(__name__)
        >>> try:
        ...     raise FileReadError("File not found", details={"path": "/tmp/file.xlsx"})
        ... except FileReadError as e:
        ...     log_exception(logger, e, context="Reading input file")
        # Logs: "Reading input file: INVALID_INPUT (1001): File not found"
        #       "Error details: {'path': '/tmp/file.xlsx'}"
    """
    error_code = map_exception_to_code(exc)
    error_details = get_error_details(exc)
    formatted_message = format_error_for_display(exc)

    # Build log message with context
    if context:
        log_message = f"{context}: {formatted_message}"
    else:
        log_message = formatted_message

    # Log the error message with error code in structured format
    logger.log(level, "%s [error_code=%s]", log_message, error_code.value)

    # Log structured details if available
    if error_details and error_details != {"exception_type": type(exc).__name__}:
        logger.log(level, "Error details: %s", error_details)

    # Log full traceback
    logger.log(level, "Exception traceback:", exc_info=exc)
