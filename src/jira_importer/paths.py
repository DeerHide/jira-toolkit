"""Path helpers for executable and logs directory (stdlib only).

Kept separate so logging can use get_logs_directory without pulling in
heavy dependencies (excel, console). Re-exported from utils for backward compatibility.

Author:
    Julien (@tom4897)
"""

from __future__ import annotations

import os
import sys


def get_executable_dir() -> str:
    """Return the directory where the script or compiled executable resides."""
    if getattr(sys, "frozen", False):
        # Running as a PyInstaller bundle
        exe_dir = os.path.dirname(sys.executable)
    else:
        # Running from source
        exe_dir = os.path.dirname(os.path.abspath(__file__))
    return exe_dir


def get_logs_directory() -> str:
    """Get or create the logs directory next to the executable or script."""
    exe_dir = get_executable_dir()
    logs_dir = os.path.join(exe_dir, "jira_importer_logs")

    try:
        os.makedirs(logs_dir, exist_ok=True)
        return logs_dir
    except (PermissionError, OSError):
        import tempfile  # pylint: disable=import-outside-toplevel

        temp_logs_dir = os.path.join(tempfile.gettempdir(), "jira-toolkit", "logs")
        os.makedirs(temp_logs_dir, exist_ok=True)
        return temp_logs_dir
