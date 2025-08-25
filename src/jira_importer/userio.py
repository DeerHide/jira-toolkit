#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script Name: userio.py
Description: This script manages the user interactions for the Jira Importer.
Author: Julien (@tom4897)
License: MIT
Date: 2025
"""

import logging
import sys
import webbrowser
from typing import Callable, Optional
from console import ui, fmt
logger = logging.getLogger(__name__)

class UserIO:
    """
    Simple IO abstraction for user interaction with improved testability and robustness.

    Instance-based with injectable dependencies to allow easy mocking in tests and
    safer behavior in non-interactive environments.
    """

    def __init__(
        self,
        input_func: Callable[[str], str] = input,
        output_func: Callable[[str], None] = print,
        error_func: Optional[Callable[[str], None]] = None,
        opener: Callable[..., bool] = webbrowser.open,
        logger_ref: Optional[logging.Logger] = None,
    ) -> None:
        self._input: Callable[[str], str] = input_func
        self._output: Callable[[str], None] = output_func
        self._error: Callable[[str], None] = (
            error_func if error_func is not None else (lambda msg: print(msg, file=sys.stderr))
        )
        self._open: Callable[..., bool] = opener
        self._logger: logging.Logger = logger_ref or logging.getLogger(__name__)

    def open_browser(self, url: str) -> bool:
        """Open a URL in the user's default browser. Returns True on success."""
        try:
            self._logger.debug("Opening URL in browser: %s", url)
            result = self._open(url, new=2)
            if not result:
                self._logger.warning("Failed to open URL in browser: %s", url)
            return bool(result)
        except Exception as e:  # pylint: disable=broad-except
            # Keep broad except here to prevent UI crash due to platform/browser issues
            self._logger.exception("Exception while opening URL %s: %s", url, e)
            return False
