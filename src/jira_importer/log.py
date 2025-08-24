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
from typing import Optional
import colorlog
try:
    import colorama  # type: ignore
    colorama.init()  # Initialize colors on Windows terminals
except Exception:
    pass

from utils import resource_path, get_logs_directory

_CONFIGURED = False


def is_debug_mode() -> bool:
    debug_file_path = resource_path('.debug')
    debug_mode = os.path.isfile(debug_file_path)
    return debug_mode





def _set_levels(level: int) -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    for handler in root_logger.handlers:
        try:
            handler.setLevel(level)
        except Exception:
            pass


def set_log_level(level: int) -> None:
    """Dynamically adjust root logger and handler levels."""
    _set_levels(level)


def setup_logger(level_override: Optional[int] = None) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        # Allow raising/lowering level after initial setup
        if level_override is not None:
            _set_levels(level_override)
        return

    # Resolve desired level: CLI override > .debug file > INFO
    level = level_override if level_override is not None else None
    if level is None:
        level = logging.DEBUG if is_debug_mode() else logging.INFO

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Console handler: colored if TTY, else plain
    is_tty = hasattr(sys.stderr, 'isatty') and sys.stderr.isatty()
    if is_tty:
        handler = colorlog.StreamHandler()
        formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(levelname)s%(reset)s %(asctime)s %(name)s: %(message)s",
            datefmt="%H:%M:%S",
            reset=True,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
    else:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(levelname)s %(asctime)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    handler.setFormatter(formatter)
    handler.setLevel(level)

    # Avoid duplicate handlers if something similar is already attached
    existing_signatures = {
        (type(h), getattr(getattr(h, 'formatter', None), "_fmt", None)) for h in root_logger.handlers
    }
    signature = (type(handler), getattr(formatter, "_fmt", None))
    if signature not in existing_signatures:
        root_logger.addHandler(handler)

    # Capture warnings via logging
    logging.captureWarnings(True)
    _CONFIGURED = True


def add_file_logging(config):
    """Add file handler to existing root logger if enabled in config."""
    if not config or not config.get_value('app.logging.write_to_file', default=False):
        return

    try:
        # Get log directory and create log file
        log_dir = get_logs_directory()
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"jira-toolkit_{timestamp}.log")

        # Get rotation settings from config
        max_bytes = config.get_value('app.logging.max_log_size_mb', default=10) * 1024 * 1024
        max_log_files = config.get_value('app.logging.max_log_files', default=5)

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
            "%(levelname)s %(asctime)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)

        # Use same level as root logger
        root_logger = logging.getLogger()
        file_handler.setLevel(root_logger.level)

        # Add file handler to root logger
        root_logger.addHandler(file_handler)

        # Log that file logging is enabled
        root_logger.info(f"File logging enabled: {log_file}")

    except Exception as e:
        # Don't fail if file logging can't be set up
        logging.getLogger().warning(f"Failed to setup file logging: {e}")
