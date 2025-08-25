#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script Name: fileops.py
Description: This script manages the file operations for the Jira Importer.
Author: Julien (@tom4897)
License: MIT
Date: 2025
"""

from contextlib import suppress
import logging
import os
import csv
from typing import Iterable, Optional
from pathlib import Path
import pandas as pd

from artifacts import ArtifactManager
from console import ui, fmt

logger = logging.getLogger(__name__)

class FileManager:
    """Manage file operations and integrate with `ArtifactManager`.

    Responsibilities:
    - Writing CSV files with progress and atomic replace to avoid partial files
    - Converting XLSX to CSV (formatting unchanged per design)
    - Generating output filenames based on input path, extension and suffix
    - Deleting files with logging
    """

    def __init__(self, artifact_manager: Optional[ArtifactManager] = None, config: Optional[object] = None) -> None:
        self.artifact_manager = artifact_manager
        self.config = config

    def write_csv_file(self, output_file: str, csv_file, is_artifact: bool = True) -> bool:
        """
        Write a CSV file from an object exposing `header` and `data`.
        Atomic write via temp file + replace. Returns True on success.
        """
        # --- Validate inputs (duck-typed)
        header = getattr(csv_file, "header", None)
        data = getattr(csv_file, "data", None)

        if not isinstance(header, Iterable) or data is None:
            msg = "Invalid csv_file object: missing 'header' or 'data' attribute"
            ui.error(msg); logger.error(msg)
            return False

        path = Path(output_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")

        # Try to get total for progress; fall back to indeterminate
        try:
            total = len(data)
        except TypeError:
            total = None

        try:
            with open(tmp_path, mode="w", newline="", encoding="utf-8", errors="ignore") as f:
                writer = csv.writer(f)
                writer.writerow(header)

                # local bind for speed in loop
                write_row = writer.writerow

                with ui.progress() as progress:
                    task = progress.add_task("Writing items", total=total)
                    if total is None:
                        for row in data:
                            write_row(row)
                            progress.advance(task)
                    else:
                        for row in data:
                            write_row(row)
                            progress.advance(task)
                            progress.refresh()

            os.replace(tmp_path, path)

            ui.success(f"CSV file written: {path}")
            logger.info("CSV file written: %s", path)

            if getattr(self, "artifact_manager", None) and is_artifact:
                self.artifact_manager.add(str(path))

            return True

        except Exception as exc:
            logger.exception("Failed to write CSV '%s': %s", path, exc)
            with suppress(Exception):
                if tmp_path.exists():
                    tmp_path.unlink()
            return False

    def xlsx_to_csv(self, xlsx_file: str, csv_file: str, is_artifact: bool = True) -> bool:
        """Convert an XLSX file to a CSV file. Returns True if successful, False otherwise."""
        # Process and formatting intentionally unchanged
        Path(csv_file).parent.mkdir(parents=True, exist_ok=True)
        # List all sheet names with indices for debugging visibility
        sheet_name_to_read = 0
        # Get desired sheet name from configuration, defaulting to 'dataset'
        dataset_sheet_name = 'dataset'
        try:
            if getattr(self, 'config', None):
                dataset_sheet_name = self.config.get_value('app.sheet_name', default='dataset', expected_type=str) or 'dataset'
        except Exception as exc:
            logger.debug("Unable to read 'app.sheet_name' from configuration, defaulting to 'dataset': %s", exc)
        try:
            excel_file = pd.ExcelFile(xlsx_file, engine='openpyxl')
            for idx, name in enumerate(excel_file.sheet_names):
                logger.debug("XLSX sheets: [%d] %s", idx, name)
            # Prefer a sheet named as configured (case-sensitive first, then case-insensitive)
            if dataset_sheet_name in excel_file.sheet_names:
                sheet_name_to_read = dataset_sheet_name
            else:
                for name in excel_file.sheet_names:
                    if isinstance(name, str) and name.lower() == str(dataset_sheet_name).lower():
                        sheet_name_to_read = name
                        break
            logger.debug("Using sheet for conversion: %s (preferred: %s)", sheet_name_to_read, dataset_sheet_name)
        except Exception as exc:
            logger.debug("Unable to list sheets for '%s' (using index 0): %s", xlsx_file, exc)
        excel_content = pd.read_excel(xlsx_file, sheet_name=sheet_name_to_read, engine='openpyxl')
        # integer-like coercion (e.g. 1.0 -> 1, 1.1 -> 1)
        for col in excel_content.select_dtypes(include=['float']):
            excel_content[col] = excel_content[col].astype('Int64')
        excel_content.to_csv(csv_file, index=False)
        ui.success(f"Converted XLSX to CSV: {csv_file}")
        logger.info(f"Converted XLSX to CSV: {csv_file}")
        if self.artifact_manager and is_artifact:
            self.artifact_manager.add(csv_file)
        return os.path.isfile(csv_file)

    def generate_output_filename(self, input_file: str, file_extension: str = '', suffix: str = "") -> str:
        """Generate an output filename by altering extension and appending a suffix.

        Avoids trailing dots when no extension is provided.
        """
        base_name, ext = os.path.splitext(input_file)
        if file_extension:
            ext = file_extension
        ext = ext.lstrip('.')
        output_file = f"{base_name}{suffix}.{ext}" if ext else f"{base_name}{suffix}"
        logger.debug(f"Output file: {output_file}")
        return output_file

    def delete_file(self, file_path: str) -> bool:
        """Delete a file if it exists. Returns True if deleted, False otherwise."""
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Deleted file: {file_path}")
                return True
            except Exception as exc:
                logger.exception("Failed to delete file '%s': %s", file_path, exc)
                return False
        else:
            ui.error(f"File '{file_path}' does not exist.")
            logger.warning(f"Missing file: '{file_path}'")
            return False
