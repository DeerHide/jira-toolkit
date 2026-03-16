"""Unit tests for built-in validation rules."""

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

from jira_importer.import_pipeline.models import ColumnIndices, ValidationContext, ValidationResult
from jira_importer.import_pipeline.rules.builtin_rules import (
    IssueTypeAllowedRule,
    PriorityAllowedRule,
)


def _make_ctx(config_get: Callable[[str, Any], Any] | None = None) -> ValidationContext:
    """Create a minimal ValidationContext for rule tests."""
    cfg = config_get if config_get else (lambda k, d=None: d)
    return ValidationContext(
        row_index=2,
        config=SimpleNamespace(get=cfg),
        feature_flags={},
        auto_fix_enabled=False,
        issue_id_seen={},
        issue_data={},
        custom_field_configs=None,
    )


class TestIssueTypeAllowedRuleCaseInsensitive:
    """Issue type validation is case-insensitive (matches Jira API behavior)."""

    def test_accepts_lowercase_issuetype(self) -> None:
        """'sub-task' passes when 'Sub-Task' is allowed."""
        rule = IssueTypeAllowedRule(allowed={"Story", "Task", "Sub-Task", "Bug", "Epic"})
        row: list[Any] = ["Summary", "High", "sub-task"]
        indices = ColumnIndices(summary=0, priority=1, issuetype=2)
        ctx = _make_ctx()

        result = rule.apply(row, indices, ctx)

        assert result.problems == ()
        assert result == ValidationResult.empty()

    def test_accepts_uppercase_issuetype(self) -> None:
        """'SUB-TASK' passes when 'Sub-Task' is allowed."""
        rule = IssueTypeAllowedRule(allowed={"Story", "Task", "Sub-Task", "Bug", "Epic"})
        row: list[Any] = ["Summary", "High", "SUB-TASK"]
        indices = ColumnIndices(summary=0, priority=1, issuetype=2)
        ctx = _make_ctx()

        result = rule.apply(row, indices, ctx)

        assert result.problems == ()

    def test_accepts_mixed_case_issuetype(self) -> None:
        """'StOrY' passes when 'Story' is allowed."""
        rule = IssueTypeAllowedRule(allowed={"Story", "Task", "Bug", "Epic"})
        row: list[Any] = ["Summary", "High", "StOrY"]
        indices = ColumnIndices(summary=0, priority=1, issuetype=2)
        ctx = _make_ctx()

        result = rule.apply(row, indices, ctx)

        assert result.problems == ()

    def test_rejects_invalid_issuetype(self) -> None:
        """Unknown issue type is rejected."""
        rule = IssueTypeAllowedRule(allowed={"Story", "Task", "Bug", "Epic"})
        row: list[Any] = ["Summary", "High", "UnknownType"]
        indices = ColumnIndices(summary=0, priority=1, issuetype=2)
        ctx = _make_ctx()

        result = rule.apply(row, indices, ctx)

        assert len(result.problems) == 1
        assert result.problems[0].code == "issuetype.invalid"


class TestPriorityAllowedRuleCaseInsensitive:
    """Priority validation is case-insensitive (matches Jira API behavior)."""

    def test_accepts_lowercase_priority(self) -> None:
        """'low' passes when 'Low' is allowed."""
        cfg_get: Callable[[str, Any], Any] = lambda k, d=None: (
            ["Highest", "High", "Medium", "Low", "Lowest"] if k == "jira.priorities" else d
        )
        rule = PriorityAllowedRule()
        row: list[Any] = ["Summary", "low", "Task"]
        indices = ColumnIndices(summary=0, priority=1, issuetype=2)
        ctx = _make_ctx(cfg_get)

        result = rule.apply(row, indices, ctx)

        assert result.problems == ()

    def test_accepts_uppercase_priority(self) -> None:
        """'HIGH' passes when 'High' is allowed."""
        cfg_get: Callable[[str, Any], Any] = lambda k, d=None: (
            ["Highest", "High", "Medium", "Low", "Lowest"] if k == "jira.priorities" else d
        )
        rule = PriorityAllowedRule()
        row: list[Any] = ["Summary", "HIGH", "Task"]
        indices = ColumnIndices(summary=0, priority=1, issuetype=2)
        ctx = _make_ctx(cfg_get)

        result = rule.apply(row, indices, ctx)

        assert result.problems == ()

    def test_accepts_mixed_case_priority(self) -> None:
        """'MeDiUm' passes when 'Medium' is allowed."""
        cfg_get: Callable[[str, Any], Any] = lambda k, d=None: (
            ["Highest", "High", "Medium", "Low", "Lowest"] if k == "jira.priorities" else d
        )
        rule = PriorityAllowedRule()
        row: list[Any] = ["Summary", "MeDiUm", "Task"]
        indices = ColumnIndices(summary=0, priority=1, issuetype=2)
        ctx = _make_ctx(cfg_get)

        result = rule.apply(row, indices, ctx)

        assert result.problems == ()

    def test_rejects_invalid_priority(self) -> None:
        """Unknown priority is rejected."""
        cfg_get: Callable[[str, Any], Any] = lambda k, d=None: (
            ["Highest", "High", "Medium", "Low", "Lowest"] if k == "jira.priorities" else d
        )
        rule = PriorityAllowedRule()
        row: list[Any] = ["Summary", "Critical", "Task"]
        indices = ColumnIndices(summary=0, priority=1, issuetype=2)
        ctx = _make_ctx(cfg_get)

        result = rule.apply(row, indices, ctx)

        assert len(result.problems) == 1
        assert result.problems[0].code == "priority.invalid"
