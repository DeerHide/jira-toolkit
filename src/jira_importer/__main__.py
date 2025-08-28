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
from pathlib import Path
from typing import Any
import warnings
import pandas as pd
import os
import sys
import logging
from tqdm import tqdm

# Global variables
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
from .userio import UserIO
from .log import is_debug_mode, setup_logger, add_file_logging
from .utils import resource_path, find_config_path
from .csvprocessor import CSVProcessor
from .import_pipeline.processor import ImportProcessor
from .import_pipeline.reporting import ProblemReporter, ReportOptions
from .import_pipeline.sinks.csv_sink import write_csv

# Suppress specific warnings from openpyxl
warnings.filterwarnings("ignore", category=FutureWarning, module="openpyxl")
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

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

def _default_out_path(in_path: Path) -> Path:
    return f"{in_path.stem}_jira_ready.csv"

def main():
    """Main function for the Jira Importer application."""
    args = App.parse_args()
    ui.title_banner("Jira Toolkit: Importer 🚀", icon="")
    ui.say("Authors:", fmt.default("Julien (@tom4897)"), ", ", fmt.default("Alain (@Nakool)"))
    ui.say(fmt.kv("License", "MIT"))
    ui.say(fmt.kv("Version", "1.0.0"))

    ui.lf()
    ui.title_h2("Initializing Jira Importer")

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

    # Add file logging if enabled in config
    from .log import add_file_logging
    add_file_logging(config)

    if logging.getLogger().level == logging.DEBUG:
        ui.debug("Debug mode is enabled.")

    artifact_manager = ArtifactManager(config)
    file_manager = FileManager(artifact_manager, config)
    user_prompt = UserIO()
    app = App(artifact_manager)

    if args.version:
        ui.say("Jira Importer v1.0.0")
        app.event_close(exit_code=0, cleanup=False)

    logging.info(f"Input: {args.input_file}")
    ui.say(f"Excel file: {fmt.path(args.input_file)}")
    logging.info(f"Config: {config_path}")
    ui.say(f"Configuration file: {fmt.path(config_path)}")

    logging.debug("Jira Importer initialized.")
    logging.debug(f"Configuration loaded: {config.path}")
    logging.debug(f"Debug mode: {is_debug_mode()}")
    logging.debug(f"Input file: {args.input_file}")
    logging.debug(fmt.kv("Input file", fmt.path(App._args.input_file)))
    logging.debug(fmt.kv("Configuration", fmt.path(App._args.config)))
    logging.debug(fmt.kv("Debug mode", App._args.debug))
    logging.debug(fmt.kv("Version", App._args.version))
    logging.debug(fmt.kv("Config default", App._args.config_default))
    logging.debug(fmt.kv("Config input", App._args.config_input))
    logging.debug(fmt.kv("args", App._args))

    xlsx_file = args.input_file
    if not os.path.isfile(xlsx_file):
        ui.error(f"The XLSX file '{xlsx_file}' does not exist or is not a file. Please check the file path and try again.")
        logging.error(f"The XLSX file '{xlsx_file}' does not exist or is not a file.")
        App.event_fatal()


    # Convert XLSX to CSV
    ui.lf()
    ui.title_h2("Converting XLSX file to CSV")

    in_path = Path(args.input_file)
    if not in_path.exists():
        logging.error("Input path does not exist: %s", in_path)
        ui.error(f"The XLSX file '{xlsx_file}' does not exist or is not a file. Please check the file path and try again.")
        return 2

    out_path = file_manager.generate_output_filename(xlsx_file, file_extension='csv', suffix='_jira_ready')
    logging.debug(f"out_path: {out_path}")

    config, mgr = _load_config_for_input(in_path, args.data_sheet)

    # Process the CSV file
    ui.lf()
    ui.title_h2("Processing CSV file for Jira Import")
    try:
        processor = ImportProcessor(
            path=in_path,
            config=config,
            ui=None,  # pipeline is UI-agnostic; reporting handled below
            enable_excel_rules=args.enable_excel_rules,
            excel_rules_source=str(in_path) if args.enable_excel_rules else None,
            enable_auto_fix=args.auto_fix,
        )
        logging.debug(f"Processor:\n{processor.path}\nconfig: {processor.config}\nenable_excel_rules: {processor.enable_excel_rules}\nexcel_rules_source: {processor.excel_rules_source}\nenable_auto_fix: {processor.enable_auto_fix}")

        result = processor.process()

        # Report
        if not args.no_report:
            ProblemReporter(options=ReportOptions(show_details=True, show_aggregate_by_code=True)).render(result)

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
        logging.info("Wrote output CSV → %s", out_path)

        # non-zero exit if there were errors (so CI can gate)
        return 0 if result.report.errors == 0 else 1

    except Exception as exc:
        logging.exception("Import failed: %s", exc)
        App.event_fatal(exit_code=3)
    finally:
        try:
            if mgr is not None:
                mgr.close()
        except Exception:
            pass

    return 0
    csv_raw = file_manager.generate_output_filename(xlsx_file, file_extension='csv', suffix='')
    logging.debug(f"XLSX: '{os.path.abspath(xlsx_file)}'")
    logging.debug(f"CSV: '{os.path.abspath(csv_raw)}'")
    excel_manager = ExcelWorkbookManager(xlsx_file)
    file_manager.xlsx_to_csv(xlsx_file, csv_raw, dataset_sheet_name='dataset', ui=ui, artifact_cb=artifact_manager.add, manager=excel_manager)
    excel_manager.close()

    logging.info(f"Formatting CSV file for Jira Import: '{os.path.abspath(csv_raw)}'")
    if not os.path.isfile(csv_raw):
        ui.error(f"The CSV file '{csv_raw}' wasn't created. Please check the XLSX file path and try again.")
        logging.error(f"Missing '{csv_raw}'")
        App.event_fatal()

    logging.info(f"Started processing '{os.path.abspath(csv_raw)}'")


    # processing the CSV file
    ui.lf()
    ui.title_h2("Processing CSV file for Jira Import")

    csv_jira = CSVProcessor(csv_raw, config)

    # Show validation report after processing
    csv_jira.show_report()

    if csv_jira.problems_found():
        ui.warning("The CSVProcessor has found errors or warnings in the input CSV file.")
        ui.hint("You can review the report to decide whether these are blockers or not before continuing.")
        ui.hint("Check your excel file and configuration if you see false positives.")
        if not ui.prompt_yes_no("Do you want to continue?", default=False):
            app.event_abort(exit_code=1)
        else:
            ui.success("Continuing...")

    if not csv_jira.data:
        ui.error("No data to write to Jira.")
        logging.error("CSV file is empty.")
        app.event_close(exit_code=1, cleanup=False)

    #if args.import_to_cloud == 'none':
    #    logging.info("Import to Atlassian Cloud via the API is disabled.")
    #else:
    #    logging.info(f"Import to Atlassian Cloud via the API: {args.import_to_cloud}")

    csv_jira_output = file_manager.generate_output_filename(csv_raw, file_extension='csv', suffix='_JiraReady')

    # Write the formatted CSV file to the output directory
    ui.lf()
    ui.title_h2("Writing CSV file to Jira")
    ui.say(f"Destination: {fmt.path(csv_jira_output)}")
    logging.info(f"Writing to: {os.path.abspath(csv_jira_output)}")
    file_manager.write_csv_file(csv_jira_output, csv_jira, is_artifact=False)

    if config.get_value('app.import.auto_open_page', default=False, expected_type=bool):
        site_address = config.get_value('jira.connection.site_address', default='', expected_type=str)
        if not 'BulkCreateSetupPage' in site_address:
            site_address += '/secure/BulkCreateSetupPage!default.jspa?externalSystem=com.atlassian.jira.plugins.jim-plugin%3AbulkCreateCsv&new=true'
        user_prompt.open_browser(f"{site_address}")

    ui.lf()
    ui.full_panel(fmt.success("Processing complete. You can close this window now."))
    app.event_close(exit_code=0, cleanup=True)

# Main function
if __name__ == "__main__":
    main()
