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
from typing import Optional
import colorlog
try:
    import colorama  # type: ignore
    colorama.init()  # Initialize colors on Windows terminals
except Exception:
    pass

from utils import resource_path

_CONFIGURED = False


def is_debug_mode() -> bool:
    debug_file_path = resource_path('.debug')
    debug_mode = os.path.isfile(debug_file_path)
    return debug_mode

def _env_log_level() -> Optional[int]:
    level_str = os.getenv('JTK_LOG_LEVEL', '').upper()
    if not level_str:
        return None
    level = getattr(logging, level_str, None)
    return level if isinstance(level, int) else None

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

    # Resolve desired level: env > .debug file > INFO
    # If a CLI or caller provided override, use it first
    level = level_override if level_override is not None else _env_log_level()
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