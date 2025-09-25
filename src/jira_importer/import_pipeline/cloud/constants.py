"""Constants for Jira Cloud HTTP client behavior and defaults.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

from typing import Final

# Default headers
DEFAULT_HEADERS: Final[dict[str, str]] = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}

# HTTP status codes and ranges
HTTP_SUCCESS_MIN: Final[int] = 200
HTTP_SUCCESS_MAX: Final[int] = 299

HTTP_SERVER_ERROR_MIN: Final[int] = 500
HTTP_SERVER_ERROR_MAX: Final[int] = 599

STATUS_TOO_MANY_REQUESTS: Final[int] = 429
STATUS_BAD_REQUEST: Final[int] = 400
HTTP_ERROR_THRESHOLD: Final[int] = 400

# Retry/backoff configuration
RETRY_MAX_ATTEMPTS: Final[int] = 3
BACKOFF_INITIAL_SECONDS: Final[float] = 1.0
BACKOFF_MULTIPLIER: Final[float] = 2.0
BACKOFF_MAX_SECONDS: Final[float] = 16.0

# Bulk operation configuration
BATCH_SIZE: Final[int] = 50

# Jira key validation
JIRA_KEY_PARTS_COUNT: Final[int] = 2

# Parent resolution keywords for logical parent finding
PARENT_RESOLUTION_KEYWORDS: Final[list[str]] = [
    "authentication",
    "security",
    "project",
    "field",
    "discovery",
    "data validation",
    "mapping",
    "import process",
    "error handling",
    "recovery",
    "integration",
    "workflow",
    "validation",
    "performance",
]
