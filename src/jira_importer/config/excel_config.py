"""Description: This script manages the excel config.

Author:
    Julien (@tom4897)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, TypeVar

from .. import CFG_REQ_DEFAULT
from ..excel.excel_io import ExcelWorkbookManager
from ..excel.excel_table_reader import ExcelTableReader
from .config_models import ExcelTableConfig

T = TypeVar("T")
logger = logging.getLogger(__name__)


class ExcelConfigurationError(Exception):
    """Raised when the Excel configuration file is invalid or cannot be read."""


class ExcelConfiguration:
    """Configuration class for Excel-based configuration.

    Provides the same interface as the JSON Configuration class but reads
    from Excel files. Supports nested keys using dot notation.
    """

    def __init__(self, excel_path: str, config_sheet: str = "Config", cfg_req: int = CFG_REQ_DEFAULT) -> None:
        """Initialize the ExcelConfiguration class.

        Args:
            excel_path: Path to the Excel file containing configuration
            config_sheet: Name of the sheet containing configuration (default: "Config")
            cfg_req: Required configuration version (default: CFG_REQ_DEFAULT)
        """
        logger.debug(f"Loading Excel configuration from {excel_path}")
        if not Path(excel_path).is_file():
            logger.error(f"The provided path '{excel_path}' is not a valid file path.")
            raise ValueError(f"Invalid file path: {excel_path}")

        self.path = excel_path
        self.config_sheet = config_sheet
        self.cfg_req = cfg_req
        self._workbook_manager: ExcelWorkbookManager | None = None
        self.content = self._load_config()
        self.table_config: ExcelTableConfig | None = None

        if self.version_check():
            logger.critical("Wrong file config version or missing version key.")
            # raise ExcelConfigurationError("Wrong file config version or missing version key.")

        logger.debug(f"Excel configuration content: {self._redacted_content()}")

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

    def _load_config(self) -> dict[str, Any]:
        """Load the configuration from Excel file."""
        logger.debug(f"Reading Excel configuration file: {self.path}")
        try:
            self._workbook_manager = ExcelWorkbookManager(self.path)
            self._workbook_manager.load()
            config_dict = self._workbook_manager.read_config(sheet=self.config_sheet)

            # Convert flat key-value pairs to nested structure
            return self._build_nested_config(config_dict)
        except Exception as e:
            message = f"Error reading Excel configuration file '{self.path}': {e}"
            logger.error(message)
            raise ExcelConfigurationError(message) from e

    def _build_nested_config(self, flat_config: dict[str, Any]) -> dict[str, Any]:
        """Convert flat key-value pairs to nested dictionary structure.

        Args:
            flat_config: Dictionary with keys like "jira.connection.site_address"

        Returns:
            Nested dictionary structure
        """
        nested_config: dict[str, Any] = {}

        for key, value in flat_config.items():
            if not key or not isinstance(key, str):
                continue

            # Split key by dots and build nested structure
            keys = key.split(".")
            current = nested_config

            # Navigate/create nested structure
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                elif not isinstance(current[k], dict):
                    # Convert existing value to dict if needed
                    current[k] = {}
                current = current[k]

            # Set the final value
            final_key = keys[-1]
            current[final_key] = value

        return nested_config

    def get_value(self, key: str, default: T | None = None, expected_type: type[T] | None = None) -> T | None:
        """Get a value from the configuration file.

        Args:
            key: Configuration key (supports dot notation like "jira.connection.site_address")
            default: Default value if key not found
            expected_type: Expected type for validation

        Returns:
            Configuration value or default
        """
        # Handle new nested structure
        if "metadata" in self.content:
            value: Any = self._get_nested_value(key)
        else:
            # Fallback to old flat structure
            value = self.content.get(key, default)

        if value is None:
            return default

        # Handle type conversion for Excel configurations
        if expected_type is not None and not isinstance(value, expected_type):
            # Try to convert string values to expected types for Excel configurations
            if isinstance(expected_type, type) and expected_type is bool and isinstance(value, str):
                # Convert common boolean string representations
                value_lower = value.lower().strip()
                if value_lower in {"true", "1", "yes", "on", "enabled"}:
                    value = True
                elif value_lower in {"false", "0", "no", "off", "disabled"}:
                    value = False
                else:
                    raise TypeError(
                        f"Config key '{key}' expected {expected_type.__name__}, got {type(value).__name__} (value: '{value}')"
                    )
            elif isinstance(expected_type, type) and expected_type is int and isinstance(value, str):
                try:
                    value = int(value)
                except ValueError as exc:
                    raise TypeError(
                        f"Config key '{key}' expected {expected_type.__name__}, got {type(value).__name__} (value: '{value}')"
                    ) from exc
            elif isinstance(expected_type, type) and expected_type is float and isinstance(value, str):
                try:
                    value = float(value)
                except ValueError as exc:
                    raise TypeError(
                        f"Config key '{key}' expected {expected_type.__name__}, got {type(value).__name__} (value: '{value}')"
                    ) from exc
            else:
                # For other type mismatches, raise an error
                raise TypeError(f"Config key '{key}' expected {expected_type.__name__}, got {type(value).__name__}")

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

    def _redacted_content(self) -> dict[str, Any]:
        """Return a redacted copy of the configuration for safe logging."""
        sensitive_keys = {"api_token", "password", "secret", "token"}

        def redact(obj: Any) -> Any:
            """Redact the configuration file."""
            if isinstance(obj, dict):
                return {k: ("***" if k in sensitive_keys else redact(v)) for k, v in obj.items()}
            if isinstance(obj, list):
                return [redact(v) for v in obj]
            return obj

        return redact(self.content)

    def load_table_config(self) -> ExcelTableConfig:
        """Load structured table configuration from Excel file.

        Returns:
            ExcelTableConfig object containing all parsed table data
        """
        if self.table_config is not None:
            return self.table_config

        if self._workbook_manager is None:
            raise RuntimeError("Workbook manager not initialized. Call load() first.")

        logger.debug(f"Loading table configuration from sheet '{self.config_sheet}'")
        table_reader = ExcelTableReader(self._workbook_manager)
        self.table_config = table_reader.read_all_tables(self.config_sheet)

        return self.table_config

    def get_table_config(self) -> ExcelTableConfig | None:
        """Get the table configuration if loaded.

        Returns:
            ExcelTableConfig object or None if not loaded
        """
        return self.table_config

    def has_table_config(self) -> bool:
        """Check if table configuration is available.

        Returns:
            True if table configuration is loaded, False otherwise
        """
        return self.table_config is not None

    def close(self) -> None:
        """Close the workbook manager and release resources."""
        if self._workbook_manager:
            self._workbook_manager.close()
            self._workbook_manager = None

    def __repr__(self) -> str:
        """Return a string representation of the configuration."""
        try:
            version = self.get_value("metadata.version", default="unknown")
        except Exception:
            version = "unknown"
        return f"ExcelConfiguration(path='{self.path}', sheet='{self.config_sheet}', version={version})"

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
