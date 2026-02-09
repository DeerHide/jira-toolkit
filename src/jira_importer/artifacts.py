"""Description: Manage temporary/output artifacts for the Jira Importer.

Author:
    Julien (@tom4897)
"""

import logging
import threading
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from jira_importer.fileops import FileOperations

logger = logging.getLogger(__name__)


class ArtifactManager:
    """Track and optionally delete generated artifacts.

    - Stores normalized absolute file paths as a set to avoid duplicates
    - Uses a lock for thread-safety
    - Can restrict tracking to a base directory (if provided)
    """

    def __init__(self, config: Any, base_dir: str | Path | None = None):
        """Initialize the ArtifactManager."""
        self._artifacts: set[Path] = set()
        # Coerce to bool so None -> False
        self.delete_enabled: bool = bool(config.get_value("app.artifacts.delete_enabled"))
        self._base_dir: Path | None = Path(base_dir).resolve() if base_dir is not None else None
        self._lock = threading.Lock()
        self._file_operations = FileOperations()

    def _normalize(self, file_path: str | Path) -> Path | None:
        """Normalize a file path."""
        if not file_path:
            return None
        path = Path(file_path).resolve()
        if self._base_dir and not (path == self._base_dir or self._base_dir in path.parents):
            logger.warning("Refusing to track artifact outside base_dir: %s", path)
            return None
        return path

    def add(self, file_path: str | Path) -> None:
        """Add an artifact to the tracking set."""
        path = self._normalize(file_path)
        if path is None:
            return
        with self._lock:
            if path not in self._artifacts:
                self._artifacts.add(path)
                logger.debug("Artifact added: %s", path)

    def add_many(self, file_paths: Iterable[str | Path]) -> None:
        """Add multiple artifacts to the tracking set."""
        for p in file_paths:
            self.add(p)

    def remove(self, file_path: str | Path) -> None:
        """Remove an artifact from the tracking set."""
        path = self._normalize(file_path)
        if path is None:
            return
        with self._lock:
            self._artifacts.discard(path)

    def list(self) -> Iterable[Path]:
        """List all artifacts in the tracking set."""
        with self._lock:
            return list(self._artifacts)

    def clear(self) -> None:
        """Clear the tracking set."""
        with self._lock:
            self._artifacts.clear()

    def delete_all(self, include_dirs: bool = False, dry_run: bool = False) -> dict[str, int]:
        """Delete all tracked artifacts.

        Parameters:
        - include_dirs: also delete directories (non-symlink) via rmtree
        - dry_run: log actions without deleting

        Returns a summary dict with counts of deleted/skipped/errors.
        """
        if not self.delete_enabled:
            with self._lock:
                artifact_count = len(self._artifacts)
            if not dry_run:
                logger.debug(
                    "Artifact deletion is disabled in configuration. Skipping deletion of %d artifact(s).",
                    artifact_count,
                )
            else:
                logger.debug(
                    "Artifact deletion is disabled in configuration. Would skip deletion of %d artifact(s) in dry-run mode.",
                    artifact_count,
                )
            return {"deleted": 0, "skipped": artifact_count, "errors": 0}

        deleted = 0
        skipped = 0
        errors = 0

        with self._lock:
            # Work on a snapshot to allow safe modification
            for path in list(self._artifacts):
                try:
                    if not path.exists():
                        skipped += 1
                        logger.debug("Artifact does not exist: %s", path)
                    elif dry_run:
                        skipped += 1
                        logger.info("Dry-run: would delete %s", path)
                    else:
                        success = False
                        if path.is_file() or path.is_symlink():
                            # Avoid rmtree on directory symlinks
                            success = self._file_operations.delete(str(path))
                        elif include_dirs and path.is_dir() and not path.is_symlink():
                            success = self._file_operations.delete_tree(path)
                        else:
                            skipped += 1
                            logger.debug("Skipping non-file artifact: %s", path)
                            self._artifacts.discard(path)
                            continue

                        if success:
                            deleted += 1
                            logger.info("Deleted artifact: %s", path)
                        else:
                            errors += 1
                            logger.error("Failed to delete artifact '%s'", path)

                    self._artifacts.discard(path)
                except FileNotFoundError:
                    skipped += 1
                    logger.debug("Artifact vanished before deletion: %s", path)
                    self._artifacts.discard(path)
                except Exception as exc:
                    errors += 1
                    logger.error("Failed to delete artifact '%s': %s", path, exc)

        logger.debug("Artifacts deletion completed: deleted=%d skipped=%d errors=%d", deleted, skipped, errors)
        return {"deleted": deleted, "skipped": skipped, "errors": errors}
