#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script Name: app.py
Description: This script is the main application for the Jira Importer.
Author: Julien (@tom4897)
License: MIT
Date: 2025
"""

import logging
import sys
import argparse
from rich_argparse import RichHelpFormatter
from .artifacts import ArtifactManager
from .console import ui, fmt

logger = logging.getLogger(__name__)

class App:
    # Class variable to store command line arguments
    _args = None

    def __init__(self, artifact_manager: ArtifactManager):
        self.artifact_manager = artifact_manager

    def event_close(self, exit_code: int = 0, cleanup: bool = True) -> None:
        if cleanup:
            self.artifact_manager.delete_all()
        logger.info("Jira Importer finished.")
        sys.exit(exit_code)

    def event_abort(self, exit_code: int = -1) -> None:
        ui.error("You have aborted the script.")
        logger.critical("Aborted script.")
        self.event_close(exit_code=exit_code)

    @staticmethod
    def event_fatal(exit_code: int = -1, message: str = "Fatal error!") -> None:
        logger.debug("event_fatal")

        # Show arguments if available
        if App._args:
            logger.critical("Script failed with the following arguments:")
            logger.critical(f"  Input file: {App._args.input_file}")
            logger.critical(f"  Configuration: {App._args.config}")
            logger.critical(f"  Debug mode: {App._args.debug}")
            #logging.critical(f"  Import to cloud: {App._args.import_to_cloud}")
            if App._args.config_default:
                logger.critical(f"  Config default: {App._args.config_default}")
            if App._args.config_input:
                logger.critical(f"  Config input: {App._args.config_input}")
            if App._args.version:
                logger.critical(f"  Version: {App._args.version}")
            logger.critical(f" args: {App._args}")
            ui.error("Fatal event raised!")
            _str = "\n" + fmt.kv("Input file", fmt.path(App._args.input_file)) + "\n"
            _str += fmt.kv("Configuration", fmt.path(App._args.config)) + "\n"
            _str += fmt.kv("Debug mode", App._args.debug) + "\n"
            _str += fmt.kv("Version", App._args.version) + "\n"
            _str += fmt.kv("Config default", App._args.config_default) + "\n"
            _str += fmt.kv("Config input", App._args.config_input) + "\n"
            for arg in App._args.__dict__:
                _str += fmt.kv(arg, App._args.__dict__[arg]) + "\n"
            ui.panel("Script failed with the following arguments:", _str)

        logger.critical(message)
        sys.exit(exit_code)

    @staticmethod
    def parse_args() -> argparse.Namespace:
        parser = argparse.ArgumentParser(
            prog="jira-importer",
            description="This script formats a CSV file for Jira import, validating and correcting data according to specified rules.",
            formatter_class=RichHelpFormatter,
            epilog="""
            Example:
            jira-importer dataset.xlsx -c config_importer.json -d -y
            """,
        )
        parser.add_argument("input_file", help="Excel XLSX file", default='import.xlsx')

        config_group = parser.add_mutually_exclusive_group()
        config_group.add_argument("-c", "--config", help="Configuration file path", default='config_importer.json', type=str)
        config_group.add_argument("-ci", "--config-input", help="Get the configuration path from the input file location", action='store_true')
        config_group.add_argument("-cd", "--config-default", help="Get the configuration path from the application location", action='store_true')

        # TODO: Add output group
        #output_group = parser.add_mutually_exclusive_group()
        #output_group.add_argument("-o", "--out", default=None, help="Output CSV path (default: <input>.processed.csv)")
        #output_group.add_argument("-od", "--out-default", default=None, help="Output CSV path in the application location (default: <input>.processed.csv)", action='store_true')
        #output_group.add_argument("-oi", "--out-input", default=None, help="Output CSV path in the input file location (default: <input>.processed.csv)", action='store_true')
        #output_group.add_argument("-oc", "--out-current", default=None, help="Output CSV path in the current directory", action='store_true')

        auto_yes_group = parser.add_mutually_exclusive_group()
        auto_yes_group.add_argument("-y", "-f", "--auto-yes", default=None, action="store_true", help="Auto-yes all prompts")
        auto_yes_group.add_argument("-n", "--auto-no", default=None, action="store_true", help="Auto-no all prompts")

        parser.add_argument("--data-sheet", default="Dataset", help="XLSX data sheet name (default: Dataset)")
        parser.add_argument("--enable-excel-rules", default=False, action="store_true",
                   help="Enable loading rules from Excel (scaffold only; safe to leave off).")
        parser.add_argument("--auto-fix", default=False, action="store_true",
                   help="Enable safe auto-fixes (priority normalization, estimates, project key, etc.).")
        parser.add_argument("--no-report", action="store_true", help="Do not print the validation report.")

        parser.add_argument("--fix-cloud-estimates", default=False, action="store_true",
                   help="Apply Jira Cloud ×60 estimate quirk IN THE SINK (kept out of rules/fixes).")

        parser.add_argument("-v", "--version", help="Show version", action='store_true')
        parser.add_argument("-d", "--debug", help="Enable debug mode", action='store_true')
        #parser.add_argument("-i", "--import-to-cloud", dest="import_to_cloud", help="Import to Atlassian Cloud via the API", default='none')

        args = parser.parse_args()
        # Store args in class variable for access by event_fatal
        App._args = args
        return args
