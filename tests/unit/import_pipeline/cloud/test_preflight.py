"""Unit tests for PreflightValidator."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from jira_importer.config.config_view import ConfigView
from jira_importer.import_pipeline.cloud.metadata import MetadataCache
from jira_importer.import_pipeline.cloud.preflight import PreflightValidator
from jira_importer.import_pipeline.models import ColumnIndices, ProcessorResult, ProblemSeverity


class TestPreflightValidator:
    """Tests for PreflightValidator."""

    @pytest.fixture
    def mock_metadata(self) -> MagicMock:
        """Create mock MetadataCache."""
        meta = MagicMock(spec=MetadataCache)
        meta.get_project.return_value = {"key": "TEST"}
        meta.get_priorities.return_value = [{"name": "High"}, {"name": "Medium"}, {"name": "Low"}]
        meta.get_issuetypes.return_value = [{"name": "Task"}, {"name": "Story"}, {"name": "Bug"}]
        meta.user_exists.return_value = True
        return meta

    def test_validate_empty_rows_returns_empty(
        self, mock_metadata: MagicMock
    ) -> None:
        """Test validate returns no problems for empty rows."""
        result = ProcessorResult(
            header=["Summary", "Priority", "Issue Type", "Project Key"],
            rows=[],
            indices=ColumnIndices(summary=0, priority=1, issuetype=2, project_key=3),
        )
        cfg = ConfigView({})
        validator = PreflightValidator(result, cfg, mock_metadata)
        problems = validator.validate()
        assert len(problems) == 0

    def test_validate_project_not_found(
        self, mock_metadata: MagicMock
    ) -> None:
        """Test validate reports project not found."""
        mock_metadata.get_project.return_value = None

        result = ProcessorResult(
            header=["Summary", "Priority", "Issue Type", "Project Key"],
            rows=[["Fix bug", "High", "Task", "MISSING"]],
            indices=ColumnIndices(summary=0, priority=1, issuetype=2, project_key=3),
        )
        cfg = ConfigView({})
        validator = PreflightValidator(result, cfg, mock_metadata)
        problems = validator.validate()

        assert len(problems) == 1
        assert problems[0].code == "preflight.project.not_found"
        assert problems[0].severity == ProblemSeverity.CRITICAL
        assert "MISSING" in problems[0].message

    def test_validate_priority_invalid(
        self, mock_metadata: MagicMock
    ) -> None:
        """Test validate reports invalid priority."""
        result = ProcessorResult(
            header=["Summary", "Priority", "Issue Type"],
            rows=[["Fix bug", "InvalidPriority", "Task"]],
            indices=ColumnIndices(summary=0, priority=1, issuetype=2),
        )
        cfg = ConfigView({})
        validator = PreflightValidator(result, cfg, mock_metadata)
        problems = validator.validate()

        assert len(problems) == 1
        assert problems[0].code == "preflight.priority.invalid"
        assert problems[0].severity == ProblemSeverity.CRITICAL

    def test_validate_issuetype_invalid(
        self, mock_metadata: MagicMock
    ) -> None:
        """Test validate reports invalid issue type."""
        result = ProcessorResult(
            header=["Summary", "Priority", "Issue Type"],
            rows=[["Fix bug", "High", "InvalidType"]],
            indices=ColumnIndices(summary=0, priority=1, issuetype=2),
        )
        cfg = ConfigView({})
        validator = PreflightValidator(result, cfg, mock_metadata)
        problems = validator.validate()

        assert len(problems) == 1
        assert problems[0].code == "preflight.issuetype.invalid"
        assert problems[0].severity == ProblemSeverity.CRITICAL

    def test_validate_assignee_not_found(
        self, mock_metadata: MagicMock
    ) -> None:
        """Test validate reports assignee account ID not found."""
        mock_metadata.user_exists.side_effect = lambda aid: aid != "bad-account-id"

        result = ProcessorResult(
            header=["Summary", "Assignee"],
            rows=[["Fix bug", "bad-account-id"]],
            indices=ColumnIndices(summary=0, assignee=1),
        )
        cfg = ConfigView({})
        validator = PreflightValidator(result, cfg, mock_metadata)
        problems = validator.validate()

        assert len(problems) == 1
        assert problems[0].code == "preflight.assignee.not_found"
        assert problems[0].severity == ProblemSeverity.CRITICAL

    def test_validate_skips_optional_columns(
        self, mock_metadata: MagicMock
    ) -> None:
        """Test validate skips checks when column index is None."""
        result = ProcessorResult(
            header=["Summary"],
            rows=[["Fix bug"]],
            indices=ColumnIndices(summary=0, assignee=None, reporter=None, project_key=None),
        )
        cfg = ConfigView({})
        validator = PreflightValidator(result, cfg, mock_metadata)
        problems = validator.validate()

        assert len(problems) == 0
        mock_metadata.user_exists.assert_not_called()
        mock_metadata.get_project.assert_not_called()

    def test_validate_config_project_not_found(
        self, mock_metadata: MagicMock
    ) -> None:
        """Test validate checks config jira.project.key when set."""
        mock_metadata.get_project.return_value = None

        result = ProcessorResult(
            header=["Summary"],
            rows=[["Fix bug"]],
            indices=ColumnIndices(summary=0, project_key=None),
        )
        cfg = ConfigView({"jira": {"project": {"key": "MISSING"}}})
        validator = PreflightValidator(result, cfg, mock_metadata)
        problems = validator.validate()

        assert len(problems) == 1
        assert problems[0].code == "preflight.project.not_found"
        assert "jira.project.key" in problems[0].message

    def test_validate_issuetype_case_insensitive(
        self, mock_metadata: MagicMock
    ) -> None:
        """Sub-Task passes when Jira returns Sub-task; case-insensitive match."""
        mock_metadata.get_issuetypes.return_value = [
            {"name": "Sub-task"},
            {"name": "Story"},
            {"name": "Task"},
        ]

        result = ProcessorResult(
            header=["Summary", "Priority", "Issue Type"],
            rows=[
                ["Fix bug", "High", "Sub-Task"],
                ["Add feature", "Medium", "sub-task"],
            ],
            indices=ColumnIndices(summary=0, priority=1, issuetype=2),
        )
        cfg = ConfigView({})
        validator = PreflightValidator(result, cfg, mock_metadata)
        problems = validator.validate()

        assert len(problems) == 0

    def test_validate_priority_case_insensitive(
        self, mock_metadata: MagicMock
    ) -> None:
        """low passes when Jira returns Low; HIGH passes when Jira returns High."""
        mock_metadata.get_priorities.return_value = [
            {"name": "Highest"},
            {"name": "High"},
            {"name": "Medium"},
            {"name": "Low"},
            {"name": "Lowest"},
        ]

        result = ProcessorResult(
            header=["Summary", "Priority", "Issue Type"],
            rows=[
                ["Fix bug", "low", "Task"],
                ["Add feature", "HIGH", "Task"],
                ["Refactor", "Medium", "Task"],
            ],
            indices=ColumnIndices(summary=0, priority=1, issuetype=2),
        )
        cfg = ConfigView({})
        validator = PreflightValidator(result, cfg, mock_metadata)
        problems = validator.validate()

        assert len(problems) == 0

    def test_validate_empty_whitespace_priority_issuetype_no_crash(
        self, mock_metadata: MagicMock
    ) -> None:
        """Empty or whitespace values do not cause crashes."""
        result = ProcessorResult(
            header=["Summary", "Priority", "Issue Type"],
            rows=[
                ["Fix bug", "", "Task"],
                ["Add feature", "High", "  "],
                ["Refactor", "  ", ""],
            ],
            indices=ColumnIndices(summary=0, priority=1, issuetype=2),
        )
        cfg = ConfigView({})
        validator = PreflightValidator(result, cfg, mock_metadata)
        problems = validator.validate()

        # Empty/whitespace are skipped by _collect_unique_with_row, no crash
        assert isinstance(problems, list)
