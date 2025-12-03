"""Credential manager for Jira Cloud authentication.

Responsibilities:
- Resolve Jira credentials (email and API token) using keyring → env → config
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
from ...errors import ConfigurationError
from .constants import AUTH_EMAIL_KEY, AUTH_TOKEN_EXPIRES_KEY, AUTH_TOKEN_INPUT_DATE_KEY, AUTH_TOKEN_KEY
from .secrets import KEYRING_SERVICE, SecretSpec, resolve_secret, resolve_secret_with_source, store_secret_in_keyring

EMAIL_KEY = AUTH_EMAIL_KEY
TOKEN_KEY = AUTH_TOKEN_KEY
TOKEN_EXPIRES_KEY = AUTH_TOKEN_EXPIRES_KEY  # ISO date YYYY-MM-DD
TOKEN_INPUT_DATE_KEY = AUTH_TOKEN_INPUT_DATE_KEY  # ISO date YYYY-MM-DD


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

    # First, try non-interactive resolution (config/env/keyring) and capture sources
    email_val, email_src = resolve_secret_with_source(
        cfg, email_spec, allow_keyring=True, prompt_if_missing=False, prompt=None
    )
    token_val, token_src = resolve_secret_with_source(
        cfg, token_spec, allow_keyring=True, prompt_if_missing=False, prompt=None
    )

    if email_val and token_val:
        status.update(
            {
                "found": True,
                "source": token_src or "none",
                "email": email_val,
                "api_token": token_val,
                "email_source": email_src or "none",
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
        email_src = "prompt" if email_val else email_src
    if prompter_token is not None:
        token_val = _resolve_with_prompt(cfg, token_spec, prompter=prompter_token)
        token_src = "prompt" if token_val else token_src

    if email_val and token_val:
        # Ask for optional expiration date only when we just collected a token interactively
        expires_on = _prompt_api_token_expiration(ui)
        input_date = datetime.now().date().isoformat()

        status.update(
            {
                "found": True,
                "source": token_src or "prompt",
                "email": email_val,
                "api_token": token_val,
                "email_source": email_src or "prompt",
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


def get_credential_status(ui, cfg: ConfigView) -> dict[str, Any]:  # pylint: disable=unused-argument
    """Get current credential status with source and metadata.

    Returns:
        {
            "email": {"value": str|None, "source": "config|env|keyring|none", "date": str|None},
            "api_token": {"value": str|None, "source": "config|env|keyring|none", "date": str|None},
            "expires_on": str|None,
            "input_date": str|None
        }
    """
    email_spec = SecretSpec(config_key=EMAIL_KEY, env_fallback="JIRA_EMAIL", keyring_service=KEYRING_SERVICE)
    token_spec = SecretSpec(config_key=TOKEN_KEY, env_fallback="JIRA_API_TOKEN", keyring_service=KEYRING_SERVICE)

    # Get values and sources
    email_val, email_src = resolve_secret_with_source(
        cfg, email_spec, allow_keyring=True, prompt_if_missing=False, prompt=None
    )
    token_val, token_src = resolve_secret_with_source(
        cfg, token_spec, allow_keyring=True, prompt_if_missing=False, prompt=None
    )

    # Get metadata from keyring when source is keyring
    email_date = None
    token_date = None
    expires_on = None
    input_date = None

    if email_src == "keyring":
        from .secrets import _keyring_get  # pylint: disable=import-outside-toplevel

        email_date = _keyring_get(KEYRING_SERVICE, f"{EMAIL_KEY}_created")

    if token_src == "keyring":
        from .secrets import _keyring_get  # pylint: disable=import-outside-toplevel

        token_date = _keyring_get(KEYRING_SERVICE, f"{TOKEN_KEY}_created")
        expires_on = _keyring_get(KEYRING_SERVICE, TOKEN_EXPIRES_KEY)
        input_date = _keyring_get(KEYRING_SERVICE, TOKEN_INPUT_DATE_KEY)

    return {
        "email": {"value": email_val, "source": email_src, "date": email_date},
        "api_token": {"value": token_val, "source": token_src, "date": token_date},
        "expires_on": expires_on,
        "input_date": input_date,
    }


def display_credential_status(ui, status: dict[str, Any]) -> None:
    """Display credentials with sources and dates (mask token)."""
    ui.say("Current Jira API credentials:")

    email_info = status.get("email", {})
    token_info = status.get("api_token", {})

    # Show email
    if email_info.get("value"):
        date_str = f" (stored {email_info['date']})" if email_info.get("date") else ""
        ui.say(f"  Email: {email_info['value']} [{email_info['source']}{date_str}]")
    else:
        ui.say("  Email: Not set")

    # Show token (masked)
    if token_info.get("value"):
        token_value = token_info["value"]
        TOKEN_MASK_LENGTH = 24
        if token_value and len(token_value) > TOKEN_MASK_LENGTH:
            masked = token_value[:TOKEN_MASK_LENGTH] + "..."
        else:
            masked = "***"
        date_str = f" (stored {token_info['date']})" if token_info.get("date") else ""
        ui.say(f"  API Token: {masked} [{token_info['source']}{date_str}]")

        # Show expiration if available
        if status.get("expires_on"):
            ui.hint(f"    Expires: {status['expires_on']}")
    else:
        ui.say("  API Token: Not set")


def setup_credentials_interactive(ui, cfg: ConfigView) -> dict[str, Any]:
    """Run interactive setup: prompt, optionally validate, store with metadata."""
    ui.say("Jira API Credential Setup")
    ui.say("=" * 40)

    # Show current status first
    current = get_credential_status(ui, cfg)
    display_credential_status(ui, current)
    ui.lf()

    # Prompt for credentials
    status = ensure_cloud_credentials(ui, cfg, auto_reply=None)
    if not status.get("found"):
        raise ConfigurationError(
            "Credentials were not provided.",
            details={"operation": "credential_setup", "status": status},
        )

    ui.success("Credentials stored in OS keychain (dh-jira-toolkit)")
    ui.hint("Use --credentials show to view, --credentials clear to remove")

    return status


def clear_credentials(ui) -> None:
    """Remove credentials from keyring and show env var unset instructions."""
    from .secrets import delete_secret_in_keyring

    delete_secret_in_keyring(KEYRING_SERVICE, EMAIL_KEY)
    delete_secret_in_keyring(KEYRING_SERVICE, TOKEN_KEY)
    delete_secret_in_keyring(KEYRING_SERVICE, TOKEN_EXPIRES_KEY)
    delete_secret_in_keyring(KEYRING_SERVICE, TOKEN_INPUT_DATE_KEY)
    delete_secret_in_keyring(KEYRING_SERVICE, f"{EMAIL_KEY}_created")
    delete_secret_in_keyring(KEYRING_SERVICE, f"{TOKEN_KEY}_created")

    ui.success("Cleared credentials from keychain (dh-jira-toolkit)")
    ui.lf()
    ui.hint("If you used environment variables, unset them:")
    ui.say("  Windows PowerShell:  Remove-Item Env:JIRA_EMAIL; Remove-Item Env:JIRA_API_TOKEN")
    ui.say("  Windows CMD:         set JIRA_EMAIL= & set JIRA_API_TOKEN=")
    ui.say("  macOS/Linux:         unset JIRA_EMAIL JIRA_API_TOKEN")
