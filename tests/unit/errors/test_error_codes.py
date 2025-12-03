"""Tests for error code enum and utilities."""

from __future__ import annotations

from jira_importer.errors import (
    ConfigurationError,
    ErrorCode,
    ExcelConfigurationError,
    FileReadError,
    InputFileError,
    JiraApiError,
    JiraAuthError,
    ProcessingError,
    ValidationError,
    format_error_for_display,
    get_error_details,
    map_exception_to_code,
)


class TestErrorCode:
    """Tests for ErrorCode enum."""

    def test_error_code_string_value(self) -> None:
        """Test that error codes have string values."""
        assert ErrorCode.INVALID_INPUT.value == "INVALID_INPUT"
        assert ErrorCode.INPUT_FILE_ERROR.value == "INPUT_FILE_ERROR"
        assert ErrorCode.CONFIG_FILE_ERROR.value == "CONFIG_FILE_ERROR"
        assert ErrorCode.VALIDATION_FAILED.value == "VALIDATION_FAILED"
        assert ErrorCode.JIRA_AUTH_ERROR.value == "JIRA_AUTH_ERROR"
        assert ErrorCode.JIRA_API_ERROR.value == "JIRA_API_ERROR"
        assert ErrorCode.INTERNAL_ERROR.value == "INTERNAL_ERROR"

    def test_error_code_numeric_code(self) -> None:
        """Test that error codes have numeric codes."""
        assert ErrorCode.INVALID_INPUT.code == 1001
        assert ErrorCode.INPUT_FILE_ERROR.code == 1003
        assert ErrorCode.CONFIG_FILE_ERROR.code == 1004
        assert ErrorCode.VALIDATION_FAILED.code == 1002
        assert ErrorCode.JIRA_AUTH_ERROR.code == 2001
        assert ErrorCode.JIRA_API_ERROR.code == 2002
        assert ErrorCode.INTERNAL_ERROR.code == 9001

    def test_error_code_display(self) -> None:
        """Test error code display format."""
        assert ErrorCode.INVALID_INPUT.display() == "INVALID_INPUT (1001)"
        assert ErrorCode.VALIDATION_FAILED.display() == "VALIDATION_FAILED (1002)"

    def test_error_code_get_by_number(self) -> None:
        """Test lookup by numeric code."""
        assert ErrorCode.get_by_number(1001) == ErrorCode.INVALID_INPUT
        assert ErrorCode.get_by_number(1003) == ErrorCode.INPUT_FILE_ERROR
        assert ErrorCode.get_by_number(1004) == ErrorCode.CONFIG_FILE_ERROR
        assert ErrorCode.get_by_number(2001) == ErrorCode.JIRA_AUTH_ERROR
        assert ErrorCode.get_by_number(9999) is None


class TestExceptions:
    """Tests for exception classes."""

    def test_processing_error_default_code(self) -> None:
        """Test that ProcessingError defaults to INTERNAL_ERROR."""
        exc = ProcessingError("Test error")
        assert exc.code == ErrorCode.INTERNAL_ERROR
        assert exc.message == "Test error"
        assert exc.details == {}

    def test_processing_error_with_code(self) -> None:
        """Test ProcessingError with explicit code."""
        exc = ProcessingError("Test error", code=ErrorCode.INVALID_INPUT)
        assert exc.code == ErrorCode.INVALID_INPUT

    def test_processing_error_with_details(self) -> None:
        """Test ProcessingError with details."""
        details = {"key": "value"}
        exc = ProcessingError("Test error", details=details)
        assert exc.details == details

    def test_file_read_error_code(self) -> None:
        """Test that FileReadError has correct code."""
        exc = FileReadError("File not found")
        assert exc.code == ErrorCode.INVALID_INPUT

    def test_validation_error_code(self) -> None:
        """Test that ValidationError has correct code."""
        exc = ValidationError("Validation failed")
        assert exc.code == ErrorCode.VALIDATION_FAILED

    def test_jira_auth_error_with_status_code(self) -> None:
        """Test JiraAuthError with status code."""
        exc = JiraAuthError("Auth failed", status_code=401)
        assert exc.code == ErrorCode.JIRA_AUTH_ERROR
        assert exc.status_code == 401

    def test_jira_api_error_with_status_code(self) -> None:
        """Test JiraApiError with status code."""
        exc = JiraApiError("API error", status_code=404)
        assert exc.code == ErrorCode.JIRA_API_ERROR
        assert exc.status_code == 404

    def test_configuration_error_code(self) -> None:
        """Test that ConfigurationError has correct code."""
        exc = ConfigurationError("Config error")
        assert exc.code == ErrorCode.CONFIG_FILE_ERROR

    def test_excel_configuration_error_inheritance(self) -> None:
        """Test that ExcelConfigurationError inherits from ConfigurationError."""
        exc = ExcelConfigurationError("Excel config error")
        assert isinstance(exc, ConfigurationError)
        assert exc.code == ErrorCode.CONFIG_FILE_ERROR

    def test_input_file_error_code(self) -> None:
        """Test that InputFileError has correct code."""
        exc = InputFileError("Input file not found")
        assert exc.code == ErrorCode.INPUT_FILE_ERROR


class TestErrorMapping:
    """Tests for error mapping utilities."""

    def test_map_processing_error(self) -> None:
        """Test mapping ProcessingError to code."""
        exc = FileReadError("File not found")
        assert map_exception_to_code(exc) == ErrorCode.INVALID_INPUT

    def test_map_standard_exceptions(self) -> None:
        """Test mapping standard exceptions to codes."""
        assert map_exception_to_code(ValueError("test")) == ErrorCode.INVALID_INPUT
        assert map_exception_to_code(TypeError("test")) == ErrorCode.INVALID_INPUT
        assert map_exception_to_code(FileNotFoundError()) == ErrorCode.INVALID_INPUT

    def test_map_unknown_exception(self) -> None:
        """Test mapping unknown exception to INTERNAL_ERROR."""
        assert map_exception_to_code(Exception("test")) == ErrorCode.INTERNAL_ERROR

    def test_get_error_details_processing_error(self) -> None:
        """Test extracting details from ProcessingError."""
        exc = FileReadError("File not found", details={"path": "/test"})
        details = get_error_details(exc)
        assert details == {"path": "/test"}

    def test_get_error_details_jira_error_with_status(self) -> None:
        """Test extracting details from Jira error with status code."""
        exc = JiraAuthError("Auth failed", status_code=401, details={"email": "test@example.com"})
        details = get_error_details(exc)
        assert details["status_code"] == 401
        assert details["email"] == "test@example.com"

    def test_get_error_details_standard_exception(self) -> None:
        """Test extracting details from standard exception."""
        exc = ValueError("test")
        details = get_error_details(exc)
        assert details == {"exception_type": "ValueError"}

    def test_format_error_for_display(self) -> None:
        """Test formatting error for display."""
        exc = FileReadError("File not found")
        formatted = format_error_for_display(exc)
        assert "INVALID_INPUT (1001)" in formatted
        assert "File not found" in formatted

    def test_format_error_for_display_standard_exception(self) -> None:
        """Test formatting standard exception for display."""
        exc = ValueError("test")
        formatted = format_error_for_display(exc)
        assert formatted == "test"
