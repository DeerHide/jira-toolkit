"""Team resolution fixer for Jira Importer.

This fixer handles team resolution by:
1. Looking up symbolic team names in CfgTeams table
2. Using Team.Name as fallback when Team is empty
3. Failing with CRITICAL error if resolution fails (for non-empty values)

Author:
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
class TeamResolverFixer(IFixer):
    """Resolves team names to team IDs using CfgTeams table.

    Fixes:
      - team.display_name -> replace with Team.ID from CfgTeams
      - team.empty_with_name -> populate from Team.Name lookup

    Notes:
      - Empty values are ignored (no team specified).
      - If a value already matches a known Team.ID, it is used directly.
    """

    def apply(self, problem: Problem, row: Sequence[Any], indices: ColumnIndices, ctx: ValidationContext) -> FixOutcome:
        """Apply team resolution fix."""
        # Only handle team-related problems
        if not problem.code.startswith("team."):
            return FixOutcome(applied=False)

        team_value = _cell_str(row, indices.team)
        team_name_value = _cell_str(row, indices.team_name)

        # Case 1: Team has a value in the Team column
        if team_value:
            if indices.team is None:
                return FixOutcome(applied=False)
            return self._resolve_team_value(team_value, indices.team, ctx)

        # Case 2: Team is empty, but Team.Name exists
        if team_name_value:
            if indices.team is None:
                return FixOutcome(applied=False)
            return self._resolve_team_value(team_name_value, indices.team, ctx)

        # Case 3: Both are empty - no team (this is OK)
        logger.debug(f"Row {ctx.row_index}: No team specified")
        return FixOutcome(applied=False)

    def _resolve_team_value(self, value: str, team_index: int, ctx: ValidationContext) -> FixOutcome:
        """Resolve a team value (name or id) using CfgTeams table."""
        table_config = _get_table_config(ctx)
        if not table_config:
            # This should not happen as the rule already checked, but handle gracefully
            logger.error(f"Row {ctx.row_index}: Cannot resolve team '{value}' - no CfgTeams table available")
            return FixOutcome(applied=False)

        # 1) If value matches a known Team.ID, use it directly
        team_cfg = table_config.get_team_by_id(value)
        if team_cfg:
            logger.debug(f"Row {ctx.row_index}: Using Team.ID directly: {value}")
            return FixOutcome(applied=False)

        # 2) Try resolving by Team.Name
        team_cfg = table_config.get_team_by_name(value)
        if not team_cfg:
            logger.error(f"Row {ctx.row_index}: Team '{value}' not found in CfgTeams table")
            return FixOutcome(applied=False)

        logger.info(f"Row {ctx.row_index}: Resolved team '{value}' to id '{team_cfg.id}'")
        return FixOutcome(
            applied=True,
            patch={team_index: team_cfg.id},
            notes=f"Resolved team '{value}' to id '{team_cfg.id}'",
        )


@dataclass(slots=True)
class TeamResolverRule(IRowRule):
    """Rule that validates team fields and generates problems for resolution.

    Behaviour:
      - Empty Team / Team.Name is allowed (no problems).
      - Non-empty values must be resolvable via CfgTeams, otherwise CRITICAL.
    """

    def apply(self, row: Sequence[Any], indices: ColumnIndices, ctx: ValidationContext) -> ValidationResult:
        """Validate team fields and generate problems for resolution."""
        problems: list[Problem] = []

        team_value = _cell_str(row, indices.team)
        team_name_value = _cell_str(row, indices.team_name)

        # If both are empty, ignore (no team specified)
        if not team_value and not team_name_value:
            return ValidationResult.empty()

        # Choose the value to validate/resolve:
        # - Prefer explicit Team column if present
        # - Otherwise fall back to Team.Name
        source_value = team_value or team_name_value

        table_config = _get_table_config(ctx)
        if not table_config or not getattr(table_config, "teams", None):
            problems.append(
                Problem(
                    code="team.no_table_config",
                    message=f"Cannot resolve team '{source_value}' - no CfgTeams table available",
                    severity=ProblemSeverity.CRITICAL,
                    row_index=ctx.row_index,
                    col_key="team",
                )
            )
            return ValidationResult(problems=tuple(problems))

        # If it matches a known Team.ID, accept without further problems
        if table_config.get_team_by_id(source_value):
            return ValidationResult.empty()

        # If it matches a known Team.Name, record that it will be resolved (FIX)
        if table_config.get_team_by_name(source_value):
            code = "team.display_name" if team_value else "team.empty_with_name"
            message = (
                f"Team contains symbolic name '{source_value}' - will resolve to Team.ID"
                if team_value
                else f"Team is empty but Team.Name is '{source_value}' - will resolve to Team.ID"
            )
            problems.append(
                Problem(
                    code=code,
                    message=message,
                    severity=ProblemSeverity.FIX,
                    row_index=ctx.row_index,
                    col_key="team",
                )
            )
            return ValidationResult(problems=tuple(problems))

        # Otherwise, unresolvable non-empty value → CRITICAL
        problems.append(
            Problem(
                code="team.not_found",
                message=f"Team '{source_value}' not found in CfgTeams table",
                severity=ProblemSeverity.CRITICAL,
                row_index=ctx.row_index,
                col_key="team",
            )
        )
        return ValidationResult(problems=tuple(problems))
