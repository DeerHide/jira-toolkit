"""Description: This script manages the file operations for the Jira Importer.

Author:
    Julien (@tom4897)
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .artifacts import ArtifactManager
from .console import ConsoleIO

logger = logging.getLogger(__name__)
ui = ConsoleIO.getUI()  # pylint: disable=invalid-name

try:
    import pandas as pd  # type: ignore[import-untyped]
except Exception:  # pragma: no cover
    pd = None  # type: ignore[assignment] # pylint: disable=invalid-name


class FileManager:
    """Manage file operations and integrate with `ArtifactManager`.

    Responsibilities:
    - Writing CSV files with progress and atomic replace to avoid partial files
    - Converting XLSX to CSV (formatting unchanged per design)
    - Generating output filenames based on input path, extension and suffix
    - Deleting files with logging
    """

    def __init__(self, artifact_manager: ArtifactManager | None = None, config: object | None = None) -> None:
        """Initialize the FileManager."""
        self.artifact_manager = artifact_manager
        self.config = config

    def _notify(self, ui: Any | None, artifact_cb: Callable[[str], None] | None, csv_path: Path) -> None:  # pylint: disable=W0621
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

    def generate_output_filename(self, input_file: str, file_extension: str = "", suffix: str = "") -> str:
        """Generate an output filename by altering extension and appending a suffix.

        Avoids trailing dots when no extension is provided.
        """
        base_name = Path(input_file).stem
        ext = Path(input_file).suffix
        if file_extension:
            ext = file_extension
        ext = ext.lstrip(".")
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

    @staticmethod
    def validate_input_file(in_path: Path, xlsx_file: str, logger_ref: logging.Logger) -> None:
        """Validate the input file exists and is a file.

        Args:
            in_path: Path to the input file.
            xlsx_file: Input file path as string (for error messages).
            logger_ref: Logger instance for error logging.

        Raises:
            InputFileError: If the file doesn't exist or is not a file.
        """
        from jira_importer.app import App  # pylint: disable=import-outside-toplevel
        from jira_importer.errors import (  # pylint: disable=import-outside-toplevel
            InputFileError,
            format_error_for_display,
            log_exception,
        )

        try:
            if not in_path.exists():
                raise InputFileError(
                    f"Input file does not exist: {xlsx_file}",
                    details={"file_path": str(xlsx_file), "operation": "input_validation"},
                )
            if not in_path.is_file():
                raise InputFileError(
                    f"Input path is not a file: {xlsx_file}",
                    details={
                        "file_path": str(xlsx_file),
                        "operation": "input_validation",
                        "path_type": "directory_or_other",
                    },
                )
        except InputFileError as file_exc:
            # Log the error with structured details
            log_exception(logger_ref, file_exc, context="Input file validation")
            # Display formatted error with error code
            error_message = format_error_for_display(file_exc)
            ui.error(error_message)
            logger_ref.critical(f"Input file validation failed: {error_message}")
            # Use App.graceful_exit for consistent error handling
            App.graceful_exit(exit_code=2, do_cleanup=False)
