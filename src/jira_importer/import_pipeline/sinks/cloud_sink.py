"""Jira Cloud API sink: creates issues via REST v3 in batches."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...config.config_view import ConfigView
from ..cloud.bulk import build_bulk_create_payload, chunk_issues
from ..cloud.client import JiraCloudClient
from ..cloud.constants import BATCH_SIZE
from ..cloud.mappers import IssueMapper, build_issue_payloads
from ..cloud.metadata import MetadataCache
from ..models import ProcessorResult


@dataclass
class CloudSubmitReport:
    """Report for Jira Cloud submission."""

    created: int
    failed: int
    batches: int
    errors: list[dict[str, Any]]


def write_cloud(result: ProcessorResult, config: object, *, dry_run: bool = False) -> CloudSubmitReport:
    """Submit processed issues to Jira Cloud in batches.

    This is a minimal implementation; auth and base_url/cloud_id resolution will be
    wired in a subsequent step. Here we only construct payloads and, if not dry-run,
    post them to /issue/bulk.
    """
    cfg = ConfigView(config)

    # Resolve base_url (prefer cloud_id path later). Expect full v3 base here for now.
    # Prefer existing structure: jira.connection.site_address
    base_url = cfg.get("jira.connection.site_address", None)
    if not base_url:
        raise ValueError("Missing jira.connection.site_address in configuration for Cloud sink")

    # Temporary basic auth read (OAuth wiring in later step)
    email = cfg.get("jira.connection.auth.email", None)
    api_token = cfg.get("jira.connection.auth.api_token", None)
    if not email or not api_token:
        raise ValueError("Missing jira.connection.auth.email or jira.connection.auth.api_token in configuration")

    from ..cloud.auth import BasicAuthProvider  # pylint: disable=import-outside-toplevel

    client = JiraCloudClient(
        base_url=f"{base_url.rstrip('/')}/rest/api/3", auth_provider=BasicAuthProvider(email=email, api_token=api_token)
    )
    metadata = MetadataCache(client)
    mapper = IssueMapper(cfg, metadata)

    issues = build_issue_payloads(result, mapper)

    if dry_run:
        return CloudSubmitReport(created=0, failed=0, batches=0, errors=[])

    created = 0
    failed = 0
    errors: list[dict[str, Any]] = []
    batches = 0

    for batch in chunk_issues(issues, batch_size=BATCH_SIZE):
        batches += 1
        payload = build_bulk_create_payload(batch)
        resp = client.post("issue/bulk", json=payload)
        if resp.status_code >= 400:  # noqa: PLR2004 - using status code literal is acceptable here
            # Surface server error details if available
            try:
                detail = resp.json()
            except Exception:
                detail = {"error": resp.text}
            errors.append({"status": resp.status_code, "detail": detail})
            failed += len(batch)
            continue
        data = resp.json()
        # Jira bulk returns per-issue results; count successes/errors
        issues_created = len(data.get("issues", []))
        created += issues_created
        for err in data.get("errors", []):
            failed += 1
            errors.append(err)

    return CloudSubmitReport(created=created, failed=failed, batches=batches, errors=errors)


# NOTE, Jira CLoud: Some Jira Cloud users are affected by the historical "divide by 60" behavior. The fix (*60) will be implemented in this sink.
#   if config.get("jira.cloud.estimate.multiply_by_60", False):
#       row[estimate_index] = str(int(row[estimate_index]) * 60)
