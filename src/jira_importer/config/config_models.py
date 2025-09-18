"""Description: This script contains models for Excel table-based configuration.

Author:
    Julien (@tom4897)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class AssigneeConfig:
    """Configuration for assignee mapping."""

    name: str
    id: str


@dataclass(slots=True, frozen=True)
class SprintConfig:
    """Configuration for sprint mapping."""

    name: str
    id: str


@dataclass(slots=True, frozen=True)
class FixVersionConfig:
    """Configuration for fix version mapping."""

    name: str


@dataclass(slots=True, frozen=True)
class ComponentConfig:
    """Configuration for component mapping."""

    name: str


@dataclass(slots=True, frozen=True)
class IssueTypeConfig:
    """Configuration for issue type mapping."""

    name: str


@dataclass(slots=True, frozen=True)
class IgnoreListConfig:
    """Configuration for ignore list items."""

    name: str


@dataclass(slots=True, frozen=True)
class PriorityConfig:
    """Configuration for priority mapping."""

    name: str


@dataclass(slots=True, frozen=True)
class AutoFieldValueConfig:
    """Configuration for auto field values."""

    name: str
    value: str


@dataclass(slots=True, frozen=True)
class TeamConfig:
    """Configuration for team mapping."""

    name: str
    id: str


@dataclass(slots=True)
class ExcelTableConfig:  # pylint: disable=too-many-instance-attributes
    """Container for all Excel table-based configuration data.

    This class holds all the structured configuration data read from Excel tables,
    providing a clean interface for accessing configuration values by category.
    """

    # Table data - grouped by logical categories
    assignees: list[AssigneeConfig] | None = None
    sprints: list[SprintConfig] | None = None
    fix_versions: list[FixVersionConfig] | None = None
    components: list[ComponentConfig] | None = None
    issue_types: list[IssueTypeConfig] | None = None
    ignore_list: list[IgnoreListConfig] | None = None
    priorities: list[PriorityConfig] | None = None
    auto_field_values: list[AutoFieldValueConfig] | None = None

    def __post_init__(self):
        """Initialize empty lists if None."""
        if self.assignees is None:
            object.__setattr__(self, "assignees", [])
        if self.sprints is None:
            object.__setattr__(self, "sprints", [])
        if self.fix_versions is None:
            object.__setattr__(self, "fix_versions", [])
        if self.components is None:
            object.__setattr__(self, "components", [])
        if self.issue_types is None:
            object.__setattr__(self, "issue_types", [])
        if self.ignore_list is None:
            object.__setattr__(self, "ignore_list", [])
        if self.priorities is None:
            object.__setattr__(self, "priorities", [])
        if self.auto_field_values is None:
            object.__setattr__(self, "auto_field_values", [])

    def get_assignee_by_name(self, assignee_name: str) -> AssigneeConfig | None:
        """Get assignee configuration by name."""
        return next((a for a in (self.assignees or []) if a.name == assignee_name), None)

    def get_assignee_by_id(self, assignee_id: str) -> AssigneeConfig | None:
        """Get assignee configuration by ID."""
        return next((a for a in (self.assignees or []) if a.id == assignee_id), None)

    def get_sprint_by_name(self, sprint_name: str) -> SprintConfig | None:
        """Get sprint configuration by name."""
        return next((s for s in (self.sprints or []) if s.name == sprint_name), None)

    def get_sprint_by_id(self, sprint_id: str) -> SprintConfig | None:
        """Get sprint configuration by ID."""
        return next((s for s in (self.sprints or []) if s.id == sprint_id), None)

    def get_fix_version_by_name(self, fix_version_name: str) -> FixVersionConfig | None:
        """Get fix version configuration by name."""
        return next((f for f in (self.fix_versions or []) if f.name == fix_version_name), None)

    def get_component_by_name(self, component_name: str) -> ComponentConfig | None:
        """Get component configuration by name."""
        return next((c for c in (self.components or []) if c.name == component_name), None)

    def get_issue_type_by_name(self, issue_type_name: str) -> IssueTypeConfig | None:
        """Get issue type configuration by name."""
        return next((i for i in (self.issue_types or []) if i.name == issue_type_name), None)

    def get_priority_by_name(self, priority_name: str) -> PriorityConfig | None:
        """Get priority configuration by name."""
        return next((p for p in (self.priorities or []) if p.name == priority_name), None)

    def get_auto_field_value(self, field_name: str) -> str | None:
        """Get auto field value by name."""
        config = next((a for a in (self.auto_field_values or []) if a.name == field_name), None)
        return config.value if config else None

    def is_ignored(self, item_name: str) -> bool:
        """Check if a name is in the ignore list."""
        return any(item.name == item_name for item in (self.ignore_list or []))

    def get_all_assignee_names(self) -> list[str]:
        """Get all assignee names."""
        return [a.name for a in (self.assignees or [])]

    def get_all_sprint_names(self) -> list[str]:
        """Get all sprint names."""
        return [s.name for s in (self.sprints or [])]

    def get_all_fix_version_names(self) -> list[str]:
        """Get all fix version names."""
        return [f.name for f in (self.fix_versions or [])]

    def get_all_component_names(self) -> list[str]:
        """Get all component names."""
        return [c.name for c in (self.components or [])]

    def get_all_issue_type_names(self) -> list[str]:
        """Get all issue type names."""
        return [i.name for i in (self.issue_types or [])]

    def get_all_priority_names(self) -> list[str]:
        """Get all priority names."""
        return [p.name for p in (self.priorities or [])]

    def get_all_ignore_list_names(self) -> list[str]:
        """Get all ignore list names."""
        return [i.name for i in (self.ignore_list or [])]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for compatibility with existing config system."""
        return {
            "assignees": [{"name": a.name, "id": a.id} for a in (self.assignees or [])],
            "sprints": [{"name": s.name, "id": s.id} for s in (self.sprints or [])],
            "fix_versions": [{"name": f.name} for f in (self.fix_versions or [])],
            "components": [{"name": c.name} for c in (self.components or [])],
            "issue_types": [{"name": i.name} for i in (self.issue_types or [])],
            "ignore_list": [{"name": i.name} for i in (self.ignore_list or [])],
            "priorities": [{"name": p.name} for p in (self.priorities or [])],
            "auto_field_values": [{"name": a.name, "value": a.value} for a in (self.auto_field_values or [])],
        }
