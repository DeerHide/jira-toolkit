"""Secrets resolution utilities for Jira Cloud integration.

Resolution order:
    1) OS keychain (keyring) if enabled
    2) Environment variable (supports literal value or ${ENV:VARNAME} indirection)
    3) Configuration file (with ${ENV:VARNAME} indirection)
    4) Optional interactive prompt (dev mode only), then store to keyring

All returned secrets must be redacted from logs/reports by callers using `redact_secret`.

Error Handling Strategy:
    - Keyring operations are best-effort: failures are logged but do not raise exceptions.
      This allows the application to continue even if keyring is unavailable.
    - Missing secrets return None (never empty strings). Empty strings are normalized to None.
    - Exceptions are only raised for truly exceptional cases, not for expected failures
      like keyring unavailability.
    - Callers are responsible for validating that secrets are not None before use.

author:
    Julien (@tom4897)
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module

from ...config.config_view import ConfigView

logger = logging.getLogger(__name__)

REDACTED = "****"
KEYRING_SERVICE = "dh-jira-toolkit"


def redact_secret(_: str | None) -> str:
    """Redact a secret value for safe logging/display.

    Args:
        _: Secret value to redact (ignored, always returns redacted string).

    Returns:
        Constant redaction string (REDACTED constant).
    """
    return REDACTED


def _normalize_secret_value(value: str | None) -> str | None:
    """Normalize secret value: treat empty strings as None.

    Args:
        value: Secret value to normalize.

    Returns:
        Normalized value (None if empty or whitespace-only string).
    """
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        return stripped
    return value


def _from_env_or_literal(value: str | None) -> str | None:
    """Resolve a config value possibly using ${ENV:VARNAME} indirection.

    Args:
        value: Config value that may be a literal string or ${ENV:VARNAME} indirection.

    Returns:
        Resolved value from environment variable if indirection, or literal value.
        Returns None if value is None or if environment variable is not set.

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
    """Get value from environment variable.

    Args:
        env_var: Environment variable name, or None.

    Returns:
        Environment variable value if set, None otherwise.
    """
    if not env_var:
        return None
    return os.environ.get(env_var)


def _keyring_get(service: str, username: str) -> str | None:
    """Get a secret from the OS keyring.

    Args:
        service: Keyring service name.
        username: Keyring username/key.

    Returns:
        Secret value or None if not found or keyring unavailable.
    """
    try:
        kr = import_module("keyring")  # type: ignore
    except ImportError:
        # Keyring module not available - expected in some environments
        logger.debug("Keyring module not available (service=%s, username=%s)", service, username)
        return None
    except Exception as e:
        # Unexpected error importing keyring
        logger.warning("Failed to import keyring module: %s (service=%s, username=%s)", e, service, username)
        return None
    try:
        return kr.get_password(service, username)  # type: ignore[attr-defined]
    except Exception as e:
        # Unexpected error accessing keyring
        logger.warning("Keyring get_password failed: %s (service=%s, username=%s)", e, service, username)
        return None


def _keyring_set(service: str, username: str, secret: str) -> None:
    """Set a secret in the OS keyring (best-effort).

    Args:
        service: Keyring service name.
        username: Keyring username/key.
        secret: Secret value to store.
    """
    try:
        kr = import_module("keyring")  # type: ignore
    except ImportError:
        # Keyring module not available - expected in some environments
        logger.debug("Keyring module not available (service=%s, username=%s)", service, username)
        return
    except Exception as e:
        # Unexpected error importing keyring
        logger.warning("Failed to import keyring module: %s (service=%s, username=%s)", e, service, username)
        return
    try:
        kr.set_password(service, username, secret)  # type: ignore[attr-defined]
    except Exception as e:
        # Unexpected error accessing keyring
        logger.warning("Keyring set_password failed: %s (service=%s, username=%s)", e, service, username)


def store_secret_in_keyring(service: str, username: str, secret: str) -> None:
    """Public helper to persist secrets in the OS keychain (best-effort).

    This is a best-effort operation. If keyring is unavailable, the operation
    will fail silently (logged at DEBUG level).

    Args:
        service: Keyring service name (e.g., "dh-jira-toolkit").
        username: Keyring username/key identifier.
        secret: Secret value to store.
    """
    _keyring_set(service, username, secret)


def _keyring_delete(service: str, username: str) -> None:
    """Delete a secret from the OS keyring (best-effort).

    Args:
        service: Keyring service name.
        username: Keyring username/key.
    """
    try:
        kr = import_module("keyring")  # type: ignore
    except ImportError:
        # Keyring module not available - expected in some environments
        logger.debug("Keyring module not available (service=%s, username=%s)", service, username)
        return
    except Exception as e:
        # Unexpected error importing keyring
        logger.warning("Failed to import keyring module: %s (service=%s, username=%s)", e, service, username)
        return
    try:
        kr.delete_password(service, username)  # type: ignore[attr-defined]
    except Exception as e:
        # Unexpected error accessing keyring
        logger.warning("Keyring delete_password failed: %s (service=%s, username=%s)", e, service, username)


def delete_secret_in_keyring(service: str, username: str) -> None:
    """Public helper to delete a secret from the OS keychain (best-effort).

    This is a best-effort operation. If keyring is unavailable, the operation
    will fail silently (logged at DEBUG level).

    Args:
        service: Keyring service name (e.g., "dh-jira-toolkit").
        username: Keyring username/key identifier.
    """
    _keyring_delete(service, username)


@dataclass
class SecretSpec:
    """Descriptor for a secret to resolve."""

    config_key: str  # e.g., "jira.cloud.auth.api_token"
    env_fallback: str | None = None  # e.g., "JIRA_API_TOKEN"
    keyring_service: str = KEYRING_SERVICE
    keyring_user_key: str | None = None  # defaults to config_key if None


def _resolve_secret_impl(
    cfg: ConfigView,
    spec: SecretSpec,
    *,
    allow_keyring: bool = True,
    prompt_if_missing: bool = False,
    prompt: Callable[[str], str] | None = None,
) -> tuple[str | None, str]:
    """Internal implementation of secret resolution that returns (value, source).

    This is the shared implementation used by both resolve_secret() and
    resolve_secret_with_source() to avoid code duplication.

    Args:
        cfg: Configuration view.
        spec: Secret specification.
        allow_keyring: Whether to allow keyring access.
        prompt_if_missing: Whether to prompt if secret is missing.
        prompt: Optional prompt function.

    Returns:
        Tuple of (secret value, source) where source is one of:
        "keyring", "env", "config", "prompt", or "none".
    """
    # 1) Keyring if enabled in config and globally allowed
    use_keyring = bool(cfg.get("security.use_keyring", True)) and allow_keyring
    if use_keyring:
        user_key = spec.keyring_user_key or spec.config_key
        kr_val = _keyring_get(spec.keyring_service, user_key)
        kr_val = _normalize_secret_value(kr_val)
        if kr_val:
            return kr_val, "keyring"

    # 2) Explicit env override
    env_val = _get_env_override(spec.env_fallback)
    env_val = _normalize_secret_value(env_val)
    if env_val:
        return env_val, "env"

    # 3) Read from config; apply ${ENV:VAR}
    raw = cfg.get(spec.config_key, None)
    value = _from_env_or_literal(raw)
    value = _normalize_secret_value(value)
    if value:
        # If raw looks like indirection, treat as env; otherwise as config
        source = "env" if isinstance(raw, str) and raw.strip().startswith("${ENV:") else "config"
        return value, source

    # 4) Optional prompt (dev mode only) then store to keyring
    if prompt_if_missing and prompt is not None:
        user_key = spec.keyring_user_key or spec.config_key
        entered_raw = prompt(f"Enter value for {spec.config_key}: ")
        entered = _normalize_secret_value(entered_raw)
        if entered:
            if use_keyring:
                _keyring_set(spec.keyring_service, user_key, entered)
            return entered, "prompt"

    return None, "none"


def resolve_secret(
    cfg: ConfigView,
    spec: SecretSpec,
    *,
    allow_keyring: bool = True,
    prompt_if_missing: bool = False,
    prompt: Callable[[str], str] | None = None,
) -> str | None:
    """Resolve a secret using keyring -> env -> config -> optional prompt.

    - First checks keyring if enabled.
    - Then checks explicit env fallback (spec.env_fallback).
    - Then reads the config value and applies ${ENV:VAR} indirection if present.
    - If missing and prompting is enabled with a prompt function, asks the user and stores in keyring.

    Empty strings and whitespace-only strings are treated as missing secrets and return None.

    Returns:
        Secret value as string, or None if not found or empty.
    """
    value, _ = _resolve_secret_impl(
        cfg, spec, allow_keyring=allow_keyring, prompt_if_missing=prompt_if_missing, prompt=prompt
    )
    return value


def resolve_secret_with_source(
    cfg: ConfigView,
    spec: SecretSpec,
    *,
    allow_keyring: bool = True,
    prompt_if_missing: bool = False,
    prompt: Callable[[str], str] | None = None,
) -> tuple[str | None, str]:
    """Resolve a secret and return a tuple of (value, source).

    Args:
        cfg: Configuration view.
        spec: Secret specification.
        allow_keyring: Whether to allow keyring access.
        prompt_if_missing: Whether to prompt if secret is missing.
        prompt: Optional prompt function.

    Returns:
        Tuple of (secret value, source) where source is one of:
        "keyring", "env", "config", "prompt", or "none" when not found.

    Empty strings and whitespace-only strings are treated as missing secrets.
    """
    return _resolve_secret_impl(
        cfg, spec, allow_keyring=allow_keyring, prompt_if_missing=prompt_if_missing, prompt=prompt
    )


def resolve_minimal_cloud_config(cfg: ConfigView) -> dict[str, str | bool | None]:
    """Return minimal cloud config values resolved (non-secret + placeholders for secrets).

    This function extracts non-sensitive configuration values needed for cloud operations.
    Secret values are not included and should be resolved separately using resolve_secret().

    Args:
        cfg: Configuration view to read from.

    Returns:
        Dictionary with keys:
        - jira.cloud.auth.mode: Authentication mode (e.g., "basic", "oauth")
        - jira.cloud.base_url: Base URL of Jira instance
        - jira.cloud.cloud_id: Cloud ID if available

        Values may be None if not configured.
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
