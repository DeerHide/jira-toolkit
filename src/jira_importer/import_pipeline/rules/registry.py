"""
script name: registry.py
description: This script contains the registry for the Jira Importer.
author: Julien (@tom4897)
license: MIT
date: 2025
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..models import IRowRule
from .builtin_rules import (
    SummaryRequiredRule,
    IssueTypeAllowedRule,
    PriorityAllowedRule,
    IssueIdPresenceRule,
    EstimateFormatRule,
    ProjectKeyConsistencyRule,
)

@dataclass(slots=True)
class RuleRegistry:
    """Simple container returning a deterministic list of row rules."""
    rules: List[IRowRule]

    def get_rules(self) -> List[IRowRule]:
        # Already ordered; return a shallow copy to avoid external mutation.
        return list(self.rules)


def build_registry(config_view, excel_ctx: object | None) -> RuleRegistry:
    """
    Compose built-in rules and, later, Excel-defined rules.
    For now we only return a conservative, stable set of built-ins.
    """
    rules: List[IRowRule] = []

    # Order matters: normalize/required checks early, cross-field later.
    rules.append(ProjectKeyConsistencyRule())
    rules.append(SummaryRequiredRule())
    rules.append(IssueTypeAllowedRule())
    rules.append(PriorityAllowedRule())
    rules.append(IssueIdPresenceRule())
    rules.append(EstimateFormatRule())

    # TODO: if excel_ctx provided, extend with excel_rule_loader.compile(excel_ctx)
    # and insert with explicit 'order' fields.

    return RuleRegistry(rules=rules)
