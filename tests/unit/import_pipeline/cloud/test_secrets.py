"""Unit tests for secrets management module."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from jira_importer.config.config_view import ConfigView
from jira_importer.import_pipeline.cloud.secrets import (
    KEYRING_SERVICE,
    REDACTED,
    SecretSpec,
    _from_env_or_literal,
    _get_env_override,
    _normalize_secret_value,
    delete_secret_in_keyring,
    redact_secret,
    resolve_secret,
    resolve_secret_with_source,
    store_secret_in_keyring,
)


class TestRedactSecret:
    """Tests for redact_secret function."""

    def test_redact_secret_with_value(self) -> None:
        """Test redact_secret returns constant redaction string."""
        assert redact_secret("secret123") == REDACTED
        assert redact_secret("any-value") == REDACTED

    def test_redact_secret_with_none(self) -> None:
        """Test redact_secret with None input."""
        assert redact_secret(None) == REDACTED

    def test_redact_secret_with_empty_string(self) -> None:
        """Test redact_secret with empty string."""
        assert redact_secret("") == REDACTED


class TestNormalizeSecretValue:
    """Tests for _normalize_secret_value function."""

    def test_normalize_none(self) -> None:
        """Test normalizing None returns None."""
        assert _normalize_secret_value(None) is None

    def test_normalize_empty_string(self) -> None:
        """Test normalizing empty string returns None."""
        assert _normalize_secret_value("") is None

    def test_normalize_whitespace_only(self) -> None:
        """Test normalizing whitespace-only string returns None."""
        assert _normalize_secret_value("   ") is None
        assert _normalize_secret_value("\t\n") is None

    def test_normalize_valid_string(self) -> None:
        """Test normalizing valid string returns stripped value."""
        assert _normalize_secret_value("  secret123  ") == "secret123"
        assert _normalize_secret_value("token") == "token"


class TestFromEnvOrLiteral:
    """Tests for _from_env_or_literal function."""

    def test_from_env_or_literal_none(self) -> None:
        """Test with None input."""
        assert _from_env_or_literal(None) is None

    def test_from_env_or_literal_literal_value(self) -> None:
        """Test with literal value."""
        assert _from_env_or_literal("plain-value") == "plain-value"
        assert _from_env_or_literal("  token  ") == "token"

    def test_from_env_or_literal_env_indirection(self) -> None:
        """Test with ${ENV:VARNAME} indirection."""
        with patch.dict(os.environ, {"TEST_VAR": "env-value"}):
            assert _from_env_or_literal("${ENV:TEST_VAR}") == "env-value"

    def test_from_env_or_literal_env_not_set(self) -> None:
        """Test with ${ENV:VARNAME} when env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            assert _from_env_or_literal("${ENV:NONEXISTENT}") is None

    def test_from_env_or_literal_invalid_format(self) -> None:
        """Test with invalid ${ENV:} format."""
        assert _from_env_or_literal("${ENV:INCOMPLETE") == "${ENV:INCOMPLETE"
        assert _from_env_or_literal("ENV:VAR") == "ENV:VAR"


class TestGetEnvOverride:
    """Tests for _get_env_override function."""

    def test_get_env_override_none(self) -> None:
        """Test with None input."""
        assert _get_env_override(None) is None

    def test_get_env_override_empty_string(self) -> None:
        """Test with empty string."""
        assert _get_env_override("") is None

    def test_get_env_override_set(self) -> None:
        """Test with environment variable set."""
        with patch.dict(os.environ, {"TEST_VAR": "test-value"}):
            assert _get_env_override("TEST_VAR") == "test-value"

    def test_get_env_override_not_set(self) -> None:
        """Test with environment variable not set."""
        with patch.dict(os.environ, {}, clear=True):
            assert _get_env_override("NONEXISTENT") is None


class TestResolveSecret:
    """Tests for resolve_secret function."""

    def test_resolve_secret_from_keyring(self) -> None:
        """Test resolving secret from keyring."""
        mock_keyring = MagicMock()
        mock_keyring.get_password.return_value = "keyring-secret"

        cfg = ConfigView({})
        spec = SecretSpec(config_key="test.key", keyring_service=KEYRING_SERVICE)

        with patch("jira_importer.import_pipeline.cloud.secrets.import_module", return_value=mock_keyring):
            result = resolve_secret(cfg, spec, allow_keyring=True)
            assert result == "keyring-secret"

    def test_resolve_secret_from_env(self) -> None:
        """Test resolving secret from environment variable."""
        cfg = ConfigView({})
        spec = SecretSpec(config_key="test.key", env_fallback="TEST_SECRET")

        with patch.dict(os.environ, {"TEST_SECRET": "env-secret"}):
            result = resolve_secret(cfg, spec, allow_keyring=False)
            assert result == "env-secret"

    def test_resolve_secret_from_config(self) -> None:
        """Test resolving secret from config."""
        cfg = ConfigView({"test": {"key": "config-secret"}})
        spec = SecretSpec(config_key="test.key")

        result = resolve_secret(cfg, spec, allow_keyring=False)
        assert result == "config-secret"

    def test_resolve_secret_from_config_env_indirection(self) -> None:
        """Test resolving secret from config with ${ENV:} indirection."""
        cfg = ConfigView({"test": {"key": "${ENV:TEST_SECRET}"}})
        spec = SecretSpec(config_key="test.key")

        with patch.dict(os.environ, {"TEST_SECRET": "indirect-secret"}):
            result = resolve_secret(cfg, spec, allow_keyring=False)
            assert result == "indirect-secret"

    def test_resolve_secret_empty_string_treated_as_none(self) -> None:
        """Test that empty strings are treated as missing."""
        cfg = ConfigView({"test": {"key": ""}})
        spec = SecretSpec(config_key="test.key")

        result = resolve_secret(cfg, spec, allow_keyring=False)
        assert result is None

    def test_resolve_secret_not_found(self) -> None:
        """Test resolving secret when not found."""
        cfg = ConfigView({})
        spec = SecretSpec(config_key="test.key")

        result = resolve_secret(cfg, spec, allow_keyring=False)
        assert result is None

    def test_resolve_secret_keyring_unavailable(self) -> None:
        """Test resolving secret when keyring is unavailable."""
        cfg = ConfigView({})
        spec = SecretSpec(config_key="test.key")

        with patch("jira_importer.import_pipeline.cloud.secrets.import_module", side_effect=ImportError()):
            result = resolve_secret(cfg, spec, allow_keyring=True)
            # Should fall back to other sources or return None
            assert result is None


class TestResolveSecretWithSource:
    """Tests for resolve_secret_with_source function."""

    def test_resolve_secret_with_source_keyring(self) -> None:
        """Test resolving secret from keyring with source tracking."""
        mock_keyring = MagicMock()
        mock_keyring.get_password.return_value = "keyring-secret"

        cfg = ConfigView({})
        spec = SecretSpec(config_key="test.key", keyring_service=KEYRING_SERVICE)

        with patch("jira_importer.import_pipeline.cloud.secrets.import_module", return_value=mock_keyring):
            value, source = resolve_secret_with_source(cfg, spec, allow_keyring=True)
            assert value == "keyring-secret"
            assert source == "keyring"

    def test_resolve_secret_with_source_env(self) -> None:
        """Test resolving secret from env with source tracking."""
        cfg = ConfigView({})
        spec = SecretSpec(config_key="test.key", env_fallback="TEST_SECRET")

        with patch.dict(os.environ, {"TEST_SECRET": "env-secret"}):
            value, source = resolve_secret_with_source(cfg, spec, allow_keyring=False)
            assert value == "env-secret"
            assert source == "env"

    def test_resolve_secret_with_source_config(self) -> None:
        """Test resolving secret from config with source tracking."""
        cfg = ConfigView({"test": {"key": "config-secret"}})
        spec = SecretSpec(config_key="test.key")

        value, source = resolve_secret_with_source(cfg, spec, allow_keyring=False)
        assert value == "config-secret"
        assert source == "config"

    def test_resolve_secret_with_source_config_env_indirection(self) -> None:
        """Test resolving secret from config with ${ENV:} indirection."""
        cfg = ConfigView({"test": {"key": "${ENV:TEST_SECRET}"}})
        spec = SecretSpec(config_key="test.key")

        with patch.dict(os.environ, {"TEST_SECRET": "indirect-secret"}):
            value, source = resolve_secret_with_source(cfg, spec, allow_keyring=False)
            assert value == "indirect-secret"
            assert source == "env"  # Source is "env" when using ${ENV:} indirection

    def test_resolve_secret_with_source_not_found(self) -> None:
        """Test resolving secret when not found."""
        cfg = ConfigView({})
        spec = SecretSpec(config_key="test.key")

        value, source = resolve_secret_with_source(cfg, spec, allow_keyring=False)
        assert value is None
        assert source == "none"


class TestKeyringOperations:
    """Tests for keyring operations."""

    def test_store_secret_in_keyring_success(self) -> None:
        """Test storing secret in keyring successfully."""
        mock_keyring = MagicMock()
        mock_keyring.set_password = MagicMock()

        with patch("jira_importer.import_pipeline.cloud.secrets.import_module", return_value=mock_keyring):
            store_secret_in_keyring(KEYRING_SERVICE, "test-key", "test-secret")
            mock_keyring.set_password.assert_called_once_with(KEYRING_SERVICE, "test-key", "test-secret")

    def test_store_secret_in_keyring_unavailable(self) -> None:
        """Test storing secret when keyring is unavailable."""
        with patch("jira_importer.import_pipeline.cloud.secrets.import_module", side_effect=ImportError()):
            # Should not raise exception
            store_secret_in_keyring(KEYRING_SERVICE, "test-key", "test-secret")

    def test_delete_secret_in_keyring_success(self) -> None:
        """Test deleting secret from keyring successfully."""
        mock_keyring = MagicMock()
        mock_keyring.delete_password = MagicMock()

        with patch("jira_importer.import_pipeline.cloud.secrets.import_module", return_value=mock_keyring):
            delete_secret_in_keyring(KEYRING_SERVICE, "test-key")
            mock_keyring.delete_password.assert_called_once_with(KEYRING_SERVICE, "test-key")

    def test_delete_secret_in_keyring_unavailable(self) -> None:
        """Test deleting secret when keyring is unavailable."""
        with patch("jira_importer.import_pipeline.cloud.secrets.import_module", side_effect=ImportError()):
            # Should not raise exception
            delete_secret_in_keyring(KEYRING_SERVICE, "test-key")


class TestSecretSpec:
    """Tests for SecretSpec dataclass."""

    def test_secret_spec_defaults(self) -> None:
        """Test SecretSpec with default values."""
        spec = SecretSpec(config_key="test.key")
        assert spec.config_key == "test.key"
        assert spec.env_fallback is None
        assert spec.keyring_service == KEYRING_SERVICE
        assert spec.keyring_user_key is None

    def test_secret_spec_custom_values(self) -> None:
        """Test SecretSpec with custom values."""
        spec = SecretSpec(
            config_key="test.key",
            env_fallback="TEST_ENV",
            keyring_service="custom-service",
            keyring_user_key="custom-key",
        )
        assert spec.config_key == "test.key"
        assert spec.env_fallback == "TEST_ENV"
        assert spec.keyring_service == "custom-service"
        assert spec.keyring_user_key == "custom-key"
