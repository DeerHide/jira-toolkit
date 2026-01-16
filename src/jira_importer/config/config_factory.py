"""Description: This script provides a factory for creating configuration objects.

Author:
    Julien (@tom4897)
"""

from __future__ import annotations

import logging
from pathlib import Path

from .. import CFG_REQ_DEFAULT
from ..errors import ConfigurationError
from .excel_config import ExcelConfiguration
from .json_config import JsonConfiguration

logger = logging.getLogger(__name__)

# Type alias for configuration objects
ConfigurationType = JsonConfiguration | ExcelConfiguration


class ConfigurationFactory:
    """Factory for creating configuration objects from different sources.

    Provides a unified interface for loading configuration from JSON or Excel files
    while maintaining backward compatibility with existing code.
    """

    @staticmethod
    def create_config(path: str, cfg_req: int = CFG_REQ_DEFAULT, config_sheet: str = "Config") -> ConfigurationType:
        """Create appropriate configuration object based on file extension.

        Args:
            path: Path to the configuration file
            cfg_req: Required configuration version
            config_sheet: Excel sheet name for configuration (only used for Excel files)

        Returns:
            JsonConfiguration or ExcelConfiguration object

        Raises:
            ConfigurationError: If file extension is not supported or file does not exist
        """
        file_path = Path(path)

        if not file_path.exists():
            raise ConfigurationError(
                f"Configuration file not found: {path}",
                details={"file_path": str(path), "operation": "config_loading"},
            )

        file_extension = file_path.suffix.lower()

        logger.debug(f"Creating configuration from {path} (extension: {file_extension})")

        if file_extension in {".json"}:
            return JsonConfiguration(path, cfg_req=cfg_req)
        elif file_extension in {".xlsx", ".xlsm"}:
            return ExcelConfiguration(path, config_sheet=config_sheet, cfg_req=cfg_req)
        else:
            raise ConfigurationError(
                f"Unsupported configuration file format: {file_extension}. Supported formats: .json, .xlsx, .xlsm",
                details={"file_path": str(path), "file_extension": file_extension},
            )

    @staticmethod
    def create_config_with_fallback(
        primary_path: str,
        fallback_path: str | None = None,
        cfg_req: int = CFG_REQ_DEFAULT,
        config_sheet: str = "Config",
    ) -> ConfigurationType:
        """Create configuration with fallback support.

        Args:
            primary_path: Primary configuration file path
            fallback_path: Fallback configuration file path (optional)
            cfg_req: Required configuration version
            config_sheet: Excel sheet name for configuration

        Returns:
            JsonConfiguration or ExcelConfiguration object from primary or fallback path

        Raises:
            ConfigurationError: If neither primary nor fallback file exists
        """
        # Try primary path first
        if Path(primary_path).exists():
            logger.debug(f"Using primary configuration: {primary_path}")
            return ConfigurationFactory.create_config(primary_path, cfg_req, config_sheet)

        # Try fallback path if provided
        if fallback_path and Path(fallback_path).exists():
            logger.debug(f"Using fallback configuration: {fallback_path}")
            return ConfigurationFactory.create_config(fallback_path, cfg_req, config_sheet)

        # Neither file exists
        error_msg = f"Configuration file not found: {primary_path}"
        if fallback_path:
            error_msg += f" (fallback: {fallback_path})"
        raise ConfigurationError(
            error_msg,
            details={
                "primary_path": str(primary_path),
                "fallback_path": str(fallback_path) if fallback_path else None,
                "operation": "config_loading_with_fallback",
            },
        )

    @staticmethod
    def is_excel_config(path: str) -> bool:
        """Check if the given path points to an Excel configuration file.

        Args:
            path: File path to check

        Returns:
            True if the file is an Excel file, False otherwise
        """
        return Path(path).suffix.lower() in {".xlsx", ".xlsm"}

    @staticmethod
    def is_json_config(path: str) -> bool:
        """Check if the given path points to a JSON configuration file.

        Args:
            path: File path to check

        Returns:
            True if the file is a JSON file, False otherwise
        """
        return Path(path).suffix.lower() == ".json"
