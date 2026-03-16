"""Unit tests for ExcelConfiguration get_value table fallback."""

from __future__ import annotations

from pathlib import Path

import pytest

from jira_importer.config.config_models import (
    ExcelTableConfig,
    IssueTypeConfig,
    PriorityConfig,
)
from jira_importer.config.excel_config import ExcelConfiguration


def _excel_template_path() -> Path:
    """Return path to ImportTemplate.xlsx."""
    return Path(__file__).resolve().parent.parent.parent.parent / "resources" / "templates" / "ImportTemplate.xlsx"


class TestExcelConfigurationGetValueTableFallback:
    """Tests for ExcelConfiguration.get_value table fallback for jira.issuetypes and jira.priorities."""

    def test_get_value_jira_issuetypes_from_table_when_content_empty(self) -> None:
        """get_value('jira.issuetypes', None) returns data from CfgIssueTypes when content has no value."""
        path = _excel_template_path()
        if not path.is_file():
            pytest.skip(f"Template not found: {path}")

        cfg = ExcelConfiguration(str(path))
        cfg.content = {}  # Simulate no jira.issuetypes in Config sheet
        cfg.table_config = ExcelTableConfig(
            issue_types=[
                IssueTypeConfig(name="Story"),
                IssueTypeConfig(name="Sub-task"),
            ],
        )

        result = cfg.get_value("jira.issuetypes", None)

        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 2
        names = [it["name"] for it in result]
        assert "Story" in names
        assert "Sub-task" in names
        for it in result:
            assert "name" in it
            assert "level" in it
            assert isinstance(it["level"], int)

    def test_get_value_jira_priorities_from_table_when_content_empty(self) -> None:
        """get_value('jira.priorities', None) returns data from CfgPriorities when content has no value."""
        path = _excel_template_path()
        if not path.is_file():
            pytest.skip(f"Template not found: {path}")

        cfg = ExcelConfiguration(str(path))
        cfg.content = {}
        cfg.table_config = ExcelTableConfig(
            priorities=[
                PriorityConfig(name="High"),
                PriorityConfig(name="Low"),
                PriorityConfig(name="Medium"),
            ],
        )

        result = cfg.get_value("jira.priorities", None)

        assert result is not None
        assert result == ["High", "Low", "Medium"]

    def test_get_value_jira_issuetypes_content_wins_over_table(self) -> None:
        """When content has jira.issuetypes, table_config is not used."""
        path = _excel_template_path()
        if not path.is_file():
            pytest.skip(f"Template not found: {path}")

        cfg = ExcelConfiguration(str(path))
        cfg.content = {
            "jira": {
                "issuetypes": [
                    {"name": "Epic", "level": 2},
                    {"name": "Task", "level": 3},
                ],
            },
        }
        cfg.table_config = ExcelTableConfig(
            issue_types=[IssueTypeConfig(name="Story"), IssueTypeConfig(name="Bug")],
        )

        result = cfg.get_value("jira.issuetypes", None)

        assert result is not None
        assert len(result) == 2
        assert result[0]["name"] == "Epic"
        assert result[1]["name"] == "Task"

    def test_get_value_jira_priorities_content_wins_over_table(self) -> None:
        """When content has jira.priorities, table_config is not used."""
        path = _excel_template_path()
        if not path.is_file():
            pytest.skip(f"Template not found: {path}")

        cfg = ExcelConfiguration(str(path))
        cfg.content = {"jira": {"priorities": ["Highest", "Lowest"]}}
        cfg.table_config = ExcelTableConfig(
            priorities=[PriorityConfig(name="High"), PriorityConfig(name="Low")],
        )

        result = cfg.get_value("jira.priorities", None)

        assert result is not None
        assert result == ["Highest", "Lowest"]
