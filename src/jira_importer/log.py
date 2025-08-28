#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script Name: log.py
Description: This script contains the logging configuration for the Jira Importer.
Author: Julien (@tom4897)
License: MIT
Date: 2025
"""

import logging
import os
import sys
import time
from typing import Optional, Any
import colorlog
try:
    import colorama  # type: ignore
    colorama.init()  # Initialize colors on Windows terminals
except Exception:
    pass

from .utils import resource_path, get_logs_directory

# Logging format constants
CONSOLE_FORMAT_TTY = "%(log_color)s%(levelname)s%(reset)s %(asctime)s %(name)s: %(message)s"
CONSOLE_FORMAT_PLAIN = "%(levelname)s %(asctime)s %(name)s: %(message)s"
FILE_FORMAT = "%(levelname)s %(asctime)s %(name)s: %(message)s"

# Date format constants
CONSOLE_DATE_TTY = "%H:%M:%S"
CONSOLE_DATE_PLAIN = "%Y-%m-%d %H:%M:%S"
FILE_DATE = "%Y-%m-%d %H:%M:%S"

# Color scheme for TTY output
LOG_COLORS = {
    'DEBUG': 'cyan',
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'red,bg_white',
}

# Default values
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_DEBUG_LEVEL = logging.DEBUG

# File logging defaults
DEFAULT_MAX_LOG_SIZE_MB = 10
DEFAULT_MAX_LOG_FILES = 5

# Console logging defaults
DEFAULT_CONSOLE_OUTPUT = False

_CONFIGURED = False


class LoggingConfig:
    """
    Centralized logging configuration management.

    This class handles all aspects of logging configuration including
    level resolution, TTY detection, and file logging settings.
    """

    def __init__(self, level_override: Optional[int] = None, config: Optional[Any] = None):
        """
        Initialize logging configuration.

        Args:
            level_override: Optional CLI override level
            config: Optional configuration object for file logging
        """
        self.level_override = level_override
        self.config = config
        self._resolved_level = None
        self._is_tty = None
        self._file_logging_enabled = None
        self._file_settings = None

    @property
    def level(self) -> int:
        """Get the resolved log level with proper priority."""
        if self._resolved_level is None:
            self._resolved_level = self._resolve_level()
        return self._resolved_level

    @property
    def is_tty(self) -> bool:
        """Check if terminal supports colors."""
        if self._is_tty is None:
            self._is_tty = _detect_tty()
        return self._is_tty

    @property
    def file_logging_enabled(self) -> bool:
        """Check if file logging is enabled in config."""
        if self._file_logging_enabled is None:
            self._file_logging_enabled = (
                self.config and
                self.config.get_value('app.logging.write_to_file', default=False)
            )
        return self._file_logging_enabled

    @property
    def console_output_enabled(self) -> bool:
        """Check if console output is enabled in config."""
        if self.config:
            return self.config.get_value('app.logging.console_output', default=DEFAULT_CONSOLE_OUTPUT)
        return DEFAULT_CONSOLE_OUTPUT

    @property
    def file_settings(self) -> dict:
        """Get file logging settings from config."""
        if self._file_settings is None:
            if not self.file_logging_enabled:
                self._file_settings = {}
            else:
                self._file_settings = {
                    'max_size_mb': self.config.get_value('app.logging.max_log_size_mb', default=DEFAULT_MAX_LOG_SIZE_MB),
                    'max_log_files': self.config.get_value('app.logging.max_log_files', default=DEFAULT_MAX_LOG_FILES),
                    'log_level': self.config.get_value('app.logging.log_level', default=None)
                }
        return self._file_settings

    def _resolve_level(self) -> int:
        """
        Resolve the desired log level with proper priority.

        Priority: CLI override > config level > .debug file > INFO

        Returns:
            Resolved log level
        """
        # CLI override takes highest priority
        if self.level_override is not None:
            return self.level_override

        # Check config level if available
        if self.config:
            config_level = self.config.get_value('app.logging.log_level', default=None)
            if config_level:
                try:
                    resolved = getattr(logging, config_level.upper(), None)
                    if resolved is not None:
                        return resolved
                except (AttributeError, TypeError):
                    pass  # Invalid level, fall through

        # Check debug file
        if is_debug_mode():
            return DEFAULT_DEBUG_LEVEL

        # Default level
        return DEFAULT_LOG_LEVEL

    def validate_file_settings(self) -> list:
        """
        Validate file logging settings and return any issues.

        Returns:
            List of validation error messages (empty if valid)
        """
        if not self.file_logging_enabled:
            return []

        errors = []
        settings = self.file_settings

        if settings.get('max_size_mb', 0) <= 0:
            errors.append(f"Invalid max_log_size_mb: {settings['max_size_mb']} (must be > 0)")

        if settings.get('max_log_files', 0) < 0:
            errors.append(f"Invalid max_log_files: {settings['max_log_files']} (must be >= 0)")

        return errors


def is_debug_mode() -> bool:
    """Check if debug mode is enabled via .debug file."""
    debug_file_path = resource_path('.debug')
    return os.path.isfile(debug_file_path)


def _set_levels(level: int) -> None:
    """Set log level for root logger and all its handlers."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    for handler in root_logger.handlers:
        try:
            handler.setLevel(level)
        except Exception as e:
            # Log the error but don't fail - some handlers might not support level changes
            logging.getLogger(__name__).warning(f"Failed to set level {level} for handler {type(handler).__name__}: {e}")


def _create_console_handler(level: int, is_tty: bool) -> logging.Handler:
    """
    Create and configure console handler based on TTY availability.

    Args:
        level: Log level for the handler
        is_tty: Whether terminal supports colors

    Returns:
        Configured console handler

    Raises:
        RuntimeError: If handler creation fails
    """
    try:
        if is_tty:
            handler = colorlog.StreamHandler()
            formatter = colorlog.ColoredFormatter(
                CONSOLE_FORMAT_TTY,
                datefmt=CONSOLE_DATE_TTY,
                reset=True,
                log_colors=LOG_COLORS
            )
        else:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                CONSOLE_FORMAT_PLAIN,
                datefmt=CONSOLE_DATE_PLAIN
            )

        handler.setFormatter(formatter)
        handler.setLevel(level)
        return handler

    except Exception as e:
        error_msg = f"Failed to create console handler (TTY: {is_tty}, level: {level}): {e}"
        raise RuntimeError(error_msg) from e


def _detect_tty() -> bool:
    """Detect if stderr supports TTY (colors)."""
    return hasattr(sys.stderr, 'isatty') and sys.stderr.isatty()


def _resolve_log_level(level_override: Optional[int] = None) -> int:
    """
    Resolve the desired log level with proper priority.

    Priority: CLI override > .debug file > INFO

    Args:
        level_override: Optional CLI override level

    Returns:
        Resolved log level
    """
    if level_override is not None:
        return level_override

    if is_debug_mode():
        return DEFAULT_DEBUG_LEVEL

    return DEFAULT_LOG_LEVEL


def set_log_level(level: int) -> None:
    """Dynamically adjust root logger and handler levels."""
    _set_levels(level)


def _is_duplicate_handler(handler: logging.Handler, existing_handlers: list) -> bool:
    """
    Check if a handler is a duplicate of existing handlers.

    Args:
        handler: Handler to check
        existing_handlers: List of existing handlers

    Returns:
        True if duplicate, False otherwise
    """
    handler_signature = (type(handler), getattr(getattr(handler, 'formatter', None), "_fmt", None))

    for existing_handler in existing_handlers:
        existing_signature = (type(existing_handler), getattr(getattr(existing_handler, 'formatter', None), "_fmt", None))
        if handler_signature == existing_signature:
            return True

    return False


def _setup_console_logging(level: int) -> None:
    """
    Setup console logging with proper handler management.

    Args:
        level: Log level for console output

    Note:
        If console handler creation fails, logging will fall back to basic setup.
    """
    root_logger = logging.getLogger()
    is_tty = _detect_tty()

    try:
        # Create console handler
        console_handler = _create_console_handler(level, is_tty)

        # Avoid duplicate handlers
        if not _is_duplicate_handler(console_handler, root_logger.handlers):
            root_logger.addHandler(console_handler)

    except Exception as e:
        # Fall back to basic console handler if colored handler fails
        logging.getLogger(__name__).warning(f"Console handler creation failed, using fallback: {e}")

        try:
            fallback_handler = logging.StreamHandler()
            fallback_formatter = logging.Formatter(
                CONSOLE_FORMAT_PLAIN,
                datefmt=CONSOLE_DATE_PLAIN
            )
            fallback_handler.setFormatter(fallback_formatter)
            fallback_handler.setLevel(level)

            if not _is_duplicate_handler(fallback_handler, root_logger.handlers):
                root_logger.addHandler(fallback_handler)

        except Exception as fallback_error:
            logging.getLogger(__name__).error(f"Fallback console handler also failed: {fallback_error}")
            # At this point, we have no console output, but we shouldn't crash the app


def setup_logger(level_override: Optional[int] = None, config: Optional[Any] = None) -> None:
    """
    Setup the root logger with console output.

    Args:
        level_override: Optional log level override (e.g., logging.DEBUG from CLI)
        config: Optional configuration object for additional settings

    Note:
        This function can only be called once. Subsequent calls with level_override
        will only adjust the log level, not reconfigure handlers.
    """
    global _CONFIGURED
    if _CONFIGURED:
        # Allow raising/lowering level after initial setup
        if level_override is not None:
            _set_levels(level_override)
        return

    # Create logging configuration
    logging_config = LoggingConfig(level_override, config)

    # Validate file logging settings if config is provided
    if config:
        validation_errors = logging_config.validate_file_settings()
        if validation_errors:
            logging.getLogger(__name__).warning(f"File logging validation issues: {'; '.join(validation_errors)}")

    # Setup root logger with resolved level
    root_logger = logging.getLogger()
    root_logger.setLevel(logging_config.level)

    # Setup console logging
    if logging_config.console_output_enabled:
        _setup_console_logging(logging_config.level)
    else:
        # Remove all existing handlers to prevent any console output
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Add a null handler to prevent default stderr output
        from logging import NullHandler
        root_logger.addHandler(NullHandler())

        # Set propagate to False for all loggers to prevent inheritance
        # This ensures child loggers don't output to the root logger's handlers
        logging.getLogger().propagate = False

    # Capture warnings via logging
    logging.captureWarnings(True)
    _CONFIGURED = True


def _create_file_handler_from_config(logging_config: LoggingConfig, level: int) -> logging.Handler:
    """
    Create and configure file handler using LoggingConfig.

    Args:
        logging_config: LoggingConfig instance with file settings
        level: Log level for the file handler

    Returns:
        Configured rotating file handler

    Raises:
        OSError: If log directory cannot be created or accessed
        ValueError: If rotation settings are invalid
        RuntimeError: If file handler creation fails
    """
    try:
        # Get log directory and create log file
        log_dir = get_logs_directory()
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"jira-toolkit_{timestamp}.log")

        # Get rotation settings from config
        settings = logging_config.file_settings
        max_size_mb = settings.get('max_size_mb', DEFAULT_MAX_LOG_SIZE_MB)
        max_log_files = settings.get('max_log_files', DEFAULT_MAX_LOG_FILES)

        # Validate rotation settings
        if max_size_mb <= 0:
            raise ValueError(f"Invalid max_log_size_mb: {max_size_mb} (must be > 0)")
        if max_log_files < 0:
            raise ValueError(f"Invalid max_log_files: {max_log_files} (must be >= 0)")

        max_bytes = max_size_mb * 1024 * 1024

        # Create rotating file handler
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=max_log_files,
            encoding='utf-8'
        )

        # Use same formatter as console (but without colors)
        file_formatter = logging.Formatter(
            FILE_FORMAT,
            datefmt=FILE_DATE
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(level)

        return file_handler

    except (OSError, ValueError) as e:
        # Re-raise these specific errors as-is
        raise
    except Exception as e:
        # Wrap other errors with context
        error_msg = f"Failed to create file handler: {e}"
        raise RuntimeError(error_msg) from e


def _create_file_handler(config: Any, level: int) -> logging.Handler:
    """
    Create and configure file handler for logging.

    Args:
        config: Configuration object with logging settings
        level: Log level for the file handler

    Returns:
        Configured rotating file handler

    Raises:
        OSError: If log directory cannot be created or accessed
        ValueError: If rotation settings are invalid
        RuntimeError: If file handler creation fails
    """
    try:
        # Get log directory and create log file
        log_dir = get_logs_directory()
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"jira-toolkit_{timestamp}.log")

        # Get rotation settings from config
        max_size_mb = config.get_value('app.logging.max_log_size_mb', default=DEFAULT_MAX_LOG_SIZE_MB)
        max_log_files = config.get_value('app.logging.max_log_files', default=DEFAULT_MAX_LOG_FILES)

        # Validate rotation settings
        if max_size_mb <= 0:
            raise ValueError(f"Invalid max_log_size_mb: {max_size_mb} (must be > 0)")
        if max_log_files < 0:
            raise ValueError(f"Invalid max_log_files: {max_log_files} (must be >= 0)")

        max_bytes = max_size_mb * 1024 * 1024

        # Create rotating file handler
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=max_log_files,
            encoding='utf-8'
        )

        # Use same formatter as console (but without colors)
        file_formatter = logging.Formatter(
            FILE_FORMAT,
            datefmt=FILE_DATE
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(level)

        return file_handler

    except (OSError, ValueError) as e:
        # Re-raise these specific errors as-is
        raise
    except Exception as e:
        # Wrap other errors with context
        error_msg = f"Failed to create file handler: {e}"
        raise RuntimeError(error_msg) from e


def add_file_logging(config: Any):
    """
    Add file handler to existing root logger if enabled in config.

    Args:
        config: Configuration object that may contain logging settings

    Note:
        This function should be called after setup_logger() has been called.
        It will add a rotating file handler to the existing root logger.
    """
    # Create logging configuration for validation
    logging_config = LoggingConfig(config=config)

    if not logging_config.file_logging_enabled:
        return

    try:
        # Get current root logger level
        root_logger = logging.getLogger()
        level = root_logger.level

        # Create and add file handler using config settings
        file_handler = _create_file_handler_from_config(logging_config, level)
        root_logger.addHandler(file_handler)

        # Log that file logging is enabled
        log_file = file_handler.baseFilename
        root_logger.info(f"File logging enabled: {log_file}")

    except (OSError, ValueError) as e:
        # Log specific errors with context
        logging.getLogger().warning(f"File logging setup failed (config error): {e}")
    except RuntimeError as e:
        # Log runtime errors with context
        logging.getLogger().warning(f"File logging setup failed (runtime): {e}")
    except Exception as e:
        # Log unexpected errors
        logging.getLogger().warning(f"File logging setup failed (unexpected): {e}")
