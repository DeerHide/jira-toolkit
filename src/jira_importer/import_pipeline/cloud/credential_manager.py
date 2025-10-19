"""Credential manager for Jira Cloud authentication.

Responsibilities:
- Resolve Jira credentials (email and API token) using config → env → keyring
- Optionally prompt the user (when interactive) to input missing values
- Best-effort persistence to the OS keychain

This module is designed to be used early (preflight) and also from sinks as a
secondary safety net. It never logs or returns the API token in logs/UI.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from ...config.config_view import ConfigView
from .secrets import KEYRING_SERVICE, SecretSpec, resolve_secret, store_secret_in_keyring

EMAIL_KEY = "jira.connection.auth.email"
TOKEN_KEY = "jira.connection.auth.api_token"
TOKEN_EXPIRES_KEY = "jira.connection.auth.api_token_expires_on"  # ISO date YYYY-MM-DD
TOKEN_INPUT_DATE_KEY = "jira.connection.auth.api_token_input_date"  # ISO date YYYY-MM-DD


def _prompt_with_ui(ui, prompt_text: str, *, required: bool = True, hint: str | None = None) -> str:
    """Prompt using the provided UI, with minimal dependencies.

    Falls back to empty string when not interactive; caller decides how to handle.
    """
    if ui and hasattr(ui, "prompt_text"):
        return ui.prompt_text(prompt_text, required=required, hint=hint)  # type: ignore[no-any-return]
    # No UI available
    return ""


def _prompt_email(ui) -> str:
    return _prompt_with_ui(ui, "Enter your Jira account email", required=True, hint="example@company.com").strip()


def _prompt_api_token(ui) -> str:
    # Shown in plain text to ease copy/paste as requested by the user
    return _prompt_with_ui(
        ui,
        "Enter your Jira API token",
        required=True,
        hint="Create at id.atlassian.com/manage-profile/security/api-tokens",
    ).strip()


def _prompt_api_token_expiration(ui) -> str:
    """Prompt for API token expiration date (optional). Returns ISO date or empty string.

    Accepts formats like YYYY-MM-DD. Empty input means unknown/no expiration captured.
    """
    value = _prompt_with_ui(
        ui,
        "Enter API token expiration date (YYYY-MM-DD) [optional]",
        required=False,
        hint="Leave empty if no expiration or unknown",
    ).strip()
    if not value:
        return ""
    # basic validation for YYYY-MM-DD
    try:
        dt = datetime.strptime(value, "%Y-%m-%d").date()
        return dt.isoformat()
    except Exception:
        # If invalid, do not block; return empty to avoid storing bad value
        return ""


def _resolve_with_prompt(
    cfg: ConfigView,
    spec: SecretSpec,
    *,
    prompter: Callable[[], str] | None,
) -> str | None:
    # Use resolve_secret's prompt hook to both prompt and store to keyring when available
    def _prompt_adapter(_: str) -> str:
        return prompter() if prompter else ""

    return resolve_secret(
        cfg,
        spec,
        allow_keyring=True,
        prompt_if_missing=prompter is not None,
        prompt=_prompt_adapter if prompter is not None else None,
    )


def ensure_cloud_credentials(ui, cfg: ConfigView, auto_reply: bool | None) -> dict[str, Any]:
    """Ensure Jira Cloud credentials are available.

    Returns a status dict:
        { "found": bool, "source": "config|env|keyring|prompt|none", "email": str | None, "api_token": str | None }

    Notes:
      - Does not log or print the token.
      - If credentials are missing and auto_reply is True (-y), returns found=False (no prompt).
      - If interactive (auto_reply is None), prompts for both values and attempts to store in keyring.
    """
    status: dict[str, Any] = {
        "found": False,
        "source": "none",
        "email": None,
        "api_token": None,
        "api_token_expires_on": None,
        "api_token_input_date": None,
    }

    email_spec = SecretSpec(config_key=EMAIL_KEY, env_fallback="JIRA_EMAIL", keyring_service=KEYRING_SERVICE)
    token_spec = SecretSpec(config_key=TOKEN_KEY, env_fallback="JIRA_API_TOKEN", keyring_service=KEYRING_SERVICE)

    # First, try non-interactive resolution (config/env/keyring)
    email_val = resolve_secret(cfg, email_spec, allow_keyring=True, prompt_if_missing=False, prompt=None)
    token_val = resolve_secret(cfg, token_spec, allow_keyring=True, prompt_if_missing=False, prompt=None)

    if email_val and token_val:
        status.update(
            {
                "found": True,
                "source": "config|env|keyring",
                "email": email_val,
                "api_token": token_val,
            }
        )
        return status

    # If auto-yes is set or explicitly non-interactive, do not prompt
    if auto_reply is True:
        return status

    # Interactive: prompt for any missing values
    prompter_email = None if email_val else (lambda: _prompt_email(ui))
    prompter_token = None if token_val else (lambda: _prompt_api_token(ui))

    if prompter_email is not None:
        email_val = _resolve_with_prompt(cfg, email_spec, prompter=prompter_email)
    if prompter_token is not None:
        token_val = _resolve_with_prompt(cfg, token_spec, prompter=prompter_token)

    if email_val and token_val:
        # Ask for optional expiration date only when we just collected a token interactively
        expires_on = _prompt_api_token_expiration(ui)
        input_date = datetime.now().date().isoformat()

        status.update(
            {
                "found": True,
                "source": "prompt",
                "email": email_val,
                "api_token": token_val,
                "api_token_expires_on": expires_on or None,
                "api_token_input_date": input_date,
            }
        )

        # Best-effort: ensure stored in keyring (resolve_secret already attempted when keyring enabled)
        try:
            store_secret_in_keyring(KEYRING_SERVICE, EMAIL_KEY, email_val)
            store_secret_in_keyring(KEYRING_SERVICE, TOKEN_KEY, token_val)
            if expires_on:
                store_secret_in_keyring(KEYRING_SERVICE, TOKEN_EXPIRES_KEY, expires_on)
            store_secret_in_keyring(KEYRING_SERVICE, TOKEN_INPUT_DATE_KEY, input_date)
        except Exception:
            # Best-effort only; no hard failure
            pass
        return status

    # Still missing after prompt or non-interactive
    return status
