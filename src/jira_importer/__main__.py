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

from jira_importer import CFG_REQ_DEFAULT, DEFAULT_CONFIG_FILENAME

# Import classes
from jira_importer.app import App
from jira_importer.artifacts import ArtifactManager
from jira_importer.config.config_display import display_config_content, display_table_config
from jira_importer.config.config_factory import ConfigurationFactory
from jira_importer.console import ConsoleIO
from jira_importer.excel.excel_io import ExcelWorkbookManager
from jira_importer.fileops import FileManager
from jira_importer.import_pipeline.processor import ImportProcessor
from jira_importer.import_pipeline.reporting import CloudReportReporter, ProblemReporter, ReportOptions
from jira_importer.import_pipeline.sinks.cloud_sink import write_cloud
from jira_importer.import_pipeline.sinks.csv_sink import write_csv
from jira_importer.log import add_file_logging, setup_logger
from jira_importer.utils import find_config_path, open_browser

# Global variables
# Warning = Critical = False
debug_mode = False  # pylint: disable=invalid-name


# Suppress specific warnings from openpyxl
warnings.filterwarnings("ignore", category=FutureWarning, module="openpyxl")
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

ui = ConsoleIO.getUI()  # pylint: disable=invalid-name
fmt = ui.fmt  # pylint: disable=invalid-name


def _determine_config_path(args: Any) -> str:
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


def _display_config(config_file: str) -> None:
    """Display configuration from the specified file in a user-friendly format.

    Args:
        config_file: Path to the configuration file to display
    """
    setup_logger(logging.DEBUG, None)  # Use debug level for config check
    logger = logging.getLogger(__name__)

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
        ui.success("Configuration check completed successfully!")
        logger.info("Configuration check completed successfully!")

    except Exception as exc:
        logger.error(f"Configuration check failed: {exc}")
        App.event_fatal(exit_code=1, message=f"Failed to load configuration: {exc}")


def _load_config_for_input(in_path: Path, data_sheet: str) -> tuple[Any, ExcelWorkbookManager | None]:  # pylint: disable=unused-argument
    """Return (config_like, excel_manager_or_None).

    - For XLSX input, read 'Config' via ExcelWorkbookManager (keeps things generic).
    - For CSV input, return {} (you can replace this with your own config loader).
    """
    if in_path.suffix.lower() in {".xlsx", ".xlsm"}:
        mgr = ExcelWorkbookManager(in_path)
        mgr.load()
        cfg = mgr.read_config(sheet="Config")
        # ImportProcessor will also create/use a manager for meta/report writing.
        return cfg, mgr
    return {}, None


# TODO: Move to utils
def _default_out_path(in_path: Path) -> Path:
    return Path(f"{in_path.stem}_jira_ready.csv")


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
        class MinimalConfig:  # pylint: disable=too-few-public-methods
            def get_value(self, key: str, default: Any = None, expected_type: Any = None) -> Any:  # pylint: disable=unused-argument
                return default

        minimal_config = MinimalConfig()
        artifact_manager = ArtifactManager(minimal_config)
        app = App(artifact_manager)
        app.print_version()
        app.event_close(exit_code=0, cleanup=False)
        return 0

    # Handle config-check mode
    if hasattr(args, "config_check") and args.config_check:
        _display_config(args.config_check)
        return 0

    # Respect -y and -n args: set _autoreply True for -y/--yes, False for -n/--no, None otherwise
    if getattr(args, "auto_yes", False):
        autoreply = True
    elif getattr(args, "auto_no", False):
        autoreply = False
    else:
        autoreply = None

    # Determine configuration file path
    config_path = _determine_config_path(args)
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

    _, mgr = _load_config_for_input(in_path, args.data_sheet)

    ui.success_light("Input file is valid")

    # --- Processing Dataset file ---
    ui.lf()
    ui.progress_light("Processing CSV file for Jira Import")

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
                app.event_abort(exit_code=1)
            else:
                ui.success("Continuing...")

        # Determine output target strictly from CLI: --cloud implies cloud, otherwise csv
        output_target = "csv"
        if getattr(args, "output_target_cloud", False):
            output_target = "cloud"

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
        App.event_fatal(exit_code=3, message=f"Import failed: {exc}")
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
