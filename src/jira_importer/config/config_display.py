"""Configuration display utilities.

This module provides utilities for displaying configuration data in a user-friendly format,
including support for both JSON and Excel table-based configurations.
"""

import logging
from typing import Any

from ..console import ConsoleIO

ui = ConsoleIO.getUI()  # pylint: disable=invalid-name
fmt = ui.fmt  # pylint: disable=invalid-name


def display_config_content(content: dict[str, Any], indent: int = 0) -> None:
    """Display configuration content in a nested format.

    Args:
        content: Configuration dictionary to display
        indent: Current indentation level
    """
    indent_str = "  " * indent

    for key, value in content.items():
        if isinstance(value, dict):
            ui.say(f"{indent_str}{fmt.bold(key)}:")
            display_config_content(value, indent + 1)
        else:
            # Redact sensitive information
            display_value = value
            if any(sensitive in key.lower() for sensitive in ["password", "token", "secret", "key", "auth"]):
                display_value = "***"

            ui.say(f"{indent_str}{fmt.bold(key)}: {fmt.default(display_value)}")


def display_table_config(config: Any) -> None:
    """Display table configuration for Excel files.

    Args:
        config: Configuration object with table support
    """
    logger = logging.getLogger(__name__)

    try:
        table_config = config.get_table_config()
        if not table_config:
            ui.say(fmt.warning("No table configuration available"))
            logger.warning("No table configuration available")
            return

        # Display each table type
        table_types = [
            ("Assignees", table_config.assignees),
            ("Sprints", table_config.sprints),
            ("Fix Versions", table_config.fix_versions),
            ("Components", table_config.components),
            ("Issue Types", table_config.issue_types),
            ("Priorities", table_config.priorities),
            ("Ignore List", table_config.ignore_list),
            ("Auto Field Values", table_config.auto_field_values),
        ]

        for table_name, table_data in table_types:
            if table_data:
                logger.info(f"Displaying {table_name}: {len(table_data)} items")
                ui.say(fmt.bold(f"{table_name} ({len(table_data)} items):"))
                for item in table_data[:10]:  # Show first 10 items
                    if hasattr(item, "name"):
                        ui.say(f"  • {item.name}")
                        logger.debug(f"  {table_name} item: {item.name}")
                    elif hasattr(item, "id"):
                        ui.say(f"  • {item.id}")
                        logger.debug(f"  {table_name} item: {item.id}")
                if len(table_data) > 5:
                    ui.say(f"  ... and {len(table_data) - 5} more items")
                    logger.debug(f"  ... and {len(table_data) - 5} more items")
                ui.lf()

    except Exception as exc:
        ui.say(fmt.warning(f"Could not display table configuration: {exc}"))
