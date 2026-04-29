"""Phase 1 compatibility tests for config loading behavior."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from jira_importer.config.excel_config import ExcelConfiguration
from jira_importer.config.json_config import JsonConfiguration
from jira_importer.errors import ConfigurationError, ExcelConfigurationError


class _FakeWorkbookManager:
    """Test double for Excel workbook manager."""

    def __init__(self, path: str, data: Mapping[str, object]) -> None:
        self.path = path
        self._data = dict(data)

    def load(self) -> None:
        """No-op load."""

    def read_config(self, sheet: str = "Config") -> dict[str, object]:  # pylint: disable=unused-argument
        """Return fake flat config data."""
        return self._data

    def close(self) -> None:
        """No-op close."""


class _FakeTableReader:
    """Test double for Excel table reader."""

    def __init__(self, workbook_manager: _FakeWorkbookManager) -> None:
        self.workbook_manager = workbook_manager

    def read_all_tables(self, config_sheet: str):  # pylint: disable=unused-argument
        """Return no table config to keep tests focused."""
        return None


def _write_json_config(tmp_path: Path, payload: dict[str, object]) -> str:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    return str(config_path)


def _write_excel_placeholder(tmp_path: Path) -> str:
    excel_path = tmp_path / "config.xlsx"
    excel_path.write_text("placeholder", encoding="utf-8")
    return str(excel_path)


class TestConfigPhase1Compatibility:
    """Tests for JT-314 Phase 1 compatibility contract."""

    def test_json_version_issue_warns_and_does_not_block(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """JSON version issues should warn with future requirement text."""
        config_path = _write_json_config(tmp_path, {"metadata": {"version": 0}})

        caplog.set_level("WARNING")
        config = JsonConfiguration(config_path, cfg_req=7)

        assert config.get_value("metadata.version") == 0
        assert any(
            "will be required in a future release" in record.message for record in caplog.records if record.levelname == "WARNING"
        )

    def test_excel_version_issue_warns_and_does_not_block(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Excel version issues should warn with the same future requirement text."""
        excel_path = _write_excel_placeholder(tmp_path)
        fake_data = {"metadata.version": "0"}

        monkeypatch.setattr(
            "jira_importer.config.excel_config.ExcelWorkbookManager",
            lambda path: _FakeWorkbookManager(path, fake_data),
        )
        monkeypatch.setattr("jira_importer.config.excel_config.ExcelTableReader", _FakeTableReader)

        caplog.set_level("WARNING")
        config = ExcelConfiguration(excel_path, cfg_req=7)

        assert config.get_value("metadata.version") == "0"
        assert any(
            "will be required in a future release" in record.message for record in caplog.records if record.levelname == "WARNING"
        )

    def test_excel_string_coercion_is_preserved_in_phase1(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Excel keeps implicit coercion for bool/int/float string values."""
        excel_path = _write_excel_placeholder(tmp_path)
        fake_data = {
            "metadata.version": "7",
            "app.import.auto_open_page": "yes",
            "jira.timeout.seconds": "120",
            "jira.estimate.factor": "1.5",
        }

        monkeypatch.setattr(
            "jira_importer.config.excel_config.ExcelWorkbookManager",
            lambda path: _FakeWorkbookManager(path, fake_data),
        )
        monkeypatch.setattr("jira_importer.config.excel_config.ExcelTableReader", _FakeTableReader)

        config = ExcelConfiguration(excel_path, cfg_req=7)
        assert config.get_value("app.import.auto_open_page", expected_type=bool) is True
        assert config.get_value("jira.timeout.seconds", expected_type=int) == 120
        assert config.get_value("jira.estimate.factor", expected_type=float) == 1.5

    def test_type_mismatch_message_and_details_are_aligned(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Equivalent type mismatch should use aligned message/details in JSON and Excel."""
        key = "app.import.auto_open_page"

        json_path = _write_json_config(
            tmp_path,
            {
                "metadata": {"version": 7},
                "app": {"import": {"auto_open_page": [1, 2]}},
            },
        )
        json_config = JsonConfiguration(json_path, cfg_req=7)

        with pytest.raises(ConfigurationError) as json_exc:
            json_config.get_value(key, expected_type=bool)

        excel_path = _write_excel_placeholder(tmp_path)
        fake_data = {"metadata.version": "7", "app.import.auto_open_page": [1, 2]}
        monkeypatch.setattr(
            "jira_importer.config.excel_config.ExcelWorkbookManager",
            lambda path: _FakeWorkbookManager(path, fake_data),
        )
        monkeypatch.setattr("jira_importer.config.excel_config.ExcelTableReader", _FakeTableReader)

        excel_config = ExcelConfiguration(excel_path, cfg_req=7)
        with pytest.raises(ExcelConfigurationError) as excel_exc:
            excel_config.get_value(key, expected_type=bool)

        assert str(json_exc.value) == str(excel_exc.value)
        assert json_exc.value.details == excel_exc.value.details
