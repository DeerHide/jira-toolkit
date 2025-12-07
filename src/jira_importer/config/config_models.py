"""Description: This script contains models for Excel table-based configuration.

Author:
    Julien (@tom4897)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

from ..errors import ConfigurationError

logger = logging.getLogger(__name__)


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


@dataclass(slots=True, frozen=True)
class CustomFieldConfig:
    """Configuration for custom field mapping.

    Attributes:
        name: User-friendly name that must match Excel column header (normalized).
        id: Jira custom field ID (e.g., "customfield_10125").
        type: Field type - one of "text", "number", "date", or "select".
    """

    name: str
    id: str
    type: Literal["text", "number", "date", "select"]


def parse_custom_fields(cfg_view: Any) -> list[CustomFieldConfig]:
    """Parse custom field definitions from JSON config.

    Args:
        cfg_view: Configuration view (ConfigView instance).

    Returns:
        List of CustomFieldConfig instances.

    Raises:
        ConfigurationError: If invalid field type or missing required fields.
    """
    from .config_view import ConfigView

    if not isinstance(cfg_view, ConfigView):
        cfg_view = ConfigView(cfg_view)

    # Use direct nested access to avoid ConfigView.get() calling dict.get() on dotted keys
    # ConfigView.get() has a bug where it calls the underlying dict.get() for dotted keys
    # instead of walking the path. We'll access it directly.
    jira_data = cfg_view.get("jira", {})
    if isinstance(jira_data, dict):
        custom_fields_data = jira_data.get("custom_fields", [])
    else:
        custom_fields_data = cfg_view.get("jira.custom_fields", [])

    if not custom_fields_data:
        return []

    custom_fields = []
    seen_ids: dict[str, CustomFieldConfig] = {}
    seen_names: dict[str, CustomFieldConfig] = {}

    # Normalize names for comparison
    def normalize_name(name: str) -> str:
        return name.strip().lower()

    for cf_data in custom_fields_data:
        if not isinstance(cf_data, dict):
            raise ConfigurationError(
                f"Invalid custom field definition: expected dict, got {type(cf_data).__name__}",
                details={"custom_field_data": cf_data},
            )

        name = str(cf_data.get("name", "")).strip()
        field_id = str(cf_data.get("id", "")).strip()
        field_type = str(cf_data.get("type", "")).strip().lower()

        if not name:
            raise ConfigurationError("Custom field definition missing 'name'", details={"custom_field_data": cf_data})

        if not field_id:
            raise ConfigurationError(
                f"Custom field definition missing 'id' for field '{name}'",
                details={"custom_field_data": cf_data, "name": name},
            )

        if field_type not in ["text", "number", "date", "select"]:
            raise ConfigurationError(
                f"Invalid custom field type '{field_type}' for field '{name}'. Must be one of: text, number, date, select",
                details={"custom_field_data": cf_data, "name": name, "type": field_type},
            )

        # Check for duplicate id
        if field_id in seen_ids:
            raise ConfigurationError(
                f"Duplicate custom field id '{field_id}' found in JSON config. "
                f"First definition: '{seen_ids[field_id].name}', "
                f"Second definition: '{name}'",
                details={
                    "field_id": field_id,
                    "first_name": seen_ids[field_id].name,
                    "second_name": name,
                    "source": "JSON",
                },
            )

        # Check for name conflict (same name, different id)
        normalized_name = normalize_name(name)
        if normalized_name in seen_names:
            existing = seen_names[normalized_name]
            if existing.id != field_id:
                raise ConfigurationError(
                    f"Custom field name '{name}' is defined for multiple field ids in JSON: "
                    f"'{existing.id}' and '{field_id}'",
                    details={"field_name": name, "first_id": existing.id, "second_id": field_id, "source": "JSON"},
                )

        cfg = CustomFieldConfig(
            name=name,
            id=field_id,
            type=field_type,  # type: ignore[arg-type]
        )

        custom_fields.append(cfg)
        seen_ids[field_id] = cfg
        seen_names[normalized_name] = cfg

    return custom_fields


def get_custom_field_configs(config: Any, cfg_view: Any) -> list[CustomFieldConfig]:
    """Get custom field configs from the appropriate source based on config type.

    The config system already handles selecting between JSON and Excel configs based on command-line args.
    This function simply accesses the appropriate source:
    - ExcelConfiguration: Use config.table_config.custom_fields (from CfgCustomFields table)
    - JsonConfiguration: Use parse_custom_fields(cfg_view) (from jira.custom_fields in JSON)

    Args:
        config: Configuration object (JsonConfiguration or ExcelConfiguration).
        cfg_view: Configuration view for accessing JSON values.

    Returns:
        List of CustomFieldConfig instances from the active config source.
    """
    from .config_view import ConfigView
    from .excel_config import ExcelConfiguration

    if not isinstance(cfg_view, ConfigView):
        cfg_view = ConfigView(cfg_view)

    # Excel config mode: use table config
    if isinstance(config, ExcelConfiguration):
        # Load table config if not already loaded
        if config.table_config is None:
            try:
                config.load_table_config()
            except Exception as e:
                # If loading fails (e.g., workbook not initialized), return empty list
                logger.debug(f"Could not load table config for custom fields: {e}")
                return []
        table_config = config.get_table_config()
        if table_config and table_config.custom_fields:
            return table_config.custom_fields
        return []

    # JSON config mode: parse from JSON
    return parse_custom_fields(cfg_view)


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
    custom_fields: list[CustomFieldConfig] | None = None

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
        if self.custom_fields is None:
            object.__setattr__(self, "custom_fields", [])

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
