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
from jira_importer.errors import ErrorResponse, JiraAuthError, ProcessingError, format_error_for_display, log_exception
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


def main() -> int:
    """Main function for the Jira Importer application."""
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
    if hasattr(args, "credentials") and args.credentials:
        from .import_pipeline.cloud.credential_manager import (  # pylint: disable=import-outside-toplevel
            run_credentials_cli,
        )

        # For "test" action, we need the actual config to get site_address
        # For other actions (run, show, clear), minimal config is sufficient
        if args.credentials == "test":
            # Set up logging first (needed for config loading)
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
    config, config_path, exit_code = load_configuration_with_error_handling(args, logger)  # type: ignore[assignment]
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

    FileManager.validate_input_file(in_path, xlsx_file, logger)

    output_filename: str = file_manager.generate_output_filename(xlsx_file, file_extension="csv", suffix="_jira_ready")
    output_filepath: Path = output_dir_path / output_filename
    logger.debug(f"Output path: {output_filepath}")

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
