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

class App:
    # Class variable to store command line arguments
    _args = None
    
    def __init__(self, artifact_manager):
        self.artifact_manager = artifact_manager

    def event_close(self, exit_code=0, cleanup=True):
        if cleanup:
            self.artifact_manager.delete_all()
        logging.info("Jira Importer finished.")
        sys.exit(exit_code)

    def event_abort(self, exit_code=-1):
        logging.debug("event_abort")
        
        logging.fatal("Aborted script.")
        self.event_close(exit_code=exit_code)

    @staticmethod
    def event_fatal(exit_code=-1):
        logging.debug("event_fatal")
        
        # Show arguments if available
        if App._args:
            logging.critical("Script failed with the following arguments:")
            logging.critical(f"  Input file: {App._args.input_file}")
            logging.critical(f"  Configuration: {App._args.config}")
            logging.critical(f"  Debug mode: {App._args.debug}")
            #logging.critical(f"  Import to cloud: {App._args.import_to_cloud}")
            if App._args.config_default:
                logging.critical(f"  Config default: {App._args.config_default}")
            if App._args.config_input:
                logging.critical(f"  Config input: {App._args.config_input}")
            if App._args.version:
                logging.critical(f"  Version: {App._args.version}")
            logging.critical(f" args: {App._args}")
        
        logging.critical("Fatal error.")
        sys.exit(exit_code)

    @staticmethod
    def parse_args():
        parser = argparse.ArgumentParser(description="This script formats a CSV file for Jira import, validating and correcting data according to specified rules.", formatter_class=argparse.RawTextHelpFormatter)
        parser.add_argument("input_file", help="Excel XLSX file", default='import.xlsx')
        
        config_group = parser.add_mutually_exclusive_group()
        config_group.add_argument("-c", "--config", help="Configuration file path", default='config_importer.json')
        config_group.add_argument("-cd", "--config-default", help="Get the configuration path from the application location", action='store_true')
        config_group.add_argument("-ci", "--config-input", help="Get the configuration path from the input file location", action='store_true')
        
        parser.add_argument("-d", "--debug", help="Enable debug mode", action='store_true')
        parser.add_argument("-v", "--version", help="Show version", action='store_true')
        #parser.add_argument("-i", "--import-to-cloud", dest="import_to_cloud", help="Import to Atlassian Cloud via the API", default='none')

        args = parser.parse_args()
        # Store args in class variable for access by event_fatal
        App._args = args
        return args