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

    def get_yes_no(
        self,
        prompt: str = "Do you want to continue? (yes/no): ",
        default: Optional[bool] = None,
        max_attempts: int = 3,
    ) -> bool:
        """Prompt the user for a yes/no answer.

        - Accepts y/yes and n/no (case-insensitive). Also accepts q/quit as no.
        - If `default` is provided and the user enters empty input, returns the default.
        - In non-interactive mode (no TTY), returns `default` if provided, else False.
        - On EOFError/KeyboardInterrupt, returns `default` if provided, else False.
        - Limits invalid attempts to `max_attempts` and then returns `default` if provided, else False.
        """
        attempts = 0
        while True:
            try:
                if not sys.stdin.isatty():
                    return default if default is not None else False
                response = self._input(prompt).strip().lower()
            except (EOFError, KeyboardInterrupt):
                return default if default is not None else False

            if not response and default is not None:
                return default

            if response in ("y", "yes"):
                return True
            if response in ("n", "no"):
                return False
            if response in ("q", "quit"):
                return False

            attempts += 1
            if attempts >= max_attempts:
                return default if default is not None else False
            self.show_message("Please enter 'yes' or 'no'.")

    def get_input(self, prompt: str = "Enter value: ") -> str:
        """Get raw input from the user. Returns empty string if interrupted."""
        try:
            if not sys.stdin.isatty():
                return ""
            return self._input(prompt)
        except (EOFError, KeyboardInterrupt):
            return ""

    def show_message(self, message: str) -> None:
        """Display a message to the user and optionally log it."""
        self._output(message)
        # Optionally mirror to logs; keep at info to avoid excessive noise when desired
        # self._logger.info(message)

    def show_error(self, message: str) -> None:
        """Display an error message to the user and log it."""
        self._error(f"Error: {message}")
        self._logger.error(message)

    def open_browser(self, url: str) -> bool:
        """Open a URL in the user's default browser. Returns True on success."""
        try:
            self._logger.debug("Opening URL in browser: %s", url)
            result = self._open(url, new=2)
            if not result:
                self._logger.warning("Failed to open URL in browser: %s", url)
            return bool(result)
        except Exception as exc:  # pylint: disable=broad-except
            # Keep broad except here to prevent UI crash due to platform/browser issues
            self._logger.exception("Exception while opening URL %s: %s", url, exc)
            return False
