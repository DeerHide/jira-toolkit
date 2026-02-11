"""Reporter resolution fixer for Jira Importer.

This fixer handles reporter resolution by:
1. Detecting Cloud accountId format vs display names
2. Looking up display names in CfgAssignees table
3. Using Reporter.Name as fallback when Reporter is empty
4. Failing with CRITICAL error if resolution fails

author:
    Julien (@tom4897)
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from ..models import (
    ColumnIndices,
    FixOutcome,
    IFixer,
    IRowRule,
    Problem,
    ProblemSeverity,
    ValidationContext,
    ValidationResult,
)

logger = logging.getLogger(__name__)


def is_cloud_account_id(value: str) -> bool:
    """Check if value is Cloud accountId format: NUMBER:HEXA."""
    if ":" not in value:
        return False
    parts = value.split(":", 1)
    return parts[0].isdigit() and len(parts[1]) > 10


def is_display_name(value: str) -> bool:
    """Check if value looks like a display name (contains spaces)."""
    return " " in value.strip()


def _cell_str(row: Sequence[Any], idx: int | None) -> str:
    """Helper function to safely extract string values from cells."""
    if idx is None or idx < 0 or idx >= len(row):
        return ""
    v = row[idx]
    return "" if v is None else str(v).strip()


def _get_table_config(ctx: ValidationContext) -> Any:
    """Get Excel table configuration from the context."""
    # Access the underlying config object directly (needed for Excel table config)
    underlying_config = getattr(ctx.config, "_cfg", ctx.config)
    if hasattr(underlying_config, "get_table_config"):
        return underlying_config.get_table_config()
    return None


@dataclass(slots=True)
class ReporterResolverFixer(IFixer):
    """Resolves reporter names to accountIds using CfgAssignees table.

    Fixes:
      - reporter.display_name -> replace with accountId from CfgAssignees
      - reporter.empty_with_name -> populate from Reporter.Name lookup
      - reporter.not_found -> CRITICAL error to stop processing

    Notes:
      - Cloud accountIds (NUMBER:HEXA format) are used directly
      - DC reporter IDs (any other format) are used directly
      - Display names (containing spaces) trigger lookup
      - Reporter.Name is used as fallback when Reporter is empty
    """

    def apply(self, problem: Problem, row: Sequence[Any], indices: ColumnIndices, ctx: ValidationContext) -> FixOutcome:
        """Apply reporter resolution fix."""
        # Only handle reporter-related problems
        if not problem.code.startswith("reporter."):
            return FixOutcome(applied=False)

        reporter_value = _cell_str(row, indices.reporter)
        reporter_name_value = _cell_str(row, indices.reporter_name)

        # Reporter has value
        if reporter_value:
            # Check if it's already a Cloud accountId
            if is_cloud_account_id(reporter_value):
                logger.debug(f"Row {ctx.row_index}: Using Cloud accountId directly for reporter: {reporter_value}")
                return FixOutcome(applied=False)  # No fix needed

            # Check if it's a display name (contains spaces)
            if is_display_name(reporter_value):
                logger.debug(f"Row {ctx.row_index}: Resolving reporter display name: {reporter_value}")
                if indices.reporter is not None:
                    return self._resolve_display_name(reporter_value, indices.reporter, ctx)

            # Otherwise, treat as DC reporter ID (use directly)
            logger.debug(f"Row {ctx.row_index}: Using DC reporter ID directly: {reporter_value}")
            return FixOutcome(applied=False)  # No fix needed

        # Reporter is empty, but Reporter.Name exists
        if reporter_name_value:
            logger.debug(f"Row {ctx.row_index}: Using Reporter.Name fallback: {reporter_name_value}")
            if indices.reporter is not None:
                return self._resolve_display_name(reporter_name_value, indices.reporter, ctx)

        # Both are empty - no reporter (this is OK)
        logger.debug(f"Row {ctx.row_index}: No reporter specified")
        return FixOutcome(applied=False)  # No fix needed

    def _resolve_display_name(self, display_name: str, reporter_index: int, ctx: ValidationContext) -> FixOutcome:
        """Resolve a reporter display name to accountId using CfgAssignees table."""
        table_config = _get_table_config(ctx)
        if not table_config:
            # This should not happen as the rule already checked, but handle gracefully
            logger.error(
                f"Row {ctx.row_index}: Cannot resolve reporter '{display_name}' - no CfgAssignees table available"
            )
            return FixOutcome(applied=False)

        # Look up the reporter in the assignees table (shared user directory)
        reporter_config = table_config.get_assignee_by_name(display_name)
        if not reporter_config:
            # This should not happen as the rule already checked, but handle gracefully
            logger.error(f"Row {ctx.row_index}: Reporter '{display_name}' not found in CfgAssignees table")
            return FixOutcome(applied=False)

        # Found the reporter - apply the fix
        logger.info(f"Row {ctx.row_index}: Resolved reporter '{display_name}' to accountId '{reporter_config.id}'")
        return FixOutcome(
            applied=True,
            patch={reporter_index: reporter_config.id},
            notes=f"Resolved reporter '{display_name}' to accountId '{reporter_config.id}'",
        )


@dataclass(slots=True)
class ReporterResolverRule(IRowRule):
    """Rule that generates problems for reporter resolution."""

    def apply(self, row: Sequence[Any], indices: ColumnIndices, ctx: ValidationContext) -> ValidationResult:
        """Validate reporter fields and generate problems for resolution."""
        problems: list[Problem] = []

        reporter_value = _cell_str(row, indices.reporter)
        reporter_name_value = _cell_str(row, indices.reporter_name)

        # Reporter has value
        if reporter_value:
            # Check if it's a display name (contains spaces)
            if is_display_name(reporter_value):
                # Check if we can resolve it
                table_config = _get_table_config(ctx)
                if not table_config:
                    problems.append(
                        Problem(
                            code="reporter.no_table_config",
                            message=(
                                f"Cannot resolve reporter '{reporter_value}' - no CfgAssignees table available"
                            ),
                            severity=ProblemSeverity.CRITICAL,
                            row_index=ctx.row_index,
                            col_key="reporter",
                        )
                    )
                elif not table_config.get_assignee_by_name(reporter_value):
                    problems.append(
                        Problem(
                            code="reporter.not_found",
                            message=f"Reporter '{reporter_value}' not found in CfgAssignees table",
                            severity=ProblemSeverity.CRITICAL,
                            row_index=ctx.row_index,
                            col_key="reporter",
                        )
                    )
                else:
                    problems.append(
                        Problem(
                            code="reporter.display_name",
                            message=(
                                f"Reporter contains display name '{reporter_value}' - will resolve to accountId"
                            ),
                            severity=ProblemSeverity.FIX,
                            row_index=ctx.row_index,
                            col_key="reporter",
                        )
                    )

        # Reporter is empty, but Reporter.Name exists
        elif reporter_name_value:
            # Check if we can resolve it
            table_config = _get_table_config(ctx)
            if not table_config:
                problems.append(
                    Problem(
                        code="reporter.no_table_config",
                        message=(
                            f"Cannot resolve reporter '{reporter_name_value}' - no CfgAssignees table available"
                        ),
                        severity=ProblemSeverity.CRITICAL,
                        row_index=ctx.row_index,
                        col_key="reporter",
                    )
                )
            elif not table_config.get_assignee_by_name(reporter_name_value):
                problems.append(
                    Problem(
                        code="reporter.not_found",
                        message=f"Reporter '{reporter_name_value}' not found in CfgAssignees table",
                        severity=ProblemSeverity.CRITICAL,
                        row_index=ctx.row_index,
                        col_key="reporter",
                    )
                )
            else:
                problems.append(
                    Problem(
                        code="reporter.empty_with_name",
                        message=(
                            "Reporter is empty but Reporter.Name is "
                            f"'{reporter_name_value}' - will resolve to accountId"
                        ),
                        severity=ProblemSeverity.FIX,
                        row_index=ctx.row_index,
                        col_key="reporter",
                    )
                )

        return ValidationResult(problems=tuple(problems))
