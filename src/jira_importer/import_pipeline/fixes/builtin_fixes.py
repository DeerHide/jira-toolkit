"""
script name: builtin_fixes.py
description: This script contains the built-in fixes for the Jira Importer.
author: Julien (@tom4897)
license: MIT
date: 2025
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Sequence

import re

from ..models import (
    IFixer,
    FixOutcome,
    Problem,
    ProblemSeverity,
    ValidationContext,
    ColumnIndices,
)

# helpers functions

def _cell_str(row: Sequence[Any], idx: Optional[int]) -> str:
    if idx is None or idx < 0 or idx >= len(row):
        return ""
    v = row[idx]
    return "" if v is None else str(v).strip()

def _int_try(s: str) -> Optional[int]:
    try:
        return int(s)
    except Exception:
        return None

def _canonical_priority(value: str, *, allowed: list[str]) -> Optional[str]:
    """Return canonical priority label if value matches (case-insensitive), else None."""
    v = value.strip()
    if not v:
        return None
    # exact (fast path)
    if v in allowed:
        return v
    lower_map = {a.lower(): a for a in allowed}
    # numeric mapping like '1' => first allowed
    as_int = _int_try(v)
    if as_int is not None and 1 <= as_int <= len(allowed):
        return allowed[as_int - 1]
    # case-insensitive match
    return lower_map.get(v.lower())

def _cfg_get(ctx: ValidationContext, key: str, default: Any) -> Any:
    g = getattr(ctx.config, "get", None)
    return g(key, default) if callable(g) else default

# fixes definitions

@dataclass(slots=True)
class ProjectKeyFixer(IFixer):
    """
    Fixes:
      - project_key.missing  -> set to configured key (if available)
      - project_key.mismatch -> override with configured key
    Notes:
      - Column may be absent (optional) → no-op
      - Config key: 'jira.project.key' should contain the canonical project key
    """
    def apply(self, problem: Problem, row: Sequence[Any], indices: ColumnIndices, ctx: ValidationContext) -> FixOutcome:
        if indices.project_key is None:
            return FixOutcome(applied=False)

        if problem.code not in {"project_key.missing", "project_key.mismatch"}:
            return FixOutcome(applied=False)

        expected = _cfg_get(ctx, "jira.project.key", None)
        if not expected:
            return FixOutcome(applied=False)

        return FixOutcome(
            applied=True,
            patch={indices.project_key: str(expected)},
            notes=f"Project Key set to '{expected}'.",
        )


@dataclass(slots=True)
class PriorityNormalizeFixer(IFixer):
    """
    Normalizes priority to a canonical label list.

    Config (optional):
      - validation.allowed_priorities: list[str]
        default: ["Highest","High","Medium","Low","Lowest"]
      - validation.priority.number_map: bool
        if true, '1'->first allowed, '2'->second, etc. (default: true)
    """
    def apply(self, problem: Problem, row: Sequence[Any], indices: ColumnIndices, ctx: ValidationContext) -> FixOutcome:
        if indices.priority is None:
            return FixOutcome(applied=False)
        if problem.col_key not in {None, "priority"}:
            return FixOutcome(applied=False)
        if problem.code not in {"priority.invalid", "priority.missing"}:
            return FixOutcome(applied=False)

        allowed = list(_cfg_get(ctx, "validation.allowed_priorities", ["Highest", "High", "Medium", "Low", "Lowest"]))
        val = _cell_str(row, indices.priority)

        # If empty priority, choose to no-op by default (teams may prefer manual fill).
        if val == "":
            return FixOutcome(applied=False)

        canon = _canonical_priority(val, allowed=allowed)
        if not canon:
            # Try number mapping only if enabled
            if bool(_cfg_get(ctx, "validation.priority.number_map", True)):
                as_int = _int_try(val)
                if as_int is not None and 1 <= as_int <= len(allowed):
                    canon = allowed[as_int - 1]

        if not canon or canon == val:
            return FixOutcome(applied=False)

        return FixOutcome(applied=True, patch={indices.priority: canon}, notes=f"Priority normalized to '{canon}'.")

@dataclass(slots=True)
class EstimateNormalizeFixer(IFixer):
    """
    Parses human-friendly estimates and normalizes them to the target unit.

    Input examples accepted (case-insensitive):
      '1w 2d 3h 30m', '2h', '45m', '3600', '90' (int per config)
    Config (optional):
      - validation.estimate.accept_integers_as: 'seconds' | 'minutes' (default 'seconds')
      - output.estimate.unit: 'seconds' | 'minutes' (default 'seconds')
      - time.h_per_day: int (default 8)
      - time.wd_per_week: int (default 5)
    """
    def apply(self, problem: Problem, row: Sequence[Any], indices: ColumnIndices, ctx: ValidationContext) -> FixOutcome:
        # Only handle estimate-format problems
        if problem.code != "estimate.invalid_format":
            return FixOutcome(applied=False)

        # Choose which column to normalize based on the problem's col_key
        key = (problem.col_key or "").lower()
        if key == "estimate":
            col_idx = indices.estimate
        elif key == "origest":
            col_idx = indices.origest
        else:
            col_idx = None

        if col_idx is None:
            return FixOutcome(applied=False)

        raw = _cell_str(row, col_idx)
        if not raw:
            return FixOutcome(applied=False)

        accept_as = _cfg_get(ctx, "validation.estimate.accept_integers_as", "seconds")
        out_unit = _cfg_get(ctx, "output.estimate.unit", "seconds")
        h_per_day = int(_cfg_get(ctx, "time.h_per_day", 8))
        wd_per_week = int(_cfg_get(ctx, "time.wd_per_week", 5))

        seconds = _parse_estimate_to_seconds(
            raw,
            accept_int_as=accept_as,
            hours_per_day=h_per_day,
            workdays_per_week=wd_per_week,
        )
        if seconds is None:
            return FixOutcome(applied=False)

        normalized = str(seconds if out_unit == "seconds" else seconds // 60)
        return FixOutcome(
            applied=True,
            patch={col_idx: normalized},
            notes=f"Estimate normalized to {normalized} {out_unit}.",
        )



_EST_TOKEN_RE = re.compile(r"(?P<num>\d+)\s*(?P<unit>[wdhms])", re.IGNORECASE)

def _parse_estimate_to_seconds(
    value: str,
    *,
    accept_int_as: str = "seconds",
    hours_per_day: int = 8,
    workdays_per_week: int = 5,
) -> Optional[int]:
    """
    Parse estimates into SECONDS.
    Supports:
      - tokenized: '1w 2d 3h 30m', '2h', '45m', '30s'
      - chained:   '1w2d3h30m', '2h30m'
      - plain int: interpreted as 'accept_int_as' ('seconds' | 'minutes')
    """
    s = value.strip().lower()
    if not s:
        return None

    if s.isdigit():
        n = int(s)
        return n * 60 if accept_int_as == "minutes" else n

    total_minutes = 0.0
    pos = 0
    while pos < len(s):
        m = _EST_TOKEN_RE.match(s, pos)
        if not m:
            if s[pos].isspace():
                pos += 1
                continue
            return None
        qty = float(m.group("num"))
        unit = m.group("unit")
        if unit == "w":
            total_minutes += qty * workdays_per_week * hours_per_day * 60
        elif unit == "d":
            total_minutes += qty * hours_per_day * 60
        elif unit == "h":
            total_minutes += qty * 60
        elif unit == "m":
            total_minutes += qty
        elif unit == "s":
            total_minutes += qty / 60.0
        pos = m.end()

    return int(round(total_minutes * 60))


@dataclass(slots=True)
class AssignIssueIdFixer(IFixer):
    """
    Assigns a unique temporary IssueId when missing.

    Strategy:
      - Use configurable prefix (default None - no prefix)
      - Produce '0001', '0002', ... or 'TMP-0001', 'TMP-0002', ... (row-index seeded, collision-checked)
      - Ensure per-file uniqueness via ValidationContext.seen_issue_id()
    Config (optional):
      - issueid.prefix: str | None (default None - no prefix)
      - issueid.width: int (default 3)
    """
    def apply(self, problem: Problem, row: Sequence[Any], indices: ColumnIndices, ctx: ValidationContext) -> FixOutcome:
        if problem.code != "issueid.missing":
            return FixOutcome(applied=False)
        if indices.issue_id is None:
            return FixOutcome(applied=False)

        prefix = _cfg_get(ctx, "issueid.prefix", None)
        width = int(_cfg_get(ctx, "issueid.width", 3))

        # Start from row index and search for the next free id.
        n = max(1, int(problem.row_index or 1))
        for attempt in range(n, n + 100000):  # hard cap to avoid infinite loop
            candidate = f"{prefix or ''}{attempt:0{width}d}"
            # seen_issue_id() records if not seen and returns False
            if not ctx.seen_issue_id(candidate):
                return FixOutcome(applied=True, patch={indices.issue_id: candidate}, notes=f"IssueId assigned '{candidate}'.")

        # Fallback: give up gracefully (extremely unlikely)
        return FixOutcome(applied=False)

# factory function

def get_builtin_fixers() -> Dict[str, IFixer]:
    """
    Returns a mapping of problem.code -> IFixer instance for built-ins.
    A registry can consume this and register them accordingly.
    """
    return {
        "project_key.missing": ProjectKeyFixer(),
        "project_key.mismatch": ProjectKeyFixer(),
        "priority.invalid":     PriorityNormalizeFixer(),
        "priority.missing":     PriorityNormalizeFixer(),
        "estimate.invalid_format": EstimateNormalizeFixer(),
        "issueid.missing":      AssignIssueIdFixer(),
    }
