#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script Name: config.py
Description: This script loads and validates the configuration file for the Jira Importer.
Author: Julien (@tom4897)
License: MIT
Date: 2025
"""

import logging
import os
import json
from pathlib import Path
from typing import Any, Optional, Type, TypeVar

T = TypeVar('T')

logger = logging.getLogger(__name__)

class ConfigurationError(Exception):
    """Raised when the configuration file is invalid or cannot be read."""
    pass

class Configuration:
    def __init__(self, path='config_importer.json', cfg_req=1):
        logger.debug(f"Loading configuration from {path}")
        if not Path(path).is_file():
            logger.error(f"The provided path '{path}' is not a valid file path.")
            raise ValueError(f"Invalid file path: {path}")
        self.path = path
        self.content = self._load_config()
        self.cfg_req = cfg_req
        if self.version_check():
            logger.critical("Wrong file config version or missing version key.")
            raise ConfigurationError("Wrong file config version or missing version key.")
        logger.debug(f"Configuration content: {self._redacted_content()}")

    def version_check(self):
        # Check for new structure first
        if 'metadata' in self.content:
            cfg_version = self.content.get('metadata', {}).get('version')
        else:
            # Fallback to old structure
            logger.warning("Using legacy configuration structure. Please migrate to 'metadata.version' and nested keys.")
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

    def _load_config(self):
        logger.debug(f"Reading configuration file: {self.path}")
        try:
            with Path(self.path).open('r', encoding='utf-8') as config_file:
                return json.load(config_file)
        except json.JSONDecodeError as e:
            message = f"The JSON file '{self.path}' is not correctly formatted. Error: {e}"
            logger.error(message)
            raise ConfigurationError(message)
        except Exception as e:
            message = f"Error reading configuration file '{self.path}': {e}"
            logger.error(message)
            raise ConfigurationError(message)

    def get_value(self, key: str, default: Optional[T] = None, expected_type: Optional[Type[T]] = None) -> Optional[T]:
        # Handle new nested structure
        if 'metadata' in self.content:
            value: Any = self._get_nested_value(key)
        else:
            # Fallback to old flat structure
            value = self.content.get(key, default)

        if value is None:
            return default

        if expected_type is not None and not isinstance(value, expected_type):
            raise TypeError(
                f"Config key '{key}' expected {expected_type.__name__}, got {type(value).__name__}"
            )

        return value  # type: ignore[return-value]
    
    def _get_nested_value(self, key):
        keys = key.split('.')
        current = self.content
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        
        return current

    def _redacted_content(self) -> dict:
        """Return a redacted copy of the configuration for safe logging."""
        sensitive_keys = {"api_token", "password", "secret", "token"}

        def redact(obj):
            if isinstance(obj, dict):
                return {k: ('***' if k in sensitive_keys else redact(v)) for k, v in obj.items()}
            if isinstance(obj, list):
                return [redact(v) for v in obj]
            return obj

        return redact(self.content)

    def __repr__(self) -> str:
        try:
            version = self.get_value('metadata.version', default='unknown')
        except Exception:
            version = 'unknown'
        return f"Configuration(path='{self.path}', version={version})"
