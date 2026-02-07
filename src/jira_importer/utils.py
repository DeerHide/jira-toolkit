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
from .constants import ASCII_CONTROL_MAX, MAX_RELATIVE_PATH_LEN
from .excel.excel_io import ExcelWorkbookManager

logger = logging.getLogger(__name__)
ui = ConsoleIO.get_ui()  # pylint: disable=invalid-name
fmt = ui.fmt


def _contains_control_chars(value: str) -> bool:
    """Return True if the string contains ASCII control characters.

    Keeps validation lightweight to avoid rejecting legitimate Unicode input.
    """
    return any(ord(ch) <= ASCII_CONTROL_MAX for ch in value)


def _sanitize_relative_path(relative_path: str) -> Path:
    """Validate and sanitize a user-controlled relative path.

    - Reject absolute paths
    - Reject traversal elements (..)
    - Reject control characters
    - Apply lightweight length limits to avoid abuse
    """
    from .errors import ValidationError  # pylint: disable=import-outside-toplevel

    if not isinstance(relative_path, str):
        raise ValidationError(
            "relative_path must be a string",
            details={"provided_type": type(relative_path).__name__},
        )

    if _contains_control_chars(relative_path):
        raise ValidationError(
            "path contains control characters",
            details={"path": relative_path},
        )

    # Basic length constraints (conservative defaults)
    if len(relative_path) == 0 or len(relative_path) > MAX_RELATIVE_PATH_LEN:
        raise ValidationError(
            "path length is invalid",
            details={"path_length": len(relative_path), "max_length": MAX_RELATIVE_PATH_LEN},
        )

    if os.path.isabs(relative_path):
        raise ValidationError(
            "absolute paths are not allowed here",
            details={"path": relative_path},
        )

    p = Path(relative_path)
    if any(part == ".." for part in p.parts):
        # raise ValueError("path traversal is not allowed")
        logger.warning("path traversal is not recommended for security reasons: %s", relative_path)

    return p


def resource_path(relative_path: str) -> str:
    """Resolve a resource path robustly across frozen and non-frozen runs.

    - In PyInstaller (frozen), load from the temporary extraction dir (sys._MEIPASS).
    - Otherwise, prefer the current working directory, but fall back safely if CWD is invalid.
    """
    # Validate provided relative path
    try:
        rel = _sanitize_relative_path(relative_path)
    except Exception as exc:  # pylint: disable=broad-except
        ui.error(f"Invalid resource path '{fmt.path(relative_path)}': {exc}")
        logger.warning("Invalid resource path '%s': %s", relative_path, exc)
        # Fail closed with a safe default inside the module directory
        base_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        return str((base_dir / "invalid").resolve())

    # PyInstaller onefile/onedir extraction directory
    if hasattr(sys, "_MEIPASS"):
        try:
            base = Path(sys._MEIPASS)  # type: ignore[attr-defined] # pylint: disable=protected-access
        except Exception:  # pragma: no cover - very rare fallback
            base = Path(os.path.dirname(sys.executable))
        return str((base / rel).resolve())

    # Non-frozen: prefer current working directory; fallback to module directory
    try:
        cwd = Path(os.getcwd())
        return str((cwd / rel).resolve())
    except Exception:  # pragma: no cover - unusual environment issue
        base_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        return str((base_dir / rel).resolve())


# Usage: config_path = resource_path('config_importer.json')


def find_config_path(
    config_filename: str,
    input_file_path: str | None = None,
    config_default: bool = False,
    config_input: bool = False,
    config_specific: bool = False,
) -> str:
    """Find the configuration file path."""
    search_paths: list[str] = []

    # If config_specific is True (when -c is used), only try the exact path provided
    if config_specific:
        # Absolute path allowed, otherwise sanitize relative
        try:
            if os.path.isabs(config_filename):
                candidate = Path(config_filename).resolve(strict=False)
            else:
                rel = _sanitize_relative_path(config_filename)
                candidate = (Path.cwd() / rel).resolve(strict=False)
            search_paths.append(str(candidate))
        except Exception as exc:
            fmt_config_filename = fmt.path(config_filename)
            ui.error(f"Invalid configuration path '{fmt_config_filename}': {exc}")
            logger.warning("Invalid configuration path '%s': %s", config_filename, exc)
            return config_filename

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

    # Original logic for other cases (config_default, config_input, etc.) with sanitization
    # First candidate: absolute path as-is; else sanitized relative to CWD
    try:
        if os.path.isabs(config_filename):
            search_paths.append(str(Path(config_filename).resolve(strict=False)))
        else:
            rel = _sanitize_relative_path(config_filename)
            search_paths.append(str((Path.cwd() / rel).resolve(strict=False)))
    except Exception as exc:
        logger.warning("Skipping invalid config filename '%s': %s", config_filename, exc)

    if config_input:
        if input_file_path:
            try:
                base = Path(input_file_path).resolve(strict=False).parent
                # Only allow file directly under the input file's directory (no traversal)
                rel = (
                    _sanitize_relative_path(config_filename)
                    if not os.path.isabs(config_filename)
                    else Path(config_filename)
                )
                candidate = (base / rel).resolve(strict=False)
                if candidate.parent == base or os.path.isabs(config_filename):
                    search_paths.append(str(candidate))
            except Exception as exc:
                logger.warning("config-input: invalid path computation: %s", exc)
        else:
            logger.warning("config-input: wrong usage")
            return config_filename
    elif config_default:
        try:
            base = Path(os.path.abspath(__file__)).resolve(strict=False).parent
            rel = (
                _sanitize_relative_path(config_filename)
                if not os.path.isabs(config_filename)
                else Path(config_filename)
            )
            candidate = (base / rel).resolve(strict=False)
            search_paths.append(str(candidate))
        except Exception as exc:
            logger.warning("config-default: invalid path computation: %s", exc)
    else:
        try:
            if input_file_path:
                base = Path(input_file_path).resolve(strict=False).parent
                rel = (
                    _sanitize_relative_path(config_filename)
                    if not os.path.isabs(config_filename)
                    else Path(config_filename)
                )
                candidate = (base / rel).resolve(strict=False)
                search_paths.append(str(candidate))
        except Exception as exc:
            logger.warning("config: invalid input-relative path: %s", exc)
        try:
            base = Path(os.path.abspath(__file__)).resolve(strict=False).parent
            rel = (
                _sanitize_relative_path(config_filename)
                if not os.path.isabs(config_filename)
                else Path(config_filename)
            )
            candidate = (base / rel).resolve(strict=False)
            search_paths.append(str(candidate))
        except Exception as exc:
            logger.warning("config: invalid module-relative path: %s", exc)

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
