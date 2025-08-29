"""
Script Name: registry.py
Description: This script contains the registry for the Jira Importer.
Author: Julien (@tom4897)
License: MIT
Date: 2025
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, MutableMapping, Optional, Sequence

from ..models import (
    IFixer,
    FixOutcome,
    Problem,
    ColumnIndices,
    ValidationContext,
)
from .builtin_fixes import get_builtin_fixers


@dataclass(slots=True)
class FixRegistry:
    """
    Registry of fixers keyed by problem.code.

    Usage:
        registry = FixRegistry()
        registry.register("priority.invalid", PriorityNormalizeFixer())
        outcome = registry.apply(problem, row, indices, ctx)
    """
    _fixers: Dict[str, IFixer]

    def register(self, problem_code: str, fixer: IFixer) -> None:
        self._fixers[str(problem_code)] = fixer

    def unregister(self, problem_code: str) -> None:
        self._fixers.pop(str(problem_code), None)

    def has(self, problem_code: str) -> bool:
        return str(problem_code) in self._fixers

    def apply(
        self,
        problem: Problem,
        row: Sequence[object],
        indices: ColumnIndices,
        ctx: ValidationContext,
    ) -> FixOutcome:
        fixer = self._fixers.get(problem.code)
        if fixer is None:
            return FixOutcome(applied=False)
        # Defensive boundary: never let a buggy fixer crash validation.
        try:
            return fixer.apply(problem, row, indices, ctx)
        except Exception:
            return FixOutcome(applied=False)


def build_fix_registry(config_view) -> FixRegistry:
    """
    Build a registry populated with built-in fixers, honoring optional config:

    - validation.fixers.disabled : list[str] of problem codes to disable
      e.g., ["project_key.mismatch", "priority.missing"]

    You can extend this later to register custom fixers based on config.
    """
    fixers = get_builtin_fixers()  # type: Dict[str, IFixer]

    # Read optional disable list from config (duck-typed .get).
    disabled = set()
    get = getattr(config_view, "get", None)
    if callable(get):
        raw = config_view.get("validation.fixers.disabled", [])
        try:
            disabled = {str(x) for x in raw} if raw else set()
        except Exception:
            disabled = set()

    for code in list(fixers.keys()):
        if code in disabled:
            fixers.pop(code, None)

    return FixRegistry(_fixers=fixers)
