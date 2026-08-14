"""Unit tests for scripts/cleanup.py."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import cleanup  # type: ignore[import-not-found]  # pylint: disable=import-error,wrong-import-position


class TestCleanupRun:
    """Tests for cleanup run_cleanup behavior."""

    def test_empties_jira_importer_logs_and_preserves_build_logs(self, tmp_path: Path) -> None:
        """Empty app log dirs; keep files under build/logs."""
        root_logs = tmp_path / "jira_importer_logs"
        pkg_logs = tmp_path / "src" / "jira_importer" / "jira_importer_logs"
        build_logs = tmp_path / "build" / "logs"
        root_logs.mkdir(parents=True)
        pkg_logs.mkdir(parents=True)
        build_logs.mkdir(parents=True)

        (root_logs / "app.log").write_text("root", encoding="utf-8")
        (pkg_logs / "pkg.log").write_text("pkg", encoding="utf-8")
        preserved = build_logs / "build.log"
        preserved.write_text("build", encoding="utf-8")

        stray_log = tmp_path / "stray.log"
        stray_log.write_text("stray", encoding="utf-8")

        cleanup.run_cleanup(root=tmp_path, dry_run=False, verbose=False, vverbose=False)

        assert root_logs.is_dir()
        assert pkg_logs.is_dir()
        assert list(root_logs.iterdir()) == []
        assert list(pkg_logs.iterdir()) == []
        assert preserved.is_file()
        assert preserved.read_text(encoding="utf-8") == "build"
        assert not stray_log.exists()

    def test_dry_run_does_not_delete(self, tmp_path: Path) -> None:
        """Dry-run leaves files in place."""
        root_logs = tmp_path / "jira_importer_logs"
        root_logs.mkdir()
        log_file = root_logs / "app.log"
        log_file.write_text("keep", encoding="utf-8")

        cleanup.run_cleanup(root=tmp_path, dry_run=True, verbose=False, vverbose=False)

        assert log_file.is_file()
