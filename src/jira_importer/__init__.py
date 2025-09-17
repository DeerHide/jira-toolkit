"""Jira Importer package.

Lightweight metadata and constants only. Avoid heavy imports or side effects
at import time to keep startup fast for downstream users.
"""

from __future__ import annotations

# Package metadata
__author__ = "DeerHide"
__description__ = "Toolkit to process datasets into Jira-compatible CSVs with validation and reporting."

# Safe constants used across the app
DEFAULT_CONFIG_FILENAME = "config_importer.json"
CFG_REQ_DEFAULT = 1  # Minimal config requirement level for leniency in basic ops

# Version surface: derive a simple PEP 440-ish string from the generated version module
try:
    from .version import __build_number__, __version_info__

    # Example: 0.1.0+build.43 (branch/rev available via module attrs if needed)
    __version__ = ".".join(str(x) for x in __version_info__[:3]) + f"+build.{__build_number__}"
except Exception:  # pragma: no cover - tolerate missing/partial version during dev
    __version__ = "0.0.0"

__all__ = [
    "CFG_REQ_DEFAULT",
    "DEFAULT_CONFIG_FILENAME",
    "__author__",
    "__description__",
    "__version__",
]
