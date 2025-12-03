"""Configuration utility functions for the Jira Importer.

Author:
    Julien (@tom4897)
"""

import logging
from pathlib import Path
from typing import Any

from .. import CFG_REQ_DEFAULT, DEFAULT_CONFIG_FILENAME
from ..console import ConsoleIO
from ..log import add_file_logging, setup_logger
from ..utils import find_config_path
from .config_display import display_config_content, display_table_config
from .config_factory import ConfigurationFactory


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


def display_config(config_file: str) -> None:
    """Display configuration from the specified file in a user-friendly format.

    Args:
        config_file: Path to the configuration file to display
    """
    setup_logger(logging.DEBUG, None)  # Use debug level for config check
    logger = logging.getLogger(__name__)

    # Get UI components
    ui = ConsoleIO.getUI()
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

        # Display table configuration if available (Excel only)
        if hasattr(config, "load_table_config"):
            try:
                # Load table configuration for Excel files
                table_config = config.load_table_config()
                if table_config:
                    logger.info("Displaying table configuration")
                    ui.lf()
                    ui.say(fmt.bold("Table Configuration:"))
                    ui.lf()
                    display_table_config(config)
                else:
                    logger.info("No table configuration available")
            except Exception as exc:
                ui.say(fmt.warning(f"Could not load table configuration: {exc}"))
                logger.warning(f"Could not load table configuration: {exc}")

        ui.lf()
        ui.success("Configuration successfully loaded!")
        logger.info("Configuration successfully loaded!")

    except Exception as exc:
        logger.error(f"Configuration loading failed: {exc}")
        from ..app import App  # pylint: disable=import-outside-toplevel

        App.event_fatal(exit_code=1, message=f"Failed to load configuration: {exc}")
