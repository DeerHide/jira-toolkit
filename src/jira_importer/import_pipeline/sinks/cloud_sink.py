"""Jira Cloud API sink: creates issues via REST v3 in batches.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ...config.config_view import ConfigView
from ..cloud.bulk import build_bulk_create_payload, chunk_issues
from ..cloud.client import JiraCloudClient
from ..cloud.constants import BATCH_SIZE
from ..cloud.mappers import IssueMapper
from ..cloud.metadata import MetadataCache
from ..models import ProcessorResult

logger = logging.getLogger(__name__)


def _write_payload_debug(payload: dict[str, Any], batch_num: int, output_dir: Path) -> None:
    """Write JSON payload to debug file for inspection."""
    debug_file = output_dir / f"jira_cloud_payload_batch_{batch_num:03d}.json"
    try:
        with open(debug_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        logger.debug(f"Wrote Jira Cloud payload to: {debug_file}")
    except Exception as e:
        logger.warning(f"Failed to write payload debug file: {e}")


@dataclass
class CloudSubmitReport:
    """Report for Jira Cloud submission."""

    created: int
    failed: int
    batches: int
    errors: list[dict[str, Any]]


def write_cloud(
    result: ProcessorResult, config: object, *, dry_run: bool = False, output_dir: Path | None = None, ui=None
) -> CloudSubmitReport:  # pylint: disable=too-many-locals
    """Submit processed issues to Jira Cloud in batches."""
    cfg = ConfigView(config)

    # Resolve base_url from configuration
    base_url = cfg.get("jira.connection.site_address", None)
    if not base_url:
        raise ValueError("Missing jira.connection.site_address in configuration for Cloud sink")

    # Read authentication credentials from configuration
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

    # Separate parent and child issues
    parent_issues, child_issues, parent_mapping = _separate_parent_child_issues(result, mapper)

    if dry_run:
        return CloudSubmitReport(created=0, failed=0, batches=0, errors=[])

    created = 0
    failed = 0
    errors: list[dict[str, Any]] = []
    batches = 0
    parent_key_map: dict[str, str] = {}  # Maps placeholder -> real Jira key

    # Create parent issues first
    if parent_issues:
        logger.info(f"Creating {len(parent_issues)} parent issues first...")
        parent_results = _create_issues_batch(client, parent_issues, output_dir, "parent", ui)
        created += parent_results["created"]
        failed += parent_results["failed"]
        errors.extend(parent_results["errors"])
        batches += parent_results["batches"]

        # Build mapping from placeholder to real keys
        parent_key_map = _build_parent_key_mapping(parent_issues, parent_results["created_issues"])

    # Create child issues with correct parent references
    if child_issues:
        logger.info(f"Creating {len(child_issues)} child issues...")
        # Update child issues with real parent keys
        _update_child_parents(child_issues, parent_key_map, parent_mapping)
        child_results = _create_issues_batch(client, child_issues, output_dir, "child", ui)
        created += child_results["created"]
        failed += child_results["failed"]
        errors.extend(child_results["errors"])
        batches += child_results["batches"]

    return CloudSubmitReport(created=created, failed=failed, batches=batches, errors=errors)


def _separate_parent_child_issues(
    result: ProcessorResult, mapper: IssueMapper
) -> tuple[list[tuple[int, dict[str, Any]]], list[tuple[int, dict[str, Any]]], dict[str, str]]:
    """Separate issues into parents and children, return parent mapping."""
    parent_issues = []
    child_issues = []
    parent_mapping: dict[str, str] = {}  # Maps placeholder key to row index

    if result.indices is None:
        raise ValueError("Column indices not available for mapping")

    # Collect all issues and their summaries
    all_issues = []
    summary_to_row = {}

    for row_index, row in enumerate(result.rows):
        payload = mapper.map_row(row, result.indices)
        summary = payload.get("fields", {}).get("summary", "")
        all_issues.append((row_index, payload, summary))
        if summary:
            summary_to_row[summary] = row_index

    # Separate based on issue type and fix parent references
    for row_index, payload, summary in all_issues:
        issue_type = payload.get("fields", {}).get("issuetype", {}).get("name", "").lower()

        # Classify based on issue type: Sub-Tasks are children, everything else can be parents
        if issue_type == "sub-task":
            # Sub-Tasks are always children (must have parents)
            if "parent" in payload.get("fields", {}):
                # Try to fix parent reference if it looks wrong
                parent_key = payload.get("fields", {}).get("parent", {}).get("key", "")
                corrected_parent = _try_fix_parent_reference(parent_key, summary, summary_to_row, all_issues)

                if corrected_parent:
                    payload["fields"]["parent"]["key"] = corrected_parent
                    logger.info(
                        f"Row {row_index}: Corrected parent reference from '{parent_key}' to '{corrected_parent}'"
                    )

                child_issues.append((row_index, payload))
                logger.debug(
                    f"Row {row_index}: Sub-Task with parent '{payload.get('fields', {}).get('parent', {}).get('key', 'unknown')}'"
                )
            else:
                # Sub-Task without parent - convert to Story
                payload["fields"]["issuetype"]["name"] = "Story"
                parent_issues.append((row_index, payload))
                logger.info(f"Row {row_index}: Converted Sub-Task to Story (no parent found)")
                if summary:
                    parent_mapping[summary] = str(row_index)
        else:
            # Epics, Stories, Tasks can be parents (and may have parents themselves)
            # If they have parent references, try to fix them
            if "parent" in payload.get("fields", {}):
                parent_key = payload.get("fields", {}).get("parent", {}).get("key", "")
                corrected_parent = _try_fix_parent_reference(parent_key, summary, summary_to_row, all_issues)

                if corrected_parent:
                    payload["fields"]["parent"]["key"] = corrected_parent
                    logger.info(
                        f"Row {row_index}: Corrected parent reference from '{parent_key}' to '{corrected_parent}'"
                    )
                else:
                    # Remove invalid parent reference
                    del payload["fields"]["parent"]
                    logger.debug(f"Row {row_index}: Removed invalid parent reference '{parent_key}'")

            parent_issues.append((row_index, payload))
            # Store placeholder for mapping (use summary as placeholder key)
            if summary:
                parent_mapping[summary] = str(row_index)
            logger.debug(f"Row {row_index}: {issue_type.title()} issue '{summary}' (can have children)")

    logger.info(f"Separated {len(parent_issues)} parent issues and {len(child_issues)} child issues")

    return parent_issues, child_issues, parent_mapping


def _try_fix_parent_reference(
    parent_key: str, child_summary: str, summary_to_row: dict[str, int], all_issues: list
) -> str | None:
    """Try to fix incorrect parent references by finding logical parent relationships."""
    if not parent_key or not child_summary:
        return None

    # Convert parent_key to int if possible (it might be a row number)
    try:
        parent_row_num = int(float(parent_key))
    except (ValueError, TypeError):
        return None

    # Check if the referenced parent row actually exists and is a parent issue
    if parent_row_num < len(all_issues):
        _, parent_payload, _ = all_issues[parent_row_num]
        # If the referenced parent is actually a child issue, we need to find the real parent
        if "parent" in parent_payload.get("fields", {}):
            # The referenced parent is itself a child - find the logical parent
            return _find_logical_parent(child_summary, summary_to_row)

    # Find the most recent parent issue (Story or Epic)
    for i in range(len(all_issues) - 1, -1, -1):
        _, parent_payload, _ = all_issues[i]
        parent_issue_type = parent_payload.get("fields", {}).get("issuetype", {}).get("name", "").lower()

        # Stories and Epics can be parents of Sub-Tasks
        if parent_issue_type in ["story", "epic"] and "parent" not in parent_payload.get("fields", {}):
            return str(i)

    # Check if this looks like a "Jira Cloud API Integration" sub-task
    if "Jira Cloud API Integration" in summary_to_row and any(
        keyword in child_summary.lower()
        for keyword in [
            "authentication",
            "security",
            "project",
            "field",
            "discovery",
            "data validation",
            "mapping",
            "import process",
            "error handling",
            "recovery",
            "integration",
            "workflow",
            "validation",
            "performance",
        ]
    ):
        return str(summary_to_row["Jira Cloud API Integration"])

    return None


def _find_logical_parent(child_summary: str, summary_to_row: dict[str, int]) -> str | None:
    """Find the most logical parent for a child issue based on its summary."""
    # Look for common parent patterns
    for parent_summary, row_num in summary_to_row.items():
        if any(
            keyword in child_summary.lower()
            for keyword in [
                "authentication",
                "security",
                "project",
                "field",
                "discovery",
                "data validation",
                "mapping",
                "import process",
                "error handling",
                "recovery",
                "integration",
                "workflow",
                "validation",
                "performance",
            ]
        ):
            if "jira cloud" in parent_summary.lower() or "api integration" in parent_summary.lower():
                return str(row_num)

    return None


def _create_issues_batch(
    client: JiraCloudClient, issues: list[tuple[int, dict[str, Any]]], output_dir: Path | None, issue_type: str, ui=None
) -> dict[str, Any]:
    """Create a batch of issues and return results."""
    created = 0
    failed = 0
    errors: list[dict[str, Any]] = []
    batches = 0
    created_issues: list[dict[str, Any]] = []

    # Extract just the payloads for processing
    payloads = [payload for _, payload in issues]

    # Calculate total batches for progress tracking
    total_batches = len(list(chunk_issues(payloads, batch_size=BATCH_SIZE)))

    # Add progress tracking if UI is available
    if ui and hasattr(ui, "progress"):
        with ui.progress() as progress:
            task = progress.add_task(f"Creating {issue_type} issues", total=total_batches)

            for batch in chunk_issues(payloads, batch_size=BATCH_SIZE):
                batches += 1
                payload = build_bulk_create_payload(batch)

                # Write payload to debug file if output_dir is provided
                if output_dir:
                    _write_payload_debug(payload, batches, output_dir)

                resp = client.post("issue/bulk", json=payload)
                if resp.status_code >= 400:  # noqa: PLR2004
                    try:
                        detail = resp.json()
                    except Exception:
                        detail = {"error": resp.text}
                    errors.append({"status": resp.status_code, "detail": detail})
                    failed += len(batch)
                    progress.advance(task)
                    continue

                data = resp.json()
                issues_created = len(data.get("issues", []))
                created += issues_created

                # Collect created issues for mapping
                for issue in data.get("issues", []):
                    created_issues.append(issue)

                for err in data.get("errors", []):
                    failed += 1
                    errors.append(err)
                    logger.error(f"Jira API error: {err}")

                progress.advance(task)
    else:
        # Fallback without progress tracking
        for batch in chunk_issues(payloads, batch_size=BATCH_SIZE):
            batches += 1
            payload = build_bulk_create_payload(batch)

            # Write payload to debug file if output_dir is provided
            if output_dir:
                _write_payload_debug(payload, batches, output_dir)

            resp = client.post("issue/bulk", json=payload)
            if resp.status_code >= 400:  # noqa: PLR2004
                try:
                    detail = resp.json()
                except Exception:
                    detail = {"error": resp.text}
                errors.append({"status": resp.status_code, "detail": detail})
                failed += len(batch)
                continue

            data = resp.json()
            issues_created = len(data.get("issues", []))
            created += issues_created

            # Collect created issues for mapping
            for issue in data.get("issues", []):
                created_issues.append(issue)

            for err in data.get("errors", []):
                failed += 1
                errors.append(err)
                logger.error(f"Jira API error: {err}")

    return {
        "created": created,
        "failed": failed,
        "errors": errors,
        "batches": batches,
        "created_issues": created_issues,
    }


def _build_parent_key_mapping(
    parent_issues: list[tuple[int, dict[str, Any]]], created_issues: list[dict[str, Any]]
) -> dict[str, str]:
    """Build mapping from placeholder keys to real Jira keys."""
    mapping: dict[str, str] = {}

    # Map by row index and summary for flexibility
    for i, (row_index, parent_payload) in enumerate(parent_issues):
        if i < len(created_issues) and "key" in created_issues[i]:
            real_key = created_issues[i]["key"]
            # Map both row index and summary for flexibility
            mapping[str(row_index)] = real_key
            summary = parent_payload.get("fields", {}).get("summary", f"parent_{i}")
            mapping[summary] = real_key
            logger.debug(f"Mapped parent row {row_index} ('{summary}') -> '{real_key}'")

    return mapping


def _update_child_parents(
    child_issues: list[tuple[int, dict[str, Any]]],
    parent_key_map: dict[str, str],
    parent_mapping: dict[str, str],  # pylint: disable=unused-argument
) -> None:
    """Update child issues with real parent keys (modifies in place)."""
    for row_index, child_payload in child_issues:
        # Get the parent reference
        parent_ref = child_payload.get("fields", {}).get("parent", {})
        if "key" in parent_ref:
            placeholder_key = parent_ref["key"]

            # Try to find the real key
            if placeholder_key in parent_key_map:
                real_key = parent_key_map[placeholder_key]
                child_payload["fields"]["parent"]["key"] = real_key
                logger.debug(f"Updated child parent reference: {placeholder_key} -> {real_key}")
            else:
                # Check if this is a sub-task with invalid parent reference
                issuetype = child_payload.get("fields", {}).get("issuetype", {}).get("name", "")
                if issuetype.lower() == "sub-task":
                    # Convert sub-task to story since parent is invalid
                    child_payload["fields"]["issuetype"]["name"] = "Story"
                    logger.info(
                        f"Row {row_index}: Converted sub-task to story (invalid parent reference '{placeholder_key}')"
                    )

                # Remove invalid parent reference
                del child_payload["fields"]["parent"]
                logger.debug(f"Removed invalid parent reference '{placeholder_key}' for row {row_index}")
