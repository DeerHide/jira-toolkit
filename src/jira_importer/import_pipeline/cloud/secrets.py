"""Secrets resolution utilities for Jira Cloud integration.

Resolution order:
    1) Environment variable (supports literal value or ${ENV:VARNAME} indirection)
    2) OS keychain (keyring) if enabled
    3) Optional interactive prompt (dev mode only), then store to keyring

All returned secrets must be redacted from logs/reports by callers using `redact_secret`.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module

from ...config.config_view import ConfigView

REDACTED = "****"
KEYRING_SERVICE = "dh-jira-toolkit"


def redact_secret(_: str | None) -> str:
    """Return a constant redaction string regardless of input."""
    return REDACTED


def _from_env_or_literal(value: str | None) -> str | None:
    """Resolve a config value possibly using ${ENV:VARNAME} indirection.

    Examples:
        "${ENV:JIRA_API_TOKEN}" -> os.environ.get("JIRA_API_TOKEN")
        "plain-value" -> "plain-value"
        None -> None
    """
    if value is None:
        return None
    value = str(value).strip()
    if value.startswith("${ENV:") and value.endswith("}"):
        env_key = value[6:-1]  # strip ${ENV: and }
        return os.environ.get(env_key)
    return value


def _get_env_override(env_var: str | None) -> str | None:
    if not env_var:
        return None
    return os.environ.get(env_var)


def _keyring_get(service: str, username: str) -> str | None:
    try:
        kr = import_module("keyring")  # type: ignore
    except Exception:
        return None
    try:
        return kr.get_password(service, username)  # type: ignore[attr-defined]
    except Exception:
        return None


def _keyring_set(service: str, username: str, secret: str) -> None:
    try:
        kr = import_module("keyring")  # type: ignore
    except Exception:
        return
    try:
        kr.set_password(service, username, secret)  # type: ignore[attr-defined]
    except Exception:
        pass


def store_secret_in_keyring(service: str, username: str, secret: str) -> None:
    """Public helper to persist secrets in the OS keychain (best-effort)."""
    _keyring_set(service, username, secret)


@dataclass
class SecretSpec:
    """Descriptor for a secret to resolve."""

    config_key: str  # e.g., "jira.cloud.auth.api_token"
    env_fallback: str | None = None  # e.g., "JIRA_API_TOKEN"
    keyring_service: str = KEYRING_SERVICE
    keyring_user_key: str | None = None  # defaults to config_key if None


def resolve_secret(
    cfg: ConfigView,
    spec: SecretSpec,
    *,
    allow_keyring: bool = True,
    prompt_if_missing: bool = False,
    prompt: Callable[[str], str] | None = None,
) -> str | None:
    """Resolve a secret using env -> keyring -> optional prompt.

    - Reads the config value and applies ${ENV:VAR} indirection if present.
    - If not found, checks explicit env fallback (spec.env_fallback).
    - If still missing and keyring is allowed and enabled, queries keyring.
    - If missing and prompting is enabled with a prompt function, asks the user and stores in keyring.
    """
    # 1) Read from config; apply ${ENV:VAR}
    raw = cfg.get(spec.config_key, None)
    value = _from_env_or_literal(raw)
    if value:
        return value

    # 2) Explicit env override
    env_val = _get_env_override(spec.env_fallback)
    if env_val:
        return env_val

    # 3) Keyring if enabled in config and globally allowed
    use_keyring = bool(cfg.get("security.use_keyring", True)) and allow_keyring
    if use_keyring:
        user_key = spec.keyring_user_key or spec.config_key
        kr_val = _keyring_get(spec.keyring_service, user_key)
        if kr_val:
            return kr_val

    # 4) Optional prompt (dev mode only) then store to keyring
    if prompt_if_missing and prompt is not None:
        user_key = spec.keyring_user_key or spec.config_key
        entered = prompt(f"Enter value for {spec.config_key}: ")
        if entered:
            if use_keyring:
                _keyring_set(spec.keyring_service, user_key, entered)
            return entered

    return None


def resolve_secret_with_source(
    cfg: ConfigView,
    spec: SecretSpec,
    *,
    allow_keyring: bool = True,
    prompt_if_missing: bool = False,
    prompt: Callable[[str], str] | None = None,
) -> tuple[str | None, str]:
    """Resolve a secret and return a tuple of (value, source).

    Sources: "config", "env", "keyring", "prompt", or "none" when not found.
    """
    # 1) Config (with ${ENV:VAR} expansion). If raw was present and expansion yielded a value, credit to env.
    raw = cfg.get(spec.config_key, None)
    value = _from_env_or_literal(raw)
    if value:
        # If raw looks like indirection, treat as env; otherwise as config
        source = "env" if isinstance(raw, str) and raw.strip().startswith("${ENV:") else "config"
        return value, source

    # 2) Explicit env override
    env_val = _get_env_override(spec.env_fallback)
    if env_val:
        return env_val, "env"

    # 3) Keyring
    use_keyring = bool(cfg.get("security.use_keyring", True)) and allow_keyring
    if use_keyring:
        user_key = spec.keyring_user_key or spec.config_key
        kr_val = _keyring_get(spec.keyring_service, user_key)
        if kr_val:
            return kr_val, "keyring"

    # 4) Optional prompt
    if prompt_if_missing and prompt is not None:
        user_key = spec.keyring_user_key or spec.config_key
        entered = prompt(f"Enter value for {spec.config_key}: ")
        if entered:
            if use_keyring:
                _keyring_set(spec.keyring_service, user_key, entered)
            return entered, "prompt"

    return None, "none"


def resolve_minimal_cloud_config(cfg: ConfigView) -> dict[str, str | bool | None]:
    """Return minimal cloud config values resolved (non-secret + placeholders for secrets).

    Keys:
        jira.cloud.auth.mode
        jira.cloud.base_url
        jira.cloud.cloud_id
    """
    # basic or oauth
    mode = cfg.get("jira.cloud.auth.mode", None)
    # https://your-domain.atlassian.net
    base_url = cfg.get("jira.cloud.base_url", None)
    cloud_id = cfg.get("jira.cloud.cloud_id", None)
    return {
        "jira.cloud.auth.mode": mode,
        "jira.cloud.base_url": base_url,
        "jira.cloud.cloud_id": cloud_id,
    }
