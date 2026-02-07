"""description: This script contains the built-in rules for the Jira Importer.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from ...config.constants import LEVEL_4_SUBTASK
from ...config.issuetypes import get_allowed_issue_types, get_issue_type_level
from ..models import ColumnIndices, IRowRule, Problem, ProblemSeverity, ValidationContext, ValidationResult

# helpers functions


def _cell_str(row: Sequence[Any], idx: int | None) -> str:
    if idx is None:
        return ""
    if idx < 0 or idx >= len(row):
        return ""
    v = row[idx]
    if v is None:
        return ""
    s = str(v).strip()
    return s


def _is_empty(s: str) -> bool:
    return s == ""


# rules definitions


@dataclass(slots=True)
class SummaryRequiredRule(IRowRule):
    """Summary must not be empty.

    Severity: error
    Note: Mandatory for the Jira Cloud & Jira Server
    """

    def apply(self, row, indices: ColumnIndices, ctx: ValidationContext) -> ValidationResult:
        """Apply the rule to the row."""
        summary = _cell_str(row, indices.summary)
        if _is_empty(summary):
            return ValidationResult(
                problems=(
                    Problem(
                        code="summary.required",
                        message="Summary is required.",
                        severity=ProblemSeverity.ERROR,
                        row_index=ctx.row_index,
                        col_key="summary",
                    ),
                )
            )
        return ValidationResult.empty()


@dataclass(slots=True)
class IssueTypeAllowedRule(IRowRule):
    """IssueType must be one of allowed issuetypes (config override supported).

    Default: {'Story','Task','Bug','Epic','Sub-Task'}
    Severity: error
    Note: Mandatory for the Jira Cloud & Jira Server
    """

    allowed: set[str] | None = None

    def _allowed(self, ctx: ValidationContext) -> set[str]:
        # Use unified config-driven issue types (handles both old and new formats)
        try:
            return get_allowed_issue_types(ctx.config.get)
        except Exception:
            # Final fallback to hardcoded defaults if config is completely broken
            return {"Story", "Task", "Bug", "Epic", "Sub-Task"}

    def apply(self, row, indices: ColumnIndices, ctx: ValidationContext) -> ValidationResult:
        """Apply the rule to the row."""
        issuetype = _cell_str(row, indices.issuetype)
        if _is_empty(issuetype):
            return ValidationResult(
                problems=(
                    Problem(
                        code="issuetype.missing",
                        message="Issue Type is required.",
                        severity=ProblemSeverity.ERROR,
                        row_index=ctx.row_index,
                        col_key="issuetype",
                    ),
                )
            )
        allowed = self.allowed or self._allowed(ctx)
        if issuetype not in allowed:
            return ValidationResult(
                problems=(
                    Problem(
                        code="issuetype.invalid",
                        message=f"Issue Type '{issuetype}' is not allowed. Allowed: {sorted(allowed)}",
                        severity=ProblemSeverity.ERROR,
                        row_index=ctx.row_index,
                        col_key="issuetype",
                    ),
                )
            )
        return ValidationResult.empty()


@dataclass(slots=True)
class PriorityAllowedRule(IRowRule):
    """Priority must be one of allowed priorities (config override supported).

    Default: {'Highest','High','Medium','Low','Lowest'}
    Severity: warning (fixable via fixer to normalize/pad if needed)
    Note: Mandatory for the Jira Cloud & Jira Server
    """

    def _allowed(self, ctx: ValidationContext) -> set[str]:
        default = {"Highest", "High", "Medium", "Low", "Lowest"}
        cfg = getattr(ctx.config, "get", None)
        if callable(cfg):
            values = ctx.config.get("jira.priorities", default)
            try:
                return set(v if isinstance(v, str) else str(v) for v in values)
            except Exception:
                return default
        return default

    def apply(self, row, indices: ColumnIndices, ctx: ValidationContext) -> ValidationResult:
        """Apply the rule to the row."""
        pri = _cell_str(row, indices.priority)
        if _is_empty(pri):
            # Check if the priority is empty
            return ValidationResult(
                problems=(
                    Problem(
                        code="priority.missing",
                        message="Priority is empty.",
                        severity=ProblemSeverity.ERROR,
                        row_index=ctx.row_index,
                        col_key="priority",
                    ),
                )
            )
        allowed = self._allowed(ctx)
        if pri not in allowed:
            return ValidationResult(
                problems=(
                    Problem(
                        code="priority.invalid",
                        message=f"Priority '{pri}' is not allowed. Allowed: {sorted(allowed)}",
                        severity=ProblemSeverity.ERROR,
                        row_index=ctx.row_index,
                        col_key="priority",
                    ),
                )
            )
        return ValidationResult.empty()


@dataclass(slots=True)
class IssueIdPresenceRule(IRowRule):
    """IssueId may be missing; if so, we raise a 'fix' severity so a Fixer can assign one. Also checks duplicates when provided (error)."""

    def apply(self, row, indices: ColumnIndices, ctx: ValidationContext) -> ValidationResult:
        """Apply the rule to the row."""
        issue_id = _cell_str(row, indices.issue_id)

        # Missing issue ID
        if _is_empty(issue_id):
            # Signal a fixable condition
            return ValidationResult(
                problems=(
                    Problem(
                        code="issueid.missing",
                        message="IssueId is missing and will be assigned automatically.",
                        severity=ProblemSeverity.FIX,
                        row_index=ctx.row_index,
                        col_key="issue id",
                    ),
                )
            )

        # Invalid issue ID
        if ctx.invalid_issue_id(issue_id):
            return ValidationResult(
                problems=(
                    Problem(
                        code="issueid.invalid",
                        message=f"IssueId '{issue_id}' is invalid and will be assigned automatically.",
                        severity=ProblemSeverity.FIX,
                        row_index=ctx.row_index,
                        col_key="issue id",
                    ),
                )
            )

        # Duplicate detection
        if ctx.seen_issue_id_in_validation(issue_id):
            return ValidationResult(
                problems=(
                    Problem(
                        code="issueid.duplicate",
                        message=f"IssueId '{issue_id}' is duplicated.",
                        severity=ProblemSeverity.ERROR,
                        row_index=ctx.row_index,
                        col_key="issue id",
                    ),
                )
            )

        return ValidationResult.empty()


@dataclass(slots=True)
class EstimateFormatRule(IRowRule):
    """Validate 'estimate' or 'origest' fields format.

    Accepts patterns like: '1w 2d 3h 30m', '2h', '45m', or plain integers (minutes or seconds per config).
    - If unparsable → error.
    - If parsable → no problem; a Fixer may normalize to seconds/minutes for target sink.

    Config keys (optional):
      - validation.estimate.accept_integers_as: 'seconds' | 'minutes' (default 'seconds')
      - validation.estimate.fields: ['estimate','origest'] (defaults to both when present)
    """

    def _integer_unit(self, ctx: ValidationContext) -> str:
        cfg_get = getattr(ctx.config, "get", None)
        if callable(cfg_get):
            unit = ctx.config.get("validation.estimate.accept_integers_as", "seconds")
            return unit if unit in {"seconds", "minutes"} else "seconds"
        return "seconds"

    def _fields(self, indices: ColumnIndices, ctx: ValidationContext) -> list[tuple[str, int | None]]:
        # Decide which columns to validate
        cfg_get = getattr(ctx.config, "get", None)
        wanted = None
        if callable(cfg_get):
            wanted = ctx.config.get("validation.estimate.fields", None)
        keys = []
        if not wanted:
            keys = [("estimate", indices.estimate), ("origest", indices.origest)]
        else:
            wanted = [str(k).strip().lower() for k in wanted]
            if "estimate" in wanted:
                keys.append(("estimate", indices.estimate))
            if "origest" in wanted:
                keys.append(("origest", indices.origest))
        return keys

    def apply(self, row, indices: ColumnIndices, ctx: ValidationContext) -> ValidationResult:
        """Apply the rule to the row."""
        problems: list[Problem] = []
        for key, idx in self._fields(indices, ctx):
            raw = _cell_str(row, idx)
            if _is_empty(raw):
                continue
            if not _is_parseable_estimate(raw, accept_int_as=self._integer_unit(ctx)):
                problems.append(
                    Problem(
                        code="estimate.invalid_format",
                        message=f"Estimate value '{raw}' for '{key}' is not in a supported format.",
                        severity=ProblemSeverity.ERROR,
                        row_index=ctx.row_index,
                        col_key=key,
                    )
                )
        if problems:
            return ValidationResult(problems=tuple(problems))
        return ValidationResult.empty()


@dataclass(slots=True)
class ProjectKeyConsistencyRule(IRowRule):
    """If a Project Key column exists, it should match the configured one (warning/fix). Config key: jira.project.key."""

    def apply(self, row, indices: ColumnIndices, ctx: ValidationContext) -> ValidationResult:
        """Apply the rule to the row."""
        if indices.project_key is None:
            return ValidationResult.empty()

        expected = None
        cfg_get = getattr(ctx.config, "get", None)
        if callable(cfg_get):
            expected = ctx.config.get("jira.project.key", None)
        if not expected:
            return ValidationResult.empty()

        val = _cell_str(row, indices.project_key)
        if _is_empty(val):
            # Prefer a FIX (autofill) over error.
            return ValidationResult(
                problems=(
                    Problem(
                        code="project_key.missing",
                        message=f"Project Key is empty; expected '{expected}'.",
                        severity=ProblemSeverity.FIX,
                        row_index=ctx.row_index,
                        col_key="project key",
                    ),
                )
            )

        if val != str(expected):
            return ValidationResult(
                problems=(
                    Problem(
                        code="project_key.mismatch",
                        message=f"Project Key '{val}' differs from configured '{expected}'.",
                        severity=ProblemSeverity.FIX,
                        row_index=ctx.row_index,
                        col_key="project key",
                    ),
                )
            )
        return ValidationResult.empty()


#  estimate parsing utility (liberal)

_EST_TOKEN_RE = re.compile(r"(?P<num>\d+)\s*(?P<unit>[wdhms])", re.IGNORECASE)


def _is_parseable_estimate(value: str, *, accept_int_as: str = "seconds") -> bool:  # pylint: disable=unused-argument
    """True if 'value' looks like a valid estimate.

    Accepts:
      - tokenized: '1w 2d 3h 30m', '2h', '45m', '30s'
      - chained:   '1w2d3h30m', '2h30m'
      - plain int: interpreted as seconds or minutes (per accept_int_as)
    """
    s = value.strip().lower()
    if not s:
        return False

    # plain integer
    if s.isdigit():
        return True

    # token scan (supports spaces or none)
    matched = False
    pos = 0
    while pos < len(s):
        m = _EST_TOKEN_RE.match(s, pos)
        if not m:
            if s[pos].isspace():
                pos += 1
                continue
            return False
        matched = True
        pos = m.end()
    return matched


@dataclass(slots=True)
class ParentLinkValidationRule(IRowRule):
    """Validate parent-child links based on issue type hierarchy.

    Rules:
    - Parent ID cannot equal the issue's own Issue ID (no self-reference).
    - Level 1 (Initiative) can parent levels 2, 3, 4
    - Level 2 (Epic) can parent levels 3, 4
    - Level 3 (Story/Task/Bug) can parent level 4 only
    - Level 4 (Sub-Task) cannot parent anything
    - Level 4 (Sub-Task) must have a parent
    """

    def apply(self, row, indices: ColumnIndices, ctx: ValidationContext) -> ValidationResult:
        """Apply the rule to validate parent-child links based on issue type hierarchy."""
        problems = []

        # Get current issue info
        issue_type = _cell_str(row, indices.issuetype)
        issue_id = _cell_str(row, indices.issue_id)
        parent_value = _cell_str(row, indices.parent) if indices.parent else ""

        if not issue_type:
            return ValidationResult.empty()

        cfg_get = getattr(ctx.config, "get", None)
        if not callable(cfg_get):
            return ValidationResult.empty()

        child_level = get_issue_type_level(cfg_get, issue_type)

        # Check if sub-task has no parent
        if child_level == LEVEL_4_SUBTASK and _is_empty(parent_value):
            problems.append(
                Problem(
                    code="parent_link.missing",
                    message="Sub-Task must have a parent",
                    severity=ProblemSeverity.CRITICAL,
                    row_index=ctx.row_index,
                    col_key="parent",
                )
            )

        # Check parent-child links if parent exists
        if not _is_empty(parent_value):
            # Skip external Jira keys (PROJ-123 format)
            if self._is_jira_key(parent_value):
                return ValidationResult(problems=tuple(problems)) if problems else ValidationResult.empty()

            # Issue cannot be its own parent
            if not _is_empty(issue_id) and parent_value == issue_id:
                problems.append(
                    Problem(
                        code="parent_link.self_reference",
                        message=f"Parent ID '{parent_value}' cannot be the same as the issue's own Issue ID '{issue_id}'.",
                        severity=ProblemSeverity.CRITICAL,
                        row_index=ctx.row_index,
                        col_key="parent",
                    )
                )
                return ValidationResult(problems=tuple(problems)) if problems else ValidationResult.empty()

            # Try to resolve parent from issue_data (keyed by Issue ID from the sheet)
            issue_data = getattr(ctx, "issue_data", {})
            if parent_value not in issue_data:
                problems.append(
                    Problem(
                        code="parent_link.not_found",
                        message=f"Parent ID '{parent_value}' does not exist in the dataset (no row with this Issue ID).",
                        severity=ProblemSeverity.CRITICAL,
                        row_index=ctx.row_index,
                        col_key="parent",
                    )
                )
            else:
                parent_type, _ = issue_data[parent_value]
                parent_level = get_issue_type_level(cfg_get, parent_type)

                # Validate hierarchy: parent level must be < child level
                if parent_level is not None and child_level is not None and parent_level >= child_level:
                    problems.append(
                        Problem(
                            code="parent_link.unsupported",
                            message=f"Invalid parent-child links: {issue_type} (id {issue_id}, level {child_level}) cannot have {parent_type} (id {parent_value}, level {parent_level}) as parent. Parent must be at a higher level in the hierarchy.",
                            severity=ProblemSeverity.CRITICAL,
                            row_index=ctx.row_index,
                            col_key="parent",
                        )
                    )

        return ValidationResult(problems=tuple(problems)) if problems else ValidationResult.empty()

    def _is_jira_key(self, value: str) -> bool:
        """Check if value looks like external Jira key (PROJ-123)."""
        return bool(re.match(r"^[A-Z][A-Z0-9]+-\d+$", value))
