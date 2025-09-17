"""description: This script contains the registry for the Jira Importer.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import IRowRule
from .builtin_rules import (
    EstimateFormatRule,
    IssueIdPresenceRule,
    IssueTypeAllowedRule,
    PriorityAllowedRule,
    ProjectKeyConsistencyRule,
    SummaryRequiredRule,
)


@dataclass(slots=True)
class RuleRegistry:
    """Simple container returning a deterministic list of row rules."""

    rules: list[IRowRule]

    def get_rules(self) -> list[IRowRule]:
        """Already ordered; return a shallow copy to avoid external mutation."""
        return list(self.rules)


def build_registry(config_view, excel_ctx: object | None) -> RuleRegistry:  # pylint: disable=unused-argument
    """Compose built-in rules and, later, Excel-defined rules.

    For now we only return a conservative, stable set of built-ins.
    """
    rules: list[IRowRule] = []

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
