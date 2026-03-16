"""Preflight validation for Jira Cloud import.

Validates config-dependent references (project, priorities, issue types,
assignees, reporters) against the Jira API before sending payloads.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ..models import ColumnIndices, ProcessorResult, Problem, ProblemSeverity
from ..utils import split_multi_value_cell
from ...config.config_view import ConfigView
from .metadata import MetadataCache
from .secrets import redact_secret


def _cell_str(row: Sequence[Any], idx: int | None) -> str:
    """Safely extract string value from row cell."""
    if idx is None or idx < 0 or idx >= len(row):
        return ""
    v = row[idx]
    return "" if v is None else str(v).strip()


def _collect_unique_with_row(
    rows: Sequence[Sequence[Any]],
    indices: ColumnIndices,
    col_key: str,
    idx: int | None,
    *,
    multi_value: bool = False,
) -> dict[str, int]:
    """Collect unique non-empty values and the first row index where each appears.

    Returns:
        Dict mapping value -> 1-based row index (header=1).
    """
    out: dict[str, int] = {}
    if idx is None:
        return out
    for i, row in enumerate(rows):
        raw = _cell_str(row, idx)
        if not raw:
            continue
        if multi_value:
            parts = split_multi_value_cell(raw)
            for part in parts:
                if part and part not in out:
                    out[part] = i + 2  # 1-based data rows (header=1, first data=2)
        else:
            if raw not in out:
                out[raw] = i + 2
    return out


class PreflightValidator:
    """Validates processor result references against Jira Cloud API metadata.

    Phase 1 (MVP): project, priorities, issue types, assignees, reporters.
    Phase 2: components, fix versions.
    """

    def __init__(
        self,
        result: ProcessorResult,
        config: ConfigView,
        metadata: MetadataCache,
    ) -> None:
        """Initialize the preflight validator."""
        self._result = result
        self._config = config
        self._metadata = metadata

    def validate(self) -> list[Problem]:
        """Validate all references. Returns list of problems (CRITICAL for invalid refs)."""
        problems: list[Problem] = []
        indices = self._result.indices
        rows = self._result.rows

        if indices is None or not rows:
            return problems

        # Phase 1: project, priorities, issue types, assignees, reporters
        problems.extend(self._validate_projects(indices, rows))
        problems.extend(self._validate_priorities(indices, rows))
        problems.extend(self._validate_issuetypes(indices, rows))
        problems.extend(self._validate_assignees(indices, rows))
        problems.extend(self._validate_reporters(indices, rows))

        return problems

    def _validate_projects(
        self, indices: ColumnIndices, rows: Sequence[Sequence[Any]]
    ) -> list[Problem]:
        """Validate project keys exist in Jira."""
        problems: list[Problem] = []
        seen: set[str] = set()

        # From rows
        project_values = _collect_unique_with_row(
            rows, indices, "project_key", indices.project_key
        )
        for key, row_idx in project_values.items():
            key_upper = key.upper()
            if key_upper in seen:
                continue
            seen.add(key_upper)
            proj = self._metadata.get_project(key)
            if proj is None:
                problems.append(
                    Problem(
                        code="preflight.project.not_found",
                        message=f"Project '{key}' does not exist in Jira",
                        severity=ProblemSeverity.CRITICAL,
                        row_index=row_idx,
                        col_key="project_key",
                    )
                )

        # From config
        config_key = self._config.get("jira.project.key", None)
        if config_key and isinstance(config_key, str):
            key_upper = config_key.strip().upper()
            if key_upper and key_upper not in seen:
                seen.add(key_upper)
                proj = self._metadata.get_project(config_key.strip())
                if proj is None:
                    problems.append(
                        Problem(
                            code="preflight.project.not_found",
                            message=f"Project '{config_key}' (from config jira.project.key) does not exist in Jira",
                            severity=ProblemSeverity.CRITICAL,
                            row_index=None,
                            col_key="project_key",
                        )
                    )

        return problems

    def _validate_priorities(
        self, indices: ColumnIndices, rows: Sequence[Sequence[Any]]
    ) -> list[Problem]:
        """Validate priorities exist in Jira (case-insensitive, aligned with Jira API)."""
        problems: list[Problem] = []
        if indices.priority is None:
            return problems

        priorities_by_lower = {
            str(p.get("name", "")).strip().lower(): p
            for p in self._metadata.get_priorities()
            if p.get("name")
        }
        priority_values = _collect_unique_with_row(
            rows, indices, "priority", indices.priority
        )
        for name, row_idx in priority_values.items():
            if name and str(name).strip().lower() not in priorities_by_lower:
                problems.append(
                    Problem(
                        code="preflight.priority.invalid",
                        message=f"Priority '{name}' is not valid in Jira",
                        severity=ProblemSeverity.CRITICAL,
                        row_index=row_idx,
                        col_key="priority",
                    )
                )
        return problems

    def _validate_issuetypes(
        self, indices: ColumnIndices, rows: Sequence[Sequence[Any]]
    ) -> list[Problem]:
        """Validate issue types exist in Jira (case-insensitive, aligned with Jira API)."""
        problems: list[Problem] = []
        if indices.issuetype is None:
            return problems

        issuetypes_by_lower = {
            it.get("name", "").strip().lower(): it
            for it in self._metadata.get_issuetypes()
            if it.get("name")
        }
        issuetype_values = _collect_unique_with_row(
            rows, indices, "issuetype", indices.issuetype
        )
        for name, row_idx in issuetype_values.items():
            if name and name.strip().lower() not in issuetypes_by_lower:
                problems.append(
                    Problem(
                        code="preflight.issuetype.invalid",
                        message=f"Issue type '{name}' is not valid in Jira",
                        severity=ProblemSeverity.CRITICAL,
                        row_index=row_idx,
                        col_key="issuetype",
                    )
                )
        return problems

    def _validate_assignees(
        self, indices: ColumnIndices, rows: Sequence[Sequence[Any]]
    ) -> list[Problem]:
        """Validate assignee account IDs exist in Jira."""
        problems: list[Problem] = []
        if indices.assignee is None:
            return problems

        assignee_values = _collect_unique_with_row(
            rows, indices, "assignee", indices.assignee
        )
        for account_id, row_idx in assignee_values.items():
            if account_id and not self._metadata.user_exists(account_id):
                problems.append(
                    Problem(
                        code="preflight.assignee.not_found",
                        message=f"Assignee at row {row_idx} ({redact_secret(account_id)}) not found in Jira",
                        severity=ProblemSeverity.CRITICAL,
                        row_index=row_idx,
                        col_key="assignee",
                    )
                )
        return problems

    def _validate_reporters(
        self, indices: ColumnIndices, rows: Sequence[Sequence[Any]]
    ) -> list[Problem]:
        """Validate reporter account IDs exist in Jira."""
        problems: list[Problem] = []
        if indices.reporter is None:
            return problems

        reporter_values = _collect_unique_with_row(
            rows, indices, "reporter", indices.reporter
        )
        for account_id, row_idx in reporter_values.items():
            if account_id and not self._metadata.user_exists(account_id):
                problems.append(
                    Problem(
                        code="preflight.reporter.not_found",
                        message=f"Reporter at row {row_idx} ({redact_secret(account_id)}) not found in Jira",
                        severity=ProblemSeverity.CRITICAL,
                        row_index=row_idx,
                        col_key="reporter",
                    )
                )
        return problems
