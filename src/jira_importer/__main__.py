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

from jira_importer import CFG_REQ_DEFAULT

# Import classes
from jira_importer.app import App
from jira_importer.artifacts import ArtifactManager
from jira_importer.config.config_factory import ConfigurationFactory
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
from jira_importer.import_pipeline.models import ProblemSeverity
from jira_importer.import_pipeline.processor import ImportProcessor
from jira_importer.import_pipeline.reporting import CloudReportReporter, ProblemReporter, ReportOptions
from jira_importer.import_pipeline.sinks.cloud_sink import write_cloud
from jira_importer.import_pipeline.sinks.csv_sink import write_csv
from jira_importer.log import add_file_logging, setup_logger
from jira_importer.utils import (
    get_executable_dir,
    get_logs_directory,
    load_config_for_input,
    open_browser,
    open_jira_filter,
)

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
    if getattr(args, "auto_yes", False):
        autoreply = True
    elif getattr(args, "auto_no", False):
        autoreply = False
    else:
        autoreply = None

    # Set up basic logging early (before config loading) so we can log errors
    setup_logger(logging.DEBUG if args.debug else logging.INFO, None)
    logger = logging.getLogger(__name__)

    try:
        add_file_logging(None)
    except Exception:  # pylint: disable=broad-except
        # File logging is best-effort; ignore failures here
        pass

    # Determine configuration file path
    config_path = determine_config_path(args)
    try:
        config = ConfigurationFactory.create_config(config_path, cfg_req=CFG_REQ_DEFAULT, config_sheet="Config")  # type: ignore
    except ConfigurationError as config_exc:
        # Domain configuration error: use structured logging and messaging
        log_exception(logger, config_exc, context="Configuration loading")
        error_message = format_error_for_display(config_exc)
        ui.error(error_message)
        logger.critical(f"Configuration loading failed: {error_message}")
        _graceful_exit(exit_code=1, do_cleanup=False)
        return 1
    except Exception as config_exc:  # pylint: disable=broad-except
        # Unexpected internal error while loading configuration
        logger.exception("Unexpected error during configuration loading: %s", config_exc)
        ui.error(f"Unexpected error while loading configuration: {config_exc}")
        logger.critical("Configuration loading failed due to unexpected internal error")
        _graceful_exit(exit_code=1, do_cleanup=False)
        return 1

    # Re-initialize logging with config support (now that config is loaded)
    setup_logger(logging.DEBUG if args.debug else None, config)

    # Add file logging if enabled in config
    add_file_logging(config)
    logger.debug(f"Logs directory: {get_logs_directory()}")
    logger.debug(f"Executable directory: {get_executable_dir()}")

    if logging.getLogger().level == logging.DEBUG:
        ui.debug("Debug mode is enabled.")

    if args.output:
        output_dir_path = Path(args.output)
    elif args.output_is_input:
        output_dir_path = Path(args.input_file).parent
    else:
        output_dir_path = Path(args.input_file).parent

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

    # Determine output target strictly from CLI: --cloud implies cloud, otherwise csv
    output_target = "csv"
    if getattr(args, "output_target_cloud", False):
        if not ui.prompt_yes_no(
            "The Jira Cloud API support is experimental and may not work properly. Do you want to continue?",
            default=False,
            auto_reply=autoreply,
        ):
            app.event_abort(exit_code=1, message="User cancelled the Execution.")
        else:
            if autoreply is not None:
                ui.warning("Auto-reply is set. Continuing...")
            else:
                ui.success("Continuing...")
            output_target = "cloud"

    # --- Checking input file ---
    ui.lf()
    ui.progress_light("Checking input file")

    xlsx_file = args.input_file
    in_path = Path(xlsx_file)

    # Validate input file exists and is a file
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

        # Exit gracefully
        logger.critical(f"Input file validation failed: {error_message}")
        ui.lf()

        # Use minimal config for cleanup
        minimal_config = MinimalConfig()  # type: ignore[assignment]
        app = App(ArtifactManager(minimal_config))
        app.event_close(exit_code=2, cleanup=False)
        return 2

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
                    message=(
                        "Jira API credentials are missing. Set them in config/env, or run without -y to enter them."
                    ),
                )
        except Exception as preflight_exc:
            logger.exception("Credential preflight failed: %s", preflight_exc)
            App.event_fatal(exit_code=2, message=f"Credential preflight failed: {preflight_exc}")

    def _run_pipeline() -> int:
        """Run the main import pipeline and return an appropriate exit code."""
        _result_code = 0

        processor = ImportProcessor(
            path=in_path,
            config=config,
            ui=ui,  # pipeline is UI-agnostic; reporting handled below
            enable_excel_rules=args.enable_excel_rules,
            excel_rules_source=str(in_path) if args.enable_excel_rules else None,
            enable_auto_fix=args.auto_fix,
        )
        logger.debug(
            "Processor:\n%s\nconfig: %s\nenable_excel_rules: %s\nexcel_rules_source: %s\nenable_auto_fix: %s",
            processor.path,
            processor.config,
            processor.enable_excel_rules,
            processor.excel_rules_source,
            processor.enable_auto_fix,
        )

        result = processor.process()

        # Report
        # TODO: Extract as a function
        if not args.no_report:
            ProblemReporter(options=ReportOptions(show_details=True, show_aggregate_by_code=False)).render(result)
        else:
            ProblemReporter(options=ReportOptions(show_details=False, show_aggregate_by_code=True)).render(result)

        if not processor.enable_auto_fix:
            if result.report.errors > 0:
                ui.warning("Auto-fix is disabled. Please fix the issues manually.")
            ui.hint(
                "You can enable auto-fix by adding the following to your configuration file or by using the --auto-fix flag."
            )

        # Check for CRITICAL problems and handle user interaction
        critical_problems = [p for p in result.problems if p.severity == ProblemSeverity.CRITICAL]
        if critical_problems:
            # If --auto-yes and --cloud, terminate immediately
            if autoreply is True and output_target == "cloud":
                ui.error("Cannot proceed with --auto-yes and --cloud when critical issues are present.")
                app.event_abort(exit_code=1, message="Critical validation issues with --auto-yes and --cloud")

            # Skip critical validation prompt for dry-run mode since we never reach sinks
            if not args.dry_run:
                # For all other cases, ask user whether to continue
                if not ui.prompt_yes_no(
                    "Critical validation issues found. Do you want to continue?", default=False, auto_reply=autoreply
                ):
                    app.event_abort(exit_code=1, message="User cancelled due to critical issues.")
                else:
                    ui.success("Continuing despite critical issues...")

        if result.report.errors > 0:
            if not ui.prompt_yes_no("Do you want to continue?", default=False, auto_reply=autoreply):
                app.event_abort(exit_code=1, message="User cancelled the Execution.")
            else:
                ui.success("Continuing...")

        # Handle dry-run mode - stop before sinks
        if args.dry_run:
            ui.info("Dry-run mode: Processing complete, stopping before sinks")
            ui.success(f"Dry-run completed successfully. {len(result.rows)} rows processed.")
            ui.hint("Remove --dry-run flag to run with actual output")
            # Exit with validation-based code
            _result_code = 0 if result.report.errors == 0 else 1
            ui.lf()
            ui.full_panel(fmt.success("Dry-run complete. You can close this window now."))
            app.event_close(exit_code=_result_code, cleanup=True)
            return _result_code

        # Apply Jira Cloud x60 quirk in CSV sink only, if requested
        temp_config = None
        if args.fix_cloud_estimates and output_target == "csv":
            if isinstance(config, dict):
                temp_config = {**config, "jira.cloud.estimate.multiply_by_60": True}
            else:

                class _Cfg(dict):
                    def get(self, k, d=None):  # type: ignore[override]
                        return super().get(k, d)

                temp_config = _Cfg()
                temp_config.update({"jira.cloud.estimate.multiply_by_60": True})

        if output_target == "cloud":
            ui.info("Output target: Jira Cloud API")

            # Check for critical assignee errors before proceeding
            critical_assignee_errors = [
                p for p in result.problems if p.severity == ProblemSeverity.CRITICAL and p.code.startswith("assignee.")
            ]
            if critical_assignee_errors:
                ui.error("Critical assignee errors found - cannot proceed with cloud import:")
                for error in critical_assignee_errors:
                    ui.error(f"  Row {error.row_index}: {error.message}")
                App.event_fatal(exit_code=4, message="Critical assignee errors prevent cloud import")

            try:
                # Write payloads if debug mode is enabled or cloud debug flag is set
                debug_output_dir = (
                    output_dir_path if (args.debug or getattr(args, "cloud_debug_payloads", False)) else None
                )
                report = write_cloud(result, config, dry_run=False, output_dir=debug_output_dir, ui=ui)
                ui.success(f"Cloud import: created={report.created}, failed={report.failed}, batches={report.batches}")
                if debug_output_dir:
                    ui.info(f"Jira Cloud payloads written to: {debug_output_dir}")
                if report.created_issue_keys:
                    # Display created issue keys in a user-friendly format
                    issue_keys_str = ", ".join(report.created_issue_keys)
                    ui.info(f"{issue_keys_str.count(',') + 1} issues created: {issue_keys_str}")
                    logger.info(f"Created Jira issues: {issue_keys_str}")

                    # Open Jira filter if auto_open_page is enabled
                    if config.get_value("app.import.auto_open_page", default=False, expected_type=bool):
                        open_jira_filter(config, report.created_issue_keys, ui, logger)

                if report.failed > 0:
                    CloudReportReporter().render_errors(report, ui)
            except ProcessingError:
                # Let domain errors bubble up to the outer handler for rich reporting
                raise
            except Exception as exc:  # pylint: disable=broad-except
                # Unexpected internal error during cloud import
                logger.exception("Cloud import failed: %s", exc)
                App.event_fatal(exit_code=3, message=f"Cloud import failed: {exc}")
            # non-zero exit if there were errors (so CI can gate)
            _result_code = 0 if result.report.errors == 0 else 1
            # End after cloud path
            ui.lf()
            ui.full_panel(fmt.success("Processing complete. You can close this window now."))
            app.event_close(exit_code=_result_code, cleanup=True)
            return _result_code

        if output_target == "csv":
            write_csv(result, output_filepath, config=temp_config if temp_config is not None else config)
            ui.say(f"Output Import CSV Ready → {fmt.path(str(output_filepath))}")
            logger.info("Wrote output CSV → %s", output_filepath)

        # non-zero exit if there were errors (so CI can gate)
        _result_code = 0 if result.report.errors == 0 else 1
        return _result_code

    _result_code = 0
    try:
        _result_code = _run_pipeline()
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
