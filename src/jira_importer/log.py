"""Description: This script contains the logging configuration for the Jira Importer.

Author:
    Julien (@tom4897)
"""

import logging
import os
import re
import sys
import time
from typing import Any

import colorlog

try:
    import colorama  # type: ignore

    colorama.init()  # Initialize colors on Windows terminals
except Exception:
    pass

from .utils import get_logs_directory

# Import sensitive terms from centralized constants
try:
    from .import_pipeline.cloud.constants import SENSITIVE_TERMS

    _SENSITIVE_TERMS = SENSITIVE_TERMS
except ImportError:
    # Fallback if import fails (shouldn't happen in normal operation)
    _SENSITIVE_TERMS = ("password", "api_token", "token", "secret", "client_secret", "access_token", "key", "auth")


class RedactingFilter(logging.Filter):
    """Filter that redacts obvious secrets in log records.

    This is a best-effort safety net; primary redaction should happen at the source.
    Uses regex patterns to identify and redact secret values in various formats.

    Email addresses are partially redacted: the local part (before @) is redacted
    while the domain is kept visible for debugging purposes.
    """

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        """Hide secrets so they don't show in the logs."""
        try:
            msg = str(record.getMessage())
            original_msg = msg
            lower = msg.lower()

            # Email address redaction: redact local part (before @), keep domain
            # Matches email addresses in various formats: user@domain.com, "user@domain.com", etc.
            email_pattern = re.compile(r"\b([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b", re.IGNORECASE)
            msg = email_pattern.sub(r"***@\2", msg)

            # Check if any sensitive terms are present
            if any(term in lower for term in _SENSITIVE_TERMS):
                # Pattern 1: key=value (e.g., "token=abc123", "api_token=xyz")
                for term in _SENSITIVE_TERMS:
                    # Match: term=value (value can contain alphanumeric, dash, underscore, dot)
                    pattern = re.compile(rf"\b{re.escape(term)}\s*=\s*([^\s,;)\]]+)", re.IGNORECASE)
                    msg = pattern.sub(rf"{term}=[REDACTED]", msg)

                # Pattern 2: JSON-like "key": "value" or 'key': 'value'
                for term in _SENSITIVE_TERMS:
                    # Match: "term": "value" or 'term': 'value'
                    pattern = re.compile(rf'["\']?{re.escape(term)}["\']?\s*:\s*["\']([^"\']+)["\']', re.IGNORECASE)
                    msg = pattern.sub(rf'"{term}": "[REDACTED]"', msg)

                # Pattern 3: key: value (colon format, no quotes)
                for term in _SENSITIVE_TERMS:
                    # Match: term: value (value until whitespace, comma, semicolon, or end)
                    pattern = re.compile(rf"\b{re.escape(term)}\s*:\s*([^\s,;)\]]+)", re.IGNORECASE)
                    msg = pattern.sub(rf"{term}: [REDACTED]", msg)

            # If message was modified, update the record
            if msg != original_msg:
                record.msg = "[REDACTED] " + msg
                record.args = ()
        except Exception:
            # Never block logging - if redaction fails, log the original message
            pass
        return True


# Format constants
CONSOLE_FORMAT = "%(log_color)s%(levelname)s%(reset)s %(asctime)s %(name)s: %(message)s"
PLAIN_FORMAT = "%(levelname)s %(asctime)s %(name)s: %(message)s"
FILE_FORMAT = "%(levelname)s %(asctime)s %(name)s: %(message)s"

# Date formats
CONSOLE_DATE = "%H:%M:%S"
FILE_DATE = "%Y-%m-%d %H:%M:%S"

# Color scheme
LOG_COLORS = {
    "DEBUG": "cyan",
    "INFO": "green",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "red,bg_white",
}

# Defaults
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_MAX_LOG_SIZE_MB = 10
DEFAULT_MAX_LOG_FILES = 5
DEFAULT_CONSOLE_OUTPUT = False
DEFAULT_WRITE_TO_FILE = True

_CONFIGURED = False


class LoggingConfig:
    """Simplified logging configuration management."""

    def __init__(self, level_override: int | None = None, config: Any | None = None):
        """Initialize logging configuration."""
        self.level_override = level_override
        self.config = config

        # Resolve level immediately
        self.level = self._resolve_level()

        # Check TTY support
        self.is_tty = hasattr(sys.stderr, "isatty") and sys.stderr.isatty()

        # Check if file logging is enabled
        # If config is None, use default (True) to ensure errors are logged
        if self.config is None:
            self.file_logging_enabled = DEFAULT_WRITE_TO_FILE
        else:
            self.file_logging_enabled = self.config.get_value(
                "app.logging.write_to_file", default=DEFAULT_WRITE_TO_FILE
            )

        # Check if console output is enabled
        self.console_output_enabled = (
            self.config.get_value("app.logging.console_output", default=DEFAULT_CONSOLE_OUTPUT)
            if self.config
            else DEFAULT_CONSOLE_OUTPUT
        )

    def _resolve_level(self) -> int:
        """Resolve log level with priority: CLI override > config level > default."""
        if self.level_override is not None:
            return self.level_override

        if self.config:
            config_level = self.config.get_value("app.logging.log_level", default=None)
            if config_level:
                try:
                    return getattr(logging, config_level.upper(), DEFAULT_LOG_LEVEL)
                except (AttributeError, TypeError):
                    pass

        return DEFAULT_LOG_LEVEL

    def get_file_settings(self) -> dict:
        """Get file logging settings from config."""
        if not self.file_logging_enabled:
            return {}

        # If config is None, return defaults
        if not self.config:
            return {
                "max_size_mb": DEFAULT_MAX_LOG_SIZE_MB,
                "max_log_files": DEFAULT_MAX_LOG_FILES,
            }

        return {
            "max_size_mb": self.config.get_value("app.logging.max_log_size_mb", default=DEFAULT_MAX_LOG_SIZE_MB),
            "max_log_files": self.config.get_value("app.logging.max_log_files", default=DEFAULT_MAX_LOG_FILES),
        }

    def validate_file_settings(self) -> list:
        """Validate file logging settings."""
        if not self.file_logging_enabled:
            return []

        settings = self.get_file_settings()
        errors = []

        if settings.get("max_size_mb", 0) <= 0:
            errors.append(f"Invalid max_log_size_mb: {settings['max_size_mb']} (must be > 0)")
        if settings.get("max_log_files", 0) < 0:
            errors.append(f"Invalid max_log_files: {settings['max_log_files']} (must be >= 0)")

        return errors


def _set_levels(level: int) -> None:
    """Set log level for root logger and all its handlers."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    for handler in root_logger.handlers:
        try:
            handler.setLevel(level)
        except Exception as e:
            logging.getLogger(__name__).warning(
                f"Failed to set level {level} for handler {type(handler).__name__}: {e}"
            )


def _create_console_handler(level: int, is_tty: bool) -> logging.Handler:
    """Create and configure console handler."""
    if is_tty:
        handler = colorlog.StreamHandler()
        formatter: logging.Formatter = colorlog.ColoredFormatter(
            CONSOLE_FORMAT, datefmt=CONSOLE_DATE, reset=True, log_colors=LOG_COLORS
        )
    else:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(PLAIN_FORMAT, datefmt=FILE_DATE)

    handler.setFormatter(formatter)
    handler.setLevel(level)
    return handler


def _setup_console_logging(level: int, is_tty: bool) -> None:
    """Setup console logging."""
    root_logger = logging.getLogger()

    # Clear existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create and add console handler
    console_handler = _create_console_handler(level, is_tty)
    console_handler.addFilter(RedactingFilter())
    root_logger.addHandler(console_handler)


def setup_logger(level_override: int | None = None, config: Any | None = None) -> None:
    """Setup the root logger with console output."""
    global _CONFIGURED  # pylint: disable=global-statement
    if _CONFIGURED:
        if level_override is not None:
            _set_levels(level_override)
        return

    logging_config = LoggingConfig(level_override, config)

    # Validate file logging settings
    if config:
        validation_errors = logging_config.validate_file_settings()
        if validation_errors:
            logging.getLogger(__name__).warning(f"File logging validation issues: {'; '.join(validation_errors)}")

    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging_config.level)

    # Setup console logging
    if logging_config.console_output_enabled:
        _setup_console_logging(logging_config.level, logging_config.is_tty)
    else:
        # Disable console output
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        root_logger.addHandler(logging.NullHandler())
        root_logger.propagate = False

    logging.captureWarnings(True)
    _CONFIGURED = True


def _create_file_handler(logging_config: LoggingConfig, level: int) -> logging.Handler:
    """Create and configure file handler for logging."""
    # Get log directory and create log file
    log_dir = get_logs_directory()
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"jira-toolkit_{timestamp}.log")

    # Get rotation settings
    settings = logging_config.get_file_settings()
    max_size_mb = settings.get("max_size_mb", DEFAULT_MAX_LOG_SIZE_MB)
    max_log_files = settings.get("max_log_files", DEFAULT_MAX_LOG_FILES)

    # Validate rotation settings
    if max_size_mb <= 0:
        raise ValueError(f"Invalid max_log_size_mb: {max_size_mb} (must be > 0)")
    if max_log_files < 0:
        raise ValueError(f"Invalid max_log_files: {max_log_files} (must be >= 0)")

    max_bytes = max_size_mb * 1024 * 1024

    # Create rotating file handler
    from logging.handlers import RotatingFileHandler  # pylint: disable=import-outside-toplevel

    file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=max_log_files, encoding="utf-8")
    file_formatter = logging.Formatter(FILE_FORMAT, datefmt=FILE_DATE)
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(level)

    return file_handler


def add_file_logging(config: Any):
    """Add file handler to existing root logger if enabled in config."""
    logging_config = LoggingConfig(config=config)

    if not logging_config.file_logging_enabled:
        return

    try:
        root_logger = logging.getLogger()

        # Remove existing file handlers to avoid duplicates
        from logging.handlers import RotatingFileHandler  # pylint: disable=import-outside-toplevel

        for handler in root_logger.handlers[:]:
            if isinstance(handler, RotatingFileHandler):
                root_logger.removeHandler(handler)
                handler.close()  # Properly close the old handler

        file_handler = _create_file_handler(logging_config, root_logger.level)
        file_handler.addFilter(RedactingFilter())
        root_logger.addHandler(file_handler)

        log_file = getattr(file_handler, "baseFilename", "unknown")
        root_logger.info(f"File logging enabled: {log_file}")

    except Exception as e:
        logging.getLogger().error(f"File logging setup failed: {e}")
