"""Error response models and helpers.

Author:
    Julien (@tom4897)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .base import ProcessingError
from .codes import ErrorCode
from .utils import get_error_details, map_exception_to_code


@dataclass(slots=True)
class ErrorResponse:
    """Structured error response model shared by CLI and integrations.

    This model is intentionally transport-agnostic so it can be reused by:
      - The CLI (for programmatic callers that want structured errors)
      - The MCP server (for mapping domain errors to protocol errors)

    Attributes:
        code: Stable domain error code.
        message: Human-facing error message.
        details: Optional structured details (safe to log/return).
        request_id: Optional upstream request identifier, if available.
        timestamp: Optional ISO 8601 timestamp in UTC.
    """

    code: ErrorCode
    message: str
    details: dict[str, Any] | None = None
    request_id: str | None = None
    timestamp: str | None = None


def _utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(UTC).isoformat()


def error_response_from_exception(
    exc: Exception,
    *,
    include_timestamp: bool = True,
) -> ErrorResponse:
    """Build an ErrorResponse from an exception.

    Args:
        exc: Exception to convert.
        include_timestamp: Whether to attach the current UTC timestamp.

    Returns:
        ErrorResponse populated from the exception.
    """
    code = map_exception_to_code(exc)

    if isinstance(exc, ProcessingError):
        message = exc.message
    else:
        message = str(exc)

    details = get_error_details(exc)

    return ErrorResponse(
        code=code,
        message=message,
        details=details or None,
        timestamp=_utc_now_iso() if include_timestamp else None,
    )


def error_response_from_http(
    status_code: int,
    response: Any | None = None,
    *,
    include_timestamp: bool = True,
) -> ErrorResponse:
    """Build an ErrorResponse for an HTTP failure.

    This helper does not depend on the concrete HTTP client type; it only
    relies on duck-typed attributes commonly provided by response objects
    (e.g. 'url', 'reason', 'text', 'json()').

    Args:
        status_code: HTTP status code returned by the upstream service.
        response: Optional HTTP response object (e.g. requests.Response).
        include_timestamp: Whether to attach the current UTC timestamp.

    Returns:
        ErrorResponse representing the HTTP failure.
    """
    if status_code in (401, 403):
        code = ErrorCode.JIRA_AUTH_ERROR
    elif 400 <= status_code <= 599:
        code = ErrorCode.JIRA_API_ERROR
    else:
        code = ErrorCode.INTERNAL_ERROR

    # Default message; may be enriched below with reason or response text.
    message = f"HTTP {status_code} error from upstream service"

    details: dict[str, Any] = {"status_code": status_code}

    if response is not None:
        url = getattr(response, "url", None)
        reason = getattr(response, "reason", None)
        text = getattr(response, "text", None)

        if url:
            details["url"] = url
        if reason:
            details["reason"] = reason

        # Try to extract structured error information when available.
        json_payload: dict[str, Any] | None = None
        try:
            json_method = getattr(response, "json", None)
            if callable(json_method):
                json_payload = json_method()
        except Exception:  # pragma: no cover - best-effort only
            json_payload = None

        if isinstance(json_payload, dict):
            error_messages = json_payload.get("errorMessages")
            field_errors = json_payload.get("errors")
            if error_messages:
                details["errorMessages"] = error_messages
                # Prefer a more specific message when we have errorMessages.
                if isinstance(error_messages, list) and error_messages:
                    message = error_messages[0]
            if field_errors:
                details["fieldErrors"] = field_errors
        elif text and isinstance(text, str):
            # Fallback to a truncated text body to avoid massive logs.
            details["body"] = text[:500]

    return ErrorResponse(
        code=code,
        message=message,
        details=details or None,
        timestamp=_utc_now_iso() if include_timestamp else None,
    )
