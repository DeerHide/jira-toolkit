"""Map Jira Cloud bulk API errors to normalized error objects.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

from typing import Any

from ..models import CloudBulkIssueError


def resolve_bulk_error_context(
    raw_error: dict[str, Any] | str,
    *,
    batch_context: list[tuple[int, dict[str, Any]]],
) -> CloudBulkIssueError:
    """Normalize one Jira bulk API error and add row/summary context."""
    if not isinstance(raw_error, dict):
        return CloudBulkIssueError(raw=str(raw_error))

    status = raw_error.get("status")
    failed_element_number = raw_error.get("failedElementNumber")
    element_errors = raw_error.get("elementErrors", {})
    error_messages = tuple(str(msg) for msg in element_errors.get("errorMessages", []))
    field_errors_raw = element_errors.get("errors", {})
    field_errors: dict[str, str] = {}
    if isinstance(field_errors_raw, dict):
        field_errors = {str(key): str(val) for key, val in field_errors_raw.items()}

    failed_summary = None
    failed_row_index = None
    if isinstance(failed_element_number, int):
        # Jira usually reports failedElementNumber as index in the batch.
        for candidate in (failed_element_number, failed_element_number - 1):
            if 0 <= candidate < len(batch_context):
                row_idx, payload_ctx = batch_context[candidate]
                failed_row_index = row_idx
                failed_summary_value = payload_ctx.get("fields", {}).get("summary")
                if isinstance(failed_summary_value, str) and failed_summary_value.strip():
                    failed_summary = failed_summary_value
                break

    return CloudBulkIssueError(
        status=status,
        failed_element_number=failed_element_number,
        failed_row_index=failed_row_index,
        failed_summary=failed_summary,
        error_messages=error_messages,
        field_errors=field_errors,
        raw=raw_error,
    )
