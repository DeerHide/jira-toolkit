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
from typing import Any, Callable, Iterable, Optional
from pathlib import Path
import pandas as pd

from artifacts import ArtifactManager
from console import ui, fmt
from excel_io import ExcelWorkbookManager

try:
    import pandas as pd  # optional
except Exception:  # pragma: no cover
    pd = None  # type: ignore

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

    def xlsx_to_csv(
        self,
        xlsx_file: str | Path,
        csv_file: str | Path,
        *,
        dataset_sheet_name: str = "dataset",
        ui: Optional[Any] = None,                             # expects .success(msg) if provided
        artifact_cb: Optional[Callable[[str], None]] = None,  # e.g., artifact_manager.add
        manager: Optional["ExcelWorkbookManager"] = None,     # prefer using the generic manager if provided
    ) -> bool:
        """
        Convert an XLSX file to a CSV file. Returns True if successful, False otherwise.

        Behavior:
        - Creates parent dir of csv_file if needed.
        - Chooses sheet by explicit name (with case-insensitive fallback when using pandas).
        - When a manager is provided, uses openpyxl via ExcelWorkbookManager (no pandas dependency).
        - When no manager is provided, uses pandas/openpyxl (legacy path).
        - Integer-ish coercion:
            * pandas path: float columns -> Int64 (nullable) to mirror legacy behavior (e.g., 1.0 → 1, 1.1 → 1).
            * manager path: float values in any column are truncated to int (1.0 → 1, 1.9 → 1) to match legacy intent.

        Parameters:
        xlsx_file          Input .xlsx path.
        csv_file           Output .csv path.
        dataset_sheet_name Preferred sheet name (default: 'dataset' or whatever your config says).
        ui                 Optional object with ui.success(msg).
        artifact_cb        Optional callback to register the created artifact (path:str) -> None.
        manager            Optional ExcelWorkbookManager to read the workbook (no pandas dependency).
        """
        xlsx_file = Path(xlsx_file)
        csv_file = Path(csv_file)
        #csv_file.parent.mkdir(parents=True, exist_ok=True)

        if manager is not None:
            # -------- Manager path (no pandas) --------
            try:
                # If caller didn’t call load(), we’ll load/close around the operation.
                _loaded_here = False
                if getattr(manager, "_wb", None) is None:
                    manager.load()
                    _loaded_here = True

                # Read header + rows from the desired sheet
                header, rows = manager.read_dataset(sheet=dataset_sheet_name)

                # Legacy-intent numeric coercion: truncate floats to ints wherever they appear.
                coerced_rows: list[list[Any]] = []
                for r in rows:
                    new_r = []
                    for v in r:
                        if isinstance(v, float):
                            try:
                                new_r.append(int(v))
                            except Exception:
                                new_r.append(v)
                        else:
                            new_r.append(v)
                    coerced_rows.append(new_r)

                # Write CSV (no index)
                with csv_file.open("w", newline="", encoding="utf-8") as fh:
                    writer = csv.writer(fh)
                    if header:
                        writer.writerow(header)
                    writer.writerows(coerced_rows)

                if _loaded_here:
                    manager.close()

                self._notify(ui, artifact_cb, csv_file)
                logger.info("Converted XLSX to CSV via ExcelWorkbookManager: %s", csv_file)
                return os.path.isfile(csv_file)

            except Exception as exc:
                logger.debug("Manager-based conversion failed, falling back to pandas if available: %s", exc)
                # fall through to pandas path (if available)

        # -------- Pandas path (legacy behavior) --------
        if pd is None:
            logger.error("pandas is not available and no ExcelWorkbookManager was provided; cannot convert %s", xlsx_file)
            return False

        sheet_to_read: Any = 0  # default to first sheet
        preferred = str(dataset_sheet_name)

        try:
            excel_file = pd.ExcelFile(str(xlsx_file), engine="openpyxl")
            for idx, name in enumerate(excel_file.sheet_names):
                logger.debug("XLSX sheets: [%d] %s", idx, name)
            if preferred in excel_file.sheet_names:
                sheet_to_read = preferred
            else:
                for name in excel_file.sheet_names:
                    if isinstance(name, str) and name.lower() == preferred.lower():
                        sheet_to_read = name
                        break
            logger.debug("Using sheet for conversion: %s (preferred: %s)", sheet_to_read, preferred)
        except Exception as exc:
            logger.debug("Unable to list sheets for '%s' (using index 0): %s", xlsx_file, exc)

        df = pd.read_excel(str(xlsx_file), sheet_name=sheet_to_read, engine="openpyxl")

        # Legacy: coerce float columns to Int64 (nullable) → truncates 1.1 → 1
        try:
            float_cols = df.select_dtypes(include=["float"]).columns
            if len(float_cols) > 0:
                df[float_cols] = df[float_cols].astype("Int64")
        except Exception as exc:
            logger.debug("Numeric coercion skipped due to: %s", exc)

        df.to_csv(str(csv_file), index=False)

        self._notify(ui, artifact_cb, csv_file)
        logger.info("Converted XLSX to CSV via pandas: %s", csv_file)
        return os.path.isfile(csv_file)


    def _notify(self, ui: Optional[Any], artifact_cb: Optional[Callable[[str], None]], csv_path: Path) -> None:
        if ui and hasattr(ui, "success"):
            try:
                ui.success(f"Converted XLSX to CSV: {csv_path}")
            except Exception:
                pass
        if artifact_cb:
            try:
                artifact_cb(str(csv_path))
            except Exception as exc:
                logger.debug("artifact_cb failed for '%s': %s", csv_path, exc)

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
