#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script Name: utils.py
Description: This script contains utility functions for the Jira Importer.
Author: Julien (@tom4897)
License: MIT
Date: 2025
"""

import logging
import sys
import os
import colorlog


def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)  # type: ignore
    return os.path.join(os.path.abspath("."), relative_path)
# Usage: config_path = resource_path('config_importer.json')

def find_config_path(config_filename, input_file_path=None, config_default=False, config_input=False):
    search_paths = []
    
    if config_input:
        if input_file_path:
            search_paths.append(os.path.join(os.path.dirname(os.path.abspath(input_file_path)), config_filename))
        else:
            logging.warning("config-input specified but no input file path provided")
            return config_filename
    elif config_default:
        search_paths.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), config_filename))
    else:
        if input_file_path:
            search_paths.append(os.path.join(os.path.dirname(os.path.abspath(input_file_path)), config_filename))
        search_paths.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), config_filename))
    
    logging.debug(f"Searching for configuration file in: {search_paths}")
    for path in search_paths:
        if os.path.isfile(path):
            logging.debug(f"Found configuration file: {path}")
            return path
    
    logging.warning(f"Configuration file '{config_filename}' not found in expected locations. Using default path.")
    logging.warning(f"Expected locations: {search_paths}")
    return config_filename