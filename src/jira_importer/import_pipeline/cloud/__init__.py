"""Jira Cloud integration package.

Modules:
    auth: Authentication helpers (OAuth 3LO, basic fallback) and token storage.
    client: HTTP client for Jira Cloud REST API v3 with resilience.
    metadata: Cached lookups for fields, projects, issuetypes, users.
    mappers: Mapping from normalized rows to Jira issue payloads.
    bulk: Helpers to build payloads for bulk operations.
    secrets: Secrets resolution utilities for Jira Cloud integration.

Generated
"""
