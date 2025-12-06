"""Credential manager for Jira Cloud authentication.

Responsibilities:
- Resolve Jira credentials (email and API token) using keyring → env → config
- Optionally prompt the user (when interactive) to input missing values
- Best-effort persistence to the OS keychain
- Test and validate Jira connection and authentication

This module is designed to be used early (preflight) and also from sinks as a
secondary safety net. It never logs or returns the API token in logs/UI.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from ...config.config_view import ConfigView
from ...errors import ConfigurationError, JiraApiError, JiraAuthError, NetworkError
from .client import JiraCloudClient
from .constants import (
    AUTH_EMAIL_KEY,
    AUTH_TOKEN_EXPIRES_KEY,
    AUTH_TOKEN_INPUT_DATE_KEY,
    AUTH_TOKEN_KEY,
    HTTP_FORBIDDEN,
    HTTP_NOT_FOUND,
    HTTP_OK,
    HTTP_SERVER_ERROR_MAX,
    HTTP_SERVER_ERROR_MIN,
    HTTP_TOO_MANY_REQUESTS,
    HTTP_UNAUTHORIZED,
)
from .secrets import KEYRING_SERVICE, SecretSpec, resolve_secret, resolve_secret_with_source, store_secret_in_keyring

logger = logging.getLogger(__name__)

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
    """Resolve a secret with optional prompting.

    Uses resolve_secret's prompt hook to both prompt and store to keyring when available.

    Args:
        cfg: Configuration view.
        spec: Secret specification.
        prompter: Optional function that prompts for the secret value.

    Returns:
        Secret value if found or entered, None otherwise.
    """

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
      - When auto_reply is True (e.g. --auto-yes / non-interactive mode), this function will never prompt
        and simply reports whether credentials are already available.
      - When auto_reply is False, callers can use this to model a 'always no' policy for prompts.
      - When auto_reply is None, the function may prompt interactively via the provided UI and attempt
        to persist values in the OS keyring when available.
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
        TOKEN_MASK_LENGTH = 12
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


def _test_credentials_cli(ui, cfg_view: ConfigView) -> int:
    """Test stored credentials by making an API call to Jira.

    This function sets up the client and uses test_credentials() to verify
    the connection. It handles all the necessary setup (credential resolution,
    URL validation, client creation) before calling test_credentials().

    Args:
        cfg_view: Configuration view.
        ui: Console UI instance.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    from urllib.parse import urlparse  # pylint: disable=import-outside-toplevel

    from ...errors import ConfigurationError, format_error_for_display  # pylint: disable=import-outside-toplevel
    from .auth import BasicAuthProvider  # pylint: disable=import-outside-toplevel

    ui.say("Testing Jira API credentials...")
    ui.lf()

    # Get credentials
    status = ensure_cloud_credentials(ui, cfg_view, auto_reply=None)
    if not status.get("found"):
        ui.error("Credentials not found. Use '--credentials run' to set them up.")
        return 1

    email = status.get("email")
    api_token = status.get("api_token")
    source = status.get("source", "unknown")

    if not email or not api_token:
        ui.error("Credentials are incomplete. Use '--credentials run' to set them up.")
        return 1

    # Get and validate base URL from config
    base_url = cfg_view.get("jira.connection.site_address", None)
    if not base_url:
        ui.error("Missing jira.connection.site_address in configuration.")
        ui.hint("Set it in your JSON/Excel config file.")
        return 1

    # Validate URL format (same validation as _validate_config in cloud_sink.py)
    parsed = urlparse(str(base_url))
    if not parsed.scheme or not parsed.netloc:
        ui.error(f"Invalid jira.connection.site_address: {base_url}")
        ui.hint("Expected an HTTPS URL like 'https://your-domain.atlassian.net'.")
        return 1

    if parsed.scheme.lower() != "https":
        ui.error(f"Insecure URL scheme: {parsed.scheme}")
        ui.hint("Only HTTPS URLs are supported.")
        return 1

    # Normalize base URL
    normalized_base = str(base_url).rstrip("/")
    api_base_url = f"{normalized_base}/rest/api/3"

    # Create auth provider and client (required for test_credentials)
    auth_provider = BasicAuthProvider(email=email, api_token=api_token)
    client = JiraCloudClient(base_url=api_base_url, auth_provider=auth_provider)

    # Build auth context for error messages
    auth_context = {
        "email": email,
        "secret_source": source,
    }

    # Use test_credentials() to verify the connection
    try:
        test_credentials(client, normalized_base, auth_context)
        ui.lf()
        ui.success("Credentials are valid and connection successful")
        ui.say(f"  Email: {email}")
        ui.say(f"  Source: {source}")
        ui.say(f"  Base URL: {normalized_base}")
        return 0
    except (JiraAuthError, JiraApiError, NetworkError, ConfigurationError) as test_exc:
        ui.error(format_error_for_display(test_exc))
        return 1
    except Exception as test_exc:  # pylint: disable=broad-except
        ui.error(f"Unexpected error during credential test: {test_exc}")
        logger.exception("Credential test failed with unexpected error")
        return 1


def test_credentials(client: JiraCloudClient, base_url: str, auth_context: dict[str, str] | None = None) -> None:
    """Test Jira credentials and connection with a pre-flight API call.

    This pre-flight test provides clear error messages for common auth issues
    before attempting to create issues or perform other operations.

    Args:
        client: Jira Cloud API client.
        base_url: Base URL of the Jira instance.
        auth_context: Optional authentication context dictionary with email and secret_source.
            If not provided, context information will be omitted from error messages.

    Raises:
        JiraAuthError: For authentication errors (401, 403).
        JiraApiError: For API errors (404, 429, 5xx, or other status codes).
        NetworkError: For network/connection issues.
    """
    try:
        logger.info("Testing Jira authentication...")
        test_response = client.get("/myself")

        if test_response.status_code == HTTP_OK:
            try:
                user_info = test_response.json()
                logger.info(f"Authentication successful - connected as: {user_info.get('displayName', 'Unknown')}")
            except (ValueError, KeyError) as json_error:
                logger.warning(f"Authentication successful but received malformed response: {json_error}")
                logger.info("Authentication successful - proceeding with import")
            return

        # Handle specific error status codes
        email_display = "unknown"
        source_display = "unknown"
        context_suffix = ""
        if auth_context:
            email_display = auth_context.get("email") or "unknown"
            source_display = auth_context.get("secret_source") or "unknown"
            context_suffix = f" (email: {email_display}, secret source: {source_display})"

        if test_response.status_code == HTTP_UNAUTHORIZED:
            raise JiraAuthError(
                "Jira authentication failed (HTTP 401) - your API token may have expired. "
                "Use 'jira-importer --credentials show' to inspect current values, or '... --credentials' to update. "
                f"Refresh your token at: https://id.atlassian.com/manage-profile/security/api-tokens{context_suffix}",
                status_code=HTTP_UNAUTHORIZED,
                details={"email": email_display, "secret_source": source_display},
            )
        elif test_response.status_code == HTTP_FORBIDDEN:
            raise JiraAuthError(
                "Jira authentication failed (HTTP 403) - your API token may be invalid or you lack permissions. "
                "Use 'jira-importer --credentials show' to inspect current values, or '... --credentials' to update. "
                f"Check/rotate your token at: https://id.atlassian.com/manage-profile/security/api-tokens{context_suffix}",
                status_code=HTTP_FORBIDDEN,
                details={"email": email_display, "secret_source": source_display},
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
        elif HTTP_SERVER_ERROR_MIN <= test_response.status_code <= HTTP_SERVER_ERROR_MAX:
            raise JiraApiError(
                f"Jira server error (HTTP {test_response.status_code}). Please try again later or contact your Jira administrator.",
                status_code=test_response.status_code,
            )
        else:
            raise JiraApiError(
                f"Authentication test failed with status {test_response.status_code}{context_suffix}",
                status_code=test_response.status_code,
                details={"email": email_display, "secret_source": source_display},
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


def run_credentials_cli(config: Any, action: str, ui) -> int:
    """CLI entry point for credentials command.

    Handles command routing and exit codes.
    This is the CLI orchestration layer for credentials.

    Args:
        config: Application configuration (or minimal config fallback).
        action: Credential action ("run"|"show"|"clear"|"test").
        ui: Console UI instance.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    from ...errors import format_error_for_display  # pylint: disable=import-outside-toplevel

    cfg_view = ConfigView(config)

    ui.lf()

    # Route to domain functions
    if action == "show":
        status = get_credential_status(ui, cfg_view)
        display_credential_status(ui, status)
        return 0

    if action == "clear":
        clear_credentials(ui)
        return 0

    if action == "test":
        return _test_credentials_cli(ui, cfg_view)

    # default: run
    try:
        st = setup_credentials_interactive(ui, cfg_view)
        ui.lf()
        ui.success("Credentials configured successfully")
        return 0
    except ConfigurationError as cred_exc:
        ui.error(format_error_for_display(cred_exc))
        return 1
    except Exception as cred_exc:  # pylint: disable=broad-except
        # Unexpected internal error during credential setup
        ui.error(f"Credential setup failed: {cred_exc}")
        return 1
