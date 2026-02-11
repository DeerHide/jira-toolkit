"""Mappers for converting processed rows to Jira Cloud API payloads.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from ...config.config_models import CustomFieldConfig
from ...config.config_view import ConfigView
from ...config.constants import LEVEL_4_SUBTASK
from ...config.issuetypes import get_default_level3_type, get_issue_type_level
from ...errors import ConfigurationError, ProcessingError, RowProcessingError
from ..models import ColumnIndices, ProcessorResult
from .constants import JIRA_KEY_PARTS_COUNT
from .metadata import MetadataCache
from .secrets import redact_secret

logger = logging.getLogger(__name__)


@dataclass
class IssueMapper:
    """Maps processed rows to Jira issue payloads."""

    cfg: ConfigView
    metadata: MetadataCache
    _field_map: dict[str, str] | None = None
    _current_row_index: int | None = None

    def map_row(
        self,
        row: Sequence[Any],
        indices: ColumnIndices,
        custom_configs_by_id: dict[str, CustomFieldConfig] | None = None,
        row_index: int | None = None,
    ) -> dict[str, Any]:
        """Map a single row to Jira issue payload.

        Args:
            row: Row data as a sequence of values (can be Any type).
            indices: Column indices for accessing row data.
            custom_configs_by_id: Dictionary mapping field_id -> CustomFieldConfig.
            row_index: Optional 1-based row index for error reporting (header = 1).

        Returns:
            Dictionary with "fields" key containing Jira issue fields.

        Raises:
            ProcessingError: If required fields are missing.
        """
        # Store row index for error context in custom field mapping
        self._current_row_index = row_index

        fields: dict[str, Any] = {}

        # Map required fields
        self._map_project(fields, row, indices)
        self._map_issuetype(fields, row, indices)
        self._map_summary(fields, row, indices)

        # Validate required fields
        self._validate_required_fields(fields)

        # Map optional fields
        self._map_description(fields, row, indices)
        self._map_priority(fields, row, indices)
        self._map_parent(fields, row, indices)
        self._map_estimate(fields, row, indices)
        self._map_assignee(fields, row, indices)
        self._map_reporter(fields, row, indices)
        self._map_team(fields, row, indices)

        # Handle level 4 issue type conversion (must be after parent mapping)
        self._handle_level4_issuetype_conversion(fields, row, indices)

        # Map custom fields
        if custom_configs_by_id and indices.custom_fields:
            self._map_custom_fields(fields, row, indices, custom_configs_by_id)

        return {"fields": fields}

    def _cell_str(self, row: Sequence[Any], idx: int | None) -> str:
        """Safely extract string value from row cell.

        Args:
            row: Row data as a sequence of values.
            idx: Column index (None if column not present).

        Returns:
            Trimmed string value, or empty string if missing/invalid.
        """
        if idx is None or idx < 0 or idx >= len(row):
            return ""
        v = row[idx]
        return "" if v is None else str(v).strip()

    def _cell_str_or_none(self, row: Sequence[Any], idx: int | None) -> str | None:
        """Safely extract string value from row cell, returning None if empty.

        Args:
            row: Row data as a sequence of values.
            idx: Column index (None if column not present).

        Returns:
            Trimmed string value, or None if missing/invalid/empty.
        """
        value = self._cell_str(row, idx)
        return value if value else None

    def _map_project(self, fields: dict[str, Any], row: Sequence[Any], indices: ColumnIndices) -> None:
        """Map project key from row or config.

        Args:
            fields: Fields dictionary to update.
            row: Row data.
            indices: Column indices.
        """
        project_key_from_row = self._cell_str_or_none(row, indices.project_key)
        project_key_from_config = self.cfg.get("jira.project.key", None)
        final_project_key = project_key_from_row or project_key_from_config
        if final_project_key:
            fields["project"] = {"key": final_project_key}

    def _map_issuetype(self, fields: dict[str, Any], row: Sequence[Any], indices: ColumnIndices) -> None:
        """Map issue type from row.

        Args:
            fields: Fields dictionary to update.
            row: Row data.
            indices: Column indices.
        """
        issue_type = self._cell_str(row, indices.issuetype)
        if issue_type:
            fields["issuetype"] = {"name": issue_type}

    def _map_summary(self, fields: dict[str, Any], row: Sequence[Any], indices: ColumnIndices) -> None:
        """Map summary from row.

        Args:
            fields: Fields dictionary to update.
            row: Row data.
            indices: Column indices.
        """
        summary = self._cell_str(row, indices.summary)
        if summary:
            fields["summary"] = summary

    def _map_description(self, fields: dict[str, Any], row: Sequence[Any], indices: ColumnIndices) -> None:
        """Map description from row, converting to ADF format.

        Args:
            fields: Fields dictionary to update.
            row: Row data.
            indices: Column indices.
        """
        description_text = self._cell_str(row, indices.description)
        if description_text:
            fields["description"] = self._convert_to_adf(description_text)

    def _map_priority(self, fields: dict[str, Any], row: Sequence[Any], indices: ColumnIndices) -> None:
        """Map priority from row.

        Args:
            fields: Fields dictionary to update.
            row: Row data.
            indices: Column indices.
        """
        priority = self._cell_str(row, indices.priority)
        if priority:
            fields["priority"] = {"name": priority}

    def _map_parent(self, fields: dict[str, Any], row: Sequence[Any], indices: ColumnIndices) -> None:
        """Map parent key from row.

        Args:
            fields: Fields dictionary to update.
            row: Row data.
            indices: Column indices.
        """
        parent_key = self._cell_str(row, indices.parent)
        if parent_key:
            # Keep parent reference for mapping (will be resolved later)
            fields["parent"] = {"key": parent_key}

    def _map_estimate(self, fields: dict[str, Any], row: Sequence[Any], indices: ColumnIndices) -> None:
        """Map time estimate from row.

        Args:
            fields: Fields dictionary to update.
            row: Row data.
            indices: Column indices.
        """
        estimate_value = self._cell_str(row, indices.estimate)
        if estimate_value:
            try:
                est_seconds = int(float(estimate_value))
                fields["timetracking"] = {"originalEstimateSeconds": est_seconds}
            except (ValueError, TypeError):
                logger.warning(f"Invalid estimate value: {redact_secret(estimate_value)}")

    def _map_assignee(self, fields: dict[str, Any], row: Sequence[Any], indices: ColumnIndices) -> None:
        """Map assignee from row (already resolved by AssigneeResolverFixer).

        Args:
            fields: Fields dictionary to update.
            row: Row data.
            indices: Column indices.
        """
        assignee_id = self._cell_str(row, indices.assignee)
        if assignee_id:
            fields["assignee"] = {"accountId": assignee_id}

    def _map_reporter(self, fields: dict[str, Any], row: Sequence[Any], indices: ColumnIndices) -> None:
        """Map reporter from row (already resolved by ReporterResolverFixer).

        Args:
            fields: Fields dictionary to update.
            row: Row data.
            indices: Column indices.
        """
        reporter_id = self._cell_str(row, indices.reporter)
        if reporter_id:
            fields["reporter"] = {"accountId": reporter_id}

    def _map_team(self, fields: dict[str, Any], row: Sequence[Any], indices: ColumnIndices) -> None:
        """Map Advanced Roadmaps Team field from row.

        Args:
            fields: Fields dictionary to update.
            row: Row data.
            indices: Column indices.
        """
        team_id = self._cell_str(row, indices.team)
        if team_id:
            # Built-in Advanced Roadmaps Team field
            fields["team"] = {"id": team_id}

    def _handle_level4_issuetype_conversion(
        self, fields: dict[str, Any], row: Sequence[Any], indices: ColumnIndices
    ) -> None:
        """Convert level 4 issue types to level 3 if no valid parent exists.

        Args:
            fields: Fields dictionary to update.
            row: Row data.
            indices: Column indices.
        """
        if indices.issuetype is None:
            return

        issue_type_name = self._cell_str(row, indices.issuetype)
        if not issue_type_name or "parent" in fields:
            return

        if get_issue_type_level(self.cfg.get, issue_type_name) == LEVEL_4_SUBTASK:
            fallback_type = get_default_level3_type(self.cfg.get)
            logger.info(f"Converting {issue_type_name} to {fallback_type} (no valid parent found)")
            fields["issuetype"] = {"name": fallback_type}

    def _validate_required_fields(self, fields: dict[str, Any]) -> None:
        """Validate that required fields are present.

        Args:
            fields: Fields dictionary to validate.

        Raises:
            ProcessingError: If required fields are missing.
        """
        missing_fields = []
        if "project" not in fields:
            missing_fields.append("project")
        if "issuetype" not in fields:
            missing_fields.append("issuetype")
        if "summary" not in fields:
            missing_fields.append("summary")

        if missing_fields:
            raise ProcessingError(
                f"Missing required fields: {', '.join(missing_fields)}",
                details={"missing_fields": missing_fields},
            )

    def is_valid_jira_key(self, key: str) -> bool:
        """Check if a string looks like a valid Jira issue key (e.g., PROJ-123)."""
        if not key or not isinstance(key, str):
            return False
        # Basic validation: should contain a dash and have alphanumeric parts
        parts = key.split("-")
        return len(parts) == JIRA_KEY_PARTS_COUNT and parts[0].isalnum() and parts[1].isdigit()

    def _convert_to_adf(self, text: str) -> dict[str, Any]:
        """Convert plain text to Atlassian Document Format (ADF).

        ADF is a JSON structure that represents rich text content in Atlassian products.
        This creates a simple paragraph with the text content.
        """
        return {
            "version": 1,
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
        }

    def _normalize_raw_value(self, raw: Any) -> str | None:
        if raw is None:
            return None
        raw_str = str(raw).strip()
        if not raw_str:
            return None
        return raw_str

    def _serialize_any_value(self, raw: Any) -> Any:
        from datetime import date, datetime  # pylint: disable=import-outside-toplevel

        if isinstance(raw, (datetime, date)):
            return raw.isoformat()
        if isinstance(raw, (int, float, str, bool, type(None))):
            return raw
        return str(raw)

    def _transform_number_value(self, raw_str: str, cfg: CustomFieldConfig) -> int | float:
        try:
            if "." in raw_str or "e" in raw_str.lower():
                return float(raw_str)
            return int(raw_str)
        except ValueError as exc:
            raise RowProcessingError(
                f"Invalid number value for custom field '{cfg.name}' (id: {cfg.id}): '{raw_str}'",
                details={
                    "field_name": cfg.name,
                    "field_id": cfg.id,
                    "field_type": cfg.type,
                    "raw_value": raw_str,
                    "raw_type": type(raw_str).__name__,
                },
            ) from exc

    def _parse_date_string(self, date_str: str, cfg: CustomFieldConfig) -> str:
        from datetime import datetime

        default_formats = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"]
        for fmt in default_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        raise RowProcessingError(
            f"Invalid date value for custom field '{cfg.name}' (id: {cfg.id}): '{date_str}'. "
            f"Expected format: YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY",
            details={
                "field_name": cfg.name,
                "field_id": cfg.id,
                "field_type": cfg.type,
                "raw_value": date_str,
                "raw_type": type(date_str).__name__,
            },
        )

    def _transform_date_value(self, raw: Any, cfg: CustomFieldConfig) -> str:
        from datetime import date, datetime

        if isinstance(raw, datetime):
            return raw.date().isoformat()

        if isinstance(raw, date):
            return raw.isoformat()

        if isinstance(raw, (int, float)):
            raise RowProcessingError(
                f"Numeric Excel date values are not supported for custom fields yet. "
                f"Please format cells as text or proper dates. "
                f"Field: '{cfg.name}' (id: {cfg.id}), value: {raw}",
                details={
                    "field_name": cfg.name,
                    "field_id": cfg.id,
                    "field_type": cfg.type,
                    "raw_value": raw,
                    "raw_type": type(raw).__name__,
                },
            )

        if isinstance(raw, str):
            return self._parse_date_string(raw.strip(), cfg)

        raise RowProcessingError(
            f"Unsupported value type for date custom field '{cfg.name}' (id: {cfg.id}): "
            f"{type(raw).__name__}. Expected: datetime, date, or string.",
            details={
                "field_name": cfg.name,
                "field_id": cfg.id,
                "field_type": cfg.type,
                "raw_value": raw,
                "raw_type": type(raw).__name__,
            },
        )

    def _transform_select_value(self, raw_str: str) -> dict[str, str]:
        return {"value": raw_str}

    def _transform_custom_value(self, raw: Any, cfg: CustomFieldConfig) -> Any | None:
        """Transform raw Excel value to Jira API format based on field type.

        Args:
            raw: Raw value from Excel cell.
            cfg: CustomFieldConfig with type and format information.

        Returns:
            Transformed value in Jira API format, or None if no value.

        Raises:
            RowProcessingError: If value is invalid for the field type.
            ConfigurationError: If field type is unsupported.
        """
        raw_str = self._normalize_raw_value(raw)
        if raw_str is None:
            return None

        if cfg.type == "any":
            return self._serialize_any_value(raw)

        if cfg.type == "text":
            return raw_str

        if cfg.type == "number":
            return self._transform_number_value(raw_str, cfg)

        if cfg.type == "date":
            return self._transform_date_value(raw, cfg)

        if cfg.type == "select":
            return self._transform_select_value(raw_str)

        raise ConfigurationError(
            f"Unsupported custom field type '{cfg.type}' for field '{cfg.name}' (id: {cfg.id})",
            details={"field_name": cfg.name, "field_id": cfg.id, "field_type": cfg.type},
        )

    def _map_custom_fields(
        self,
        fields: dict[str, Any],
        row: Sequence[Any],
        indices: ColumnIndices,
        custom_configs_by_id: dict[str, CustomFieldConfig],
    ) -> None:
        """Map custom fields from row data to Jira fields dict.

        Args:
            fields: Jira fields dictionary to populate.
            row: Row data as sequence of values.
            indices: Column indices including custom_fields mapping.
            custom_configs_by_id: Dictionary mapping field_id -> CustomFieldConfig.
        """
        for field_id, col_idx in indices.custom_fields.items():
            cfg = custom_configs_by_id.get(field_id)
            if cfg is None:
                # Config not found (shouldn't happen, but handle gracefully)
                logger.warning(f"Custom field config not found for field_id: {field_id}")
                continue

            # Extract raw value
            if col_idx is None or col_idx < 0 or col_idx >= len(row):
                continue
            raw = row[col_idx]

            # Transform value
            try:
                value = self._transform_custom_value(raw, cfg)
                if value is not None:
                    fields[field_id] = value
            except RowProcessingError as e:
                # Re-raise with additional context including row index
                raise RowProcessingError(
                    e.message,
                    details={
                        **e.details,
                        "row_index": self._current_row_index,
                        "column_name": cfg.name,
                    },
                ) from e
            except ConfigurationError as e:
                # Convert ConfigurationError to RowProcessingError with context
                raise RowProcessingError(
                    f"Configuration error for custom field '{cfg.name}': {e.message}",
                    details={
                        **e.details,
                        "row_index": self._current_row_index,
                        "column_name": cfg.name,
                        "field_id": cfg.id,
                        "field_type": cfg.type,
                    },
                ) from e


def build_issue_payloads(
    result: ProcessorResult,
    mapper: IssueMapper,
    custom_configs_by_id: dict[str, CustomFieldConfig] | None = None,
) -> list[dict[str, Any]]:
    """Build issue payloads from processor result.

    Args:
        result: Processor result with rows and indices.
        mapper: IssueMapper instance for mapping rows.
        custom_configs_by_id: Dictionary mapping field_id -> CustomFieldConfig.

    Returns:
        List of issue payload dictionaries.
    """
    issues = []

    if result.indices is None:
        raise ProcessingError(
            "Column indices not available for mapping",
            details={"reason": "ProcessorResult.indices is None"},
        )

    for row_index, row in enumerate(result.rows):
        # Pass row_index (0-based) + 1 to get 1-based index (header = 1)
        # First data row is at index 0, so row_index + 1 = 2 (first data row)
        payload = mapper.map_row(
            row, result.indices, custom_configs_by_id=custom_configs_by_id, row_index=row_index + 1
        )
        issues.append(payload)

    return issues
