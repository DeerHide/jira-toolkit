#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Build utilities for the Jira Importer build system.

Author: Julien (@tom4897)
License: MIT
Date: 2025
"""

import os
import subprocess
import sys
import logging
from pathlib import Path


class BuildUtils:
    def __init__(self, context=None):
        self.context = context
        if context:
            self.sign_config = self.context.cfg["code_signing"]
        self._logger = self._setup_logger()

    def _setup_logger(self):
        """Setup a simple logger for consistent output."""
        logger = logging.getLogger(f"{__name__}.BuildUtils")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def sign_executable(self, executable_path: str) -> bool:
        """Sign the executable with the certificate if available."""
        if not self.sign_config["enabled"]:
            self._logger.info("Code signing disabled in config")
            return False

        certificate_path = self.sign_config["certificate"]
        signtool_path = self.sign_config["signtool"]
        timestamp_server = self.sign_config["timestamp_server"]
        digest_algorithm = self.sign_config["digest_algorithm"]

        if not os.path.exists(certificate_path):
            self._logger.warning("Certificate not found, skipping code signing...")
            return False

        if not os.path.exists(signtool_path):
            self._logger.warning("Signtool not found, skipping code signing...")
            return False

        if not os.path.exists(executable_path):
            self._logger.error("Executable not found for signing")
            return False

        try:
            # Use signtool to sign the executable
            sign_cmd = [
                signtool_path,
                "sign",
                "/f", certificate_path,
                "/fd", digest_algorithm,
                "/t", timestamp_server,
                "/v",  # Verbose output
                executable_path
            ]

            self._logger.info(f"Signing executable: {executable_path}")
            self._logger.info(f"Using certificate: {certificate_path}")

            result = subprocess.run(sign_cmd, capture_output=True, text=True)

            if result.returncode == 0:
                self._logger.info("Executable signed successfully!")
                return True
            else:
                self._logger.error(f"Code signing failed with error code: {result.returncode}")
                self._logger.error(f"Error output: {result.stderr}")
                return False

        except FileNotFoundError:
            self._logger.error(f"{signtool_path} not found. Make sure Windows SDK is installed.")
            self._logger.error("You can install it via Visual Studio Installer or download from Microsoft.")
            return False
        except Exception as e:
            self._logger.error(f"Error during code signing: {e}")
            return False

    def create_version_file(self) -> None:
        """Create version file using the same pattern as post_build."""
        try:
            scripts_dir = os.path.abspath("scripts")
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)

            import generate_version
            generate_version.main()
        except Exception as e:
            self._logger.error(f"Version file generation failed: {e}")
            raise
        finally:
            if scripts_dir in sys.path:
                sys.path.remove(scripts_dir)
