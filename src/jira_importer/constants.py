"""General-purpose constants shared across the Jira Toolkit codebase.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

from typing import Final

# Filesystem/path validation limits
ASCII_CONTROL_MAX: Final[int] = 31
MAX_RELATIVE_PATH_LEN: Final[int] = 4096

# Credentials CLI actions
CREDENTIALS_ACTIONS: Final[list[str]] = ["run", "show", "clear", "test"]
CREDENTIALS_ACTION_RUN: Final[str] = "run"
CREDENTIALS_ACTION_SHOW: Final[str] = "show"
CREDENTIALS_ACTION_CLEAR: Final[str] = "clear"
CREDENTIALS_ACTION_TEST: Final[str] = "test"
