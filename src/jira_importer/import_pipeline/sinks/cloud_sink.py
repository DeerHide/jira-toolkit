"""Jira Cloud API sink: creates issues via REST v3 in batches.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ...config.config_view import ConfigView
from ...config.constants import LEVEL_2_EPIC, LEVEL_3_STORY, LEVEL_4_SUBTASK
from ...config.issuetypes import get_default_level3_type, get_issue_type_level
from ...errors import ConfigurationError, JiraApiError, JiraAuthError, NetworkError, ProcessingError
from ..cloud.bulk import build_bulk_create_payload, chunk_issues
from ..cloud.client import JiraCloudClient
from ..cloud.constants import (
    AUTH_EMAIL_KEY,
    AUTH_TOKEN_KEY,
    BATCH_SIZE,
    HTTP_ERROR_THRESHOLD,
    PARENT_RESOLUTION_KEYWORDS,
)
from ..cloud.mappers import IssueMapper
from ..cloud.metadata import MetadataCache
from ..models import ColumnIndices, ProcessorResult

# HTTP status codes for better error handling
HTTP_OK = 200
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_TOO_MANY_REQUESTS = 429
HTTP_SERVER_ERROR_START = 500
HTTP_SERVER_ERROR_END = 600

logger = logging.getLogger(__name__)


def _write_payload_debug(payload: dict[str, Any], batch_num: int, output_dir: Path) -> None:
    """Write JSON payload to debug file for inspection."""
    debug_file = output_dir / f"jira_cloud_payload_batch_{batch_num:03d}.json"
    try:
        with open(debug_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        logger.debug(f"Wrote Jira Cloud payload to: {debug_file}")
    except (OSError, TypeError, ValueError) as e:
        logger.warning(f"Failed to write payload debug file: {e}")


@dataclass
class CloudSubmitReport:
    """Report for Jira Cloud submission."""

    created: int
    failed: int
    batches: int
    errors: list[dict[str, Any]]
    created_issue_keys: list[str] = field(default_factory=list)


def _validate_config(config: object) -> tuple[str, str, str]:
    """Validate and extract Jira Cloud configuration."""
    from ..cloud.secrets import SecretSpec, resolve_secret  # pylint: disable=import-outside-toplevel

    cfg = ConfigView(config)
    base_url = cfg.get("jira.connection.site_address", None)
    if not base_url:
        raise ConfigurationError(
            "Missing jira.connection.site_address in configuration for Cloud sink. "
            "You can set it in your JSON/Excel config.",
            details={"config_key": "jira.connection.site_address"},
        )

    # Basic URL validation to catch obvious misconfigurations early.
    parsed = urlparse(str(base_url))
    if not parsed.scheme or not parsed.netloc:
        raise ConfigurationError(
            "Invalid jira.connection.site_address in configuration for Cloud sink. "
            "Expected an HTTPS URL like 'https://your-domain.atlassian.net'.",
            details={"config_key": "jira.connection.site_address", "value": str(base_url)},
        )
    if parsed.scheme.lower() != "https":
        raise ConfigurationError(
            "Insecure jira.connection.site_address in configuration for Cloud sink. "
            "Only HTTPS URLs are supported (e.g. 'https://your-domain.atlassian.net').",
            details={"config_key": "jira.connection.site_address", "value": str(base_url)},
        )

    # Use proper credential resolution (keyring -> env -> config)
    email_spec = SecretSpec(config_key=AUTH_EMAIL_KEY, env_fallback="JIRA_EMAIL")
    token_spec = SecretSpec(config_key=AUTH_TOKEN_KEY, env_fallback="JIRA_API_TOKEN")

    email = resolve_secret(cfg, email_spec, allow_keyring=True, prompt_if_missing=False)
    api_token = resolve_secret(cfg, token_spec, allow_keyring=True, prompt_if_missing=False)

    # Check for missing email
    if not email:
        raise ConfigurationError(
            "Missing jira.connection.auth.email in configuration for Cloud sink. "
            "Set it via one of: config key 'jira.connection.auth.email'; environment variable JIRA_EMAIL; "
            "or run 'jira-importer --credentials' to enter and store it securely.",
            details={"config_key": "jira.connection.auth.email"},
        )

    # Lightweight email format validation
    if "@" not in email or email.strip().startswith("@") or email.strip().endswith("@"):
        raise ConfigurationError(
            f"Invalid Jira account email configured for Cloud sink: '{email}'. "
            "Please provide a valid email address (e.g. name@example.com).",
            details={"config_key": "jira.connection.auth.email", "value": email},
        )

    # Check for missing or empty API token
    if not api_token:
        raise ConfigurationError(
            "Missing or empty jira.connection.auth.api_token in configuration for Cloud sink. "
            "Set it via one of: config key 'jira.connection.auth.api_token'; environment variable JIRA_API_TOKEN; "
            "or run 'jira-importer --credentials' to enter and store it securely. "
            "Generate a token at: https://id.atlassian.com/manage-profile/security/api-tokens",
            details={"config_key": "jira.connection.auth.api_token"},
        )

    # Check if API token is just whitespace
    if not api_token.strip():
        raise ConfigurationError(
            "Empty jira.connection.auth.api_token in configuration for Cloud sink. "
            "The API token cannot be empty or whitespace. Set it via config/env or with 'jira-importer --credentials'. "
            "Generate a valid token at: https://id.atlassian.com/manage-profile/security/api-tokens",
            details={"config_key": "jira.connection.auth.api_token", "reason": "Token is empty or whitespace"},
        )

    return base_url, email, api_token


def _setup_auth(email: str, api_token: str):
    """Setup authentication provider for Jira Cloud."""
    from ..cloud.auth import BasicAuthProvider  # pylint: disable=import-outside-toplevel

    return BasicAuthProvider(email, api_token)


def _process_batches(
    result: ProcessorResult,
    client: JiraCloudClient,
    dry_run: bool,
    output_dir: Path | None,
    ui,
    config: object,
    auth_context: dict | None,
) -> CloudSubmitReport:
    """Process issues in batches and return submission report."""
    cfg = ConfigView(config)

    # Ensure Excel table configuration is loaded for assignee mapping
    if hasattr(config, "load_table_config"):
        try:
            config.load_table_config()
            logger.debug("Excel table configuration loaded for assignee mapping")
        except Exception as e:
            logger.warning(f"Could not load Excel table configuration: {e}")

    metadata = MetadataCache(client)
    mapper = IssueMapper(cfg, metadata)

    # Separate issues into three categories based on configurable issue type levels
    epics, stories_and_tasks, sub_tasks, parent_mapping, all_issues = _separate_parent_child_issues(
        result, mapper, config
    )

    if dry_run:
        return CloudSubmitReport(created=0, failed=0, batches=0, errors=[], created_issue_keys=[])

    created = 0
    failed = 0
    errors: list[dict[str, Any]] = []
    batches = 0
    parent_key_map: dict[str, str] = {}  # Maps placeholder -> real Jira key
    created_issue_keys: list[str] = []

    # Batch 1: Create Epics first (standalone)
    if epics:
        logger.info(f"Creating {len(epics)} epics...")
        epic_results = _create_issues_batch(client, epics, output_dir, "epic", ui, auth_context)
        created += epic_results["created"]
        failed += epic_results["failed"]
        errors.extend(epic_results["errors"])
        batches += epic_results["batches"]

        # Collect new issue keys
        for issue in epic_results["created_issues"]:
            if "key" in issue:
                created_issue_keys.append(issue["key"])

        # Build mapping from placeholder to actual keys for epics
        epic_key_map = _build_parent_key_mapping(epics, epic_results["created_issues"])
        parent_key_map.update(epic_key_map)

    # Batch 2: Create Stories and Tasks with parent references to Epics
    if stories_and_tasks:
        logger.info(f"Creating {len(stories_and_tasks)} stories and tasks...")
        # Update stories and tasks with actual parent keys
        _update_child_parents(stories_and_tasks, parent_key_map, parent_mapping, mapper, config)
        story_task_results = _create_issues_batch(
            client, stories_and_tasks, output_dir, "Stories & Tasks", ui, auth_context
        )
        created += story_task_results["created"]
        failed += story_task_results["failed"]
        errors.extend(story_task_results["errors"])
        batches += story_task_results["batches"]

        # Collect new issue keys
        for issue in story_task_results["created_issues"]:
            if "key" in issue:
                created_issue_keys.append(issue["key"])

        # Build mapping from placeholder to actual keys for stories and tasks
        story_task_key_map = _build_parent_key_mapping(stories_and_tasks, story_task_results["created_issues"])
        parent_key_map.update(story_task_key_map)

    # Batch 3: Create Sub-tasks with parent references to Stories/Tasks
    if sub_tasks:
        logger.info(f"Creating {len(sub_tasks)} sub-tasks...")
        # Resolve Sub-task parent references now that Stories/Tasks exist
        if result.indices is not None:
            _resolve_subtask_parents(sub_tasks, parent_key_map, result.indices, all_issues, config)
        # Update sub-tasks with real parent keys
        _update_child_parents(sub_tasks, parent_key_map, parent_mapping, mapper, config)
        subtask_results = _create_issues_batch(client, sub_tasks, output_dir, "subtask", ui, auth_context)
        created += subtask_results["created"]
        failed += subtask_results["failed"]
        errors.extend(subtask_results["errors"])
        batches += subtask_results["batches"]

        # Collect created issue keys
        for issue in subtask_results["created_issues"]:
            if "key" in issue:
                created_issue_keys.append(issue["key"])

    return CloudSubmitReport(
        created=created, failed=failed, batches=batches, errors=errors, created_issue_keys=created_issue_keys
    )


def write_cloud(
    result: ProcessorResult,
    config: object,
    *,
    dry_run: bool = False,
    output_dir: Path | None = None,
    ui=None,
    auto_reply: bool | None = None,
) -> CloudSubmitReport:
    """Submit processed issues to Jira Cloud in batches."""
    # Secondary safety net: opportunistic ensure of credentials if UI provided
    auth_status = None
    try:
        if ui is not None:
            from ..cloud.credential_manager import ensure_cloud_credentials  # pylint: disable=import-outside-toplevel

            status = ensure_cloud_credentials(ui, ConfigView(config), auto_reply)
            auth_status = status
            if not status.get("found"):
                raise ConfigurationError(
                    "Jira API credentials are missing. Set them via config (jira.connection.auth.email/api_token), "
                    "environment variables (JIRA_EMAIL/JIRA_API_TOKEN), or run 'jira-importer --credentials' to set them.",
                    details={"missing_credentials": True},
                )
    except Exception:
        # Do not mask errors; validation step below will provide exact messages
        pass

    base_url, email, api_token = _validate_config(config)
    # Build auth context for downstream error messages
    auth_context = {
        "email": (auth_status or {}).get("email") or email,
        "secret_source": (auth_status or {}).get("source") or "unknown",
    }
    auth_provider = _setup_auth(email, api_token)
    client = JiraCloudClient(base_url=f"{base_url.rstrip('/')}/rest/api/3", auth_provider=auth_provider)

    # Test authentication before proceeding
    # This pre-flight test provides clear error messages for common auth issues
    try:
        logger.info("Testing Jira authentication...")
        # Make a simple API call to test authentication
        test_response = client.get("/myself")
        if test_response.status_code == HTTP_OK:
            try:
                user_info = test_response.json()
                logger.info(f"Authentication successful - connected as: {user_info.get('displayName', 'Unknown')}")
            except (ValueError, KeyError) as json_error:
                logger.warning(f"Authentication successful but received malformed response: {json_error}")
                logger.info("Authentication successful - proceeding with import")
        elif test_response.status_code == HTTP_UNAUTHORIZED:
            raise JiraAuthError(
                "Jira authentication failed (HTTP 401) - your API token may have expired. "
                "Use 'jira-importer --credentials show' to inspect current values, or '... --credentials' to update. "
                "Refresh your token at: https://id.atlassian.com/manage-profile/security/api-tokens"
                f" (email: {auth_context.get('email') or 'unknown'}, secret source: {auth_context.get('secret_source')})",
                status_code=HTTP_UNAUTHORIZED,
                details={
                    "email": auth_context.get("email") or "unknown",
                    "secret_source": auth_context.get("secret_source"),
                },
            )
        elif test_response.status_code == HTTP_FORBIDDEN:
            raise JiraAuthError(
                "Jira authentication failed (HTTP 403) - your API token may be invalid or you lack permissions. "
                "Use 'jira-importer --credentials show' to inspect current values, or '... --credentials' to update. "
                "Check/rotate your token at: https://id.atlassian.com/manage-profile/security/api-tokens"
                f" (email: {auth_context.get('email') or 'unknown'}, secret source: {auth_context.get('secret_source')})",
                status_code=HTTP_FORBIDDEN,
                details={
                    "email": auth_context.get("email") or "unknown",
                    "secret_source": auth_context.get("secret_source"),
                },
            )
        elif test_response.status_code == HTTP_NOT_FOUND:
            raise JiraApiError(
                f"Jira instance not found at {base_url} (HTTP 404). Please check your site_address configuration.",
                status_code=HTTP_NOT_FOUND,
                details={"base_url": base_url},
            )
        elif test_response.status_code == HTTP_TOO_MANY_REQUESTS:
            raise JiraApiError(
                "Jira API rate limit exceeded (HTTP 429). Please wait a moment and try again.",
                status_code=HTTP_TOO_MANY_REQUESTS,
            )
        elif HTTP_SERVER_ERROR_START <= test_response.status_code < HTTP_SERVER_ERROR_END:
            raise JiraApiError(
                f"Jira server error (HTTP {test_response.status_code}). Please try again later or contact your Jira administrator.",
                status_code=test_response.status_code,
            )
        else:
            raise JiraApiError(
                f"Authentication test failed with status {test_response.status_code}"
                f" (email: {auth_context.get('email') or 'unknown'}, secret source: {auth_context.get('secret_source')})",
                status_code=test_response.status_code,
                details={
                    "email": auth_context.get("email") or "unknown",
                    "secret_source": auth_context.get("secret_source"),
                },
            )
    except (JiraAuthError, JiraApiError, ConfigurationError):
        # Re-raise our custom error messages
        raise
    except Exception as e:
        # Handle network/connection issues
        error_str = str(e).lower()
        if any(keyword in error_str for keyword in ["timeout", "connection", "network", "dns", "ssl"]):
            raise NetworkError(
                f"Network connection failed to {base_url}. Please check your internet connection and try again. Error: {e!s}",
                details={"base_url": base_url, "original_error": str(e), "error_type": type(e).__name__},
            ) from e
        elif "not found" in error_str or "404" in error_str:
            raise JiraApiError(
                f"Jira instance not found at {base_url}. Please check your site_address configuration.",
                status_code=404,
                details={"base_url": base_url, "original_error": str(e)},
            ) from e
        else:
            raise NetworkError(
                f"Failed to connect to Jira at {base_url}. Error: {e!s}",
                details={"base_url": base_url, "original_error": str(e), "error_type": type(e).__name__},
            ) from e

    return _process_batches(result, client, dry_run, output_dir, ui, config, auth_context)


def _separate_parent_child_issues(
    result: ProcessorResult, mapper: IssueMapper, config: Any
) -> tuple[
    list[tuple[int, dict[str, Any]]],
    list[tuple[int, dict[str, Any]]],
    list[tuple[int, dict[str, Any]]],
    dict[str, str],
    list,
]:
    """Separate issues into three categories: Epics, Stories/Tasks, and Sub-tasks."""
    if result.indices is None:
        raise ProcessingError(
            "Column indices not available for mapping",
            details={"reason": "ProcessorResult.indices is None"},
        )

    # Collect all issues and their summaries
    all_issues, summary_to_row = _collect_issues_with_summaries(result, mapper)

    # Separate based on issue type and fix parent references
    epics, stories_and_tasks, sub_tasks, parent_mapping = _classify_and_fix_issues(
        all_issues, summary_to_row, result.indices, config
    )

    logger.info(f"Separated {len(epics)} epics, {len(stories_and_tasks)} stories/tasks, and {len(sub_tasks)} sub-tasks")
    return epics, stories_and_tasks, sub_tasks, parent_mapping, all_issues


def _collect_issues_with_summaries(result: ProcessorResult, mapper: IssueMapper) -> tuple[list, dict[str, int]]:
    """Collect all issues and build summary to row mapping."""
    all_issues = []
    summary_to_row = {}

    for row_index, row in enumerate(result.rows):
        if result.indices is None:
            raise ProcessingError(
                "Column indices not available for mapping",
                details={"reason": "ProcessorResult.indices is None", "row_index": row_index},
            )
        payload = mapper.map_row(row, result.indices)
        summary = payload.get("fields", {}).get("summary", "")
        all_issues.append((row_index, payload, summary, row))  # Include original row data
        if summary:
            summary_to_row[summary] = row_index

    return all_issues, summary_to_row


def _classify_and_fix_issues(
    all_issues: list, summary_to_row: dict[str, int], indices: ColumnIndices, config: Any
) -> tuple[
    list[tuple[int, dict[str, Any]]], list[tuple[int, dict[str, Any]]], list[tuple[int, dict[str, Any]]], dict[str, str]
]:
    """Classify issues into three categories: Epics, Stories/Tasks, and Sub-tasks."""
    epics: list[tuple[int, dict[str, Any]]] = []
    stories_and_tasks: list[tuple[int, dict[str, Any]]] = []
    sub_tasks: list[tuple[int, dict[str, Any]]] = []
    parent_mapping: dict[str, str] = {}

    # Create ConfigView for consistent access pattern
    config_view = ConfigView(config)

    for row_index, payload, summary, _ in all_issues:
        issue_type_name = payload.get("fields", {}).get("issuetype", {}).get("name", "")

        # Use config-driven level classification instead of hardcoded strings
        # This supports both new hierarchical config and backward compatibility
        level = get_issue_type_level(config_view.get, issue_type_name)

        if level == LEVEL_2_EPIC:  # Epic level
            epics.append((row_index, payload))
            if summary:
                parent_mapping[summary] = str(row_index)
            logger.debug(f"Row {row_index}: Epic issue (can have children)")
        elif level == LEVEL_4_SUBTASK:  # Sub-task level
            _process_subtask(
                row_index,
                payload,
                summary,
                sub_tasks,
                stories_and_tasks,  # Pass as parent_issues for fallback
                parent_mapping,
                summary_to_row,
                all_issues,
                indices,
                config,
            )
        else:  # Level 3 (Story/Task/Bug) or unknown (default to level 3)
            _process_parent_issue(
                row_index,
                payload,
                summary,
                stories_and_tasks,
                parent_mapping,
                summary_to_row,
                all_issues,
                indices,
                config,
            )

    return epics, stories_and_tasks, sub_tasks, parent_mapping


def _process_subtask(
    row_index: int,
    payload: dict[str, Any],
    summary: str,
    child_issues: list,
    parent_issues: list,
    parent_mapping: dict[str, str],
    summary_to_row: dict[str, int],  # pylint: disable=unused-argument
    all_issues: list,  # pylint: disable=unused-argument
    indices: ColumnIndices,  # pylint: disable=unused-argument
    config: Any,
) -> None:
    """Process a sub-task issue."""
    if "parent" in payload.get("fields", {}):
        # For Sub-tasks, we'll defer parent reference resolution until after Stories/Tasks are created
        # Just store the Sub-task as-is for now
        child_issues.append((row_index, payload))
        logger.debug(f"Row {row_index}: Sub-Task with parent reference (will be resolved later)")
    else:
        # Sub-Task without parent - convert to default level 3 type
        config_view = ConfigView(config)
        fallback_type = get_default_level3_type(config_view.get)
        payload["fields"]["issuetype"]["name"] = fallback_type
        parent_issues.append((row_index, payload))
        logger.info(f"Row {row_index}: Converted Sub-Task to {fallback_type} (no parent found)")
        if summary:
            parent_mapping[summary] = str(row_index)


def _process_parent_issue(
    row_index: int,
    payload: dict[str, Any],
    summary: str,
    parent_issues: list,
    parent_mapping: dict[str, str],
    summary_to_row: dict[str, int],
    all_issues: list,
    indices: ColumnIndices,
    config: Any,
) -> None:
    """Process a parent issue (Epic, Story, Task)."""
    config_view = ConfigView(config)
    issue_type = payload.get("fields", {}).get("issuetype", {}).get("name", "").lower()

    # For parent issues, keep parent references if they can be resolved to actual Jira keys
    # Otherwise, remove them and they will be handled as standalone issues
    if "parent" in payload.get("fields", {}):
        parent_key = payload.get("fields", {}).get("parent", {}).get("key", "")
        # Try to resolve the parent reference to a real Jira key
        corrected_parent = _try_fix_parent_reference(parent_key, summary, summary_to_row, all_issues, indices, config)

        if corrected_parent:
            # Check if this is a valid parent reference (not a row index)
            try:
                parent_row_index = int(corrected_parent)
                if parent_row_index < len(all_issues):
                    # This is a row index - we need to check if the referenced parent exists and is a valid parent
                    _, parent_payload, _, _ = all_issues[parent_row_index]
                    parent_issue_type = parent_payload.get("fields", {}).get("issuetype", {}).get("name", "").lower()
                    parent_level = get_issue_type_level(config_view.get, parent_issue_type)
                    if parent_level == LEVEL_2_EPIC and "parent" not in parent_payload.get("fields", {}):
                        # Valid parent reference - keep it as row index for later mapping
                        payload["fields"]["parent"]["key"] = corrected_parent
                        logger.info(
                            f"Row {row_index}: Corrected parent reference from '{parent_key}' to '{corrected_parent}'"
                        )
                    else:
                        # Invalid parent reference - remove it
                        del payload["fields"]["parent"]
                        logger.debug(
                            f"Row {row_index}: Removed invalid parent reference '{parent_key}' (referenced parent is not a valid Epic)"
                        )
                else:
                    # Invalid row index - remove parent reference
                    del payload["fields"]["parent"]
                    logger.debug(
                        f"Row {row_index}: Removed invalid parent reference '{parent_key}' (invalid row index)"
                    )
            except (ValueError, TypeError):
                # corrected_parent is not a row index - remove parent reference
                del payload["fields"]["parent"]
                logger.debug(
                    f"Row {row_index}: Removed invalid parent reference '{parent_key}' (not a valid row index)"
                )
        else:
            # Remove invalid parent reference
            del payload["fields"]["parent"]
            logger.debug(f"Row {row_index}: Removed invalid parent reference '{parent_key}'")

    parent_issues.append((row_index, payload))
    # Store placeholder for mapping (use summary as placeholder key)
    if summary:
        parent_mapping[summary] = str(row_index)
    logger.debug(f"Row {row_index}: {issue_type.title()} issue (can have children)")


def _try_fix_parent_reference(
    parent_key: str,
    child_summary: str,
    summary_to_row: dict[str, int],
    all_issues: list,
    indices: ColumnIndices,
    config: Any,
) -> str | None:
    """Try to fix incorrect parent references by finding logical parent links."""
    config_view = ConfigView(config)

    if not parent_key or not child_summary:
        return None

    # Convert parent_key to int if possible (it might be an Issue ID)
    try:
        parent_issue_id = int(float(parent_key))
    except (ValueError, TypeError):
        return None

    # First, try to find the parent by Issue ID (most common case)
    parent_row_index = _find_parent_by_issue_id(parent_issue_id, all_issues, indices)
    if parent_row_index is not None:
        _, parent_payload, _, _ = all_issues[parent_row_index]
        # If the referenced parent is actually a child issue, we need to find the real parent
        if "parent" in parent_payload.get("fields", {}):
            # The referenced parent is itself a child - find the logical parent
            return _find_logical_parent(child_summary, summary_to_row)
        return str(parent_row_index)

    # Fallback: Find the most recent parent issue (Story or Epic)
    for i in range(len(all_issues) - 1, -1, -1):
        _, parent_payload, _, _ = all_issues[i]
        parent_issue_type = parent_payload.get("fields", {}).get("issuetype", {}).get("name", "").lower()

        # Stories and Epics can be parents of Sub-Tasks
        parent_level = get_issue_type_level(config_view.get, parent_issue_type)
        if parent_level in [LEVEL_2_EPIC, LEVEL_3_STORY] and "parent" not in parent_payload.get("fields", {}):
            return str(i)

    # Check if this looks like a "Jira Cloud API Integration" sub-task
    if "Jira Cloud API Integration" in summary_to_row and any(
        keyword in child_summary.lower() for keyword in PARENT_RESOLUTION_KEYWORDS
    ):
        return str(summary_to_row["Jira Cloud API Integration"])

    return None


def _find_parent_by_issue_id(issue_id: int, all_issues: list, indices: ColumnIndices) -> int | None:
    """Find the row index of an issue by its Issue ID."""
    for row_index, (_, _, _, original_row) in enumerate(all_issues):
        # Get the Issue ID from the original row data using the column indices
        if indices.issue_id is not None and indices.issue_id < len(original_row):
            issue_id_value = original_row[indices.issue_id]
            if issue_id_value and str(issue_id_value).strip() == str(issue_id):
                return row_index
    return None


def _find_logical_parent(child_summary: str, summary_to_row: dict[str, int]) -> str | None:
    """Find the most logical parent for a child issue based on its summary."""
    # Look for common parent patterns
    for parent_summary, row_num in summary_to_row.items():
        if any(keyword in child_summary.lower() for keyword in PARENT_RESOLUTION_KEYWORDS):
            if "jira cloud" in parent_summary.lower() or "api integration" in parent_summary.lower():
                return str(row_num)

    return None


def _create_issues_batch(
    client: JiraCloudClient,
    issues: list[tuple[int, dict[str, Any]]],
    output_dir: Path | None,
    issue_type: str,
    ui=None,
    auth_context: dict | None = None,
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

    # Build auth context suffix for error messages
    context_suffix = ""
    if auth_context is not None:
        context_suffix = (
            f" (email: {auth_context.get('email') or 'unknown'}, "
            f"secret source: {auth_context.get('secret_source') or 'unknown'})"
        )

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
                if resp.status_code >= HTTP_ERROR_THRESHOLD:
                    try:
                        detail = resp.json()
                    except ValueError:
                        detail = {"error": resp.text}

                    # Check for specific error cases and provide clear user guidance
                    if resp.status_code == HTTP_UNAUTHORIZED:
                        error_msg = (
                            "Authentication failed (HTTP 401) - your API token may have expired" + context_suffix
                        )
                        logger.error(error_msg)
                        raise JiraAuthError(
                            error_msg,
                            status_code=HTTP_UNAUTHORIZED,
                            details={"batch_num": batches, "issue_type": issue_type},
                        )
                    elif resp.status_code == HTTP_FORBIDDEN:
                        error_msg = (
                            "Authentication failed (HTTP 403) - your API token may be invalid or you lack permissions"
                            + context_suffix
                        )
                        logger.error(error_msg)
                        raise JiraAuthError(
                            error_msg,
                            status_code=HTTP_FORBIDDEN,
                            details={"batch_num": batches, "issue_type": issue_type},
                        )
                    elif resp.status_code == HTTP_NOT_FOUND:
                        error_msg = "Jira API endpoint not found (HTTP 404) - check your site_address"
                        logger.error(error_msg)
                        raise JiraApiError(
                            error_msg,
                            status_code=HTTP_NOT_FOUND,
                            details={"batch_num": batches, "issue_type": issue_type},
                        )
                    elif resp.status_code == HTTP_TOO_MANY_REQUESTS:
                        error_msg = "Jira API rate limit exceeded (HTTP 429) - please wait and try again"
                        logger.error(error_msg)
                        raise JiraApiError(
                            error_msg,
                            status_code=HTTP_TOO_MANY_REQUESTS,
                            details={"batch_num": batches, "issue_type": issue_type},
                        )
                    elif HTTP_SERVER_ERROR_START <= resp.status_code < HTTP_SERVER_ERROR_END:
                        error_msg = f"Jira server error (HTTP {resp.status_code}) - please try again later"
                        logger.error(error_msg)
                        raise JiraApiError(
                            error_msg,
                            status_code=resp.status_code,
                            details={"batch_num": batches, "issue_type": issue_type},
                        )

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
            if resp.status_code >= HTTP_ERROR_THRESHOLD:
                try:
                    detail = resp.json()
                except ValueError:
                    detail = {"error": resp.text}

                # Check for specific error cases
                if resp.status_code == HTTP_UNAUTHORIZED:
                    error_msg = "Authentication failed (HTTP 401) - your API token may have expired" + context_suffix
                    logger.error(error_msg)
                    raise JiraAuthError(
                        error_msg,
                        status_code=HTTP_UNAUTHORIZED,
                        details={"batch_num": batches, "issue_type": issue_type},
                    )
                elif resp.status_code == HTTP_FORBIDDEN:
                    error_msg = (
                        "Authentication failed (HTTP 403) - your API token may be invalid or you lack permissions"
                        + context_suffix
                    )
                    logger.error(error_msg)
                    raise JiraAuthError(
                        error_msg,
                        status_code=HTTP_FORBIDDEN,
                        details={"batch_num": batches, "issue_type": issue_type},
                    )
                elif resp.status_code == HTTP_NOT_FOUND:
                    error_msg = "Jira API endpoint not found (HTTP 404) - check your site_address"
                    logger.error(error_msg)
                    raise JiraApiError(
                        error_msg,
                        status_code=HTTP_NOT_FOUND,
                        details={"batch_num": batches, "issue_type": issue_type},
                    )
                elif resp.status_code == HTTP_TOO_MANY_REQUESTS:
                    error_msg = "Jira API rate limit exceeded (HTTP 429) - please wait and try again"
                    logger.error(error_msg)
                    raise JiraApiError(
                        error_msg,
                        status_code=HTTP_TOO_MANY_REQUESTS,
                        details={"batch_num": batches, "issue_type": issue_type},
                    )
                elif HTTP_SERVER_ERROR_START <= resp.status_code < HTTP_SERVER_ERROR_END:
                    error_msg = f"Jira server error (HTTP {resp.status_code}) - please try again later"
                    logger.error(error_msg)
                    raise JiraApiError(
                        error_msg,
                        status_code=resp.status_code,
                        details={"batch_num": batches, "issue_type": issue_type},
                    )

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
            logger.debug(f"Mapped parent row {row_index} -> '{real_key}'")

    return mapping


def _resolve_subtask_parents(
    sub_tasks: list[tuple[int, dict[str, Any]]],
    parent_key_map: dict[str, str],
    indices: ColumnIndices,
    all_issues: list,
    config: Any,
) -> None:
    """Resolve Sub-task parent references now that Stories/Tasks have been created."""
    for row_index, payload in sub_tasks:
        if "parent" in payload.get("fields", {}):
            parent_key = payload.get("fields", {}).get("parent", {}).get("key", "")
            # Try to fix parent reference now that we have the parent key map
            # Don't use _try_fix_parent_reference here as it has complex logic that might interfere
            corrected_parent = None

            if corrected_parent and corrected_parent in parent_key_map:
                real_parent_key = parent_key_map[corrected_parent]
                payload["fields"]["parent"]["key"] = real_parent_key
                logger.info(
                    f"Row {row_index}: Resolved Sub-task parent reference from '{parent_key}' to '{real_parent_key}'"
                )
            else:
                # Try to find parent by Issue ID
                try:
                    parent_issue_id = int(float(parent_key))
                    logger.debug(f"Row {row_index}: Looking for parent Issue ID {parent_issue_id}")
                    # Look for the parent in the key map by Issue ID
                    # The parent_key_map uses row indices as keys, but we need to find by Issue ID
                    # We need to find the row that has the matching Issue ID
                    found_parent = False
                    for key, value in parent_key_map.items():
                        # Check if this key corresponds to the parent Issue ID
                        # The key is a row index, and we need to find the row with Issue ID = parent_issue_id
                        if key.isdigit():
                            row_idx = int(key)
                            # We need to check if this row has the matching Issue ID
                            # Check if this row has the matching Issue ID
                            # We need to look up the actual Issue ID for this row
                            logger.debug(f"Row {row_index}: Checking row {row_idx} -> {value}")
                            # Check if the parent_issue_id matches the actual Issue ID for this row
                            # We need to look up the actual Issue ID for this row from the original data
                            # Find the row in all_issues that corresponds to this row_idx
                            actual_issue_id = None
                            for check_row_idx, (_, _, _, original_row) in enumerate(all_issues):
                                if (
                                    check_row_idx == row_idx
                                    and indices.issue_id is not None
                                    and indices.issue_id < len(original_row)
                                ):
                                    issue_id_value = original_row[indices.issue_id]
                                    if issue_id_value and str(issue_id_value).strip():
                                        try:
                                            actual_issue_id = int(float(issue_id_value))
                                            break
                                        except (ValueError, TypeError):
                                            continue

                            if actual_issue_id == parent_issue_id:
                                payload["fields"]["parent"]["key"] = value
                                logger.info(
                                    f"Row {row_index}: Resolved Sub-task parent reference from '{parent_key}' to '{value}'"
                                )
                                found_parent = True
                                break

                    if not found_parent:
                        # Parent not found - convert to default level 3 type
                        config_view = ConfigView(config)
                        fallback_type = get_default_level3_type(config_view.get)
                        payload["fields"]["issuetype"]["name"] = fallback_type
                        del payload["fields"]["parent"]
                        logger.info(f"Row {row_index}: Converted Sub-Task to {fallback_type} (parent not found)")
                except (ValueError, TypeError):
                    # Invalid parent reference - convert to default level 3 type
                    config_view = ConfigView(config)
                    fallback_type = get_default_level3_type(config_view.get)
                    payload["fields"]["issuetype"]["name"] = fallback_type
                    del payload["fields"]["parent"]
                    logger.info(f"Row {row_index}: Converted Sub-Task to {fallback_type} (invalid parent reference)")


def _update_child_parents(
    child_issues: list[tuple[int, dict[str, Any]]],
    parent_key_map: dict[str, str],
    parent_mapping: dict[str, str],  # pylint: disable=unused-argument
    mapper: IssueMapper,
    config: Any,
) -> None:
    """Update child issues with real parent keys (modifies in place)."""
    config_view = ConfigView(config)

    for row_index, child_payload in child_issues:
        # Get the parent reference
        parent_ref = child_payload.get("fields", {}).get("parent", {})
        if "key" in parent_ref:
            placeholder_key = parent_ref["key"]

            # Check if this is already a real Jira key
            if mapper.is_valid_jira_key(placeholder_key):
                # This is already a real Jira key, no need to update
                logger.debug(f"Row {row_index}: Parent reference already resolved to '{placeholder_key}'")
            elif placeholder_key in parent_key_map:
                real_key = parent_key_map[placeholder_key]
                child_payload["fields"]["parent"]["key"] = real_key
                logger.debug(f"Updated child parent reference for row {row_index}")
            else:
                # Check if this is a level 4 issue type with invalid parent reference
                issuetype = child_payload.get("fields", {}).get("issuetype", {}).get("name", "")
                if get_issue_type_level(config_view.get, issuetype) == LEVEL_4_SUBTASK:
                    # Convert level 4 issue to default level 3 since parent is invalid
                    fallback_type = get_default_level3_type(config_view.get)
                    child_payload["fields"]["issuetype"]["name"] = fallback_type
                    logger.info(
                        f"Row {row_index}: Converted {issuetype} to {fallback_type} (invalid parent reference '{placeholder_key}')"
                    )

                # Remove invalid parent reference
                del child_payload["fields"]["parent"]
                logger.debug(f"Removed invalid parent reference for row {row_index}")
