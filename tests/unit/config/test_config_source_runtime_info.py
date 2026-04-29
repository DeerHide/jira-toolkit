"""Tests for runtime config source display metadata."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from jira_importer import DEFAULT_CONFIG_FILENAME
from jira_importer.config.utils import get_config_source_runtime_info


def _build_args(
    input_file: str,
    *,
    config: str = DEFAULT_CONFIG_FILENAME,
    config_default: bool = False,
    config_input: bool = False,
    config_excel: bool = False,
) -> Namespace:
    return Namespace(
        input_file=input_file,
        config=config,
        config_default=config_default,
        config_input=config_input,
        config_excel=config_excel,
    )


class TestConfigSourceRuntimeInfo:
    """Tests for source labels and override hints shown at runtime."""

    def test_explicit_default_config_source(self, tmp_path: Path) -> None:
        """Shows default source when --config-default is enabled."""
        input_path = tmp_path / "input.xlsx"
        input_path.write_text("placeholder", encoding="utf-8")
        default_path = tmp_path / DEFAULT_CONFIG_FILENAME
        default_path.write_text("{}", encoding="utf-8")
        args = _build_args(str(input_path), config_default=True)

        source, hint = get_config_source_runtime_info(args, str(default_path))

        assert source == "default config file"
        assert "--config <path>" in hint

    def test_excel_config_source_when_embedded(self, tmp_path: Path) -> None:
        """Shows Excel source when input workbook is used as config."""
        input_path = tmp_path / "input.xlsx"
        input_path.write_text("placeholder", encoding="utf-8")
        args = _build_args(str(input_path))

        source, hint = get_config_source_runtime_info(args, str(input_path))

        assert source == "Excel sheet (Config tab in input workbook)"
        assert "--config-excel" not in hint
        assert "--config <path>" in hint

    def test_json_config_source_when_specific_config_provided(self, tmp_path: Path) -> None:
        """Shows JSON source when --config points to a non-default file."""
        input_path = tmp_path / "input.xlsx"
        input_path.write_text("placeholder", encoding="utf-8")
        custom_config = tmp_path / "custom.json"
        custom_config.write_text("{}", encoding="utf-8")
        args = _build_args(str(input_path), config=str(custom_config))

        source, hint = get_config_source_runtime_info(args, str(custom_config))

        assert source == "JSON config file"
        assert "--config-excel" in hint
