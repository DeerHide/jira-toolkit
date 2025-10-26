"""Mappers for converting processed rows to Jira Cloud API payloads.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ...config.config_view import ConfigView
from ...config.constants import LEVEL_4_SUBTASK
from ...config.issuetypes import get_default_level3_type, get_issue_type_level
from ..models import ColumnIndices, ProcessorResult
from .constants import JIRA_KEY_PARTS_COUNT
from .metadata import MetadataCache

logger = logging.getLogger(__name__)


def redact_secret(value: str | None) -> str:
    """Redact secret values for logging."""
    return "***" if value else ""


@dataclass
class IssueMapper:
    """Maps processed rows to Jira issue payloads."""

    cfg: ConfigView
    metadata: MetadataCache
    _field_map: dict[str, str] | None = None

    def map_row(self, row: list[str], indices: ColumnIndices) -> dict[str, Any]:
        """Map a single row to Jira issue payload."""
        fields: dict[str, Any] = {}

        # Required fields
        project_key_from_row = (
            str(row[indices.project_key]).strip()
            if indices.project_key is not None and row[indices.project_key]
            else None
        )
        project_key_from_config = self.cfg.get("jira.project.key", None)
        final_project_key = project_key_from_row or project_key_from_config
        if final_project_key:
            fields["project"] = {"key": final_project_key}

        if indices.issuetype is not None and row[indices.issuetype]:
            fields["issuetype"] = {"name": str(row[indices.issuetype]).strip()}
        if indices.summary is not None and row[indices.summary]:
            fields["summary"] = str(row[indices.summary]).strip()

        # Optional fields
        if indices.description is not None and row[indices.description]:
            description_text = str(row[indices.description]).strip()
            fields["description"] = self._convert_to_adf(description_text)

        if indices.priority is not None and row[indices.priority]:
            fields["priority"] = {"name": str(row[indices.priority]).strip()}

        if indices.parent is not None and row[indices.parent]:
            parent_key = str(row[indices.parent]).strip()
            # Keep parent reference for mapping (will be resolved later)
            fields["parent"] = {"key": parent_key}

        # Convert level 4 issue types to level 3 if no valid parent exists
        if indices.issuetype is not None and row[indices.issuetype] and "parent" not in fields:
            issue_type_name = str(row[indices.issuetype]).strip()
            if get_issue_type_level(self.cfg.get, issue_type_name) == LEVEL_4_SUBTASK:
                fallback_type = get_default_level3_type(self.cfg.get)
                logger.info(f"Converting {issue_type_name} to {fallback_type} (no valid parent found)")
                fields["issuetype"] = {"name": fallback_type}

        # Time tracking (use originalEstimateSeconds)
        if indices.estimate is not None and row[indices.estimate]:
            try:
                est_seconds = int(float(str(row[indices.estimate])))
                fields["timetracking"] = {"originalEstimateSeconds": est_seconds}
            except (ValueError, TypeError):
                logger.warning(f"Invalid estimate value: {redact_secret(str(row[indices.estimate]))}")

        # Assignee (already resolved by AssigneeResolverFixer)
        if indices.assignee is not None and row[indices.assignee]:
            assignee_id = str(row[indices.assignee]).strip()
            if assignee_id:
                fields["assignee"] = {"accountId": assignee_id}

        # TODO: Custom fields mapping

        return {"fields": fields}

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
        raise ValueError("Column indices not available for mapping")

    for row in result.rows:
        payload = mapper.map_row(row, result.indices)
        issues.append(payload)

    return issues
