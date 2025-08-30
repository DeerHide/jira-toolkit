#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script Name: main.py
Description: This script is the main entry point for the Jira Importer.
Author: Julien (@tom4897)
License: MIT
Date: 2025
"""

# Import libraries
# TODO: Move most used libraries to init
from pathlib import Path
from typing import Any
import warnings
import pandas as pd
import os
import sys
import logging
from tqdm import tqdm

# Global variables
# TODO: Move to init
Warning = Critical = False
cfg_req = 1
debug_mode = False

# Import classes
from .console import ConsoleUI, fmt, ui
from .excel_io import ExcelWorkbookManager

from .app import App
from .config import Configuration
from .artifacts import ArtifactManager
from .fileops import FileManager

from .log import is_debug_mode, setup_logger, add_file_logging
from .utils import resource_path, find_config_path, open_browser
from .import_pipeline.processor import ImportProcessor
from .import_pipeline.reporting import ProblemReporter, ReportOptions
from .import_pipeline.sinks.csv_sink import write_csv

# Suppress specific warnings from openpyxl
warnings.filterwarnings("ignore", category=FutureWarning, module="openpyxl")
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

# TODO: Add a loading config for the excel file in the excel_io.py file
# TODO: Move to utils
def _load_config_for_input(in_path: Path, data_sheet: str) -> tuple[Any, ExcelWorkbookManager | None]:
    """
    Return (config_like, excel_manager_or_None).

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
    return f"{in_path.stem}_jira_ready.csv"

# TODO: Move main logic to the app
def main():
    """Main function for the Jira Importer application."""
    # TODO: Move to cli
    ui.title_banner("Jira Toolkit: Importer 🚀", icon="")
    ui.say("Authors:", fmt.default("Julien (@tom4897)"), ", ", fmt.default("Alain (@Nakool)"))
    ui.say(fmt.kv("License", "MIT"))
    ui.say(fmt.kv("Version", "1.0.0"))

    # --- Initialization ---
    ui.lf()
    ui.progress_light("Initializing Jira Importer")
    args = App.parse_args()

    # Handle mutually exclusive configuration arguments
    if args.config_default:
        # Use default config filename in script location
        config_path = find_config_path('config_importer.json', args.input_file, config_default=True)
        logging.debug(f"config_default: {config_path}")
    elif args.config_input:
        # Use default config filename in input file location
        config_path = find_config_path('config_importer.json', args.input_file, config_input=True)
        logging.debug(f"config_input: {config_path}")
    else:
        # Use specified config file with default search behavior
        config_path = find_config_path(args.config, args.input_file)
        logging.debug(f"!config_default & !config_input: {config_path}")

    config = Configuration(config_path, cfg_req=cfg_req)

    # Initialize logging with CLI override and config support
    setup_logger(logging.DEBUG if args.debug else None, config)
    logger = logging.getLogger(__name__)

    # Add file logging if enabled in config
    from .log import add_file_logging
    add_file_logging(config)

    if logging.getLogger().level == logging.DEBUG:
        ui.debug("Debug mode is enabled.")

    artifact_manager = ArtifactManager(config)
    file_manager = FileManager(artifact_manager, config)
    app = App(artifact_manager)

    if args.version:
        ui.say("Jira Importer v1.0.0")
        app.event_close(exit_code=0, cleanup=False)

    logger.info(f"Input: {args.input_file}")
    ui.say(f"Excel file: {fmt.path(args.input_file)}")
    logger.info(f"Config: {config_path}")
    ui.say(f"Configuration file: {fmt.path(config_path)}")

    logger.debug("Jira Importer initialized.")
    logger.debug(f"Configuration loaded: {config.path}")
    logger.debug(f"Debug mode: {is_debug_mode()}")
    logger.debug(f"Input file: {args.input_file}")
    logger.debug(fmt.kv("Input file", fmt.path(App._args.input_file)))
    logger.debug(fmt.kv("Configuration", fmt.path(App._args.config)))
    logger.debug(fmt.kv("Debug mode", App._args.debug))
    logger.debug(fmt.kv("Version", App._args.version))
    logger.debug(fmt.kv("Config default", App._args.config_default))
    logger.debug(fmt.kv("Config input", App._args.config_input))
    logger.debug(fmt.kv("args", App._args))

    ui.success_light("Jira Importer initialized")

    # --- Checking input file ---
    ui.lf()
    ui.progress_light("Checking input file")

    xlsx_file = args.input_file
    if not os.path.isfile(xlsx_file):
        ui.error(f"The XLSX file '{xlsx_file}' does not exist or is not a file. Please check the file path and try again.")
        logger.error(f"The XLSX file '{xlsx_file}' does not exist or is not a file.")
        App.event_fatal(exit_code=2, message=f"The XLSX file '{xlsx_file}' does not exist or is not a file.")

    in_path = Path(args.input_file)
    if not in_path.exists():
        logger.error("Input path does not exist: %s", in_path)
        ui.error(f"The XLSX file '{xlsx_file}' does not exist or is not a file. Please check the file path and try again.")
        return 2

    out_path = file_manager.generate_output_filename(xlsx_file, file_extension='csv', suffix='_jira_ready')
    logger.debug(f"out_path: {out_path}")

    config_field, mgr = _load_config_for_input(in_path, args.data_sheet)

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
        logger.debug(f"Processor:\n{processor.path}\nconfig: {processor.config}\nenable_excel_rules: {processor.enable_excel_rules}\nexcel_rules_source: {processor.excel_rules_source}\nenable_auto_fix: {processor.enable_auto_fix}")

        result = processor.process()

        # Report
        # TODO: Extract as a function
        if not args.no_report:
            ProblemReporter(options=ReportOptions(show_details=True, show_aggregate_by_code=False)).render(result)
        else:
            ProblemReporter(options=ReportOptions(show_details=False, show_aggregate_by_code=True)).render(result)

        if (not processor.enable_auto_fix):
            ui.warning(f"Auto-fix is disabled. Please fix the issues manually.")
            ui.hint(f"You can enable auto-fix by adding the following to your configuration file or by using the --auto-fix flag.")

        if result.report.errors > 0:

            if args.auto_yes:
                ui.success("-y or --auto-yes flag is set. Continuing...")
            elif args.auto_no:
                ui.error("-n or --auto-no flag is set. Aborting...")
                app.event_abort(exit_code=1)
            else:
                if not ui.prompt_yes_no("Do you want to continue?", default=False):
                    app.event_abort(exit_code=1)
                else:
                    ui.success("Continuing...")

        # Apply Jira Cloud ×60 quirk in the SINK if requested
        if args.fix_cloud_estimates:
            if isinstance(config, dict):
                config = {**config, "jira.cloud.estimate.multiply_by_60": True}
            else:
                # minimal dict-like wrapper if config isn't a dict
                class _Cfg(dict):
                    def get(self, k, d=None):  # type: ignore[override]
                        return super().get(k, d)
                temp = _Cfg()
                temp.update({"jira.cloud.estimate.multiply_by_60": True})
                config = temp

        write_csv(result, out_path, config=config)

        ui.say(f"Output Import CSV Ready → {fmt.path(out_path)}")
        logger.info("Wrote output CSV → %s", out_path)

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
    if config.get_value('app.import.auto_open_page', default=False, expected_type=bool):
        site_address = config.get_value('jira.connection.site_address', default='', expected_type=str)
        if not 'BulkCreateSetupPage' in site_address:
            site_address += '/secure/BulkCreateSetupPage!default.jspa?externalSystem=com.atlassian.jira.plugins.jim-plugin%3AbulkCreateCsv&new=true'
        open_browser(f"{site_address}")

    ui.lf()
    ui.full_panel(fmt.success("Processing complete. You can close this window now."))
    app.event_close(exit_code=0, cleanup=True)

    return 0

# Main function
if __name__ == "__main__":
    main()
