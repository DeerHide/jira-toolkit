"""General-purpose constants shared across the Jira Toolkit codebase.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

from typing import Final

# Filesystem/path validation limits
ASCII_CONTROL_MAX: Final[int] = 31
MAX_RELATIVE_PATH_LEN: Final[int] = 4096
