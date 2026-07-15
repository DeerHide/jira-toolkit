"""Unit tests for CLI output/debug flag interactions."""

from __future__ import annotations

import pytest

from jira_importer.app import App


class TestCliOutputFlags:
    """CLI flags for cloud debug payloads and dry-run."""

    def test_cld_implies_cloud_output_target(self) -> None:
        """-cld alone selects cloud and sets cloud_debug_payloads."""
        args = App.parse_args(["dataset.xlsx", "-cld"])

        assert args.cloud_debug_payloads is True
        assert getattr(args, "output_target_cloud", False) is False
        assert App.get_output_target_from_args(args) == "cloud"

    def test_cl_and_cld_select_cloud(self) -> None:
        """-cl -cld selects cloud output with both flags set."""
        args = App.parse_args(["dataset.xlsx", "-cl", "-cld"])

        assert args.output_target_cloud is True
        assert args.cloud_debug_payloads is True
        assert App.get_output_target_from_args(args) == "cloud"

    def test_cl_alone_selects_cloud_without_debug_payloads(self) -> None:
        """-cl alone selects cloud and does not enable payload dump flag."""
        args = App.parse_args(["dataset.xlsx", "-cl"])

        assert args.output_target_cloud is True
        assert args.cloud_debug_payloads is False
        assert App.get_output_target_from_args(args) == "cloud"

    def test_dr_alone_keeps_csv_target(self) -> None:
        """-dr without -cld still parses and defaults to csv."""
        args = App.parse_args(["dataset.xlsx", "-dr"])

        assert args.dry_run is True
        assert App.get_output_target_from_args(args) == "csv"

    def test_cl_and_dr_select_cloud(self) -> None:
        """-cl -dr is allowed; dry-run with cloud target."""
        args = App.parse_args(["dataset.xlsx", "-cl", "-dr"])

        assert args.dry_run is True
        assert App.get_output_target_from_args(args) == "cloud"

    @pytest.mark.parametrize(
        "argv",
        [
            ["dataset.xlsx", "-cld", "-dr"],
            ["dataset.xlsx", "-dr", "-cld"],
        ],
    )
    def test_cld_and_dr_are_incompatible(self, argv: list[str]) -> None:
        """-cld and -dr together are rejected at parse time."""
        with pytest.raises(SystemExit) as exc_info:
            App.parse_args(argv)

        assert exc_info.value.code == 2
