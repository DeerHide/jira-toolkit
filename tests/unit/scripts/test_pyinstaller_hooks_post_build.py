"""Unit tests for pyinstaller_hooks.post_build platform gating."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import pyinstaller_hooks  # type: ignore[import-not-found]  # pylint: disable=import-error,wrong-import-position


class TestPostBuildPlatformGate:
    """Ensure post_build finds onefile/onedir artifacts and gates Windows stamping."""

    @pytest.fixture
    def interface(self) -> MagicMock:
        """Build a minimal poetry-pyinstaller plugin interface mock."""
        mock = MagicMock()
        mock.pyproject_data = {}
        mock.run = MagicMock()
        mock.write_line = MagicMock()
        mock.platform = "win_amd64"
        return mock

    def _patch_context(
        self,
        monkeypatch: pytest.MonkeyPatch,
        *,
        platform_tag: str,
        files_cfg: dict[str, Any],
        clear_session: MagicMock,
        sign_executable: MagicMock,
    ) -> None:
        context = SimpleNamespace(platform_tag=platform_tag, files_cfg=files_cfg)
        monkeypatch.setattr(pyinstaller_hooks, "BuildContext", lambda _interface: context)
        monkeypatch.setattr(
            pyinstaller_hooks,
            "BuildUtils",
            lambda _context: SimpleNamespace(sign_executable=sign_executable),
        )
        monkeypatch.setattr(
            pyinstaller_hooks,
            "load_generate_version_module",
            lambda: SimpleNamespace(clear_version_session=clear_session),
        )

    def test_windows_onefile_stamps_and_signs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, interface: MagicMock
    ) -> None:
        """onefile: dist/pyinstaller/<pep>/<name>.exe"""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("BUILD_PROFILE", "shipping")
        interface.platform = "win_amd64"

        version_file = tmp_path / "VSVersionInfo"
        version_file.write_text("version", encoding="utf-8")
        exe_path = tmp_path / "dist" / "pyinstaller" / "win_amd64" / "jira-importer.exe"
        exe_path.parent.mkdir(parents=True)
        exe_path.write_bytes(b"exe")

        clear_session = MagicMock()
        sign_executable = MagicMock(return_value=True)
        self._patch_context(
            monkeypatch,
            platform_tag="windows",
            files_cfg={"version": str(version_file)},
            clear_session=clear_session,
            sign_executable=sign_executable,
        )

        pyinstaller_hooks.post_build(interface)

        expected = str(Path("dist") / "pyinstaller" / "win_amd64" / "jira-importer.exe")
        interface.run.assert_called_once_with("pyi-set_version", str(version_file), expected)
        sign_executable.assert_called_once_with(expected)
        clear_session.assert_called_once_with()
        assert "BUILD_PROFILE" not in os.environ

    def test_windows_onedir_stamps_and_signs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, interface: MagicMock
    ) -> None:
        """onedir: dist/pyinstaller/<pep>/<name>/<name>.exe (root cause of unsigned Poetry builds)."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("BUILD_PROFILE", "shipping")
        interface.platform = "win_amd64"

        version_file = tmp_path / "VSVersionInfo"
        version_file.write_text("version", encoding="utf-8")
        exe_path = tmp_path / "dist" / "pyinstaller" / "win_amd64" / "jira-importer" / "jira-importer.exe"
        exe_path.parent.mkdir(parents=True)
        exe_path.write_bytes(b"exe")

        clear_session = MagicMock()
        sign_executable = MagicMock(return_value=True)
        self._patch_context(
            monkeypatch,
            platform_tag="windows",
            files_cfg={"version": str(version_file)},
            clear_session=clear_session,
            sign_executable=sign_executable,
        )

        pyinstaller_hooks.post_build(interface)

        expected = str(Path("dist") / "pyinstaller" / "win_amd64" / "jira-importer" / "jira-importer.exe")
        interface.run.assert_called_once_with("pyi-set_version", str(version_file), expected)
        sign_executable.assert_called_once_with(expected)

    def test_macos_skips_pyi_set_version_but_signs_when_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, interface: MagicMock
    ) -> None:
        """macOS skips PE stamping; still signs if the binary exists."""
        monkeypatch.chdir(tmp_path)
        interface.platform = "macosx_14_0_arm64"

        binary = tmp_path / "dist" / "pyinstaller" / "macosx_14_0_arm64" / "jira-importer"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"bin")

        clear_session = MagicMock()
        sign_executable = MagicMock(return_value=True)
        self._patch_context(
            monkeypatch,
            platform_tag="macos",
            files_cfg={"version": str(tmp_path / "Info.plist")},
            clear_session=clear_session,
            sign_executable=sign_executable,
        )

        pyinstaller_hooks.post_build(interface)

        interface.run.assert_not_called()
        sign_executable.assert_called_once_with(
            str(Path("dist") / "pyinstaller" / "macosx_14_0_arm64" / "jira-importer")
        )

    def test_windows_skips_when_exe_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, interface: MagicMock
    ) -> None:
        """Missing onefile and onedir artifacts skips stamp and sign."""
        monkeypatch.chdir(tmp_path)
        interface.platform = "win_amd64"

        version_file = tmp_path / "VSVersionInfo"
        version_file.write_text("version", encoding="utf-8")

        clear_session = MagicMock()
        sign_executable = MagicMock(return_value=False)
        self._patch_context(
            monkeypatch,
            platform_tag="windows",
            files_cfg={"version": str(version_file)},
            clear_session=clear_session,
            sign_executable=sign_executable,
        )

        pyinstaller_hooks.post_build(interface)

        interface.run.assert_not_called()
        sign_executable.assert_not_called()
        clear_session.assert_called_once_with()
