"""Integration tests for team resolution with JSON config (jira.teams).

Verifies that when using JsonConfiguration with jira.teams, the team rule
and resolver see table config and do not report team.no_table_config.
"""

from __future__ import annotations

from pathlib import Path

from jira_importer.config.config_view import ConfigView
from jira_importer.config.json_config import JsonConfiguration
from jira_importer.import_pipeline.fixes.team_resolver import TeamResolverRule
from jira_importer.import_pipeline.models import (
    ColumnIndices,
    ValidationContext,
)


class TestTeamResolverWithJsonConfig:
    """Team resolution uses get_table_config() from JsonConfiguration."""

    def test_team_rule_no_table_config_error_when_jira_teams_present(
        self, tmp_path: Path
    ) -> None:
        """With jira.teams in JSON config, team rule does not report team.no_table_config."""
        config_path = tmp_path / "config.json"
        config_path.write_text(
            '{"metadata":{"version":7},"jira":{"teams":[{"name":"Backend","id":"12345"}]}}',
            encoding="utf-8",
        )
        config = JsonConfiguration(path=str(config_path))
        cfg_view = ConfigView(config)

        indices = ColumnIndices(
            summary=0,
            priority=1,
            issuetype=2,
            issue_id=3,
            team=4,
            team_name=None,
        )
        row: list[object] = ["Summary", "High", "Task", "PROJ-1", "Backend"]
        ctx = ValidationContext(
            row_index=2,
            config=cfg_view,
            feature_flags={},
            auto_fix_enabled=True,
            issue_id_seen={},
            issue_data={},
            custom_field_configs=None,
        )

        rule = TeamResolverRule()
        result = rule.apply(row, indices, ctx)

        # Should not have "no CfgTeams table available"
        problem_codes = [p.code for p in result.problems]
        assert "team.no_table_config" not in problem_codes

        # Team "Backend" is a name, so we expect a FIX (will resolve to ID)
        assert len(result.problems) == 1
        assert result.problems[0].code == "team.display_name"
        assert result.problems[0].severity.value == "fix"

    def test_team_rule_accepts_team_id_when_jira_teams_present(
        self, tmp_path: Path
    ) -> None:
        """When row has Team ID that exists in jira.teams, no problem is reported."""
        config_path = tmp_path / "config.json"
        config_path.write_text(
            '{"metadata":{"version":7},"jira":{"teams":[{"name":"Backend","id":"12345"}]}}',
            encoding="utf-8",
        )
        config = JsonConfiguration(path=str(config_path))
        cfg_view = ConfigView(config)

        indices = ColumnIndices(
            summary=0,
            priority=1,
            issuetype=2,
            issue_id=3,
            team=4,
            team_name=None,
        )
        row = ["Summary", "High", "Task", "PROJ-1", "12345"]
        ctx = ValidationContext(
            row_index=2,
            config=cfg_view,
            feature_flags={},
            auto_fix_enabled=True,
            issue_id_seen={},
            issue_data={},
            custom_field_configs=None,
        )

        rule = TeamResolverRule()
        result = rule.apply(row, indices, ctx)

        assert len(result.problems) == 0
