#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script Name: artifacts.py
Description: This script manages the artifacts for the Jira Importer.
Author: Julien (@tom4897)
License: MIT
Date: 2025
"""

import logging
import os

class ArtifactManager:
    def __init__(self, config):
        self.artifacts = []
        self.delete_enabled = config.get_value('app.artifacts.delete_enabled')

    def add(self, file_path):
        if file_path and file_path not in self.artifacts:
            self.artifacts.append(file_path)
            logging.debug(f"Artifact added: {file_path}")

    def delete_all(self):
        if not self.delete_enabled:
            logging.info("Artifact deletion is disabled in configuration.")
            return
        for artifact in self.artifacts:
            if os.path.isfile(artifact):
                try:
                    os.remove(artifact)
                    logging.info(f"Deleted artifact: {artifact}")
                except Exception as e:
                    logging.error(f"Failed to delete artifact '{artifact}': {e}")
            else:
                logging.warning(f"Artifact '{artifact}' does not exist.")
        self.artifacts.clear()
        logging.debug("All artifacts deleted.")
