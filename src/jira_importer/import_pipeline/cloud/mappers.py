"""Row-to-payload mapping for Jira Cloud (scaffold).

Defines an IssueMapper that will turn normalized rows into Jira issue payloads.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...config.config_view import ConfigView
from ..models import ProcessorResult
from .metadata import MetadataCache


@dataclass
class IssueMapper:
    """Issue mapper."""

    cfg: ConfigView
    metadata: MetadataCache

    def map_row(
        self, row: list[str], indices: Any
    ) -> dict[str, Any]:  # indices shape provided by ProcessorResult.indices
        """Map a row to a Jira issue payload."""
        fields: dict[str, Any] = {}

        if indices.project is not None:
            fields["project"] = {"key": row[indices.project]}
        if indices.issuetype is not None:
            fields["issuetype"] = {"name": row[indices.issuetype]}
        if indices.summary is not None:
            fields["summary"] = row[indices.summary]

        # Optional fields can be added in later steps (description, labels, etc.)

        return {"fields": fields}


def build_issue_payloads(result: ProcessorResult, mapper: IssueMapper) -> list[dict[str, Any]]:
    """Build issue payloads."""
    payloads: list[dict[str, Any]] = []
    idx = result.indices
    for row in result.rows:
        payloads.append(mapper.map_row(row, idx))
    return payloads
