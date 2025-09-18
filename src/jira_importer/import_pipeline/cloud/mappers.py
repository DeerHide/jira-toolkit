"""Row-to-payload mapping for Jira Cloud (scaffold).

Defines an IssueMapper that will turn normalized rows into Jira issue payloads.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ...config.config_view import ConfigView
from ..models import ColumnIndices, ProcessorResult
from .metadata import MetadataCache
from .secrets import redact_secret

logger = logging.getLogger(__name__)


@dataclass
class IssueMapper:
    """Issue mapper."""

    cfg: ConfigView
    metadata: MetadataCache
    _field_map: dict[str, str] | None = None

    def _get_field_map(self) -> dict[str, str]:
        """Map column names to customfield_xxxxx IDs."""
        if self._field_map is None:
            fields = self.metadata.get_fields()
            self._field_map = {
                f.get("name", ""): f.get("id", "") for f in fields if f.get("id", "").startswith("customfield_")
            }
        return self._field_map

    def map_row(self, row: list[str], indices: ColumnIndices) -> dict[str, Any]:
        """Map a row to a Jira issue payload."""
        fields: dict[str, Any] = {}

        # Required fields
        if indices.project_key is not None and row[indices.project_key]:
            fields["project"] = {"key": str(row[indices.project_key]).strip()}
        if indices.issuetype is not None and row[indices.issuetype]:
            fields["issuetype"] = {"name": str(row[indices.issuetype]).strip()}
        if indices.summary is not None and row[indices.summary]:
            fields["summary"] = str(row[indices.summary]).strip()

        # Optional fields
        if indices.description is not None and row[indices.description]:
            desc = str(row[indices.description]).strip()
            # Keep as plain text for now; ADF can be added later
            fields["description"] = desc

        if indices.priority is not None and row[indices.priority]:
            fields["priority"] = {"name": str(row[indices.priority]).strip()}

        if indices.assignee is not None and row[indices.assignee]:
            # TODO: resolve to accountId via user search
            fields["assignee"] = {"emailAddress": str(row[indices.assignee]).strip()}

        if indices.parent is not None and row[indices.parent]:
            fields["parent"] = {"key": str(row[indices.parent]).strip()}

        # Time tracking (keep canonical seconds)
        if indices.estimate is not None and row[indices.estimate]:
            try:
                est_seconds = int(float(str(row[indices.estimate])))
                fields["timetracking"] = {"originalEstimate": f"{est_seconds}s"}
            except (ValueError, TypeError):
                logger.warning(f"Invalid estimate value: {redact_secret(str(row[indices.estimate]))}")

        # Custom fields (map by column name to customfield_xxxxx)
        # TODO: Implement custom field mapping with config-driven column mapping

        return {"fields": fields}


def build_issue_payloads(result: ProcessorResult, mapper: IssueMapper) -> list[dict[str, Any]]:
    """Build issue payloads."""
    payloads: list[dict[str, Any]] = []
    if not result.indices:
        logger.warning("No column indices available in ProcessorResult")
        return payloads
    for row in result.rows:
        payloads.append(mapper.map_row(row, result.indices))
    return payloads
