"""Tests for Jira Cloud bulk error mapping."""

from __future__ import annotations

from jira_importer.import_pipeline.cloud.error_mapper import resolve_bulk_error_context


class TestErrorMapper:
    """Tests for resolve_bulk_error_context()."""

    def test_resolve_bulk_error_context_includes_summary_and_row(self) -> None:
        """Map failed element to source row context."""
        raw_error = {
            "status": 400,
            "failedElementNumber": 1,
            "elementErrors": {"errorMessages": [], "errors": {"priority": "invalid"}},
        }
        batch_context = [
            (10, {"fields": {"summary": "First"}}),
            (25, {"fields": {"summary": "Failed summary"}}),
        ]

        mapped = resolve_bulk_error_context(raw_error, batch_context=batch_context)

        assert mapped.status == 400
        assert mapped.failed_element_number == 1
        assert mapped.failed_row_index == 25
        assert mapped.failed_summary == "Failed summary"
        assert mapped.field_errors == {"priority": "invalid"}

    def test_resolve_bulk_error_context_handles_non_dict(self) -> None:
        """Return a normalized object for plain string errors."""
        mapped = resolve_bulk_error_context("plain error", batch_context=[])
        assert mapped.raw == "plain error"
