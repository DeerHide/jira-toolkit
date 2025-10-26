"""Assignee resolution fixer for Jira Importer.

This fixer handles assignee resolution by:
1. Detecting Cloud accountId format vs display names
2. Looking up display names in CfgAssignees table
3. Using Assignee.Name as fallback when Assignee is empty
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
class AssigneeResolverFixer(IFixer):
    """Resolves assignee names to accountIds using CfgAssignees table.

    Fixes:
      - assignee.display_name -> replace with accountId from CfgAssignees
      - assignee.empty_with_name -> populate from Assignee.Name lookup
      - assignee.not_found -> CRITICAL error to stop processing

    Notes:
      - Cloud accountIds (NUMBER:HEXA format) are used directly
      - DC assignee IDs (any other format) are used directly
      - Display names (containing spaces) trigger lookup
      - Assignee.Name is used as fallback when Assignee is empty
    """

    def apply(self, problem: Problem, row: Sequence[Any], indices: ColumnIndices, ctx: ValidationContext) -> FixOutcome:
        """Apply assignee resolution fix."""
        # Only handle assignee-related problems
        if not problem.code.startswith("assignee."):
            return FixOutcome(applied=False)

        assignee_value = _cell_str(row, indices.assignee)
        assignee_name_value = _cell_str(row, indices.assignee_name)

        # Case 1: Assignee has value
        if assignee_value:
            # Check if it's already a Cloud accountId
            if is_cloud_account_id(assignee_value):
                logger.debug(f"Row {ctx.row_index}: Using Cloud accountId directly: {assignee_value}")
                return FixOutcome(applied=False)  # No fix needed

            # Check if it's a display name (contains spaces)
            if is_display_name(assignee_value):
                logger.debug(f"Row {ctx.row_index}: Resolving display name: {assignee_value}")
                if indices.assignee is not None:
                    return self._resolve_display_name(assignee_value, indices.assignee, ctx)

            # Otherwise, treat as DC assignee ID (use directly)
            logger.debug(f"Row {ctx.row_index}: Using DC assignee ID directly: {assignee_value}")
            return FixOutcome(applied=False)  # No fix needed

        # Case 2: Assignee is empty, but Assignee.Name exists
        if assignee_name_value:
            logger.debug(f"Row {ctx.row_index}: Using Assignee.Name fallback: {assignee_name_value}")
            if indices.assignee is not None:
                return self._resolve_display_name(assignee_name_value, indices.assignee, ctx)

        # Case 3: Both are empty - no assignee (this is OK)
        logger.debug(f"Row {ctx.row_index}: No assignee specified")
        return FixOutcome(applied=False)  # No fix needed

    def _resolve_display_name(self, display_name: str, assignee_index: int, ctx: ValidationContext) -> FixOutcome:
        """Resolve a display name to accountId using CfgAssignees table."""
        table_config = _get_table_config(ctx)
        if not table_config:
            # This should not happen as the rule already checked, but handle gracefully
            logger.error(
                f"Row {ctx.row_index}: Cannot resolve assignee '{display_name}' - no CfgAssignees table available"
            )
            return FixOutcome(applied=False)

        # Look up the assignee in the table
        assignee_config = table_config.get_assignee_by_name(display_name)
        if not assignee_config:
            # This should not happen as the rule already checked, but handle gracefully
            logger.error(f"Row {ctx.row_index}: Assignee '{display_name}' not found in CfgAssignees table")
            return FixOutcome(applied=False)

        # Found the assignee - apply the fix
        logger.info(f"Row {ctx.row_index}: Resolved assignee '{display_name}' to accountId '{assignee_config.id}'")
        return FixOutcome(
            applied=True,
            patch={assignee_index: assignee_config.id},
            notes=f"Resolved assignee '{display_name}' to accountId '{assignee_config.id}'",
        )


# Create a validator that generates problems for assignee resolution
@dataclass(slots=True)
class AssigneeResolverRule(IRowRule):
    """Rule that generates problems for assignee resolution."""

    def apply(self, row: Sequence[Any], indices: ColumnIndices, ctx: ValidationContext) -> ValidationResult:
        """Validate assignee fields and generate problems for resolution."""
        problems = []

        assignee_value = _cell_str(row, indices.assignee)
        assignee_name_value = _cell_str(row, indices.assignee_name)

        # Case 1: Assignee has value
        if assignee_value:
            # Check if it's a display name (contains spaces)
            if is_display_name(assignee_value):
                # Check if we can resolve it
                table_config = _get_table_config(ctx)
                if not table_config:
                    problems.append(
                        Problem(
                            code="assignee.no_table_config",
                            message=f"Cannot resolve assignee '{assignee_value}' - no CfgAssignees table available",
                            severity=ProblemSeverity.CRITICAL,
                            row_index=ctx.row_index,
                            col_key="assignee",
                        )
                    )
                elif not table_config.get_assignee_by_name(assignee_value):
                    problems.append(
                        Problem(
                            code="assignee.not_found",
                            message=f"Assignee '{assignee_value}' not found in CfgAssignees table",
                            severity=ProblemSeverity.CRITICAL,
                            row_index=ctx.row_index,
                            col_key="assignee",
                        )
                    )
                else:
                    problems.append(
                        Problem(
                            code="assignee.display_name",
                            message=f"Assignee contains display name '{assignee_value}' - will resolve to accountId",
                            severity=ProblemSeverity.FIX,
                            row_index=ctx.row_index,
                            col_key="assignee",
                        )
                    )

        # Case 2: Assignee is empty, but Assignee.Name exists
        elif assignee_name_value:
            # Check if we can resolve it
            table_config = _get_table_config(ctx)
            if not table_config:
                problems.append(
                    Problem(
                        code="assignee.no_table_config",
                        message=f"Cannot resolve assignee '{assignee_name_value}' - no CfgAssignees table available",
                        severity=ProblemSeverity.CRITICAL,
                        row_index=ctx.row_index,
                        col_key="assignee",
                    )
                )
            elif not table_config.get_assignee_by_name(assignee_name_value):
                problems.append(
                    Problem(
                        code="assignee.not_found",
                        message=f"Assignee '{assignee_name_value}' not found in CfgAssignees table",
                        severity=ProblemSeverity.CRITICAL,
                        row_index=ctx.row_index,
                        col_key="assignee",
                    )
                )
            else:
                problems.append(
                    Problem(
                        code="assignee.empty_with_name",
                        message=f"Assignee is empty but Assignee.Name is '{assignee_name_value}' - will resolve to accountId",
                        severity=ProblemSeverity.FIX,
                        row_index=ctx.row_index,
                        col_key="assignee",
                    )
                )

        return ValidationResult(problems=tuple(problems))
