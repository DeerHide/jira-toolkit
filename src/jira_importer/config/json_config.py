"""Description: This script loads and validates the configuration file for the Jira Importer.

Author:
    Julien (@tom4897)
"""

import json
import logging
from pathlib import Path
from typing import Any, TypeVar

from .. import CFG_REQ_DEFAULT, DEFAULT_CONFIG_FILENAME
from ..errors import ConfigurationError
from ..import_pipeline.cloud.constants import SENSITIVE_TERMS

T = TypeVar("T")

logger = logging.getLogger(__name__)


class JsonConfiguration:
    """JSON-based configuration class."""

    def __init__(self, path: str = DEFAULT_CONFIG_FILENAME, cfg_req: int = CFG_REQ_DEFAULT) -> None:
        """Initialize the JsonConfiguration class."""
        logger.debug(f"Loading configuration from {path}")
        if not Path(path).is_file():
            logger.error(f"The provided path '{path}' is not a valid file path.")
            raise ConfigurationError(
                f"Invalid file path: {path}",
                details={"file_path": path, "reason": "File does not exist"},
            )
        self.path = path
        self.content = self._load_config()
        self.cfg_req = cfg_req
        if self.version_check():
            logger.critical("Wrong file config version or missing version key.")
            # raise ConfigurationError("Wrong file config version or missing version key.")
        logger.debug(f"Configuration content: {self._redacted_content()}")

    def version_check(self) -> bool:
        """Check the version of the configuration file."""
        # Check for new structure first
        if "metadata" in self.content:
            cfg_version = self.content.get("metadata", {}).get("version")
        else:
            # Fallback to old structure
            logger.warning(
                "Using legacy configuration structure. Please migrate to 'metadata.version' and nested keys."
            )
            cfg_version = self.content.get("app.config.version")

        logger.debug(f"Config version: {cfg_version} ({self.cfg_req} needed)")
        if cfg_version is None:
            logger.error("Missing version in configuration.")
            return True
        if not isinstance(cfg_version, (int, str)):
            logger.error("Invalid version format in configuration.")
            return True
        try:
            return int(cfg_version) < self.cfg_req
        except (ValueError, TypeError):
            logger.error("Invalid version format in configuration.")
            return True

    def _load_config(self) -> dict:
        """Load the configuration file."""
        logger.debug(f"Reading configuration file: {self.path}")
        try:
            with Path(self.path).open("r", encoding="utf-8") as config_file:
                return json.load(config_file)
        except json.JSONDecodeError as e:
            message = f"The JSON file '{self.path}' is not correctly formatted. Error: {e}"
            logger.error(message)
            raise ConfigurationError(
                message,
                details={"file_path": self.path, "original_error": str(e), "error_type": type(e).__name__},
            ) from e
        except Exception as e:  # pylint: disable=broad-except
            message = f"Error reading configuration file '{self.path}': {e}"
            logger.error(message)
            raise ConfigurationError(
                message,
                details={"file_path": self.path, "original_error": str(e), "error_type": type(e).__name__},
            ) from e

    def get_value(self, key: str, default: T | None = None, expected_type: type[T] | None = None) -> T | None:
        """Get a value from the configuration file."""
        # Handle new nested structure
        if "metadata" in self.content:
            value: Any = self._get_nested_value(key)
        else:
            # Fallback to old flat structure
            value = self.content.get(key, default)

        if value is None:
            return default

        if expected_type is not None and not isinstance(value, expected_type):
            raise ConfigurationError(
                f"Config key '{key}' expected {expected_type.__name__}, got {type(value).__name__}",
                details={"key": key, "expected_type": expected_type.__name__, "actual_type": type(value).__name__},
            )

        return value  # type: ignore[return-value]

    def _get_nested_value(self, key: str) -> Any:
        """Get a nested value from the configuration file."""
        keys = key.split(".")
        current = self.content

        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None

        return current

    def _redacted_content(self) -> dict:
        """Return a redacted copy of the configuration for safe logging.

        Redacts common sensitive keys, including nested occurrences and case-insensitive matches.
        Uses centralized SENSITIVE_TERMS constant from cloud.constants.
        """
        # Convert tuple to set for efficient membership testing
        sensitive_terms_set = set(SENSITIVE_TERMS)

        def redact(obj: Any) -> Any:
            if isinstance(obj, dict):
                redacted: dict[str, Any] = {}
                for k, v in obj.items():
                    key_lower = str(k).lower()
                    if any(term in key_lower for term in sensitive_terms_set):
                        redacted[k] = "***"
                    else:
                        redacted[k] = redact(v)
                return redacted
            if isinstance(obj, list):
                return [redact(v) for v in obj]
            return obj

        return redact(self.content)

    def __repr__(self) -> str:
        """Return a string representation of the configuration."""
        try:
            version = self.get_value("metadata.version", default="unknown")
        except Exception:
            version = "unknown"
        return f"Configuration(path='{self.path}', version={version})"
