"""
Script Name: processor.py
Description: This script contains the processor for the Jira Importer.
Author: Julien (@tom4897)
License: MIT
Date: 2025
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Iterable, List, Sequence, Optional
import logging

from .models import (
    ColumnIndices,
    HeaderSchema,
    Problem,
    ProcessingReport,
    ProcessorResult,
    ValidationContext,
    ValidationResult,
)
from .validator import JiraImportValidator  # expects validate_row(...)
from .rules.registry import build_registry
from .fixes.registry import build_fix_registry
from .sources.csv_source import CsvSource
from .sources.xlsx_source import XlsxSource
from ..excel_io import ExcelWorkbookManager, ExcelProcessingMeta  # generic, lives top-level
from .config_view import ConfigView  # typed access over your config object

logger = logging.getLogger(__name__)

class ImportProcessor:
    """
    Orchestrates reading → validation/fixes → writing.

    Notes:
      - Pure validation happens in JiraImportValidator.
      - This class applies sparse patches (no in-place mutation in rules).
      - UI/reporting is delegated elsewhere (ProblemReporter).
    """

    def __init__(
        self,
        path: str | Path,
        config: object,
        ui: object | None = None,
        *,
        enable_excel_rules: bool = False,
        excel_rules_source: str | None = None,
        enable_auto_fix: bool = False,
    ) -> None:
        self.path = Path(path)
        self.config = config
        self.ui = ui
        self.enable_excel_rules = enable_excel_rules
        self.excel_rules_source = excel_rules_source
        self.enable_auto_fix = enable_auto_fix
        logger.debug(f"ImportProcessor initialized: path={self.path}, config={self.config}, enable_excel_rules={self.enable_excel_rules}, excel_rules_source={self.excel_rules_source}, enable_auto_fix={self.enable_auto_fix}")

    def process(self) -> ProcessorResult:
        # Source
        header_schema, rows = self._read_source()

        # Resolve indices once (based on header + config mappings)
        indices = self._extract_indices(header_schema)

        logger.debug(f"Compose rules/fixes/validator")
        cfg_view = ConfigView(self.config)
        rule_registry = build_registry(cfg_view, self._excel_loader_ctx())
        rules = rule_registry.get_rules()

        fix_registry = build_fix_registry(cfg_view) if self.enable_auto_fix else None
        validator = JiraImportValidator(rules=rules, fix_registry=fix_registry)

        skip_enabled = cfg_view.get("validation.skip_rowtype", True)
        skip_issuetypes = cfg_view.get("validation.skip_issuetypes", ["comment", "note", "skip"])

        logger.debug(f"Validate + apply patches row-by-row")
        problems: list[Problem] = []
        normalized_rows = _deep_copy_rows(rows)  # we'll patch into this
        complex_children = []  # fill from your rules if needed

        issue_id_seen: dict[str, None] = {}
        skipped_rows = 0

        # Pre-populate issue_id_seen with existing Issue IDs to avoid conflicts during auto-fixing
        self._pre_populate_issue_ids(rows, indices, issue_id_seen)

        logger.debug(f"row_index is 1-based (header = 1), so first data row is 2")
        for i, row in enumerate(rows, start=2):
            # Skip rows with RowType = "SKIP"
            if self._should_skip_row_rowtype(row, indices, skip_enabled):
                skipped_rows += 1
                logger.debug(f"Skipping row {i} (RowType = SKIP)")
                continue

            # Skip rows with Issue Type = "Epic"
            if self._should_skip_row_issuetype(row, indices, skip_issuetypes):
                skipped_rows += 1
                logger.debug(f"Skipping row {i} (Issue Type = EPIC)")
                continue

            ctx = ValidationContext(
                row_index=i,
                config=cfg_view,
                feature_flags={"excel_rules": self.enable_excel_rules},
                auto_fix_enabled=self.enable_auto_fix,
                issue_id_seen=issue_id_seen,
            )
            result: ValidationResult = validator.validate_row(row, indices, ctx)

            if result.patch:
                _apply_patch_inplace(normalized_rows, row_idx=i - 2, patch=result.patch)

            if result.problems:
                problems.extend(result.problems)

        # TODO: Add a report for the skipped rows
        if skipped_rows > 0:
            logger.info(f"Skipped {skipped_rows} rows with RowType = SKIP")

        logger.debug(f"Build processor result")
        report = ProcessingReport.from_problems(problems, auto_fix_enabled=self.enable_auto_fix)
        proc_result = ProcessorResult(
            header=header_schema.normalized,
            rows=normalized_rows,
            problems=problems,
            report=report,
            complex_children=complex_children,
            indices=indices,
        )

        logger.debug(f"Optional: write back to Excel (metadata/report)")
        if self._is_excel(self.path):
            pass
            #self._write_excel_meta(proc_result)

        return proc_result

    # Internals

    def _read_source(self) -> tuple[HeaderSchema, list[list[object]]]:
        if self._is_excel(self.path):
            mgr = ExcelWorkbookManager(self.path)
            mgr.load()
            header, rows = XlsxSource(mgr, data_sheet="Dataset").read()
            self._excel_mgr = mgr  # set for lifetime of this call
            return header, rows
        else:
            return CsvSource(self.path).read()

    def _extract_indices(self, header: HeaderSchema) -> ColumnIndices:
        """
        Build ColumnIndices from the normalized header + config mappings.
        """
        name_to_pos = {name.lower(): idx for idx, name in enumerate(header.normalized)}
        def pos(key: str) -> int | None:
            return name_to_pos.get(key.lower())

        return ColumnIndices(
            summary=pos("summary"),
            priority=pos("priority"),
            issuetype=pos("issuetype"),
            issue_id=pos("issue id"),
            project_key=pos("project key"),
            assignee=pos("assignee"),
            description=pos("description"),
            parent=pos("parent"),
            epic_link=pos("epic link"),
            epic_name=pos("epic name"),
            component=pos("component"),
            fixversion=pos("fixversion"),
            origest=pos("origest"),
            estimate=pos("estimate"),
            sprint=pos("sprint"),
            rowtype=pos("rowtype"),
            child_issue_indices=[i for i, n in enumerate(header.normalized) if n.startswith("child issue")],
        )

    def _excel_loader_ctx(self):
        """
        Return an object the RuleRegistry can use to load Excel-defined rules when enable_excel_rules is True.
        """
        if not self.enable_excel_rules:
            return None

        source = self.excel_rules_source or (str(self.path) if self._is_excel(self.path) else None)
        if not source:
            return None

        if self._is_excel(Path(source)):
            mgr = getattr(self, "_excel_mgr", None)
            if mgr is None or mgr.path != Path(source):
                mgr = ExcelWorkbookManager(source)
                mgr.load()
            return mgr  # ExcelRuleLoader can wrap this manager
        return Path(source)

    def _write_excel_meta(self, result: ProcessorResult) -> None:
        mgr: ExcelWorkbookManager | None = getattr(self, "_excel_mgr", None)
        if not mgr:
            return

        from datetime import datetime, timezone

        meta = ExcelProcessingMeta(
            run_at_iso=datetime.now(timezone.utc).isoformat(),
            app_version=str(getattr(self.config, "version", "")) or "unknown",
            source_path=str(mgr.path),
            rows_in=len(result.rows),
            rows_out=len(result.rows),
            errors=result.report.errors,
            warnings=result.report.warnings,
            fixes=result.report.fixes,
            auto_fix_enabled=self.enable_auto_fix,
        )
        mgr.write_processing_meta(meta)
        agg = [
            ("error", result.report.errors, "validation.errors"),
            ("warning", result.report.warnings, "validation.warnings"),
            ("fix", result.report.fixes, "auto.fixes"),
        ]
        mgr.write_report_table(agg)
        mgr.save()
        mgr.close()

    @staticmethod
    def _is_excel(path: Path) -> bool:
        return path.suffix.lower() in {".xlsx", ".xlsm"}

    def _should_skip_row_rowtype(self, row: Sequence[object], indices: ColumnIndices, skip_enabled: bool) -> bool:
        """
        Check if a row should be skipped based on RowType = "SKIP".

        Args:
            row: The row data to check
            indices: Column indices for accessing row data
            config_view: Configuration view to check if skipping is enabled

        Returns:
            True if the row should be skipped, False otherwise
        """
        # Check if row skipping is enabled in config
        if not skip_enabled:
            return False

        if indices.rowtype is None:
            return False

        if indices.rowtype >= len(row):
            return False

        rowtype_value = row[indices.rowtype]
        if rowtype_value is None:
            return False

        return str(rowtype_value).strip().upper() == "SKIP"

    def _should_skip_row_issuetype(self, row: Sequence[object], indices: ColumnIndices, skip_issuetypes: list[str]) -> bool:
        """
        Check if a row should be skipped based on Issue Type = "Epic".
        """
        rowtype_value = row[indices.issuetype]
        if rowtype_value is None:
            return False

        return str(rowtype_value).strip().upper() in skip_issuetypes

    def _pre_populate_issue_ids(self, rows: list[Sequence[object]], indices: ColumnIndices, issue_id_seen: dict[str, None]) -> None:
        """
        Pre-populates the issue_id_seen dictionary with all existing Issue IDs from the source data.
        This is necessary to avoid conflicts when auto-fixing AssignIssueIdFixer.
        """
        if indices.issue_id is None:
            return

        for row in rows:
            issue_id_value = self._cell_str(row, indices.issue_id)
            if issue_id_value:  # _cell_str already handles None, empty strings, etc.
                issue_id_seen[issue_id_value] = None

    def _cell_str(self, row: Sequence[object], idx: Optional[int]) -> str:
        """Helper function to safely extract string values from cells."""
        if idx is None or idx < 0 or idx >= len(row):
            return ""
        v = row[idx]
        return "" if v is None else str(v).strip()


# Helpers

def _deep_copy_rows(rows: Sequence[Sequence[object]]) -> list[list[object]]:
    # Rows are shallow (cells are scalars)
    return [list(r) for r in rows]

def _apply_patch_inplace(table: list[list[object]], *, row_idx: int, patch: dict[int, str]) -> None:
    """
    Apply sparse index→value patch into table[row_idx].
    All patched values are strings (post-normalization contract).
    """
    row = table[row_idx]
    for col_idx, value in patch.items():
        # Ensure row is long enough; guard against malformed indices.
        if 0 <= col_idx < len(row):
            row[col_idx] = value
