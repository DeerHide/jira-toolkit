"""Tests for cloud error rendering in reporting."""

from __future__ import annotations

from dataclasses import dataclass, field

from jira_importer.import_pipeline.models import CloudBulkIssueError
from jira_importer.import_pipeline.reporting import CloudReportReporter
from jira_importer.import_pipeline.sinks.cloud_sink import CloudSubmitReport


@dataclass
class _FakeUI:
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)

    def warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def say(self, msg: str) -> None:
        self.messages.append(msg)


class TestCloudReportReporter:
    """Tests for CloudReportReporter."""

    def test_render_errors_shows_field_errors_with_context(self) -> None:
        """Render Jira field errors with clear context and hint."""
        report = CloudSubmitReport(
            created=0,
            failed=1,
            batches=1,
            errors=[
                CloudBulkIssueError(
                    status=400,
                    failed_element_number=25,
                    failed_summary="CSV Import / Story / Invalid Priority",
                    field_errors={"priority": "Specify the Priority (name) in the string format"},
                )
            ],
        )
        ui = _FakeUI()

        CloudReportReporter().render_errors(report, ui)

        assert any("Some issues failed to import" in msg for msg in ui.warnings)
        assert any("Row 25 (Jira failed element 25, HTTP 400)" in msg for msg in ui.errors)
        assert any("summary: CSV Import / Story / Invalid Priority" in msg for msg in ui.errors)
        assert any("priority: Specify the Priority (name) in the string format" in msg for msg in ui.errors)
        assert any("--cloud-debug-payloads" in msg for msg in ui.errors)

    def test_render_errors_shows_jira_error_messages(self) -> None:
        """Render generic Jira error messages when fields map is empty."""
        report = CloudSubmitReport(
            created=0,
            failed=1,
            batches=1,
            errors=[
                CloudBulkIssueError(
                    status=400,
                    failed_element_number=2,
                    error_messages=("Project key is invalid",),
                )
            ],
        )
        ui = _FakeUI()

        CloudReportReporter().render_errors(report, ui)

        assert any("jira: Project key is invalid" in msg for msg in ui.errors)
