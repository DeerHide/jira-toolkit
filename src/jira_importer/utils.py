#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script Name: utils.py
Description: This script contains utility functions for the Jira Importer.
Author: Julien (@tom4897)
License: MIT
Date: 2025
"""

import logging
import sys
import os
import webbrowser
import colorlog
from typing import Optional

from .console import ConsoleIO

logger = logging.getLogger(__name__)
ui = ConsoleIO.getUI()
fmt = ui.fmt

def resource_path(relative_path: str) -> str:
    """Resolve a resource path robustly across frozen and non-frozen runs.

    - In PyInstaller (frozen), load from the temporary extraction dir (sys._MEIPASS).
    - Otherwise, prefer the current working directory, but fall back safely if CWD is invalid.
    """
    # PyInstaller onefile/onedir extraction directory
    if hasattr(sys, '_MEIPASS'):
        try:
            return os.path.join(sys._MEIPASS, relative_path)  # type: ignore[attr-defined]
        except Exception:
            # As a last resort, use the executable directory
            base_dir = os.path.dirname(sys.executable)
            return os.path.join(base_dir, relative_path)

    # Non-frozen: try current working directory first
    try:
        cwd = os.getcwd()
        return os.path.join(cwd, relative_path)
    except Exception:
        # If CWD is invalid (e.g., deleted), fall back to the module directory
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, relative_path)
# Usage: config_path = resource_path('config_importer.json')

def get_logs_directory() -> str:
    """Get or create the logs directory in the executable's location."""
    # Get the directory where the executable/script is located
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller executable
        exe_dir = sys._MEIPASS
    else:
        # Regular Python script - use the directory containing the script
        exe_dir = os.path.dirname(os.path.abspath(__file__))

    logs_dir = os.path.join(exe_dir, 'jira_importer_logs')
    try:
        logger.debug(f"Creating logs directory in executable location: {logs_dir}")
        os.makedirs(logs_dir, exist_ok=True)
        return logs_dir
    except (PermissionError, OSError) as e:
        # Fallback to temp directory if we can't create logs dir
        import tempfile
        ui.error(f"Could not create logs directory in executable location: {e}")
        logger.debug(f"Could not create logs directory in executable location: {e}")
        temp_logs_dir = os.path.join(tempfile.gettempdir(), 'jira-toolkit', 'logs')
        os.makedirs(temp_logs_dir, exist_ok=True)
        return temp_logs_dir


def find_config_path(config_filename: str, input_file_path: Optional[str] = None, config_default: bool = False, config_input: bool = False, config_specific: bool = False) -> str:
    search_paths = []

    # If config_specific is True (when -c is used), only try the exact path provided
    if config_specific:
        # Check if it's an absolute path
        if os.path.isabs(config_filename):
            search_paths.append(config_filename)
        else:
            # For relative paths, try relative to current working directory
            search_paths.append(os.path.abspath(config_filename))

        logger.debug(f"Specific config path provided, searching only in: {search_paths}")
        for path in search_paths:
            if os.path.isfile(path):
                logger.debug(f"Found configuration file: {path}")
                return path

        # If not found, return the original path (let the caller handle the error)
        fmt_config_filename = fmt.path(config_filename)
        ui.error(f"Configuration file '{fmt_config_filename}' not found.")
        logger.warning(f"Configuration file '{config_filename}' not found.")
        return config_filename

    # Original logic for other cases (config_default, config_input, etc.)
    # First, check if the config_filename is an absolute path or relative to current working directory
    if os.path.isabs(config_filename) or os.path.isfile(config_filename):
        search_paths.append(config_filename)

    if config_input:
        if input_file_path:
            search_paths.append(os.path.join(os.path.dirname(os.path.abspath(input_file_path)), config_filename))
        else:
            logger.warning("config-input: wrong usage")
            return config_filename
    elif config_default:
        search_paths.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), config_filename))
    else:
        if input_file_path:
            search_paths.append(os.path.join(os.path.dirname(os.path.abspath(input_file_path)), config_filename))
        search_paths.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), config_filename))

    logger.debug(f"Searching for configuration file in: {search_paths}")
    for path in search_paths:
        if os.path.isfile(path):
            logger.debug(f"Found configuration file: {path}")
            return path

    fmt_config_filename = fmt.path(config_filename)
    ui.error(f"Configuration file '{fmt_config_filename}' not found in expected locations. Using default path.")
    logger.warning(f"Configuration file '{config_filename}' not found in expected locations. Using default path.")
    logger.warning(f"Expected locations: {search_paths}")
    ui.error(f"Expected locations: {search_paths}")
    return config_filename


def open_browser(url: str, logger_ref: Optional[logging.Logger] = None) -> bool:
    """Open a URL in the user's default browser. Returns True on success."""
    logger = logger_ref or logging.getLogger(__name__)
    try:
        logger.debug("Opening URL in browser: %s", url)
        result = webbrowser.open(url, new=2)
        if not result:
            logger.warning("Failed to open URL in browser: %s", url)
        return bool(result)
    except Exception as e:  # pylint: disable=broad-except
        # Keep broad except here to prevent UI crash due to platform/browser issues
        ui.error(f"Failed to open URL in browser: {url}")
        logger.exception("Exception while opening URL %s: %s", url, e)
        return False
