#!/usr/bin/env python
"""This script is the main entry point for the Jira Importer.

Author:
    Julien (@tom4897)
"""

from __future__ import annotations

# Import libraries
import logging
import warnings
from pathlib import Path
from typing import Any

# Import classes
from jira_importer import CFG_REQ_DEFAULT
from jira_importer.app import App
from jira_importer.artifacts import ArtifactManager
from jira_importer.config.config_factory import ConfigurationFactory, ConfigurationType
from jira_importer.config.utils import determine_config_path, display_config
from jira_importer.console import ConsoleIO
from jira_importer.errors import (
    ConfigurationError,
    ErrorResponse,
    InputFileError,
    ProcessingError,
    format_error_for_display,
    log_exception,
)
from jira_importer.fileops import FileManager
from jira_importer.import_pipeline.runner import ImportRunner, PipelineContext, PipelineOptions
from jira_importer.log import add_file_logging, setup_logger
from jira_importer.utils import get_executable_dir, get_logs_directory, load_config_for_input, open_browser

# Global variables
debug_mode = False  # pylint: disable=invalid-name


# Suppress specific warnings from openpyxl
warnings.filterwarnings("ignore", category=FutureWarning, module="openpyxl")
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

ui = ConsoleIO.getUI()  # pylint: disable=invalid-name
fmt = ui.fmt  # pylint: disable=invalid-name


# Minimal config classes for fallback scenarios when full config loading fails or isn't needed
class MinimalConfig:  # pylint: disable=too-few-public-methods
    """Minimal config that returns default values for any key.

    Used when full configuration loading fails or isn't needed (e.g., version display,
    cleanup scenarios, error handling).
    """

    def get_value(self, key: str, default: Any = None, expected_type: Any = None) -> Any:  # pylint: disable=unused-argument
        """Return default value for any key."""
        return default


class MinimalConfigForCredentials:  # pylint: disable=too-few-public-methods
    """Minimal config for credential operations with additional methods.

    Used when config loading fails but we still need credential operations.
    Includes both get_value() and get() methods, plus a path attribute.
    """

    path = "minimal"

    def get_value(self, key: str, default: Any = None, expected_type: Any = None) -> Any:  # pylint: disable=unused-argument
        """Return default value for any key."""
        return default

    def get(self, key: str, default: Any = None) -> Any:  # pylint: disable=unused-argument
        """Return default value for any key."""
        return default


def _show_version() -> int:
    """Handle --version flag and exit early."""
    minimal_config = MinimalConfig()
    artifact_manager = ArtifactManager(minimal_config)
    app = App(artifact_manager)
    app.print_version()
    app.event_close(exit_code=0, cleanup=False)
    return 0


def _show_config(args: Any) -> int:
    """Handle --show-config flag and exit early."""
    try:
        if not hasattr(args, "input_file") or not args.input_file:
            # Provide dummy input_file for config determination
            args.input_file = "dummy.xlsx"
        config_path = determine_config_path(args)
        display_config(config_path)
        return 0
    except ConfigurationError as exc:
        # Domain configuration error: show a clear message
        ui.error(format_error_for_display(exc))
        return 1
    except Exception as exc:  # pylint: disable=broad-except
        # Unexpected internal error
        ui.error(f"Failed to load configuration for show-config: {exc}")
        return 1


def _graceful_exit(exit_code: int, do_cleanup: bool = False) -> None:
    """Exit gracefully with cleanup using minimal config."""
    ui.lf()
    minimal_config = MinimalConfig()  # type: ignore[assignment]
    app = App(ArtifactManager(minimal_config))
    app.event_close(exit_code=exit_code, cleanup=do_cleanup)


def _show_debug_info(args: Any, config: Any, logger: logging.Logger) -> None:
    logger.debug("Jira Importer initialized.")
    logger.debug(f"Configuration loaded: {config.path}")
    logger.debug(f"Input file: {args.input_file}")
    logger.debug(fmt.kv("Input file", fmt.path(args.input_file)))
    logger.debug(fmt.kv("Configuration", fmt.path(args.config)))
    logger.debug(fmt.kv("Debug mode", args.debug))
    logger.debug(fmt.kv("Version", args.version))
    logger.debug(fmt.kv("Config default", args.config_default))
    logger.debug(fmt.kv("Config input", args.config_input))
    logger.debug(fmt.kv("Config excel", args.config_excel))
    logger.debug(fmt.kv("args", str(args)))


def _set_autoreply(args: Any) -> bool | None:
    """Set the autoreply flag based on the command line arguments."""
    if getattr(args, "auto_yes", False):
        return True
    if getattr(args, "auto_no", False):
        return False
    return None


def _validate_input_file(in_path: Path, xlsx_file: str, logger: logging.Logger) -> None:
    """Validate the input file exists and is a file."""
    try:
        if not in_path.exists():
            raise InputFileError(
                f"Input file does not exist: {xlsx_file}",
                details={"file_path": str(xlsx_file), "operation": "input_validation"},
            )
        if not in_path.is_file():
            raise InputFileError(
                f"Input path is not a file: {xlsx_file}",
                details={
                    "file_path": str(xlsx_file),
                    "operation": "input_validation",
                    "path_type": "directory_or_other",
                },
            )
    except InputFileError as file_exc:
        # Log the error with structured details
        log_exception(logger, file_exc, context="Input file validation")
        # Display formatted error with error code
        error_message = format_error_for_display(file_exc)
        ui.error(error_message)
        logger.critical(f"Input file validation failed: {error_message}")
        _graceful_exit(exit_code=2, do_cleanup=False)


def _load_configuration(args: Any, logger: logging.Logger) -> tuple[ConfigurationType | None, str | None, int]:
    """Load configuration from file with error handling.

    Args:
        args: Command line arguments.
        logger: Logger instance for error logging.

    Returns:
        Tuple of (config, config_path, exit_code). On success, returns (config, config_path, 0).
        On error, handles error display/logging, calls graceful exit, and returns (None, None, 1).
    """
    config_path = determine_config_path(args)
    try:
        config = ConfigurationFactory.create_config(config_path, cfg_req=CFG_REQ_DEFAULT, config_sheet="Config")  # type: ignore
        return config, config_path, 0
    except Exception as config_exc:  # pylint: disable=broad-except
        log_exception(logger, config_exc, context="Configuration loading")
        error_message = format_error_for_display(config_exc)
        ui.error(error_message)
        _graceful_exit(exit_code=1, do_cleanup=False)
        return None, None, 1


def _set_output_dir_path(args: Any) -> Path:
    """Set the output directory path based on the command line arguments."""
    if args.output:
        return Path(args.output)
    return Path(args.input_file).parent


def _set_output_target(args: Any) -> str:
    """Set the output target based on the command line arguments."""
    if args.output_target_cloud:
        return "cloud"
    return "csv"


def _credential_preflight(config: Any, autoreply: bool | None, logger: logging.Logger) -> None:
    try:
        from .config.config_view import ConfigView  # pylint: disable=import-outside-toplevel
        from .import_pipeline.cloud.credential_manager import (  # pylint: disable=import-outside-toplevel
            ensure_cloud_credentials,
        )

        status = ensure_cloud_credentials(ui, ConfigView(config), autoreply)
        if status.get("found"):
            src = status.get("source", "unknown")
            logger.info("Jira API Email/Key found (%s)", src)
            if status.get("email"):
                ui.hint(f"Using Jira account: {status['email']}")
        else:
            App.event_fatal(
                exit_code=2,
                message=("Jira API credentials are missing. Set them in config/env, or run without -y to enter them."),
            )
    except Exception as preflight_exc:
        logger.exception("Credential preflight failed: %s", preflight_exc)
        App.event_fatal(exit_code=2, message=f"Credential preflight failed: {preflight_exc}")


def main() -> int:
    """Main function for the Jira Importer application."""
    ui.title_banner("Jira Toolkit: Importer 🚀", icon="")
    ui.say(fmt.bold("Authors:"), fmt.default("Julien (@tom4897)"), fmt.default("Alain (@Nakool)"))
    ui.say(fmt.kv("Repository", "https://github.com/deerhide/jira-toolkit"))

    # --- Initialization ---
    ui.lf()
    ui.progress_light("Initializing Jira Importer")
    args = App.parse_args()

    # Handle version flag early, before any configuration loading
    if args.version:
        return _show_version()

    # Handle debug show-config mode
    if args.show_config:
        return _show_config(args)

    # Handle --credentials mode early (like --version)
    if hasattr(args, "credentials") and args.credentials:
        from .import_pipeline.cloud.credential_manager import (  # pylint: disable=import-outside-toplevel
            run_credentials_cli,
        )

        config = MinimalConfigForCredentials()  # type: ignore
        exit_code = run_credentials_cli(config, args.credentials, ui)
        return exit_code

    # Respect -y and -n args: set _autoreply True for -y/--yes, False for -n/--no, None otherwise
    autoreply = _set_autoreply(args)

    # Set up basic logging early (before config loading) so we can log errors
    setup_logger(logging.DEBUG if args.debug else logging.INFO, None)
    logger = logging.getLogger(__name__)

    try:
        add_file_logging(None)
    except Exception:  # pylint: disable=broad-except
        # File logging is best-effort; ignore failures here
        pass

    # Load configuration with error handling
    # Note: config variable from credentials path (above) is not in scope here due to early return
    config, config_path, exit_code = _load_configuration(args, logger)  # type: ignore[assignment]
    if exit_code != 0:
        return exit_code
    if config_path is None or config is None:
        raise ValueError("config_path and config should not be None when exit_code is 0")

    # Re-initialize logging with config support (now that config is loaded)
    setup_logger(logging.DEBUG if args.debug else None, config)

    # Add file logging if enabled in config
    add_file_logging(config)
    logger.debug(f"Logs directory: {get_logs_directory()}")
    logger.debug(f"Executable directory: {get_executable_dir()}")

    if logging.getLogger().level == logging.DEBUG:
        ui.debug("Debug mode is enabled.")

    artifact_manager = ArtifactManager(config)
    file_manager = FileManager(artifact_manager, config)
    app = App(artifact_manager)

    logger.info(f"Version: {app.version_info}")

    logger.info(f"Input: {args.input_file}")
    ui.say(f"Excel file: {fmt.path(args.input_file)}")
    logger.info(f"Config: {config_path}")
    ui.say(f"Configuration file: {fmt.path(config_path)}")

    _show_debug_info(args, config, logger)

    ui.success_light("Jira Importer initialized")

    output_dir_path = _set_output_dir_path(args)

    # Determine output target strictly from CLI: --cloud implies cloud, otherwise csv
    output_target = _set_output_target(args)
    if output_target == "cloud":
        _question = "The Jira Cloud API support is experimental and may not work properly. Do you want to continue?"
        if not ui.prompt_yes_no(_question, default=False, auto_reply=autoreply):
            app.event_abort(exit_code=1, message="Run (--cloud) stopped")
        elif autoreply is not None:
            ui.warning("Auto-reply is set to yes. Continuing with Jira Cloud API...")
        else:
            ui.success("Continuing with Jira Cloud API...")

    # --- Checking input file ---
    ui.lf()
    ui.progress_light("Checking input file")

    xlsx_file = args.input_file
    in_path = Path(xlsx_file)

    _validate_input_file(in_path, xlsx_file, logger)

    output_filename: str = file_manager.generate_output_filename(xlsx_file, file_extension="csv", suffix="_jira_ready")
    output_filepath: Path = output_dir_path / output_filename
    logger.debug(f"Output path: {output_filepath}")

    _, mgr = load_config_for_input(in_path, args.data_sheet)

    ui.success_light("Input file is valid")

    # --- Processing Dataset file ---
    ui.lf()
    ui.progress_light("Processing CSV file for Jira Import")

    # Early credential preflight for Jira Cloud with fail-fast and logging
    if output_target == "cloud":
        _credential_preflight(config, autoreply, logger)

    _result_code = 0
    context = PipelineContext(
        input_path=in_path,
        output_target=output_target,  # type: ignore[assignment]  # str -> Literal conversion
        output_filepath=output_filepath,
        output_dir=output_dir_path,
        config=config,
        ui=ui,
        logger=logger,
        app=app,
    )
    options = PipelineOptions(
        enable_excel_rules=args.enable_excel_rules,
        excel_rules_source=str(in_path) if args.enable_excel_rules else None,
        enable_auto_fix=args.auto_fix,
        no_report=args.no_report,
        dry_run=args.dry_run,
        fix_cloud_estimates=args.fix_cloud_estimates,
        debug=args.debug,
        cloud_debug_payloads=getattr(args, "cloud_debug_payloads", False),
        auto_reply=autoreply,
    )

    try:
        runner = ImportRunner(context, options)
        _result_code = runner.run()
    except ProcessingError as proc_exc:
        # Use structured error handling for domain exceptions
        log_exception(logger, proc_exc, context="Import pipeline")
        error_message = format_error_for_display(proc_exc)
        ui.error(error_message)
        logger.critical(f"Import pipeline failed: {error_message}")
        app.event_close(exit_code=3, cleanup=True)
        return 3
    except Exception as exc:  # pylint: disable=broad-except
        # Last-resort guard for unexpected internal errors. This broad catch is
        # intentional so we can present a clear failure to the user while
        # preserving the full traceback in the logs for diagnosis.
        logger.exception("Unexpected internal error in import pipeline: %s", exc)
        App.event_fatal(
            exit_code=3,
            message="An unexpected internal error occurred in the processor, please check the logs for details.",
        )
        return 3
    finally:
        try:
            if mgr is not None:
                mgr.close()
        except Exception:  # pylint: disable=broad-except
            # Best-effort cleanup; ignore close failures.
            pass

    # Handle CSV-specific finalization (cloud output is handled by ImportRunner)
    if output_target == "csv":
        # TODO: Move logic to utils
        if config.get_value("app.import.auto_open_page", default=False, expected_type=bool):
            site_address = config.get_value("jira.connection.site_address", default="", expected_type=str)
            if site_address and "BulkCreateSetupPage" not in site_address:
                site_address += "/secure/BulkCreateSetupPage!default.jspa?externalSystem=com.atlassian.jira.plugins.jim-plugin%3AbulkCreateCsv&new=true"
            open_browser(f"{site_address}")

        ui.lf()
        ui.full_panel(fmt.success("Processing complete. You can close this window now."))
        app.event_close(exit_code=_result_code, cleanup=True)

    return _result_code


def run_main_with_error_response() -> tuple[int, ErrorResponse | None]:
    """Run main() and return an exit code plus optional structured ErrorResponse.

    This helper is intended for programmatic callers (e.g. integrations/tests)
    that prefer a structured error model instead of console-only messaging.

    Returns:
        Tuple of (exit_code, ErrorResponse|None). On success, the error response
        is None; on failure it contains the mapped error information.
    """
    from jira_importer.errors import error_response_from_exception  # pylint: disable=import-outside-toplevel

    try:
        exit_code = main()
        return exit_code, None
    except Exception as exc:  # pylint: disable=broad-except
        error = error_response_from_exception(exc)
        return 1, error


# Main function
if __name__ == "__main__":
    main()
