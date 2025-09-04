#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Logger manager for the Jira Importer build system.

Author: Julien (@tom4897)
License: MIT
Date: 2025
"""

import os
import sys
import logging
from datetime import datetime

BASE_LOG_DIR = "build/logs"
LOG_LEVEL = logging.DEBUG


class LoggerManager:
    def __init__(self, base_dir: str = BASE_LOG_DIR) -> None:
        self.base_dir = base_dir
        self.logger = None
        self._resolved_level = None
        self._is_tty = None
        self.setup()

    def _detect_tty(self) -> bool:
        """Detect if stderr supports TTY (colors)."""
        return hasattr(sys.stderr, 'isatty') and sys.stderr.isatty()

    def _resolve_level(self) -> int:
        """Resolve the log level from configuration or environment."""
        return LOG_LEVEL

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
            self._is_tty = self._detect_tty()
        return self._is_tty

    def setup(self) -> logging.Logger:
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")

        os.makedirs(self.base_dir, exist_ok=True)
        log_file = os.path.join(self.base_dir, f"{date_str}_build_jira_importer.log")

        root_logger = logging.getLogger()
        root_logger.setLevel(LOG_LEVEL)

        if root_logger.handlers:
            root_logger.handlers.clear()

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(LOG_LEVEL)
        file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(funcName)s:%(lineno)d %(message)s")
        file_handler.setFormatter(file_formatter)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(LOG_LEVEL)
        console_formatter = logging.Formatter("%(asctime)s %(message)s")
        console_handler.setFormatter(console_formatter)

        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        self.logger = logging.getLogger(__name__)
        return self.logger

    def get_logger(self) -> logging.Logger:
        if self.logger is None:
            return self.setup()
        return self.logger
