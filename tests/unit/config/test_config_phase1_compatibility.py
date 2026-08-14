"""Phase 1 compatibility tests for config loading behavior."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from jira_importer.config.config_models import AutoFieldValueConfig, ExcelTableConfig, SettingConfig
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

    def read_basic_settings(self, config_sheet: str = "Config"):  # pylint: disable=unused-argument
        """Return no CfgBasic rows by default."""
        return []

    def read_advanced_settings(self, config_sheet: str = "Config"):  # pylint: disable=unused-argument
        """Return no CfgAdvanced rows by default."""
        return []

    def read_settings(self, config_sheet: str = "Config"):  # pylint: disable=unused-argument
        """Return no CfgSettings rows by default."""
        return []


class _FakeTableReaderWithMetadataVersion:
    """Test double returning metadata.version from CfgAutofieldValues."""

    def __init__(self, workbook_manager: _FakeWorkbookManager) -> None:
        self.workbook_manager = workbook_manager

    def read_all_tables(self, config_sheet: str):  # pylint: disable=unused-argument
        """Return table config with metadata.version fallback value."""
        return ExcelTableConfig(auto_field_values=[AutoFieldValueConfig(name="metadata.version", value="7")])

    def read_basic_settings(self, config_sheet: str = "Config"):  # pylint: disable=unused-argument
        """Return no CfgBasic rows for this test double."""
        return []

    def read_advanced_settings(self, config_sheet: str = "Config"):  # pylint: disable=unused-argument
        """Return no CfgAdvanced rows for this test double."""
        return []

    def read_settings(self, config_sheet: str = "Config"):  # pylint: disable=unused-argument
        """Return no CfgSettings rows for this test double."""
        return []


class _FakeTableReaderWithCfgSettings:
    """Test double exposing CfgSettings values for precedence tests."""

    def __init__(self, workbook_manager: _FakeWorkbookManager) -> None:
        self.workbook_manager = workbook_manager

    def read_all_tables(self, config_sheet: str):  # pylint: disable=unused-argument
        """Return empty full table config, not needed for these tests."""
        return ExcelTableConfig()

    def read_basic_settings(self, config_sheet: str = "Config"):  # pylint: disable=unused-argument
        """Return no CfgBasic rows for this test double."""
        return []

    def read_advanced_settings(self, config_sheet: str = "Config"):  # pylint: disable=unused-argument
        """Return no CfgAdvanced rows for this test double."""
        return []

    def read_settings(self, config_sheet: str = "Config"):  # pylint: disable=unused-argument
        """Return CfgSettings values used for merge precedence."""
        return [
            SettingConfig(name="metadata.version", value=7, value_type="int"),
            SettingConfig(name="app.import.auto_open_page", value=False, value_type="bool"),
        ]


class _FakeTableReaderWithLayeredSettings:
    """Test double exposing Basic/Advanced/Settings layers for precedence tests."""

    def __init__(self, workbook_manager: _FakeWorkbookManager) -> None:
        self.workbook_manager = workbook_manager

    def read_all_tables(self, config_sheet: str):  # pylint: disable=unused-argument
        """Return empty full table config, not needed for these tests."""
        return ExcelTableConfig()

    def read_basic_settings(self, config_sheet: str = "Config"):  # pylint: disable=unused-argument
        """Return CfgBasic values used for merge precedence."""
        return [
            SettingConfig(name="jira.project.key", value="BASIC"),
            SettingConfig(name="jira.connection.site_address", value="https://basic.example"),
            SettingConfig(name="app.import.auto_open_page", value="yes"),
        ]

    def read_advanced_settings(self, config_sheet: str = "Config"):  # pylint: disable=unused-argument
        """Return CfgAdvanced values used for merge precedence."""
        return [
            SettingConfig(name="app.import.auto_open_page", value="no"),
            SettingConfig(name="jira.components_source", value="jira"),
        ]

    def read_settings(self, config_sheet: str = "Config"):  # pylint: disable=unused-argument
        """Return CfgSettings values used for merge precedence."""
        return [
            SettingConfig(name="metadata.version", value=8, value_type="int"),
            SettingConfig(name="app.import.auto_open_page", value=True, value_type="bool"),
        ]


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

    def test_json_version_issue_warns_and_does_not_block(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """JSON version issues should warn with future requirement text."""
        config_path = _write_json_config(tmp_path, {"metadata": {"version": 0}})

        caplog.set_level("WARNING")
        config = JsonConfiguration(config_path, cfg_req=7)

        assert config.get_value("metadata.version") == 0
        assert any(
            "will be required in a future release" in record.message
            for record in caplog.records
            if record.levelname == "WARNING"
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
            "will be required in a future release" in record.message
            for record in caplog.records
            if record.levelname == "WARNING"
        )

    def test_excel_string_coercion_is_preserved_in_phase1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
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

    def test_excel_version_falls_back_to_auto_field_values_when_missing_in_config_rows(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Excel version check should use CfgAutofieldValues as backward-compatible fallback."""
        excel_path = _write_excel_placeholder(tmp_path)
        fake_data = {"jira.connection.site_address": "https://example.atlassian.net"}

        monkeypatch.setattr(
            "jira_importer.config.excel_config.ExcelWorkbookManager",
            lambda path: _FakeWorkbookManager(path, fake_data),
        )
        monkeypatch.setattr("jira_importer.config.excel_config.ExcelTableReader", _FakeTableReaderWithMetadataVersion)

        caplog.set_level("WARNING")
        config = ExcelConfiguration(excel_path, cfg_req=7)

        assert config.get_value("metadata.version") == "7"
        assert any(
            "fallback metadata.version from CfgAutofieldValues" in record.message
            for record in caplog.records
            if record.levelname == "WARNING"
        )
        assert not any(
            "Missing version in configuration." in record.message
            for record in caplog.records
            if record.levelname == "ERROR"
        )

    def test_excel_version_prefers_config_rows_over_auto_field_values_fallback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Excel version should prefer key/value config rows over table fallback."""
        excel_path = _write_excel_placeholder(tmp_path)
        fake_data = {"metadata.version": "7"}

        monkeypatch.setattr(
            "jira_importer.config.excel_config.ExcelWorkbookManager",
            lambda path: _FakeWorkbookManager(path, fake_data),
        )
        monkeypatch.setattr("jira_importer.config.excel_config.ExcelTableReader", _FakeTableReaderWithMetadataVersion)

        caplog.set_level("WARNING")
        config = ExcelConfiguration(excel_path, cfg_req=7)

        assert config.get_value("metadata.version") == "7"
        assert not any(
            "fallback metadata.version from CfgAutofieldValues" in record.message
            for record in caplog.records
            if record.levelname == "WARNING"
        )

    def test_excel_cfgsettings_overrides_legacy_key_value_rows(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CfgSettings should take precedence over legacy Config key/value rows."""
        excel_path = _write_excel_placeholder(tmp_path)
        fake_data = {
            "metadata.version": "3",
            "app.import.auto_open_page": "yes",
        }

        monkeypatch.setattr(
            "jira_importer.config.excel_config.ExcelWorkbookManager",
            lambda path: _FakeWorkbookManager(path, fake_data),
        )
        monkeypatch.setattr("jira_importer.config.excel_config.ExcelTableReader", _FakeTableReaderWithCfgSettings)

        config = ExcelConfiguration(excel_path, cfg_req=7)
        assert config.get_value("metadata.version") == 7
        assert config.get_value("app.import.auto_open_page", expected_type=bool) is False

    def test_excel_basic_advanced_settings_merge_with_cfgsettings_precedence(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CfgBasic then CfgAdvanced then CfgSettings should merge with later layers winning."""
        excel_path = _write_excel_placeholder(tmp_path)
        fake_data = {"jira.project.key": "LEGACY"}

        monkeypatch.setattr(
            "jira_importer.config.excel_config.ExcelWorkbookManager",
            lambda path: _FakeWorkbookManager(path, fake_data),
        )
        monkeypatch.setattr(
            "jira_importer.config.excel_config.ExcelTableReader",
            _FakeTableReaderWithLayeredSettings,
        )

        config = ExcelConfiguration(excel_path, cfg_req=7)
        assert config.get_value("jira.project.key") == "BASIC"
        assert config.get_value("jira.connection.site_address") == "https://basic.example"
        assert config.get_value("jira.components_source") == "jira"
        assert config.get_value("metadata.version") == 8
        assert config.get_value("app.import.auto_open_page", expected_type=bool) is True

    def test_excel_cfgsettings_version_avoids_legacy_warning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """No legacy warning should be emitted when metadata.version is resolved from CfgSettings."""
        excel_path = _write_excel_placeholder(tmp_path)
        fake_data = {"jira.connection.site_address": "https://example.atlassian.net"}

        monkeypatch.setattr(
            "jira_importer.config.excel_config.ExcelWorkbookManager",
            lambda path: _FakeWorkbookManager(path, fake_data),
        )
        monkeypatch.setattr("jira_importer.config.excel_config.ExcelTableReader", _FakeTableReaderWithCfgSettings)

        caplog.set_level("WARNING")
        config = ExcelConfiguration(excel_path, cfg_req=7)
        assert config.get_value("metadata.version") == 7
        assert not any(
            "Using legacy configuration structure" in record.message
            for record in caplog.records
            if record.levelname == "WARNING"
        )

    def test_type_mismatch_message_and_details_are_aligned(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
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
