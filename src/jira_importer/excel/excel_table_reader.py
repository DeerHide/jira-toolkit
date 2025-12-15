"""Description: This script contains utilities for reading structured Excel tables.

Author:
    Julien (@tom4897)
"""

from __future__ import annotations

import logging
from typing import Any

from ..config.config_models import (
    AssigneeConfig,
    AutoFieldValueConfig,
    ComponentConfig,
    CustomFieldConfig,
    ExcelTableConfig,
    FixVersionConfig,
    IgnoreListConfig,
    IssueTypeConfig,
    PriorityConfig,
    SprintConfig,
    TeamConfig,
)
from ..errors import ConfigurationError
from .excel_io import ExcelWorkbookManager

logger = logging.getLogger(__name__)


class ExcelTableReader:  # pylint: disable=too-few-public-methods
    """Reader for structured Excel configuration tables.

    This class handles the parsing of specific table structures from Excel files,
    converting them into typed configuration objects.
    """

    def __init__(self, workbook_manager: ExcelWorkbookManager):
        """Initialize the ExcelTableReader.

        Args:
            workbook_manager: ExcelWorkbookManager instance for reading data
        """
        self.workbook_manager = workbook_manager
        # Cache mapping of row id -> { lower_key: original_key }
        # to speed up case-insensitive lookups performed repeatedly per row.
        self._row_lower_key_cache: dict[int, dict[str, str]] = {}

    def read_all_tables(self, config_sheet: str = "Config") -> ExcelTableConfig:
        """Read all configuration tables from the Excel file.

        Args:
            config_sheet: Name of the sheet containing configuration tables

        Returns:
            ExcelTableConfig object containing all parsed table data
        """
        logger.debug(f"Reading all configuration tables from sheet '{config_sheet}'")

        return ExcelTableConfig(
            assignees=self._read_assignees(config_sheet),
            teams=self._read_teams(config_sheet),
            sprints=self._read_sprints(config_sheet),
            fix_versions=self._read_fix_versions(config_sheet),
            components=self._read_components(config_sheet),
            issue_types=self._read_issue_types(config_sheet),
            ignore_list=self._read_ignore_list(config_sheet),
            priorities=self._read_priorities(config_sheet),
            auto_field_values=self._read_auto_field_values(config_sheet),
            custom_fields=self._read_custom_fields(config_sheet),
        )

    def _read_assignees(self, sheet: str) -> list[AssigneeConfig]:
        """Read CfgAssignees table."""
        table_data = self.workbook_manager.read_table(sheet=sheet, table_name="CfgAssignees")
        assignees = []

        for row in table_data:
            name = self._get_cell_value(row, "Assignee.Name")
            id_value = self._get_cell_value(row, "Assignee.ID")

            if name and id_value:
                assignees.append(AssigneeConfig(name=str(name), id=str(id_value)))
            else:
                logger.warning(f"Skipping incomplete assignee row: {row}")

        logger.debug(f"Read {len(assignees)} assignees from CfgAssignees table")
        return assignees

    def _read_teams(self, sheet: str) -> list[TeamConfig]:
        """Read CfgTeams table."""
        try:
            table_data = self.workbook_manager.read_table(sheet=sheet, table_name="CfgTeams")
        except Exception:
            # Table doesn't exist, return empty list
            return []

        teams: list[TeamConfig] = []

        for row in table_data:
            name = self._get_cell_value(row, "Team.Name")
            id_value = self._get_cell_value(row, "Team.ID")

            if name and id_value:
                teams.append(TeamConfig(name=str(name), id=str(id_value)))
            else:
                logger.warning(f"Skipping incomplete team row: {row}")

        logger.debug(f"Read {len(teams)} teams from CfgTeams table")
        return teams

    def _read_sprints(self, sheet: str) -> list[SprintConfig]:
        """Read CfgSprints table."""
        table_data = self.workbook_manager.read_table(sheet=sheet, table_name="CfgSprints")
        sprints = []

        for row in table_data:
            name = self._get_cell_value(row, "Sprint.Name")
            id_value = self._get_cell_value(row, "Sprint.ID")

            if name and id_value:
                sprints.append(SprintConfig(name=str(name), id=str(id_value)))
            else:
                logger.warning(f"Skipping incomplete sprint row: {row}")

        logger.debug(f"Read {len(sprints)} sprints from CfgSprints table")
        return sprints

    def _read_fix_versions(self, sheet: str) -> list[FixVersionConfig]:
        """Read CfgFixVersions table."""
        table_data = self.workbook_manager.read_table(sheet=sheet, table_name="CfgFixVersions")
        fix_versions = []

        for row in table_data:
            name = self._get_cell_value(row, "FixVersion.Name")

            if name:
                fix_versions.append(FixVersionConfig(name=str(name)))
            else:
                logger.warning(f"Skipping incomplete fix version row: {row}")

        logger.debug(f"Read {len(fix_versions)} fix versions from CfgFixVersions table")
        return fix_versions

    def _read_components(self, sheet: str) -> list[ComponentConfig]:
        """Read CfgComponents table."""
        table_data = self.workbook_manager.read_table(sheet=sheet, table_name="CfgComponents")
        components = []

        for row in table_data:
            name = self._get_cell_value(row, "Component.Name")

            if name:
                components.append(ComponentConfig(name=str(name)))
            else:
                logger.warning(f"Skipping incomplete component row: {row}")

        logger.debug(f"Read {len(components)} components from CfgComponents table")
        return components

    def _read_issue_types(self, sheet: str) -> list[IssueTypeConfig]:
        """Read CfgIssueTypes table."""
        table_data = self.workbook_manager.read_table(sheet=sheet, table_name="CfgIssueTypes")
        issue_types = []

        for row in table_data:
            name = self._get_cell_value(row, "IssueType.Name")

            if name:
                issue_types.append(IssueTypeConfig(name=str(name)))
            else:
                logger.warning(f"Skipping incomplete issue type row: {row}")

        logger.debug(f"Read {len(issue_types)} issue types from CfgIssueTypes table")
        return issue_types

    def _read_ignore_list(self, sheet: str) -> list[IgnoreListConfig]:
        """Read CfgIgnoreList table."""
        table_data = self.workbook_manager.read_table(sheet=sheet, table_name="CfgIgnoreList")
        ignore_list = []

        for row in table_data:
            name = self._get_cell_value(row, "IgnoreList.Name")

            if name:
                ignore_list.append(IgnoreListConfig(name=str(name)))
            else:
                logger.warning(f"Skipping incomplete ignore list row: {row}")

        logger.debug(f"Read {len(ignore_list)} ignore list items from CfgIgnoreList table")
        return ignore_list

    def _read_priorities(self, sheet: str) -> list[PriorityConfig]:
        """Read CfgPriorities table."""
        table_data = self.workbook_manager.read_table(sheet=sheet, table_name="CfgPriorities")
        priorities = []

        for row in table_data:
            name = self._get_cell_value(row, "Priority.Name")

            if name:
                priorities.append(PriorityConfig(name=str(name)))
            else:
                logger.warning(f"Skipping incomplete priority row: {row}")

        logger.debug(f"Read {len(priorities)} priorities from CfgPriorities table")
        return priorities

    def _read_auto_field_values(self, sheet: str) -> list[AutoFieldValueConfig]:
        """Read CfgAutofieldValues table."""
        table_data = self.workbook_manager.read_table(sheet=sheet, table_name="CfgAutofieldValues")
        auto_field_values = []

        for row in table_data:
            name = self._get_cell_value(row, "Name")
            value = self._get_cell_value(row, "Value")

            if name and value is not None:
                auto_field_values.append(AutoFieldValueConfig(name=str(name), value=str(value)))
            else:
                logger.warning(f"Skipping incomplete auto field value row: {row}")

        logger.debug(f"Read {len(auto_field_values)} auto field values from CfgAutofieldValues table")
        return auto_field_values

    def _read_custom_fields(self, sheet: str) -> list[CustomFieldConfig]:
        """Read CfgCustomFields table."""
        try:
            table_data = self.workbook_manager.read_table(sheet=sheet, table_name="CfgCustomFields")
        except Exception:
            # Table doesn't exist, return empty list
            return []

        custom_fields = []
        seen_ids: dict[str, CustomFieldConfig] = {}
        seen_names: dict[str, CustomFieldConfig] = {}

        # Normalize names for comparison
        def normalize_name(name: str) -> str:
            return name.strip().lower()

        for row in table_data:
            name = self._get_cell_value(row, "Name")
            field_id = self._get_cell_value(row, "Id")
            field_type = self._get_cell_value(row, "Type")

            name_str = str(name if name is not None else "").strip()
            if not name_str:
                # Include available column names in error details for debugging
                available_columns = list(row.keys()) if isinstance(row, dict) else []
                raise ConfigurationError(
                    "Custom field definition missing 'name' in Excel config",
                    details={
                        "source": "Excel",
                        "sheet": sheet,
                        "row_data": row,
                        "available_columns": available_columns,
                        "id": str(field_id if field_id is not None else "").strip() or None,
                    },
                )

            field_id_str = str(field_id if field_id is not None else "").strip()
            if not field_id_str:
                raise ConfigurationError(
                    f"Custom field definition missing 'id' for field '{name_str}' in Excel config",
                    details={
                        "source": "Excel",
                        "sheet": sheet,
                        "row_data": row,
                        "name": name_str,
                    },
                )

            field_type_str = str(field_type if field_type is not None else "").strip().lower()
            if not field_type_str:
                raise ConfigurationError(
                    f"Custom field definition missing 'type' for field '{name_str}' in Excel config",
                    details={
                        "source": "Excel",
                        "sheet": sheet,
                        "row_data": row,
                        "name": name_str,
                        "id": field_id_str,
                    },
                )

            # Validate type
            if field_type_str not in ["text", "number", "date", "select", "any"]:
                raise ConfigurationError(
                    f"Invalid custom field type '{field_type_str}' for field '{name_str}'. Must be one of: text, number, date, select, any",
                    details={"name": name_str, "id": field_id_str, "type": field_type_str, "source": "Excel"},
                )

            # Check for duplicate id
            if field_id_str in seen_ids:
                raise ConfigurationError(
                    f"Duplicate custom field id '{field_id_str}' found in Excel config. "
                    f"First definition: '{seen_ids[field_id_str].name}', "
                    f"Second definition: '{name_str}'",
                    details={
                        "field_id": field_id_str,
                        "first_name": seen_ids[field_id_str].name,
                        "second_name": name_str,
                        "source": "Excel",
                    },
                )

            # Check for name conflict (same name, different id)
            normalized_name = normalize_name(name_str)
            if normalized_name in seen_names:
                existing = seen_names[normalized_name]
                if existing.id != field_id_str:
                    raise ConfigurationError(
                        f"Custom field name '{name_str}' is defined for multiple field ids in Excel: "
                        f"'{existing.id}' and '{field_id_str}'",
                        details={
                            "field_name": name_str,
                            "first_id": existing.id,
                            "second_id": field_id_str,
                            "source": "Excel",
                        },
                    )

            cfg = CustomFieldConfig(
                name=name_str,
                id=field_id_str,
                type=field_type_str,  # type: ignore[arg-type]
            )

            custom_fields.append(cfg)
            seen_ids[field_id_str] = cfg
            seen_names[normalized_name] = cfg

        logger.debug(f"Read {len(custom_fields)} custom field definitions from CfgCustomFields table")
        return custom_fields

    def _get_cell_value(self, row: dict[str, Any], column_name: str) -> Any | None:
        """Get cell value from row dictionary.

        Args:
            row: Dictionary representing a table row
            column_name: Name of the column to retrieve

        Returns:
            Cell value or None if not found
        """
        # Try exact match first
        if column_name in row:
            return row[column_name]

        # Case-insensitive match using cached lowercase-key map per row
        try:
            lower_map = self._row_lower_key_cache[id(row)]
        except KeyError:
            # Build and cache mapping once per row
            lower_map = {}
            for key in row.keys():
                if isinstance(key, str):
                    lower_map[key.lower()] = key
            self._row_lower_key_cache[id(row)] = lower_map

        lookup_key = column_name.lower()
        original_key = lower_map.get(lookup_key)
        if original_key is not None:
            return row.get(original_key)

        return None
