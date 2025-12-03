"""Shared error message snippets and helpers."""

from __future__ import annotations

JIRA_API_TOKEN_GUIDANCE = (
    "Create or rotate your Jira API token at: https://id.atlassian.com/manage-profile/security/api-tokens"
)

JIRA_CLOUD_CREDENTIALS_HINT = (
    "Ensure jira.connection.auth.email and jira.connection.auth.api_token are set in your configuration, "
    "or via environment variables JIRA_EMAIL / JIRA_API_TOKEN, or run the tool with --credentials to set them."
)
