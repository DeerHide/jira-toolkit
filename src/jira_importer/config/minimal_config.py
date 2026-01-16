"""Minimal configuration classes for fallback scenarios.

These classes provide minimal configuration implementations that return default
values for any key. They are used when full configuration loading fails or
isn't needed (e.g., version display, cleanup scenarios, error handling).

Author:
    Julien (@tom4897)
"""

from typing import Any


class MinimalConfig:
    """Minimal config that returns default values for any key.

    Used when full configuration loading fails or isn't needed (e.g., version display,
    cleanup scenarios, error handling).
    """

    def get_value(self, key: str, default: Any = None, expected_type: Any = None) -> Any:  # pylint: disable=unused-argument
        """Return default value for any key.

        Args:
            key: Configuration key (ignored).
            default: Default value to return.
            expected_type: Expected type (ignored).

        Returns:
            The default value provided.
        """
        return default


class MinimalConfigForCredentials:
    """Minimal config for credential operations with additional methods.

    Used when config loading fails but we still need credential operations.
    Includes both get_value() and get() methods, plus a path attribute.
    """

    path = "minimal"

    def get_value(self, key: str, default: Any = None, expected_type: Any = None) -> Any:  # pylint: disable=unused-argument
        """Return default value for any key.

        Args:
            key: Configuration key (ignored).
            default: Default value to return.
            expected_type: Expected type (ignored).

        Returns:
            The default value provided.
        """
        return default

    def get(self, key: str, default: Any = None) -> Any:  # pylint: disable=unused-argument
        """Return default value for any key.

        Args:
            key: Configuration key (ignored).
            default: Default value to return.

        Returns:
            The default value provided.
        """
        return default
