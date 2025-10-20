#!/usr/bin/env python
"""This script is the main entry point for the Jira Importer.

Author:
    Julien (@tom4897)
"""

from __future__ import annotations

# Import libraries
# TODO: Move most used libraries to init
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
from jira_importer.fileops import FileManager
from jira_importer.import_pipeline.processor import ImportProcessor
from jira_importer.import_pipeline.reporting import CloudReportReporter, ProblemReporter, ReportOptions
from jira_importer.import_pipeline.sinks.cloud_sink import write_cloud
from jira_importer.import_pipeline.sinks.csv_sink import write_csv
from jira_importer.log import add_file_logging, setup_logger
from jira_importer.utils import load_config_for_input, open_browser, open_jira_filter

# Global variables
# Warning = Critical = False
debug_mode = False  # pylint: disable=invalid-name


# Suppress specific warnings from openpyxl
warnings.filterwarnings("ignore", category=FutureWarning, module="openpyxl")
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

ui = ConsoleIO.getUI()  # pylint: disable=invalid-name
fmt = ui.fmt  # pylint: disable=invalid-name


# TODO: Move main logic to the app
def main() -> int:
    """Main function for the Jira Importer application."""
    # TODO: Move to cli
    ui.title_banner("Jira Toolkit: Importer 🚀", icon="")
    ui.say(fmt.bold("Authors:"), fmt.default("Julien (@tom4897)"), fmt.default("Alain (@Nakool)"))
    ui.say(fmt.kv("Repository", "https://github.com/deerhide/jira-toolkit"))

    # --- Initialization ---
    ui.lf()
    ui.progress_light("Initializing Jira Importer")
    args = App.parse_args()

    # Handle version flag early, before any configuration loading
    if args.version:
        # Create a minimal config for version display
        class MinimalConfigForVersion:  # pylint: disable=too-few-public-methods
            def get_value(self, key: str, default: Any = None, expected_type: Any = None) -> Any:  # pylint: disable=unused-argument
                return default

        minimal_config = MinimalConfigForVersion()
        artifact_manager = ArtifactManager(minimal_config)
        app = App(artifact_manager)
        app.print_version()
        app.event_close(exit_code=0, cleanup=False)
        return 0

    # Handle config-check mode
    if hasattr(args, "config_check") and args.config_check:
        display_config(args.config_check)
        return 0

    # Handle --credentials mode early (like --version)
    if hasattr(args, "credentials") and args.credentials:
        # For credentials, we need minimal config for resolution but don't require input file
        # Use a minimal config or load default
        try:
            if not hasattr(args, "input_file") or not args.input_file:
                # Provide dummy input_file for config determination
                args.input_file = "dummy.xlsx"
            config_path = determine_config_path(args)
            config = ConfigurationFactory.create_config(config_path, cfg_req=CFG_REQ_DEFAULT)
        except Exception:
            # If config loading fails, use minimal config for keyring/env only
            class MinimalConfigForCredentials:  # pylint: disable=too-few-public-methods
                def get_value(self, key: str, default: Any = None, expected_type: Any = None) -> Any:  # pylint: disable=unused-argument
                    return default

                def get(self, key: str, default: Any = None) -> Any:  # pylint: disable=unused-argument
                    return default

                path = "minimal"

            config = MinimalConfigForCredentials()  # type: ignore

        from .config.config_view import ConfigView
        from .import_pipeline.cloud.credential_manager import (
            clear_credentials,
            display_credential_status,
            get_credential_status,
            setup_credentials_interactive,
        )

        # Create minimal app for event_close
        artifact_manager = ArtifactManager(config)
        app = App(artifact_manager)

        action = args.credentials  # "run"|"show"|"clear"
        cfg_view = ConfigView(config)

        ui.lf()

        if action == "show":
            st = get_credential_status(ui, cfg_view)
            display_credential_status(ui, st)
            app.event_close(exit_code=0, cleanup=False)
            return 0

        if action == "clear":
            clear_credentials(ui)
            app.event_close(exit_code=0, cleanup=False)
            return 0

        # default: run
        try:
            st = setup_credentials_interactive(ui, cfg_view)
            ui.lf()
            ui.success("✓ Credentials configured successfully")
        except Exception as cred_exc:
            ui.error(f"Credential setup failed: {cred_exc}")
            app.event_close(exit_code=1, cleanup=False)
            return 1

        app.event_close(exit_code=0, cleanup=False)
        return 0

    # Respect -y and -n args: set _autoreply True for -y/--yes, False for -n/--no, None otherwise
    if getattr(args, "auto_yes", False):
        autoreply = True
    elif getattr(args, "auto_no", False):
        autoreply = False
    else:
        autoreply = None

    # Determine configuration file path
    config_path = determine_config_path(args)
    config = ConfigurationFactory.create_config(config_path, cfg_req=CFG_REQ_DEFAULT)

    # Initialize logging with CLI override and config support
    setup_logger(logging.DEBUG if args.debug else None, config)
    logger = logging.getLogger(__name__)

    # Add file logging if enabled in config

    add_file_logging(config)

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
    if not Path(xlsx_file).is_file():
        ui.error(
            f"The XLSX file '{xlsx_file}' does not exist or is not a file. Please check the file path and try again."
        )
        logger.error(f"The XLSX file '{xlsx_file}' does not exist or is not a file.")
        App.event_fatal(exit_code=2, message=f"The XLSX file '{xlsx_file}' does not exist or is not a file.")

    in_path = Path(args.input_file)
    if not in_path.exists():
        logger.error("Input path does not exist: %s", in_path)
        ui.error(
            f"The XLSX file '{xlsx_file}' does not exist or is not a file. Please check the file path and try again."
        )
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

    _result_code = 0
    try:
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
            ui.warning("Auto-fix is disabled. Please fix the issues manually.")
            ui.hint(
                "You can enable auto-fix by adding the following to your configuration file or by using the --auto-fix flag."
            )

        if result.report.errors > 0:
            if not ui.prompt_yes_no("Do you want to continue?", default=False, auto_reply=autoreply):
                app.event_abort(exit_code=1, message="User cancelled the Execution.")
            else:
                ui.success("Continuing...")

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
            except Exception as exc:
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

    except Exception as exc:
        logger.exception("Import failed: %s", exc)
        App.event_fatal(exit_code=3, message=f"An exception occurred in the processor, please check the logs: {exc}")
    finally:
        try:
            if mgr is not None:
                mgr.close()
        except Exception:
            pass

    # TODO: Move logic to utils
    if config.get_value("app.import.auto_open_page", default=False, expected_type=bool):
        site_address = config.get_value("jira.connection.site_address", default="", expected_type=str)
        if site_address and "BulkCreateSetupPage" not in site_address:
            site_address += "/secure/BulkCreateSetupPage!default.jspa?externalSystem=com.atlassian.jira.plugins.jim-plugin%3AbulkCreateCsv&new=true"
        open_browser(f"{site_address}")

    ui.lf()
    ui.full_panel(fmt.success("Processing complete. You can close this window now."))
    app.event_close(exit_code=0, cleanup=True)

    return 0


# Main function
if __name__ == "__main__":
    main()
