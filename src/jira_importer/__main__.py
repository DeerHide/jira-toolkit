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
from jira_importer.app import App
from jira_importer.artifacts import ArtifactManager
from jira_importer.config.minimal_config import MinimalConfigForCredentials
from jira_importer.config.utils import load_configuration_with_error_handling
from jira_importer.console import ConsoleIO
from jira_importer.constants import CREDENTIALS_ACTION_TEST, CREDENTIALS_ACTIONS
from jira_importer.errors import (
    ErrorResponse,
    InputFileError,
    JiraAuthError,
    ProcessingError,
    format_error_for_display,
    log_exception,
)
from jira_importer.fileops import FileManager, FileValidator
from jira_importer.import_pipeline.runner import ImportRunner, PipelineContext, PipelineOptions
from jira_importer.log import add_file_logging, setup_logger
from jira_importer.paths import get_executable_dir, get_logs_directory
from jira_importer.utils import load_config_for_input, open_browser

# Suppress specific warnings from openpyxl
warnings.filterwarnings("ignore", category=FutureWarning, module="openpyxl")
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

ui, fmt = ConsoleIO.get_components()


def _show_debug_info(args: Any, config: Any, logger: logging.Logger) -> None:
    """Emit structured debug information about startup configuration.

    This is intended purely for developers/support, not end users. It avoids
    Rich styling and keeps messages concise so they are readable in log files.
    """
    logger.debug("Jira Importer initialized.")
    logger.debug("Configuration loaded from: %s", getattr(config, "path", "<unknown>"))
    logger.debug("Input file: %s", args.input_file)
    logger.debug("Logs directory: %s", get_logs_directory())
    logger.debug("Executable directory: %s", get_executable_dir())
    logger.debug(
        "CLI flags: debug=%s version=%s config_default=%s config_input=%s config_excel=%s config=%s",
        getattr(args, "debug", False),
        getattr(args, "version", False),
        getattr(args, "config_default", False),
        getattr(args, "config_input", False),
        getattr(args, "config_excel", False),
        getattr(args, "config", None),
    )
    logger.debug("Full args namespace: %s", args)


def main() -> int:
    """Main function for the Jira Importer application."""
    # Set up minimal logging before parse_args so parser errors and early failures are visible
    setup_logger(logging.INFO, None)

    ui.title_banner("Jira Toolkit: Importer 🚀", icon="")
    ui.say(fmt.kv("Repository", "https://github.com/deerhide/jira-toolkit"))

    # --- Initialization ---
    ui.lf()
    ui.progress_light("Initializing Jira Importer")
    args = App.parse_args()

    # Handle version flag early, before any configuration loading
    if args.version:
        return App.show_version()

    # Handle debug show-config mode
    if args.show_config:
        return App.show_config(args)

    # Handle --credentials mode early (like --version)
    if hasattr(args, "credentials") and args.credentials in CREDENTIALS_ACTIONS:
        from .import_pipeline.cloud.credential_manager import (  # pylint: disable=import-outside-toplevel
            run_credentials_cli,
        )

        # For "test" action, we need the actual config to get site_address
        # For other actions (run, show, clear), minimal config is sufficient
        if args.credentials == CREDENTIALS_ACTION_TEST:
            # Apply -d level before config load (logging already configured at start of main)
            setup_logger(logging.DEBUG if args.debug else logging.INFO, None)
            logger = logging.getLogger(__name__)

            try:
                add_file_logging(None)
            except Exception:  # pylint: disable=broad-except
                # File logging is best-effort; ignore failures here
                pass

            # Load configuration for test action
            config, config_path, exit_code = load_configuration_with_error_handling(args, logger)  # type: ignore[assignment]
            if exit_code != 0:
                return exit_code
            if config_path is None or config is None:
                # Fallback to minimal config if loading fails
                config = MinimalConfigForCredentials()  # type: ignore
        else:
            # For run/show/clear, minimal config is sufficient
            config = MinimalConfigForCredentials()  # type: ignore

        exit_code = run_credentials_cli(config, args.credentials, ui)
        return exit_code

    # Respect -y and -n args: set _autoreply True for -y/--yes, False for -n/--no, None otherwise
    autoreply = App.get_autoreply_from_args(args)

    # Apply log level from -d before config load (logging already set up at start of main)
    setup_logger(logging.DEBUG if args.debug else logging.INFO, None)
    logger = logging.getLogger(__name__)

    try:
        add_file_logging(None, announce=False)
    except Exception:  # pylint: disable=broad-except
        # File logging is best-effort; ignore failures here
        pass

    # Load configuration with error handling
    # Note: config variable from credentials path (above) is not in scope here due to early return
    config, config_path, exit_code = load_configuration_with_error_handling(args, logger)  # type: ignore[assignment]
    if exit_code != 0:
        return exit_code
    if config_path is None or config is None:
        raise ValueError("config_path and config should not be None when exit_code is 0")

    # Re-initialize logging with config support (now that config is loaded)
    setup_logger(logging.DEBUG if args.debug else None, config)

    # Add file logging if enabled in config
    add_file_logging(config)

    if logging.getLogger().level == logging.DEBUG:
        ui.debug("Debug mode is enabled.")

    artifact_manager = ArtifactManager(config)
    file_manager = FileManager(config, ui=ui)
    app = App(artifact_manager, ui=ui, fmt=fmt)

    logger.info(f"Version: {app.version_info}")

    config_is_embedded = Path(config_path).resolve() == Path(args.input_file).resolve()

    if config_is_embedded:
        logger.info(f"Data source: {args.input_file} (config embedded)")
        ui.say(f"Data source: {fmt.path(args.input_file)} {fmt.accent('(config embedded)')}")
    else:
        logger.info(f"Data source: {args.input_file}")
        ui.say(f"Data source: {fmt.path(args.input_file)}")
        logger.info(f"Config file: {config_path}")
        ui.say(f"Config file: {fmt.path(config_path)}")

    _show_debug_info(args, config, logger)

    ui.success_light("Jira Importer initialized")

    output_dir_path = App.get_output_dir_from_args(args)

    # Determine output target strictly from CLI: --cloud implies cloud, otherwise csv
    output_target = App.get_output_target_from_args(args)
    if output_target == "cloud":
        # Check credentials BEFORE asking if user wants to continue
        # Note: In dry-run mode, missing credentials only show a warning
        try:
            from .config.config_view import ConfigView  # pylint: disable=import-outside-toplevel
            from .import_pipeline.cloud.credential_manager import (  # pylint: disable=import-outside-toplevel
                validate_cloud_credentials_for_import,
            )

            validate_cloud_credentials_for_import(
                ui,
                ConfigView(config),
                autoreply,
                dry_run=getattr(args, "dry_run", False),
                logger_instance=logger,
            )
        except JiraAuthError as auth_exc:
            # Handle credential errors with proper error display
            log_exception(logger, auth_exc, context="Credential preflight")
            error_message = format_error_for_display(auth_exc)
            ui.error(error_message)
            logger.critical(f"Credential preflight failed: {error_message}")
            app.event_close(exit_code=2, cleanup=True)
            return 2

        if not args.dry_run:
            _question = "Using the Cloud mode will directly import the data into your Jira Cloud instance. Do you want to continue?"
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

    try:
        FileValidator.validate(in_path, xlsx_file, logger)
    except InputFileError as exc:
        log_exception(logger, exc, context="Input file validation")
        ui.error(format_error_for_display(exc))
        logger.critical("Input file validation failed: %s", format_error_for_display(exc))
        app.event_close(exit_code=2, cleanup=False)
        return 2

    output_filename: str = file_manager.generate_output_filename(
        xlsx_file,
        file_extension="csv",
        suffix="_jira_ready",
    )
    output_filepath: Path = output_dir_path / output_filename
    logger.info("Output path: %s", output_filepath)

    _, mgr = load_config_for_input(in_path, args.data_sheet)

    ui.success_light("Input file is valid")

    # --- Processing Dataset file ---
    ui.lf()
    ui.progress_light("Processing CSV file for Jira Import")

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
            args=args,
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
