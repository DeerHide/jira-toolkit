"""Configuration utility functions for the Jira Importer.

Author:
    Julien (@tom4897)
"""

import logging
from pathlib import Path
from typing import Any

from .. import CFG_REQ_DEFAULT, DEFAULT_CONFIG_FILENAME
from ..console import ConsoleIO
from ..log import add_file_logging, set_console_handler_level, setup_logger
from ..utils import find_config_path
from .config_display import display_config_content, display_table_config
from .config_factory import ConfigurationFactory, ConfigurationType
from .constants import (
    EPIC_NAMES,
    INITIATIVE_NAMES,
    LEVEL_1_INITIATIVE,
    LEVEL_2_EPIC,
    LEVEL_3_STORY,
    LEVEL_4_SUBTASK,
    SUBTASK_NAMES,
)


def get_default_level_for_name(name: str) -> int:
    """Get default level for common issue type names.

    Shared helper used by IssueTypesConfig and ExcelConfiguration to derive
    issue type hierarchy level from name when level is not explicitly configured.
    Avoids circular imports between config.models.issuetypes and config.excel_config.

    Args:
        name: Issue type name (case-insensitive for built-in names).

    Returns:
        Level (1-4): 1=Initiative, 2=Epic, 3=Story/Task/Bug, 4=Sub-task.
    """
    name_lower = name.lower()
    if name_lower in INITIATIVE_NAMES:
        return LEVEL_1_INITIATIVE
    if name_lower in EPIC_NAMES:
        return LEVEL_2_EPIC
    if name_lower in SUBTASK_NAMES:
        return LEVEL_4_SUBTASK
    return LEVEL_3_STORY


def determine_config_path(args: Any) -> str:
    """Determine the configuration file path based on command line arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        Path to the configuration file
    """
    # Handle mutually exclusive configuration arguments
    if args.config_default:
        # Use default config filename in script location
        config_path = find_config_path(DEFAULT_CONFIG_FILENAME, args.input_file, config_default=True)
        logging.debug(f"config_default: {config_path}")
    elif args.config_input:
        # Use default config filename in input file location
        config_path = find_config_path(DEFAULT_CONFIG_FILENAME, args.input_file, config_input=True)
        logging.debug(f"config_input: {config_path}")
    elif args.config_excel:
        # Use the input Excel file as configuration source
        config_path = args.input_file
        logging.debug(f"config_excel: using input file as config: {config_path}")
    # Check if a specific config file was provided (not the default)
    # This ensures --config parameter takes precedence over smart defaults
    elif args.config != DEFAULT_CONFIG_FILENAME:
        # Use specified config file with specific path search
        config_path = find_config_path(args.config, args.input_file, config_specific=True)
        logging.debug(f"Specific config provided: {config_path}")
    # Smart default: if input is Excel, try using it as config first
    elif args.input_file and Path(args.input_file).suffix.lower() in {".xlsx", ".xlsm"}:
        # Try using the input Excel file as config source
        input_path = Path(args.input_file)
        if input_path.exists():
            config_path = args.input_file
            logging.debug(f"Smart default: using input Excel file as config: {config_path}")
        else:
            # Fall back to traditional config search
            config_path = find_config_path(args.config, args.input_file)
            logging.debug(f"Smart default fallback: {config_path}")
    else:
        # Use specified config file with default search behavior
        config_path = find_config_path(args.config, args.input_file)
        logging.debug(f"!config_default & !config_input & !config_excel: {config_path}")

    return config_path


def display_config(config_file: str, *, args: Any = None) -> None:
    """Display configuration from the specified file in a user-friendly format.

    Args:
        config_file: Path to the configuration file to display.
        args: Optional parsed CLI arguments; when provided and a fatal error occurs,
            they are passed to event_fatal for diagnosis output.
    """
    setup_logger(logging.DEBUG, None)  # Root at DEBUG so file gets full detail
    set_console_handler_level(logging.WARNING)  # Console: no log lines, only UI output
    logger = logging.getLogger(__name__)

    # Get UI components
    ui = ConsoleIO.get_ui()
    fmt = ui.fmt

    try:
        # Load configuration first to get logging settings
        config = ConfigurationFactory.create_config(config_file, cfg_req=CFG_REQ_DEFAULT)

        add_file_logging(config)
        logger.info(f"Configuration check started for: {config_file}")
        ui.title_banner("Configuration Check 🔍", icon="")
        ui.say(f"Loading configuration from: {fmt.path(config_file)}")
        ui.lf()

        # Display basic info
        ui.say(fmt.bold("Configuration Type:"), fmt.default(type(config).__name__))
        ui.say(fmt.bold("Configuration File:"), fmt.path(config_file))
        logger.info(f"Configuration type: {type(config).__name__}")
        logger.info(f"Configuration file: {config_file}")

        if hasattr(config, "path"):
            ui.say(fmt.bold("Resolved Path:"), fmt.path(config.path))
            logger.info(f"Resolved path: {config.path}")

        ui.lf()

        # Display configuration content
        ui.say(fmt.bold("Configuration Content:"))
        ui.lf()

        if hasattr(config, "content") and config.content:
            logger.info("Displaying configuration content")
            display_config_content(config.content, indent=0)
        else:
            ui.say(fmt.warning("No configuration content found"))
            logger.warning("No configuration content found")

        # Display table configuration if available (Excel or JSON with jira.teams etc.)
        if hasattr(config, "load_table_config"):
            try:
                config.load_table_config()
            except Exception as exc:
                ui.say(fmt.warning(f"Could not load table configuration: {exc}"))
                logger.warning(f"Could not load table configuration: {exc}")
        if hasattr(config, "get_table_config"):
            try:
                table_config = config.get_table_config()
                if table_config:
                    logger.info("Displaying table configuration")
                    ui.lf()
                    ui.say(fmt.bold("Table Configuration:"))
                    ui.lf()
                    display_table_config(config)
                else:
                    logger.info("No table configuration available")
            except Exception as exc:
                ui.say(fmt.warning(f"Could not display table configuration: {exc}"))
                logger.warning(f"Could not display table configuration: {exc}")

        ui.lf()
        ui.success("Configuration successfully loaded!")
        logger.info("Configuration successfully loaded!")

    except Exception as exc:
        logger.error(f"Configuration loading failed: {exc}")
        from jira_importer.app import App  # pylint: disable=import-outside-toplevel

        App.event_fatal(exit_code=1, message=f"Failed to load configuration: {exc}", args=args)


def load_configuration_with_error_handling(
    args: Any, logger: logging.Logger
) -> tuple[ConfigurationType | None, str | None, int]:
    """Load configuration from file with error handling.

    Args:
        args: Command line arguments.
        logger: Logger instance for error logging.

    Returns:
        Tuple of (config, config_path, exit_code). On success, returns (config, config_path, 0).
        On error, handles error display/logging, calls graceful exit, and returns (None, None, 1).
    """
    from jira_importer.app import App  # pylint: disable=import-outside-toplevel
    from jira_importer.errors import format_error_for_display, log_exception  # pylint: disable=import-outside-toplevel

    ui_instance = ConsoleIO.get_ui()

    config_path = determine_config_path(args)
    try:
        config = ConfigurationFactory.create_config(config_path, cfg_req=CFG_REQ_DEFAULT, config_sheet="Config")
        return config, config_path, 0
    except Exception as config_exc:  # pylint: disable=broad-except
        log_exception(logger, config_exc, context="Configuration loading")
        error_message = format_error_for_display(config_exc)
        ui_instance.error(error_message)
        # Use App.graceful_exit for consistent error handling
        App.graceful_exit(exit_code=1, do_cleanup=False)
        return None, None, 1
