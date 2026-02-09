"""description: This script contains the models for the Jira Importer.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

import re
from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..config.config_models import CustomFieldConfig

# models definitions


class ProblemSeverity(str, Enum):
    """Discrete severities used across validation and reporting."""

    ERROR = "error"
    WARNING = "warning"
    FIX = "fix"  # indicates we applied (or can apply) a safe auto-fix when auto-fix is enabled
    CRITICAL = "critical"  # indicates a critical error that should stop processing


@dataclass(slots=True, frozen=True)
class Problem:
    """A single validation finding.

    Attributes:
        code: Stable machine code, e.g. 'priority.invalid', 'issueid.missing'.
        message: Human-friendly detail ready for console/Excel report.
        severity: error | warning | fix. fix is only used when auto-fix is enabled.
        row_index: 1-based row index in the original spreadsheet/CSV (header = 1).
        col_key: Canonical column key when applicable (e.g. 'priority'); None for row-level.
    """

    code: str
    message: str
    severity: ProblemSeverity
    row_index: int | None = None
    col_key: str | None = None


@dataclass(slots=True, frozen=True)
class ProcessingReport:
    """Aggregated counts for user-facing summary and quick gating.

    These mirror the UI summary you show today (⚠️, ❌, 🔧),
    but remain UI-agnostic here.
    """

    errors: int = 0
    warnings: int = 0
    fixes: int = 0

    @classmethod
    def from_problems(cls, problems: Sequence[Problem], auto_fix_enabled: bool) -> ProcessingReport:
        """Create a ProcessingReport from a list of problems."""
        if auto_fix_enabled:
            # With auto-fix enabled, keep FIXes separate but always treat CRITICAL as errors.
            e = sum(
                1
                for p in problems
                if p.severity == ProblemSeverity.ERROR or p.severity == ProblemSeverity.CRITICAL
            )
            w = sum(1 for p in problems if p.severity == ProblemSeverity.WARNING)
            f = sum(1 for p in problems if p.severity == ProblemSeverity.FIX)
        else:
            e = sum(
                1
                for p in problems
                if p.severity == ProblemSeverity.ERROR
                or p.severity == ProblemSeverity.FIX
                or p.severity == ProblemSeverity.CRITICAL
            )
            w = sum(1 for p in problems if p.severity == ProblemSeverity.WARNING)
            f = 0

        return cls(errors=e, warnings=w, fixes=f)


# header & indices definitions


@dataclass(slots=True, frozen=True)
class HeaderSchema:
    """Original + normalized header snapshot.

    normalized should align with the normalization already used in the legacy CSVProcessor
    (trim/lowercase, digits removed) so indices are consistent.
    """

    original: list[str]
    normalized: list[str]


@dataclass(slots=True)
class ColumnIndices:
    """Column index map aligned with today's processor, including optional columns and the special list of child-issue columns.

    All indices are 0-based; None means column absent.
    """

    # Required
    summary: int | None = None
    priority: int | None = None
    issuetype: int | None = None
    issue_id: int | None = None

    # Optional (keep names consistent with current CSV headers)
    project_key: int | None = None
    assignee: int | None = None
    assignee_name: int | None = None
    team: int | None = None
    team_name: int | None = None
    description: int | None = None
    parent: int | None = None
    epic_link: int | None = None
    epic_name: int | None = None
    component: int | None = None
    fixversion: int | None = None
    origest: int | None = None
    estimate: int | None = None
    sprint: int | None = None
    rowtype: int | None = None

    # Special (can be multiple)
    child_issue_indices: list[int] = field(default_factory=list)

    # Custom fields mapping (field_id -> column_index)
    custom_fields: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict[str, int | None]:
        """Dict view (useful when passing to generic helpers)."""
        d = self.__dict__.copy()
        return d  # includes child_issue_indices


# validation results definitions


@dataclass(slots=True, frozen=True)
class ValidationResult:
    """Output of validating a single row.

    Attributes:
        problems: All problems found for this row.
        patch: Sparse patch of cell updates to apply (index → stringified value).
               Using indices keeps this independent of header keys.
        notes: Optional free-form note from a rule/fix (may be surfaced in a debug report).
    """

    problems: tuple[Problem, ...] = field(default_factory=tuple)
    patch: Mapping[int, str] = field(default_factory=dict)
    notes: str | None = None

    @staticmethod
    def empty() -> ValidationResult:  # noqa: D102
        return ValidationResult()


@dataclass(slots=True, frozen=True)
class ComplexChildIssue:
    """Represents a 'range' form of child issue (e.g., '1-4') detected during validation."""

    row_index: int
    start: str
    end: str


@dataclass(slots=True)
class ProcessorResult:  # pylint: disable=too-many-instance-attributes
    """End-to-end processing result for a file.

    Attributes:
        header: Normalized header used for downstream writing.
        rows: Mutated/normalized rows after validation + auto-fixes.
        problems: Flat list of problems across all rows.
        report: Aggregated counts (errors/warnings/fixes).
        complex_children: Ranges found that require external handling.
        indices: Column indices used during processing.
        original_row_count: Total number of rows in the source data.
        processed_row_count: Number of rows after skipping and processing.
        skipped_row_count: Number of rows that were skipped during processing.
    """

    header: list[str]
    rows: list[list[Any]]
    problems: list[Problem] = field(default_factory=list)
    report: ProcessingReport = field(default_factory=ProcessingReport)
    complex_children: list[ComplexChildIssue] = field(default_factory=list)
    indices: ColumnIndices | None = None
    original_row_count: int | None = None
    processed_row_count: int | None = None
    skipped_row_count: int | None = None


# rule & fix contracts definitions


@dataclass(slots=True, frozen=True)
class RuleDefinition:
    r"""Definition for a rule (from built-ins or compiled from Excel).

    Attributes:
        id: Stable id ('summary.required', 'priority.allowed', etc.).
        target: Column key (e.g., 'priority') or 'row' for cross-field rules.
        condition: Expression/selector (e.g., 'required', 'enum:High,Medium,Low',
                   'regex:^PROJ-\\d+$', 'if(issuetype==Story)->required(parent)').
        params: Free-form structured params; keep small/simple for Excel authors.
        severity: Default severity when rule fails.
        message: Default message; rules may format it with row/context.
        order: Integer to enforce deterministic rule ordering.
    """

    id: str
    target: str
    condition: str
    params: Mapping[str, Any]
    severity: ProblemSeverity
    message: str
    order: int = 0


class IRowRule:
    """Runtime rule interface; concrete implementations live in rules/ (built-ins or compiled from Excel)."""

    def apply(
        self,
        row: Sequence[Any],
        indices: ColumnIndices,
        ctx: ValidationContext,
    ) -> ValidationResult:
        """Apply the rule to a row."""
        raise NotImplementedError


@dataclass(slots=True, frozen=True)
class FixOutcome:
    """Result of attempting to fix a single problem.

    Attributes:
        applied: Whether a change was applied.
        patch: Sparse cell updates (index → stringified value).
        notes: Free-form note (e.g., 'normalized priority to 02').
    """

    applied: bool
    patch: Mapping[int, str] = field(default_factory=dict)
    notes: str | None = None


class IFixer:
    """Fixer interface mapping to a specific problem code; registered in FixRegistry."""

    def apply(
        self,
        problem: Problem,
        row: Sequence[Any],
        indices: ColumnIndices,
        ctx: ValidationContext,
    ) -> FixOutcome:
        """Apply the fix to a problem."""
        raise NotImplementedError


# execution context definitions


@dataclass(slots=True)
class ValidationContext:
    """Context passed to rules/fixes.

    Attributes:
        row_index: 1-based index of the current data row (header = 1).
        config: Typed/opaque config view (keep as Any to avoid circular deps).
        feature_flags: Feature toggles controlling rule composition and behavior.
        auto_fix_enabled: If True, validator may ask FixRegistry to apply safe fixes.
        issue_id_seen: Mutable set to detect duplicates (shared across row validations).
    """

    row_index: int
    config: Any
    feature_flags: Mapping[str, Any] = field(default_factory=dict)
    auto_fix_enabled: bool = False
    issue_id_seen: MutableMapping[str, None] = field(default_factory=dict)
    # Tracks first-time encounter during validation pass (not pre-populated)
    validation_issue_id_seen: MutableMapping[str, None] = field(default_factory=dict)
    # Maps issue_id -> (issue_type, row_index) for parent validation
    issue_data: MutableMapping[str, tuple[str, int]] = field(default_factory=dict)
    # Maps field_id -> CustomFieldConfig for custom field validation
    custom_field_configs: dict[str, CustomFieldConfig] | None = None

    def seen_issue_id(self, value: str) -> bool:
        """Returns True if value was seen before; otherwise records it and returns False.

        Check if an issue ID has been seen before.
        """
        if value in self.issue_id_seen:
            return True
        self.issue_id_seen[value] = None
        return False

    def seen_issue_id_in_validation(self, value: str) -> bool:
        """Duplicate detection for validation pass only (ignores pre-populated set).

        Returns True if value was already encountered during this validation pass.
        """
        if value in self.validation_issue_id_seen:
            return True
        self.validation_issue_id_seen[value] = None
        return False

    _RE_ISSUE_ID = re.compile(r"^(?:[A-Za-z]+-\d+|\d+)$")

    def invalid_issue_id(self, value: str) -> bool:
        """Returns True if value is invalid; otherwise records it and returns False.

        Check if an issue ID is invalid.
        """
        return self._RE_ISSUE_ID.match(value) is None
