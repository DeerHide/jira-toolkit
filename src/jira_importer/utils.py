"""Description: This script contains utility functions for the Jira Importer.

Author:
    Julien (@tom4897)
"""

import logging
import os
import sys
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Any

from .console import ConsoleIO
from .excel.excel_io import ExcelWorkbookManager

logger = logging.getLogger(__name__)
ui = ConsoleIO.getUI()  # pylint: disable=invalid-name
fmt = ui.fmt


def resource_path(relative_path: str) -> str:
    """Resolve a resource path robustly across frozen and non-frozen runs.

    - In PyInstaller (frozen), load from the temporary extraction dir (sys._MEIPASS).
    - Otherwise, prefer the current working directory, but fall back safely if CWD is invalid.
    """
    # PyInstaller onefile/onedir extraction directory
    if hasattr(sys, "_MEIPASS"):
        try:
            return os.path.join(sys._MEIPASS, relative_path)  # type: ignore[attr-defined] # pylint: disable=protected-access
        except Exception:
            # As a last resort, use the executable directory
            base_dir = os.path.dirname(sys.executable)
            return os.path.join(base_dir, relative_path)

    # Non-frozen: try current working directory first
    try:
        cwd = os.getcwd()
        return os.path.join(cwd, relative_path)
    except Exception:
        # If CWD is invalid (e.g., deleted), fall back to the module directory
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, relative_path)


# Usage: config_path = resource_path('config_importer.json')


def get_logs_directory() -> str:
    """Get or create the logs directory in the executable's location."""
    # Get the directory where the executable/script is located
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller executable
        exe_dir = sys._MEIPASS  # pylint: disable=protected-access
    else:
        # Regular Python script - use the directory containing the script
        exe_dir = os.path.dirname(os.path.abspath(__file__))

    logs_dir = os.path.join(exe_dir, "jira_importer_logs")
    try:
        logger.debug("Creating logs directory in executable location: %s", logs_dir)
        os.makedirs(logs_dir, exist_ok=True)
        return logs_dir
    except (PermissionError, OSError) as e:
        # Fallback to temp directory if we can't create logs dir
        import tempfile  # pylint: disable=import-outside-toplevel

        ui.error(f"Could not create logs directory in executable location: {e}")
        logger.debug(f"Could not create logs directory in executable location: {e}")
        temp_logs_dir = os.path.join(tempfile.gettempdir(), "jira-toolkit", "logs")
        os.makedirs(temp_logs_dir, exist_ok=True)
        return temp_logs_dir


def find_config_path(
    config_filename: str,
    input_file_path: str | None = None,
    config_default: bool = False,
    config_input: bool = False,
    config_specific: bool = False,
) -> str:
    """Find the configuration file path."""
    search_paths = []

    # If config_specific is True (when -c is used), only try the exact path provided
    if config_specific:
        # Check if it's an absolute path
        if os.path.isabs(config_filename):
            search_paths.append(config_filename)
        else:
            # For relative paths, try relative to current working directory
            search_paths.append(os.path.abspath(config_filename))

        logger.debug(f"Specific config path provided, searching only in: {search_paths}")
        for path in search_paths:
            if os.path.isfile(path):
                logger.debug(f"Found configuration file: {path}")
                return path

        # If not found, return the original path (let the caller handle the error)
        fmt_config_filename = fmt.path(config_filename)
        ui.error(f"Configuration file '{fmt_config_filename}' not found.")
        logger.warning(f"Configuration file '{config_filename}' not found.")
        return config_filename

    # Original logic for other cases (config_default, config_input, etc.)
    # First, check if the config_filename is an absolute path or relative to current working directory
    if os.path.isabs(config_filename) or os.path.isfile(config_filename):
        search_paths.append(config_filename)

    if config_input:
        if input_file_path:
            search_paths.append(os.path.join(os.path.dirname(os.path.abspath(input_file_path)), config_filename))
        else:
            logger.warning("config-input: wrong usage")
            return config_filename
    elif config_default:
        search_paths.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), config_filename))
    else:
        if input_file_path:
            search_paths.append(os.path.join(os.path.dirname(os.path.abspath(input_file_path)), config_filename))
        search_paths.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), config_filename))

    logger.debug(f"Searching for configuration file in: {search_paths}")
    for path in search_paths:
        if os.path.isfile(path):
            logger.debug(f"Found configuration file: {path}")
            return path

    fmt_config_filename = fmt.path(config_filename)
    ui.error(f"Configuration file '{fmt_config_filename}' not found in expected locations. Using default path.")
    logger.warning(f"Configuration file '{config_filename}' not found in expected locations. Using default path.")
    logger.warning(f"Expected locations: {search_paths}")
    ui.error(f"Expected locations: {search_paths}")
    return config_filename


def default_out_path(in_path: Path) -> Path:
    """Generate default output path for CSV file based on input path.

    Args:
        in_path: Input file path

    Returns:
        Output path with '_jira_ready.csv' suffix
    """
    return Path(f"{in_path.stem}_jira_ready.csv")


def load_config_for_input(in_path: Path, data_sheet: str) -> tuple[Any, ExcelWorkbookManager | None]:  # pylint: disable=unused-argument
    """Return (config_like, excel_manager_or_None).

    - For XLSX input, read 'Config' via ExcelWorkbookManager (keeps things generic).
    - For CSV input, return {} (you can replace this with your own config loader).

    Args:
        in_path: Input file path
        data_sheet: Data sheet name (unused parameter for compatibility)

    Returns:
        Tuple of (config_dict, excel_manager_or_None)
    """
    if in_path.suffix.lower() in {".xlsx", ".xlsm"}:
        mgr = ExcelWorkbookManager(in_path)
        mgr.load()
        cfg = mgr.read_config(sheet="Config")
        # ImportProcessor will also create/use a manager for meta/report writing.
        return cfg, mgr
    return {}, None


def open_jira_filter(config: Any, created_issue_keys: list[str], ui_instance: Any, logger_ref: logging.Logger) -> None:
    """Open Jira filter page showing the newly created issues.

    Args:
        config: Configuration object with get_value method
        created_issue_keys: List of created issue keys
        ui_instance: UI instance for displaying messages
        logger_ref: Logger instance for logging
    """
    if not created_issue_keys:
        return

    # Get project key and site address from config
    project_key = config.get_value("jira.project.key", default="", expected_type=str)
    site_address = config.get_value("jira.connection.site_address", default="", expected_type=str)

    if not project_key or not site_address:
        ui_instance.warning("Cannot open Jira filter: missing project key or site address")
        return

    # Sort issue keys to get min and max for range query
    sorted_keys = sorted(created_issue_keys)
    min_key = sorted_keys[0]
    max_key = sorted_keys[-1]

    # Build JQL query
    jql_query = f'project = "{project_key}" AND issuekey >= {min_key} AND issuekey <= {max_key} ORDER BY created DESC'

    # URL encode the JQL query
    encoded_jql = urllib.parse.quote(jql_query)

    # Build Jira filter URL
    filter_url = f"{site_address.rstrip('/')}/jira/software/c/projects/{project_key}/issues/?jql={encoded_jql}&selectedIssue={max_key}"

    ui_instance.info(f"Opening Jira filter: {filter_url}")
    logger_ref.info(f"Opening Jira filter for created issues: {jql_query}")

    # Use the existing open_browser function from utils
    open_browser(filter_url, logger_ref)


def open_browser(url: str, logger_ref: logging.Logger | None = None) -> bool:
    """Open a URL in the user's default browser. Returns True on success."""
    log = logger_ref or logging.getLogger(__name__)
    try:
        log.debug("Opening URL in browser: %s", url)
        result = webbrowser.open(url, new=2)
        if not result:
            log.warning("Failed to open URL in browser: %s", url)
        return bool(result)
    except Exception as e:  # pylint: disable=broad-except
        # Keep broad except here to prevent UI crash due to platform/browser issues
        ui.error(f"Failed to open URL in browser: {url}")
        log.exception("Exception while opening URL %s: %s", url, e)
        return False
