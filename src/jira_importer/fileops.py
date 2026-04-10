"""Description: This script manages the file operations for the Jira Importer.

Author:
    Julien (@tom4897)
"""

from __future__ import annotations

import logging
import os
import shutil
import stat
from collections.abc import Callable
from pathlib import Path

from .console import ConsoleUI
from .errors import InputFileError

logger = logging.getLogger(__name__)


class FileOperations:
    """Low-level file system operations (delete, existence checks)."""

    def delete(self, file_path: str) -> bool:
        """Delete a file if it exists.

        Args:
            file_path: Path to the file to delete.

        Returns:
            True if the file was deleted, False if it did not exist or removal failed.
        """
        if not os.path.isfile(file_path):
            return False
        try:
            os.remove(file_path)
            logger.info("Deleted file: %s", file_path)
            return True
        except Exception as exc:
            logger.exception("Failed to delete file '%s': %s", file_path, exc)
            return False

    def delete_tree(self, path: Path | str) -> bool:
        """Delete a directory tree.

        Use only for real directories (not symlinks). Symlinks to directories should be
        deleted via ``delete`` instead.

        Args:
            path: Directory path to delete.

        Returns:
            True if the directory tree was deleted, False otherwise.
        """
        target = Path(path).resolve()
        if not target.is_dir() or target.is_symlink():
            logger.debug("delete_tree skipped non-directory path: %s", target)
            return False

        try:
            shutil.rmtree(target, onexc=self._on_rmtree_onexc)
        except Exception as exc:
            logger.error("Failed to delete directory tree '%s': %s", target, exc)
            return False

        if target.exists():
            logger.warning("Directory tree still exists after delete_tree: %s", target)
            return False

        logger.info("Deleted directory tree: %s", target)
        return True

    def _on_rmtree_onexc(
        self,
        func: Callable[..., object],
        path: str | bytes,
        _exc: BaseException,
    ) -> None:
        """``shutil.rmtree`` ``onexc``: chmod writable, then retry ``func(path)`` (see stdlib)."""
        try:
            os.chmod(path, stat.S_IWRITE)
        except OSError:
            logger.exception("Failed to chmod during rmtree recovery: %s", path)
            return
        func(path)


class PathGenerator:
    """Generate output filenames from input path, extension and suffix."""

    def generate(
        self,
        input_file: str,
        file_extension: str = "",
        suffix: str = "",
    ) -> str:
        """Generate an output filename by altering extension and appending a suffix.

        Avoids trailing dots when no extension is provided.

        Args:
            input_file: Input file path (used for base name and default extension).
            file_extension: Override extension (e.g. 'csv'). Optional.
            suffix: Suffix to append before extension (e.g. '_jira_ready'). Optional.

        Returns:
            Generated filename string.
        """
        base_name = Path(input_file).stem
        ext = Path(input_file).suffix
        if file_extension:
            ext = file_extension
        ext = ext.lstrip(".")
        output_file = f"{base_name}{suffix}.{ext}" if ext else f"{base_name}{suffix}"
        logger.debug("Output file: %s", output_file)
        return output_file


class FileValidator:
    """Validates input file path: exists and is a file. Raises InputFileError on failure."""

    @staticmethod
    def validate(in_path: Path, file_path_str: str, logger_ref: logging.Logger) -> None:
        """Validate the input file exists and is a file.

        Args:
            in_path: Path to the input file.
            file_path_str: Input file path as string (for error messages).
            logger_ref: Logger instance (unused; for API compatibility).

        Raises:
            InputFileError: If the file doesn't exist or is not a file.
        """
        if not in_path.exists():
            raise InputFileError(
                f"Input file does not exist: {file_path_str}",
                details={"file_path": str(file_path_str), "operation": "input_validation"},
            )
        if not in_path.is_file():
            raise InputFileError(
                f"Input path is not a file: {file_path_str}",
                details={
                    "file_path": str(file_path_str),
                    "operation": "input_validation",
                    "path_type": "directory_or_other",
                },
            )


class FileManager:
    """Orchestrates file operations, path generation and validation via injected services."""

    def __init__(self, config: object | None = None, ui: ConsoleUI | None = None) -> None:
        """Initialize the FileManager.

        Args:
            config: Optional application config.
            ui: Optional console UI for user-facing messages.
        """
        self.config = config
        self._ui = ui
        self._file_operations = FileOperations()
        self._path_generator = PathGenerator()
        self._file_validator = FileValidator()

    def generate_output_filename(
        self,
        input_file: str,
        file_extension: str = "",
        suffix: str = "",
    ) -> str:
        """Generate an output filename by altering extension and appending a suffix."""
        return self._path_generator.generate(input_file, file_extension=file_extension, suffix=suffix)

    def delete_file(self, file_path: str) -> bool:
        """Delete a file if it exists. Returns True if deleted, False otherwise."""
        deleted = self._file_operations.delete(file_path)
        if deleted:
            return True
        if self._ui is not None:
            self._ui.error(f"File '{file_path}' does not exist.")
        logger.warning("Missing file: '%s'", file_path)
        return False

    def validate_input_file(self, in_path: Path, file_path_str: str, logger_ref: logging.Logger) -> None:
        """Validate the input file exists and is a file. Raises InputFileError on failure."""
        self._file_validator.validate(in_path, file_path_str, logger_ref)
