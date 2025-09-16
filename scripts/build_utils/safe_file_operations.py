#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Safe file operations for the Jira Importer build system.

Author: Julien (@tom4897)
License: MIT
Date: 2025
"""

import os
import shutil
import time
import logging
from pathlib import Path
from typing import Union


class SafeFileOperations:
    """Generic file operations handler with consistent error handling and retry logic."""

    def __init__(self, max_retries: int = 3, retry_delay: int = 1):
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def _handle_operation_with_retry(self, operation_name: str, operation_func, *args, **kwargs) -> bool:
        """Execute an operation with retry logic and consistent error handling."""
        # Get logger from the calling module
        logger = logging.getLogger(__name__)

        for attempt in range(self.max_retries):
            try:
                return operation_func(*args, **kwargs)
            except PermissionError as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"⚠️  Permission error during {operation_name} (attempt {attempt + 1}/{self.max_retries}): {e}")
                    logger.warning(f"⏳ Waiting {self.retry_delay} seconds before retry...")
                    time.sleep(self.retry_delay)
                    self.retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"❌ Failed {operation_name} after {self.max_retries} attempts: {e}")
                    return False
            except OSError as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"⚠️  OS error during {operation_name} (attempt {attempt + 1}/{self.max_retries}): {e}")
                    logger.warning(f"⏳ Waiting {self.retry_delay} seconds before retry...")
                    time.sleep(self.retry_delay)
                    self.retry_delay *= 2
                else:
                    logger.error(f"❌ Failed {operation_name} after {self.max_retries} attempts: {e}")
                    return False
            except Exception as e:
                logger.error(f"❌ Unexpected error during {operation_name}: {e}")
                return False
        return False

    def remove_directory(self, directory_path: Union[str, Path], description: str = "directory") -> bool:
        """Safely remove a directory with retry logic and proper error handling."""
        directory_path = Path(directory_path)
        logger = logging.getLogger(__name__)

        if not directory_path.exists():
            logger.info(f"⏭️  {description.capitalize()} does not exist: {directory_path}")
            return True

        def _remove_operation():
            logger.info(f"🧹 Removing {description}: {directory_path}")
            shutil.rmtree(directory_path)
            logger.info(f"✅ Successfully removed {description}: {directory_path}")
            return True

        return self._handle_operation_with_retry(f"removing {description}", _remove_operation)

    def create_directory(self, directory_path: Union[str, Path], description: str = "directory", clean_if_exists: bool = False) -> bool:
        """Safely create a directory with optional cleaning and proper error handling."""
        directory_path = Path(directory_path)
        logger = logging.getLogger(__name__)

        def _create_operation():
            if clean_if_exists and directory_path.exists():
                if not self.remove_directory(directory_path, description):
                    return False

            directory_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ Created/ensured {description}: {directory_path}")
            return True

        return self._handle_operation_with_retry(f"creating {description}", _create_operation)

    def copy_file(self, source_path: Union[str, Path], dest_path: Union[str, Path], description: str = "file") -> bool:
        """Safely copy a file with proper error handling."""
        source_path = Path(source_path)
        dest_path = Path(dest_path)
        logger = logging.getLogger(__name__)

        def _copy_operation():
            # Ensure destination directory exists
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(source_path, dest_path)
            logger.info(f"✅ Successfully copied {description}: {source_path} → {dest_path}")
            return True

        try:
            if not source_path.exists():
                logger.error(f"❌ Source {description} not found: {source_path}")
                return False

            return self._handle_operation_with_retry(f"copying {description}", _copy_operation)
        except Exception as e:
            logger.error(f"❌ Unexpected error copying {description}: {e}")
            return False

    def copy_directory(self, source_path: Union[str, Path], dest_path: Union[str, Path], description: str = "directory") -> bool:
        """Safely copy a directory with proper error handling."""
        source_path = Path(source_path)
        dest_path = Path(dest_path)
        logger = logging.getLogger(__name__)

        def _copy_operation():
            # Remove destination if it exists
            if dest_path.exists():
                logger.info(f"🗑️  Removing existing {description}: {dest_path}")
                if not self.remove_directory(dest_path, description):
                    return False

            shutil.copytree(source_path, dest_path)
            logger.info(f"✅ Successfully copied {description}: {source_path} → {dest_path}")
            return True

        try:
            if not source_path.exists():
                logger.error(f"❌ Source {description} not found: {source_path}")
                return False

            return self._handle_operation_with_retry(f"copying {description}", _copy_operation)
        except Exception as e:
            logger.error(f"❌ Unexpected error copying {description}: {e}")
            return False

    def file_exists(self, file_path: Union[str, Path], description: str = "file") -> bool:
        """Safely check if a file exists with proper error handling."""
        file_path = Path(file_path)
        logger = logging.getLogger(__name__)

        try:
            exists = file_path.is_file()
            if not exists:
                logger.warning(f"⚠️  {description.capitalize()} not found: {file_path}")
            return exists
        except Exception as e:
            logger.debug(f"❌ Error checking {description}: {e}")
            return False

    def directory_exists(self, directory_path: Union[str, Path], description: str = "directory") -> bool:
        """Safely check if a directory exists with proper error handling."""
        directory_path = Path(directory_path)
        logger = logging.getLogger(__name__)

        try:
            exists = directory_path.is_dir()
            if not exists:
                logger.debug(f"⚠️  {description.capitalize()} not found: {directory_path}")
            return exists
        except Exception as e:
            logger.debug(f"❌ Error checking {description}: {e}")
            return False
