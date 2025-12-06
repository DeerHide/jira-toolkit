"""Mappers for converting processed rows to Jira Cloud API payloads.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from ...config.config_view import ConfigView
from ...config.constants import LEVEL_4_SUBTASK
from ...config.issuetypes import get_default_level3_type, get_issue_type_level
from ...errors import ProcessingError
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

    def map_row(self, row: Sequence[Any], indices: ColumnIndices) -> dict[str, Any]:
        """Map a single row to Jira issue payload.

        Args:
            row: Row data as a sequence of values (can be Any type).
            indices: Column indices for accessing row data.

        Returns:
            Dictionary with "fields" key containing Jira issue fields.

        Raises:
            ProcessingError: If required fields are missing.
        """
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

        # Handle level 4 issue type conversion (must be after parent mapping)
        self._handle_level4_issuetype_conversion(fields, row, indices)

        # TODO: Custom fields mapping

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


def build_issue_payloads(result: ProcessorResult, mapper: IssueMapper) -> list[dict[str, Any]]:
    """Build issue payloads from processor result."""
    issues = []

    if result.indices is None:
        raise ProcessingError(
            "Column indices not available for mapping",
            details={"reason": "ProcessorResult.indices is None"},
        )

    for row in result.rows:
        payload = mapper.map_row(row, result.indices)
        issues.append(payload)

    return issues
