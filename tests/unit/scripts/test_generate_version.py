"""Unit tests for once-per-session version generation."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import generate_version  # type: ignore[import-not-found]  # pylint: disable=import-error,wrong-import-position

INITIAL_BUILD_NUMBER = 10
FIRST_BUMPED_BUILD_NUMBER = 11
SECOND_BUMPED_BUILD_NUMBER = 12


@pytest.fixture
def version_project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create an isolated project tree for version generation."""
    root = tmp_path
    (root / "build" / "configs").mkdir(parents=True)
    (root / "build" / "version").mkdir(parents=True)
    (root / "src" / "jira_importer").mkdir(parents=True)

    (root / "build" / "configs" / "base.json").write_text(
        json.dumps({"metadata": {"version": "1.2.3"}}),
        encoding="utf-8",
    )
    (root / "build" / "version" / "build-counter.json").write_text(
        json.dumps(
            {
                "major": 1,
                "minor": 2,
                "patch": 3,
                "build_number": INITIAL_BUILD_NUMBER,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(generate_version, "_get_project_root", lambda: str(root))
    monkeypatch.setattr(generate_version, "get_git_commit_hash", lambda: "abc1234")
    monkeypatch.setattr(generate_version, "get_git_branch", lambda: "test-branch")
    generate_version.clear_version_session()
    return root


def _read_counter(root: Path) -> dict[str, int]:
    return json.loads((root / "build" / "version" / "build-counter.json").read_text(encoding="utf-8"))


class TestGenerateVersionOncePerSession:
    """Ensure build number increments exactly once per session."""

    def test_first_call_increments_build_number(self, version_project_root: Path) -> None:
        """Bump on first generate_version_files call."""
        result = generate_version.generate_version_files(increment=True)

        assert result[5] == FIRST_BUMPED_BUILD_NUMBER
        assert _read_counter(version_project_root)["build_number"] == FIRST_BUMPED_BUILD_NUMBER
        assert (version_project_root / "build" / "version" / "VSVersionInfo").is_file()
        assert (version_project_root / "build" / "version" / "Info.plist").is_file()
        assert (version_project_root / "src" / "jira_importer" / "version.py").is_file()

    def test_second_call_does_not_double_increment(self, version_project_root: Path) -> None:
        """Reuse build number on a second call in the same session."""
        first = generate_version.generate_version_files(increment=True)
        second = generate_version.generate_version_files(increment=True)

        assert first[5] == FIRST_BUMPED_BUILD_NUMBER
        assert second[5] == FIRST_BUMPED_BUILD_NUMBER
        assert _read_counter(version_project_root)["build_number"] == FIRST_BUMPED_BUILD_NUMBER

    def test_env_marker_blocks_increment_across_module_reload_state(
        self, version_project_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Honor VERSION_INCREMENT_DONE_ENV when the process flag is cleared."""
        generate_version.generate_version_files(increment=True)
        monkeypatch.setattr(generate_version, "_increment_applied_this_process", False)

        again = generate_version.generate_version_files(increment=True)

        assert again[5] == FIRST_BUMPED_BUILD_NUMBER
        assert _read_counter(version_project_root)["build_number"] == FIRST_BUMPED_BUILD_NUMBER

    def test_clear_session_allows_new_increment(self, version_project_root: Path) -> None:
        """Allow another bump after clear_version_session()."""
        generate_version.generate_version_files(increment=True)
        generate_version.clear_version_session()

        again = generate_version.generate_version_files(increment=True)

        assert again[5] == SECOND_BUMPED_BUILD_NUMBER
        assert _read_counter(version_project_root)["build_number"] == SECOND_BUMPED_BUILD_NUMBER

    def test_no_increment_flag_rewrites_without_bump(self, version_project_root: Path) -> None:
        """Leave counter unchanged when increment=False."""
        result = generate_version.generate_version_files(increment=False)

        assert result[5] == INITIAL_BUILD_NUMBER
        assert _read_counter(version_project_root)["build_number"] == INITIAL_BUILD_NUMBER

    def test_build_utils_wrapper_uses_shared_entrypoint(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """BuildUtils.generate_version_file delegates to generate_version_files."""
        import build_utils.build_utils as build_utils_mod  # type: ignore[import-not-found]  # pylint: disable=import-error

        calls: list[bool] = []

        def _fake_generate_version_files(*, increment: bool = True) -> tuple[str, str, int, int, int, int]:
            calls.append(increment)
            return ("1.2.3", "1.2.3.11", 1, 2, 3, FIRST_BUMPED_BUILD_NUMBER)

        fake_module = SimpleNamespace(generate_version_files=_fake_generate_version_files)
        monkeypatch.setattr(build_utils_mod, "load_generate_version_module", lambda: fake_module)

        build_utils_mod.BuildUtils().generate_version_file(increment=True)

        assert calls == [True]
