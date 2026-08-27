"""Description: This script contains utilities for reading structured Excel tables.

Author:
    Julien (@tom4897)
"""

from __future__ import annotations

import json
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
    SettingConfig,
    SprintConfig,
    TeamConfig,
)
from ..config.constants import LEVEL_1_INITIATIVE, LEVEL_4_SUBTASK
from ..errors import ConfigurationError
from .excel_io import ExcelWorkbookManager

logger = logging.getLogger(__name__)

TABLE_CFG_ASSIGNEES = "CfgAssignees"
TABLE_CFG_TEAMS = "CfgTeams"
TABLE_CFG_SPRINTS = "CfgSprints"
TABLE_CFG_FIX_VERSIONS = "CfgFixVersions"
TABLE_CFG_COMPONENTS = "CfgComponents"
TABLE_CFG_ISSUE_TYPES = "CfgIssueTypes"
TABLE_CFG_IGNORE_LIST = "CfgIgnoreList"
TABLE_CFG_PRIORITIES = "CfgPriorities"
TABLE_CFG_AUTO_FIELD_VALUES = "CfgAutofieldValues"
TABLE_CFG_CUSTOM_FIELDS = "CfgCustomFields"
TABLE_CFG_BASIC = "CfgBasic"
TABLE_CFG_ADVANCED = "CfgAdvanced"
TABLE_CFG_SETTINGS = "CfgSettings"


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
        # Keep config_sheet argument for backward API compatibility.
        lookup_sheet: str | None = None
        logger.debug(
            f"Reading all configuration tables using indexed config-sheet discovery (config_sheet='{config_sheet}')"
        )

        return ExcelTableConfig(
            assignees=self._read_assignees(lookup_sheet),
            teams=self._read_teams(lookup_sheet),
            sprints=self._read_sprints(lookup_sheet),
            fix_versions=self._read_fix_versions(lookup_sheet),
            components=self._read_components(lookup_sheet),
            issue_types=self._read_issue_types(lookup_sheet),
            ignore_list=self._read_ignore_list(lookup_sheet),
            priorities=self._read_priorities(lookup_sheet),
            auto_field_values=self._read_auto_field_values(lookup_sheet),
            custom_fields=self._read_custom_fields(lookup_sheet),
            settings=self._read_settings(lookup_sheet),
        )

    def read_basic_settings(self, config_sheet: str = "Config") -> list[SettingConfig]:
        """Read settings from CfgBasic for early configuration merge."""
        logger.debug(f"Reading {TABLE_CFG_BASIC} using indexed discovery (config_sheet='{config_sheet}')")
        return self._read_name_value_settings_table(table_name=TABLE_CFG_BASIC, sheet=None)

    def read_advanced_settings(self, config_sheet: str = "Config") -> list[SettingConfig]:
        """Read settings from CfgAdvanced for early configuration merge."""
        logger.debug(f"Reading {TABLE_CFG_ADVANCED} using indexed discovery (config_sheet='{config_sheet}')")
        return self._read_name_value_settings_table(table_name=TABLE_CFG_ADVANCED, sheet=None)

    def read_settings(self, config_sheet: str = "Config") -> list[SettingConfig]:
        """Read settings from CfgSettings for early configuration merge."""
        # Keep arg for API consistency with other readers.
        logger.debug(f"Reading {TABLE_CFG_SETTINGS} using indexed discovery (config_sheet='{config_sheet}')")
        lookup_sheet: str | None = None
        return self._read_settings(lookup_sheet)

    def _read_assignees(self, sheet: str | None) -> list[AssigneeConfig]:
        """Read CfgAssignees table."""
        table_data = self.workbook_manager.read_table(sheet=sheet, table_name=TABLE_CFG_ASSIGNEES)
        assignees = []

        for row in table_data:
            name = self._get_cell_value(row, "Assignee.Name")
            id_value = self._get_cell_value(row, "Assignee.ID")

            if name and id_value:
                assignees.append(AssigneeConfig(name=str(name), id=str(id_value)))
            else:
                logger.warning(f"Skipping incomplete assignee row: {row}")

        logger.debug(f"Read {len(assignees)} assignees from {TABLE_CFG_ASSIGNEES} table")
        return assignees

    def _read_teams(self, sheet: str | None) -> list[TeamConfig]:
        """Read CfgTeams table."""
        try:
            table_data = self.workbook_manager.read_table(sheet=sheet, table_name=TABLE_CFG_TEAMS, optional=True)
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

        logger.debug(f"Read {len(teams)} teams from {TABLE_CFG_TEAMS} table")
        return teams

    def _read_sprints(self, sheet: str | None) -> list[SprintConfig]:
        """Read CfgSprints table."""
        table_data = self.workbook_manager.read_table(sheet=sheet, table_name=TABLE_CFG_SPRINTS, optional=True)
        sprints = []

        for row in table_data:
            name = self._get_cell_value(row, "Sprint.Name")
            id_value = self._get_cell_value(row, "Sprint.ID")

            if name and id_value:
                sprints.append(SprintConfig(name=str(name), id=str(id_value)))
            else:
                logger.warning(f"Skipping incomplete sprint row: {row}")

        logger.debug(f"Read {len(sprints)} sprints from {TABLE_CFG_SPRINTS} table")
        return sprints

    def _read_fix_versions(self, sheet: str | None) -> list[FixVersionConfig]:
        """Read CfgFixVersions table."""
        table_data = self.workbook_manager.read_table(sheet=sheet, table_name=TABLE_CFG_FIX_VERSIONS, optional=True)
        fix_versions = []

        for row in table_data:
            name = self._get_cell_value(row, "FixVersion.Name")

            if name:
                fix_versions.append(FixVersionConfig(name=str(name)))
            else:
                logger.warning(f"Skipping incomplete fix version row: {row}")

        logger.debug(f"Read {len(fix_versions)} fix versions from {TABLE_CFG_FIX_VERSIONS} table")
        return fix_versions

    def _read_components(self, sheet: str | None) -> list[ComponentConfig]:
        """Read CfgComponents table."""
        table_data = self.workbook_manager.read_table(sheet=sheet, table_name=TABLE_CFG_COMPONENTS, optional=True)
        components = []

        for row in table_data:
            name = self._get_cell_value(row, "Component.Name")

            if name:
                components.append(ComponentConfig(name=str(name)))
            else:
                logger.warning(f"Skipping incomplete component row: {row}")

        logger.debug(f"Read {len(components)} components from {TABLE_CFG_COMPONENTS} table")
        return components

    def _read_issue_types(self, sheet: str | None) -> list[IssueTypeConfig]:
        """Read CfgIssueTypes table."""
        table_data = self.workbook_manager.read_table(sheet=sheet, table_name=TABLE_CFG_ISSUE_TYPES)
        issue_types = []

        for row in table_data:
            name = self._get_cell_value(row, "IssueType.Name")
            level = ExcelTableReader._parse_issue_type_level(self._get_cell_value(row, "IssueType.Level"))

            if name:
                issue_types.append(IssueTypeConfig(name=str(name), level=level))
            else:
                logger.warning(f"Skipping incomplete issue type row: {row}")

        logger.debug(f"Read {len(issue_types)} issue types from {TABLE_CFG_ISSUE_TYPES} table")
        return issue_types

    def _read_ignore_list(self, sheet: str | None) -> list[IgnoreListConfig]:
        """Read CfgIgnoreList table."""
        table_data = self.workbook_manager.read_table(sheet=sheet, table_name=TABLE_CFG_IGNORE_LIST)
        ignore_list = []

        for row in table_data:
            name = self._get_cell_value(row, "IgnoreList.Name")

            if name:
                ignore_list.append(IgnoreListConfig(name=str(name)))
            else:
                logger.warning(f"Skipping incomplete ignore list row: {row}")

        logger.debug(f"Read {len(ignore_list)} ignore list items from {TABLE_CFG_IGNORE_LIST} table")
        return ignore_list

    def _read_priorities(self, sheet: str | None) -> list[PriorityConfig]:
        """Read CfgPriorities table."""
        table_data = self.workbook_manager.read_table(sheet=sheet, table_name=TABLE_CFG_PRIORITIES)
        priorities = []

        for row in table_data:
            name = self._get_cell_value(row, "Priority.Name")

            if name:
                priorities.append(PriorityConfig(name=str(name)))
            else:
                logger.warning(f"Skipping incomplete priority row: {row}")

        logger.debug(f"Read {len(priorities)} priorities from {TABLE_CFG_PRIORITIES} table")
        return priorities

    def _read_auto_field_values(self, sheet: str | None) -> list[AutoFieldValueConfig]:
        """Read CfgAutofieldValues table."""
        table_data = self.workbook_manager.read_table(sheet=sheet, table_name=TABLE_CFG_AUTO_FIELD_VALUES)
        auto_field_values = []

        for row in table_data:
            name = self._get_cell_value(row, "Name")
            value = self._get_cell_value(row, "Value")

            if name and value is not None:
                auto_field_values.append(AutoFieldValueConfig(name=str(name), value=str(value)))
            else:
                logger.warning(f"Skipping incomplete auto field value row: {row}")

        logger.debug(f"Read {len(auto_field_values)} auto field values from {TABLE_CFG_AUTO_FIELD_VALUES} table")
        return auto_field_values

    def _read_custom_fields(self, sheet: str | None) -> list[CustomFieldConfig]:
        """Read CfgCustomFields table."""
        try:
            table_data = self.workbook_manager.read_table(
                sheet=sheet, table_name=TABLE_CFG_CUSTOM_FIELDS, optional=True
            )
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
                        "sheet": sheet or "<indexed>",
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
                        "sheet": sheet or "<indexed>",
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
                        "sheet": sheet or "<indexed>",
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

        logger.debug(f"Read {len(custom_fields)} custom field definitions from {TABLE_CFG_CUSTOM_FIELDS} table")
        return custom_fields

    def _read_settings(self, sheet: str | None) -> list[SettingConfig]:
        """Read CfgSettings table."""
        return self._read_name_value_settings_table(table_name=TABLE_CFG_SETTINGS, sheet=sheet)

    def _read_name_value_settings_table(self, *, table_name: str, sheet: str | None) -> list[SettingConfig]:
        """Read an optional Name/Value settings table into SettingConfig rows."""
        table_data = self.workbook_manager.read_table(sheet=sheet, table_name=table_name, optional=True)
        settings: list[SettingConfig] = []

        for row in table_data:
            name = self._get_cell_value(row, "Name")
            value = self._get_cell_value(row, "Value")
            value_type = self._get_cell_value(row, "Type")

            name_str = str(name if name is not None else "").strip()
            if not name_str:
                logger.warning(f"Skipping {table_name} row with missing name: {row}")
                continue

            normalized_type = str(value_type).strip().lower() if value_type is not None else ""
            coerced = self._coerce_setting_value(
                value=value,
                value_type=normalized_type,
                key=name_str,
                table_name=table_name,
            )
            settings.append(
                SettingConfig(
                    name=name_str,
                    value=coerced,
                    value_type=normalized_type or None,
                )
            )

        logger.debug(f"Read {len(settings)} settings from {table_name} table")
        return settings

    @staticmethod
    def _parse_issue_type_level(raw: Any) -> int | None:
        """Parse optional IssueType.Level from an Excel cell.

        Invalid or out-of-range values return None so callers can fall back to
        name-based default levels. Unlike `_coerce_setting_value`, this does not raise.

        Args:
            raw: Raw cell value (int, float, or numeric string).

        Returns:
            Hierarchy level between 1 and 4, or None when absent/invalid.
        """
        if raw is None:
            return None
        if isinstance(raw, bool):
            return None

        level: int | None
        if isinstance(raw, int):
            level = raw
        elif isinstance(raw, float) and raw.is_integer():
            level = int(raw)
        else:
            text = str(raw).strip()
            if not text:
                return None
            try:
                level = int(text)
            except ValueError:
                logger.warning(f"Ignoring invalid IssueType.Level value: {raw!r}")
                return None

        if not LEVEL_1_INITIATIVE <= level <= LEVEL_4_SUBTASK:
            logger.warning(
                f"Ignoring out-of-range IssueType.Level value: {raw!r} "
                f"(expected {LEVEL_1_INITIATIVE}-{LEVEL_4_SUBTASK})"
            )
            return None
        return level

    @staticmethod
    def _coerce_setting_value(
        value: Any,
        value_type: str,
        key: str,
        table_name: str = TABLE_CFG_SETTINGS,
    ) -> Any:
        """Coerce settings value based on optional Type column."""
        if not value_type:
            return value

        if value_type == "str":
            return "" if value is None else str(value)
        if value_type == "int":
            try:
                return int(value)
            except (TypeError, ValueError) as exc:
                raise ConfigurationError(
                    f"{table_name} key '{key}' expected int value, got '{value}'",
                    details={"key": key, "type": "int", "value": value, "table_name": table_name},
                ) from exc
        if value_type == "float":
            try:
                return float(value)
            except (TypeError, ValueError) as exc:
                raise ConfigurationError(
                    f"{table_name} key '{key}' expected float value, got '{value}'",
                    details={"key": key, "type": "float", "value": value, "table_name": table_name},
                ) from exc
        if value_type == "bool":
            if isinstance(value, bool):
                return value
            value_str = str(value).strip().lower()
            if value_str in {"true", "1", "yes", "on", "enabled"}:
                return True
            if value_str in {"false", "0", "no", "off", "disabled"}:
                return False
            raise ConfigurationError(
                f"{table_name} key '{key}' expected bool value, got '{value}'",
                details={"key": key, "type": "bool", "value": value, "table_name": table_name},
            )
        if value_type == "json":
            try:
                return json.loads(str(value))
            except (TypeError, ValueError) as exc:
                raise ConfigurationError(
                    f"{table_name} key '{key}' expected valid JSON value, got '{value}'",
                    details={"key": key, "type": "json", "value": value, "table_name": table_name},
                ) from exc

        raise ConfigurationError(
            f"{table_name} key '{key}' has unsupported type '{value_type}'. "
            "Supported types: str, int, float, bool, json",
            details={"key": key, "type": value_type, "value": value, "table_name": table_name},
        )

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
