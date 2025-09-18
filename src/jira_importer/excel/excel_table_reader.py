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
    ExcelTableConfig,
    FixVersionConfig,
    IgnoreListConfig,
    IssueTypeConfig,
    PriorityConfig,
    SprintConfig,
)
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
            sprints=self._read_sprints(config_sheet),
            fix_versions=self._read_fix_versions(config_sheet),
            components=self._read_components(config_sheet),
            issue_types=self._read_issue_types(config_sheet),
            ignore_list=self._read_ignore_list(config_sheet),
            priorities=self._read_priorities(config_sheet),
            auto_field_values=self._read_auto_field_values(config_sheet),
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

        # Try case-insensitive match
        for key, value in row.items():
            if key and key.lower() == column_name.lower():
                return value

        return None
