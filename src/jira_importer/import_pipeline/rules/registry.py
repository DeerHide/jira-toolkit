"""description: This script contains the registry for the Jira Importer.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

from dataclasses import dataclass

from ..fixes.assignee_resolver import AssigneeResolverRule
from ..fixes.reporter_resolver import ReporterResolverRule
from ..fixes.team_resolver import TeamResolverRule
from ..models import IRowRule
from .builtin_rules import (
    ComponentsAllowedRule,
    EstimateFormatRule,
    IssueIdPresenceRule,
    IssueTypeAllowedRule,
    ParentLinkValidationRule,
    PriorityAllowedRule,
    ProjectKeyConsistencyRule,
    SummaryRequiredRule,
)
from .custom_field_rule import CustomFieldValidationRule


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
    rules.append(ComponentsAllowedRule())
    rules.append(IssueIdPresenceRule())
    rules.append(EstimateFormatRule())
    rules.append(ParentLinkValidationRule())  # Add parent link validation rule
    rules.append(AssigneeResolverRule())  # Add assignee resolution rule
    rules.append(ReporterResolverRule())  # Add reporter resolution rule
    rules.append(TeamResolverRule())  # Add team resolution rule
    rules.append(CustomFieldValidationRule())

    # TODO: if excel_ctx provided, extend with excel_rule_loader.compile(excel_ctx)
    # and insert with explicit 'order' fields.

    return RuleRegistry(rules=rules)
