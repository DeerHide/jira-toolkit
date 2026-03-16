"""Unit tests for MetadataCache extensions (get_project, get_priorities, user_exists, etc.)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from jira_importer.import_pipeline.cloud.client import JiraCloudClient
from jira_importer.import_pipeline.cloud.metadata import MetadataCache


class TestMetadataCacheExtensions:
    """Tests for MetadataCache get_project, get_priorities, get_project_components, etc."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create mock JiraCloudClient."""
        return MagicMock(spec=JiraCloudClient)

    def test_get_project_success(self, mock_client: MagicMock) -> None:
        """Test get_project returns project when API returns 200."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"key": "TEST", "id": "10000", "name": "Test Project"}
        mock_client.get.return_value = mock_resp

        cache = MetadataCache(client=mock_client)
        proj = cache.get_project("TEST")

        assert proj is not None
        assert proj["key"] == "TEST"
        mock_client.get.assert_called_once_with("project/TEST")

    def test_get_project_not_found(self, mock_client: MagicMock) -> None:
        """Test get_project returns None when API returns 404."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_client.get.return_value = mock_resp

        cache = MetadataCache(client=mock_client)
        proj = cache.get_project("MISSING")

        assert proj is None
        # Second call should use cache
        proj2 = cache.get_project("MISSING")
        assert proj2 is None
        mock_client.get.assert_called_once()

    def test_get_priorities(self, mock_client: MagicMock) -> None:
        """Test get_priorities returns list from API."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"id": "1", "name": "Highest"},
            {"id": "2", "name": "High"},
        ]
        mock_client.get.return_value = mock_resp

        cache = MetadataCache(client=mock_client)
        priorities = cache.get_priorities()

        assert len(priorities) == 2
        assert priorities[0]["name"] == "Highest"
        mock_client.get.assert_called_once_with("priority")

    def test_user_exists_true(self, mock_client: MagicMock) -> None:
        """Test user_exists returns True when API returns 200."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.ok = True
        mock_client.get.return_value = mock_resp

        cache = MetadataCache(client=mock_client)
        assert cache.user_exists("5b10ac8d82e05b22cc7d4ef5") is True
        mock_client.get.assert_called_once_with(
            "user", params={"accountId": "5b10ac8d82e05b22cc7d4ef5"}
        )

    def test_user_exists_false_on_404(self, mock_client: MagicMock) -> None:
        """Test user_exists returns False when API returns 404."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_client.get.return_value = mock_resp

        cache = MetadataCache(client=mock_client)
        assert cache.user_exists("nonexistent-id") is False

    def test_user_exists_cached(self, mock_client: MagicMock) -> None:
        """Test user_exists results are cached."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.ok = True
        mock_client.get.return_value = mock_resp

        cache = MetadataCache(client=mock_client)
        assert cache.user_exists("id123") is True
        assert cache.user_exists("id123") is True
        mock_client.get.assert_called_once()
