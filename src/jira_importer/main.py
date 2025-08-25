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
import warnings
import pandas as pd
import os
import sys
import logging
from tqdm import tqdm

from console import ConsoleUI, fmt, ui

# Global variables
Warning = Critical = False
cfg_req = 1
debug_mode = False

# Import classes
from app import App
from config import Configuration
from artifacts import ArtifactManager
from fileops import FileManager
from userio import UserIO
from log import is_debug_mode, setup_logger
from utils import resource_path, find_config_path
from csvprocessor import CSVProcessor

# Suppress specific warnings from openpyxl
warnings.filterwarnings("ignore", category=FutureWarning, module="openpyxl")
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

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
    elif args.config_input:
        # Use default config filename in input file location
        config_path = find_config_path('config_importer.json', args.input_file, config_input=True)
    else:
        # Use specified config file with default search behavior
        config_path = find_config_path(args.config, args.input_file)

    config = Configuration(config_path, cfg_req=cfg_req)

    # Initialize logging with CLI override and config support
    setup_logger(logging.DEBUG if args.debug else None, config)

    # Add file logging if enabled in config
    from log import add_file_logging
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


    #if args.import_to_cloud == 'none':
    #    logging.info("Import to Atlassian Cloud via the API is disabled.")
    #else:
    #    logging.info(f"Import to Atlassian Cloud via the API: {args.import_to_cloud}")

    logging.debug("Jira Importer initialized.")
    logging.debug(f"Configuration loaded: {config.path}")
    logging.debug(f"Artifact manager initialized: {artifact_manager.delete_enabled.__class__}")
    logging.debug(f"File manager initialized: {file_manager.artifact_manager.__class__}")
    logging.debug(f"User interaction initialized: {user_prompt.__class__}")
    logging.debug(f"App initialized: {app.__class__}")
    logging.debug(f"Debug mode: {is_debug_mode()}")
    logging.debug(f"Input file: {args.input_file}")
    logging.debug(f"Configuration file: {config_path}")

    xlsx_file = args.input_file
    #if os.path.isdir(xlsx_file):
    #    ui.error(f"The XLSX file '{xlsx_file}' is a directory. Please check the file path and try again.")
    #    logging.error(f"The XLSX file '{xlsx_file}' is a directory. Please check the file path and try again.")
    #    App.event_fatal()

    if not os.path.isfile(xlsx_file):
        ui.error(f"The XLSX file '{xlsx_file}' does not exist or is not a file. Please check the file path and try again.")
        logging.error(f"The XLSX file '{xlsx_file}' does not exist or is not a file.")
        App.event_fatal()


    # Convert XLSX to CSV
    ui.lf()
    ui.title_h2("Converting XLSX file to CSV")

    csv_raw = file_manager.generate_output_filename(xlsx_file, file_extension='csv', suffix='')
    logging.debug(f"XLSX: '{os.path.abspath(xlsx_file)}'")
    logging.debug(f"CSV: '{os.path.abspath(csv_raw)}'")
    file_manager.xlsx_to_csv(xlsx_file, csv_raw)

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
