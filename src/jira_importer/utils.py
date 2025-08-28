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
import colorlog
from typing import Optional

from .console import ui, fmt

logger = logging.getLogger(__name__)

def resource_path(relative_path: str) -> str:
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)  # type: ignore
    return os.path.join(os.path.abspath("."), relative_path)
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


def find_config_path(config_filename: str, input_file_path: Optional[str] = None, config_default: bool = False, config_input: bool = False) -> str:
    search_paths = []

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
    return config_filename
