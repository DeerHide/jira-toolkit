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
    setup_logger()
    args = App.parse_args()
    
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
    artifact_manager = ArtifactManager(config)
    file_manager = FileManager(artifact_manager)
    user_prompt = UserIO()
    app = App(artifact_manager)

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.version:
        user_prompt.show_message("Jira Importer v1.0.0")
        app.event_close(exit_code=0, cleanup=False)

    logging.info(f"Input file: {args.input_file}")
    logging.info(f"Configuration file: {config_path}")

    #if args.import_to_cloud == 'none':
    #    logging.info("Import to Atlassian Cloud via the API is disabled.")
    #else:
    #    logging.info(f"Import to Atlassian Cloud via the API: {args.import_to_cloud}")

    logging.debug("Jira Importer started.")
    logging.debug(f"Configuration loaded: {config.path}")
    logging.debug(f"Artifact manager initialized: {artifact_manager.delete_enabled.__class__}")
    logging.debug(f"File manager initialized: {file_manager.artifact_manager.__class__}")
    logging.debug(f"User interaction initialized: {user_prompt.__class__}")
    logging.debug(f"App initialized: {app.__class__}")
    logging.debug(f"Debug mode: {is_debug_mode()}")
    logging.debug(f"Input file: {args.input_file}")
    logging.debug(f"Configuration file: {config_path}")

    xlsx_file = args.input_file
    if os.path.isdir(xlsx_file):
        logging.error(f"The XLSX file '{xlsx_file}' is a directory. Please check the file path and try again.")
        App.event_fatal()

    if not os.path.isfile(xlsx_file):
        logging.error(f"The XLSX file '{xlsx_file}' does not exist. Please check the file path and try again.")
        App.event_fatal()

    csv_raw = file_manager.generate_output_filename(xlsx_file, file_extension='csv', suffix='')
    logging.info(f"Converting XLSX file to CSV")
    logging.debug(f"XLSX: '{os.path.abspath(xlsx_file)}'")
    logging.debug(f"CSV: '{os.path.abspath(csv_raw)}'")
    file_manager.xlsx_to_csv(xlsx_file, csv_raw)

    logging.info(f"Formatting CSV file for Jira Import: '{os.path.abspath(csv_raw)}'")
    if not os.path.isfile(csv_raw):
        logging.error(f"The CSV file '{csv_raw}' does not exist. Please check the XLSX file path and try again.")
        App.event_fatal()

    logging.info(f"Started processing '{os.path.abspath(csv_raw)}'")

    csv_jira = CSVProcessor(csv_raw, config)
    
    # Show validation report after processing
    csv_jira.show_report()
    
    #pause = generate_report(csv_jira)
    pause = csv_jira.has_errors_or_warnings()

    if pause:
        if not user_prompt.get_yes_no("Do you want to continue and write the formatted dataset? (yes/no): "):
            app.event_abort()

    if not csv_jira.data:
        logging.error("No data to write to Jira.")
        app.event_close(exit_code=1)

    #if args.import_to_cloud == 'none':
    #    logging.info("Import to Atlassian Cloud via the API is disabled.")
    #else:
    #    logging.info(f"Import to Atlassian Cloud via the API: {args.import_to_cloud}")
        
    csv_jira_output = file_manager.generate_output_filename(csv_raw, file_extension='csv', suffix='_JiraReady')

    logging.info(f"Writing file...")
    file_manager.write_csv_file(csv_jira_output, csv_jira, is_artifact=False)
    logging.info(f"Formatted CSV file written to: ")
    logging.info(f"{os.path.abspath(csv_jira_output)}")

    if config.get_value('app.import.auto_open_page'):
        site_address = config.get_value('jira.connection.site_address')
        if not 'BulkCreateSetupPage' in site_address:
            site_address += '/secure/BulkCreateSetupPage!default.jspa?externalSystem=com.atlassian.jira.plugins.jim-plugin%3AbulkCreateCsv&new=true'
        UserIO.open_browser(f"{site_address}")
        
    logging.info("Processing complete. You can close this window now.")
    app.event_close(exit_code=0, cleanup=True)

# Main function
if __name__ == "__main__":
    main()