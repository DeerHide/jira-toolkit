#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script Name: config.py
Description: This script loads and validates the configuration file for the Jira Importer.
Author: Julien (@tom4897)
License: MIT
Date: 2025
"""

import logging
import os
import json
from app import App

class Configuration:
    def __init__(self, path='config_importer.json', cfg_req=1):
        logging.debug(f"Loading configuration from {path}")
        if not os.path.isfile(path):
            logging.error(f"The provided path '{path}' is not a valid file path.")
            raise ValueError(f"Invalid file path: {path}")
        self.path = path
        self.content = self._load_config()
        self.cfg_req = cfg_req
        if self.version_check():
            logging.fatal("Wrong file config version or missing version key.")
            raise RuntimeError("Wrong file config version or missing version key.")
        logging.debug(f"Configuration content: {self.content}")

    def version_check(self):
        # Check for new structure first
        if 'metadata' in self.content:
            cfg_version = self.content.get('metadata', {}).get('version')
        else:
            # Fallback to old structure
            cfg_version = self.get_value("app.config.version")
        
        logging.debug(f"Config version: {cfg_version} ({self.cfg_req} needed)")
        if cfg_version is None:
            logging.error("Missing version in configuration.")
            return True
        if not isinstance(cfg_version, (int, str)):
            logging.error("Invalid version format in configuration.")
            return True
        try:
            return int(cfg_version) < self.cfg_req
        except (ValueError, TypeError):
            logging.error("Invalid version format in configuration.")
            return True

    def _load_config(self):
        logging.debug(f"Reading configuration file: {self.path}")
        try:
            with open(self.path, 'r') as config_file:
                return json.load(config_file)
        except json.JSONDecodeError as e:
            logging.error(f"The JSON file '{self.path}' is not correctly formatted. Error: {e}")
            return {}
        except Exception as e:
            logging.error(f"Error reading configuration file '{self.path}': {e}")
            return {}

    def get_value(self, key):
        # Handle new nested structure
        if 'metadata' in self.content:
            return self._get_nested_value(key)
        else:
            # Fallback to old flat structure
            return self.content.get(key, None)
    
    def _get_nested_value(self, key):
        keys = key.split('.')
        current = self.content
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        
        return current
