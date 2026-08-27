"""Unit tests for issue type configuration parsing."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from jira_importer.config.constants import LEVEL_1_INITIATIVE, LEVEL_2_EPIC, LEVEL_3_STORY, LEVEL_4_SUBTASK
from jira_importer.config.models.issuetypes import IssueType, IssueTypesConfig


class TestIssueTypeDefaultLevelForName:
    """IssueType.default_level_for_name maps common names onto hierarchy levels."""

    def test_maps_known_names(self) -> None:
        """Initiative, Epic, Sub-Task, and Story map to levels 1-4."""
        assert IssueType.default_level_for_name("Initiative") == LEVEL_1_INITIATIVE
        assert IssueType.default_level_for_name("epic") == LEVEL_2_EPIC
        assert IssueType.default_level_for_name("Story") == LEVEL_3_STORY
        assert IssueType.default_level_for_name("Sub-Task") == LEVEL_4_SUBTASK


class TestIssueTypesConfigFromConfig:
    """IssueTypesConfig.from_config must honor configured custom types."""

    def test_includes_initiative_from_jira_issuetypes(self) -> None:
        """CfgIssueTypes-shaped payload includes Initiative at level 1."""
        config_get: Callable[[str, Any], Any] = lambda k, d=None: (
            [
                {"name": "Story", "level": 3},
                {"name": "Initiative", "level": 1},
            ]
            if k == "jira.issuetypes"
            else d
        )

        parsed = IssueTypesConfig.from_config(config_get)

        assert "Initiative" in parsed.allowed_names
        assert parsed.level_of("initiative") == LEVEL_1_INITIATIVE
        assert parsed.level_of("Story") == LEVEL_3_STORY
