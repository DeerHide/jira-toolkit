"""Error code definitions with numeric codes for easy reference."""

from __future__ import annotations

from enum import Enum

# Module-level numeric code mapping (avoids issues with str Enum members)
_NUMERIC_CODES: dict[str, int] = {
    "INVALID_INPUT": 1001,
    "INPUT_FILE_ERROR": 1003,
    "CONFIG_FILE_ERROR": 1004,
    "OUTPUT_FILE_ERROR": 1005,
    "VALIDATION_FAILED": 1002,
    "NETWORK_ERROR": 3001,
    "VALIDATION_SETUP_ERROR": 3002,
    "ROW_PROCESSING_ERROR": 3003,
    "METADATA_WRITE_ERROR": 3004,
    "JIRA_AUTH_ERROR": 2001,
    "JIRA_API_ERROR": 2002,
    "INTERNAL_ERROR": 9001,
}


class ErrorCode(str, Enum):
    """Standard error codes used across main app and MCP server.

    These codes represent domain-level error types and are shared
    between the CLI application and MCP server.

    Each code has:
    - String value: Used in JSON/API responses (e.g., "INVALID_INPUT")
    - Numeric code: For easy reference and research (e.g., 1001)

    Usage:
        >>> code = ErrorCode.INVALID_INPUT
        >>> str(code)  # "INVALID_INPUT"
        >>> code.value  # "INVALID_INPUT"
        >>> code.code  # 1001
        >>> code.display()  # "INVALID_INPUT (1001)"
    """

    INVALID_INPUT = "INVALID_INPUT"
    INPUT_FILE_ERROR = "INPUT_FILE_ERROR"
    OUTPUT_FILE_ERROR = "OUTPUT_FILE_ERROR"
    CONFIG_FILE_ERROR = "CONFIG_FILE_ERROR"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    NETWORK_ERROR = "NETWORK_ERROR"
    VALIDATION_SETUP_ERROR = "VALIDATION_SETUP_ERROR"
    ROW_PROCESSING_ERROR = "ROW_PROCESSING_ERROR"
    METADATA_WRITE_ERROR = "METADATA_WRITE_ERROR"
    JIRA_AUTH_ERROR = "JIRA_AUTH_ERROR"
    JIRA_API_ERROR = "JIRA_API_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"

    @property
    def code(self) -> int:
        """Get the numeric error code."""
        return _NUMERIC_CODES.get(self.value, 0)

    def display(self) -> str:
        """Display both string and numeric code for easy reference."""
        return f"{self.value} ({self.code})"

    @classmethod
    def get_by_number(cls, numeric_code: int) -> ErrorCode | None:
        """Get ErrorCode by numeric code (for lookup/reference).

        Args:
            numeric_code: The numeric error code.

        Returns:
            ErrorCode if found, None otherwise.
        """
        for code in cls:
            if code.code == numeric_code:
                return code
        return None
