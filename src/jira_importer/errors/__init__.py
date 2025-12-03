"""Error handling for Jira Importer.

This package provides:
- ErrorCode enum (shared with MCP)
- Domain exception classes with error codes
- Error mapping utilities

All exceptions can be imported from this package:
    from jira_importer.errors import (
        ErrorCode,
        ProcessingError,
        FileReadError,
        JiraAuthError,
        ...
    )
"""

from __future__ import annotations

from .base import ProcessingError

# Re-export everything for convenience (single import point)
from .codes import ErrorCode
from .config import ConfigurationError, ExcelConfigurationError
from .file import FileReadError, FileWriteError, InputFileError
from .jira import JiraApiError, JiraAuthError
from .network import NetworkError
from .processing import MetadataWriteError, RowProcessingError, ValidationError, ValidationSetupError
from .utils import format_error_for_display, get_error_details, log_exception, map_exception_to_code

__all__ = [
    "ConfigurationError",
    "ErrorCode",
    "ExcelConfigurationError",
    "FileReadError",
    "FileWriteError",
    "InputFileError",
    "JiraApiError",
    "JiraAuthError",
    "MetadataWriteError",
    "NetworkError",
    "ProcessingError",
    "RowProcessingError",
    "ValidationError",
    "ValidationSetupError",
    "format_error_for_display",
    "get_error_details",
    "log_exception",
    "map_exception_to_code",
]
