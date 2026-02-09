"""Runner for the import pipeline.

Author:
    Julien (@tom4897)
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from ..app import App
from ..errors import ProcessingError
from ..utils import open_jira_filter
from .models import Problem, ProblemSeverity, ProcessorResult
from .processor import ImportProcessor
from .reporting import EMO_ERROR, EMO_WARN, CloudReportReporter, ProblemReporter, ReportOptions
from .sinks.cloud_sink import write_cloud
from .sinks.csv_sink import write_csv


@dataclass
class PipelineOptions:
    """Options for pipeline execution."""

    enable_excel_rules: bool = False
    excel_rules_source: str | None = None
    enable_auto_fix: bool = False
    no_report: bool = False
    dry_run: bool = False
    fix_cloud_estimates: bool = False
    debug: bool = False
    cloud_debug_payloads: bool = False
    auto_reply: bool | None = None


@dataclass
class PipelineContext:
    """Context for pipeline execution."""

    input_path: Path
    config: Any
    output_target: Literal["cloud", "csv"]
    output_filepath: Path | None = None  # For CSV output
    output_dir: Path | None = None  # For cloud debug output
    ui: Any = None  # ConsoleIO
    logger: logging.Logger | None = None
    app: Any = None  # App instance


class ImportRunner:
    """Orchestrates the complete import pipeline execution.

    Handles:
    - Creating and running ImportProcessor
    - Problem reporting
    - User interaction (prompts)
    - Output routing (cloud vs CSV)
    - Exit code calculation
    """

    def __init__(self, context: PipelineContext, options: PipelineOptions) -> None:
        """Initialize the runner."""
        self.context = context
        self.options = options

    def _calculate_exit_code(self, result: ProcessorResult) -> int:
        """Calculate exit code based on validation errors.

        Returns:
            0 if no errors, 1 otherwise.
        """
        return 0 if result.report.errors == 0 else 1

    def _display_issue_summary(self, result: ProcessorResult, critical_problems: list[Problem]) -> None:
        """Display a concise summary of issues before prompting.

        Shows counts of critical problems, errors, warnings, and output target context.

        Args:
            result: The processor result containing validation report.
            critical_problems: List of critical problems found.
        """
        critical_count = len(critical_problems)
        error_count = result.report.errors
        warning_count = result.report.warnings

        # Build summary parts
        parts = []
        if critical_count > 0:
            parts.append(f"{EMO_ERROR} {critical_count} critical")
        if error_count > 0:
            parts.append(f"{EMO_ERROR} {error_count} error{'s' if error_count != 1 else ''}")
        if warning_count > 0:
            parts.append(f"{EMO_WARN} {warning_count} warning{'s' if warning_count != 1 else ''}")

        if parts:
            summary = "  ".join(parts)
            output_target_info = f" → {self.context.output_target.upper()} output"
            self.context.ui.info(f"Summary: {summary}{output_target_info}")

    def _should_prompt_for_issues(self, result: ProcessorResult, critical_problems: list[Problem]) -> bool:
        """Determine if prompting is needed for validation issues.

        Args:
            result: The processor result containing validation report.
            critical_problems: List of critical problems found.

        Returns:
            True if prompting is needed, False otherwise.
        """
        # Don't prompt in dry-run mode
        if self.options.dry_run:
            return False
        # Prompt if there are critical problems or errors
        return len(critical_problems) > 0 or result.report.errors > 0

    def _build_prompt_message(self, critical_problems: list[Problem], error_count: int) -> str:
        """Build a context-aware prompt message based on what issues exist.

        Args:
            critical_problems: List of critical problems found.
            error_count: Number of validation errors.

        Returns:
            A prompt message string.
        """
        has_critical = len(critical_problems) > 0
        has_errors = error_count > 0

        if has_critical and has_errors:
            return "Critical validation issues and errors found. Do you want to continue?"
        elif has_critical:
            return "Critical validation issues found. Do you want to continue?"
        elif has_errors:
            return "Validation errors found. Do you want to continue?"
        else:
            # Should not reach here if _should_prompt_for_issues is used correctly
            return "Validation issues found. Do you want to continue?"

    def _create_processor(self) -> ImportProcessor:
        """Create the import processor."""
        processor = ImportProcessor(
            path=self.context.input_path,
            config=self.context.config,
            ui=self.context.ui,  # pipeline is UI-agnostic; reporting handled below
            enable_excel_rules=self.options.enable_excel_rules,
            excel_rules_source=str(self.context.input_path) if self.options.enable_excel_rules else None,
            enable_auto_fix=self.options.enable_auto_fix,
        )
        if self.context.logger:
            self.context.logger.debug(
                "Processor:\n%s\nconfig: %s\nenable_excel_rules: %s\nexcel_rules_source: %s\nenable_auto_fix: %s",
                processor.path,
                processor.config,
                processor.enable_excel_rules,
                processor.excel_rules_source,
                processor.enable_auto_fix,
            )
        return processor

    def _dry_run_sink(self, result: ProcessorResult) -> int:
        """Handle dry-run mode and return exit code."""
        self.context.ui.info("Dry-run mode: Processing complete, stopping before sinks")

        # Check for critical problems and errors
        critical_problems = [p for p in result.problems if p.severity == ProblemSeverity.CRITICAL]
        has_errors = result.report.errors > 0
        has_critical = len(critical_problems) > 0

        if has_errors or has_critical:
            # Adjust success message when issues exist
            self.context.ui.warning(
                f"Dry-run completed with {len(result.rows)} rows processed, but validation issues were found."
            )

            if has_critical:
                self.context.ui.error(
                    f"{len(critical_problems)} critical issue(s) found. These must be fixed before import."
                )
            else:
                self.context.ui.error("Validation errors found. Please fix these before running the import.")
                self.context.ui.error("Importing this dataset, as-is, will likely fail.")

            if self.context.output_target == "cloud":
                self.context.ui.hint(
                    "Consider using CSV output (no --cloud) mode to see the full dataset and fix the issues. "
                    "Using --cloud with errors may produce unwanted results and partially imported work items."
                )
        else:
            self.context.ui.success(f"Dry-run completed successfully. {len(result.rows)} rows processed.")
            if result.report.warnings > 0:
                self.context.ui.hint("Dry-run completed with warnings. Review before running the import.")
            self.context.ui.hint("Remove --dry-run flag to run with actual output")

        result_code = self._calculate_exit_code(result)
        self.context.ui.lf()
        self.context.ui.full_panel(self.context.ui.fmt.success("Dry-run complete. You can close this window now."))
        self.context.app.event_close(exit_code=result_code, cleanup=True)
        return result_code

    def _cloud_sink(self, result: ProcessorResult) -> int:
        """Handle cloud output and return exit code."""
        self.context.ui.info("Output target: Jira Cloud API")

        # Check for critical assignee or team errors before proceeding
        critical_assignee_errors = [
            p for p in result.problems if p.severity == ProblemSeverity.CRITICAL and p.code.startswith("assignee.")
        ]
        critical_team_errors = [
            p for p in result.problems if p.severity == ProblemSeverity.CRITICAL and p.code.startswith("team.")
        ]
        if critical_assignee_errors or critical_team_errors:
            if critical_assignee_errors:
                self.context.ui.error("Critical assignee errors found - cannot proceed with cloud import:")
                for error in critical_assignee_errors:
                    self.context.ui.error(f"  Row {error.row_index}: {error.message}")
            if critical_team_errors:
                self.context.ui.error("Critical team errors found - cannot proceed with cloud import:")
                for error in critical_team_errors:
                    self.context.ui.error(f"  Row {error.row_index}: {error.message}")
            App.event_fatal(exit_code=4, message="Critical assignee/team errors prevent cloud import", args=None)

        try:
            # Write payloads if debug mode is enabled or cloud debug flag is set
            debug_output_dir = (
                self.context.output_dir if (self.options.debug or self.options.cloud_debug_payloads) else None
            )
            report = write_cloud(
                result, self.context.config, dry_run=False, output_dir=debug_output_dir, ui=self.context.ui
            )
            self.context.ui.success(
                f"Cloud import: created={report.created}, failed={report.failed}, batches={report.batches}"
            )
            if debug_output_dir:
                self.context.ui.info(f"Jira Cloud payloads written to: {debug_output_dir}")
            if report.created_issue_keys:
                # Display created issue keys in a user-friendly format
                issue_keys_str = ", ".join(report.created_issue_keys)
                self.context.ui.info(f"{issue_keys_str.count(',') + 1} issues created: {issue_keys_str}")
                if self.context.logger:
                    self.context.logger.info(f"Created Jira issues: {issue_keys_str}")

                # Open Jira filter if auto_open_page is enabled
                if (
                    self.context.config.get_value("app.import.auto_open_page", default=False, expected_type=bool)
                    and self.context.logger
                ):
                    open_jira_filter(
                        self.context.config, report.created_issue_keys, self.context.ui, self.context.logger
                    )

            if report.failed > 0:
                CloudReportReporter().render_errors(report, self.context.ui)
        except ProcessingError:
            # Let domain errors bubble up to the outer handler for rich reporting
            raise
        except Exception as exc:  # pylint: disable=broad-except
            # Unexpected internal error during cloud import
            if self.context.logger:
                self.context.logger.exception("Cloud import failed: %s", exc)
            App.event_fatal(exit_code=3, message=f"Cloud import failed: {exc}", args=None)

        # non-zero exit if there were errors (so CI can gate)
        result_code = self._calculate_exit_code(result)
        # End after cloud path
        self.context.ui.lf()
        self.context.ui.full_panel(self.context.ui.fmt.success("Processing complete. You can close this window now."))
        self.context.app.event_close(exit_code=result_code, cleanup=True)
        return result_code

    def _create_modified_config(self) -> Any | None:
        """Create modified config for fix_cloud_estimates if needed.

        Returns:
            Modified config object or None if modification not needed.
        """
        if not self.options.fix_cloud_estimates or self.context.output_target != "csv":
            return None

        if isinstance(self.context.config, dict):
            return {**self.context.config, "jira.cloud.estimate.multiply_by_60": True}

        # For non-dict config objects, create a wrapper dict
        class _Cfg(dict):
            def get(self, k, d=None):  # type: ignore[override]
                return super().get(k, d)

        temp_config = _Cfg()
        temp_config.update({"jira.cloud.estimate.multiply_by_60": True})
        return temp_config

    def _csv_sink(self, result: ProcessorResult) -> int:
        """Handle CSV output and return exit code."""
        # Apply Jira Cloud x60 quirk in CSV sink only, if requested
        temp_config = self._create_modified_config()

        if self.context.output_filepath is None:
            raise ValueError("output_filepath is required for CSV output")

        write_csv(
            result, self.context.output_filepath, config=temp_config if temp_config is not None else self.context.config
        )
        self.context.ui.say(f"Output Import CSV Ready → {self.context.ui.fmt.path(str(self.context.output_filepath))}")
        if self.context.logger:
            self.context.logger.info("Wrote output CSV → %s", self.context.output_filepath)

        # non-zero exit if there were errors (so CI can gate)
        return self._calculate_exit_code(result)

    def _log_run_summary(self, result: ProcessorResult) -> None:
        """Log a concise, structured summary of the run to the logger."""
        if not self.context.logger:
            return

        # Row counts from processor metadata, with safe fallbacks
        rows_in = getattr(result, "original_row_count", None)
        rows_out = getattr(result, "processed_row_count", None)
        skipped = getattr(result, "skipped_row_count", None)

        if rows_out is None:
            rows_out = len(result.rows)
        if skipped is None:
            skipped = 0
        if rows_in is None:
            rows_in = rows_out + skipped

        if self.context.output_target == "csv" and self.context.output_filepath is not None:
            output_info = str(self.context.output_filepath)
        elif self.context.output_target == "cloud":
            output_info = "Jira Cloud API"
        else:
            output_info = ""

        self.context.logger.info(
            "Run summary: rows_in=%s rows_out=%s skipped=%s errors=%s warnings=%s fixes=%s "
            "target=%s dry_run=%s output=%s",
            rows_in,
            rows_out,
            skipped,
            result.report.errors,
            result.report.warnings,
            result.report.fixes,
            self.context.output_target,
            self.options.dry_run,
            output_info,
        )

    def run(self) -> int:
        """Execute the complete pipeline and return exit code."""
        # 1. Create and run processor
        processor = self._create_processor()
        result = processor.process()
        # 2. Report problems (console + logs)
        if not self.options.no_report:
            report_options = ReportOptions(show_details=True, show_aggregate_by_code=False)
        else:
            report_options = ReportOptions(show_details=False, show_aggregate_by_code=True)

        reporter = ProblemReporter(options=report_options)
        reporter.render(result)
        if self.context.logger:
            # Always log full report: both aggregate and details, without truncation
            for line in reporter.build_plain_report_lines(
                result,
                no_truncate=True,
                force_show_aggregate=True,
                force_show_details=True,
            ):
                self.context.logger.info(line)

            # Log concise summary line for downstream consumers
            self._log_run_summary(result)

        # 3. Handle auto-fix warnings
        if not processor.enable_auto_fix and not self.options.dry_run:
            if result.report.errors > 0:
                self.context.ui.warning("Auto-fix is disabled. Please fix the issues manually.")
                self.context.ui.hint(
                    "You can enable auto-fix by adding the following to your configuration file or by using the --auto-fix flag."
                )

        # 3.5. Calculate critical problems once for reuse
        critical_problems = [p for p in result.problems if p.severity == ProblemSeverity.CRITICAL]

        # 3.6. Early exit for auto-no flag (JT-220)
        # If auto-no is set and there are issues requiring prompts, exit immediately
        # Skip early exit in dry-run mode since no prompts will be shown anyway
        if self.options.auto_reply is False and not self.options.dry_run:
            if critical_problems or result.report.errors > 0:
                self.context.ui.error("Auto-no flag is set. Aborting due to validation issues.")
                self.context.app.event_abort(exit_code=1, message="User cancelled (auto-no) due to validation issues.")
                return 1

        # 4. Check critical problems
        if critical_problems:
            # If --auto-yes and --cloud, terminate immediately
            if self.options.auto_reply is True and self.context.output_target == "cloud":
                critical_count = len(critical_problems)
                self.context.ui.error(
                    f"Cannot proceed with --auto-yes and --cloud when {critical_count} critical issue(s) are present. "
                    "The --auto-yes flag skips confirmation prompts, but critical issues require review before making API calls. "
                    "Please fix the critical issues first, remove --auto-yes to get confirmation prompts, or use CSV output mode instead."
                )
                self.context.app.event_abort(
                    exit_code=1, message=f"Critical validation issues ({critical_count}) with --auto-yes and --cloud"
                )

        # 4.5. Unified prompt for validation issues (JT-218)
        # Consolidate critical and error prompts into a single prompt
        if self._should_prompt_for_issues(result, critical_problems):
            # Display summary before prompting (JT-222)
            self._display_issue_summary(result, critical_problems)

            # Build context-aware prompt message
            prompt_message = self._build_prompt_message(critical_problems, result.report.errors)

            # Single unified prompt
            user_continues = self.context.ui.prompt_yes_no(
                prompt_message, default=False, auto_reply=self.options.auto_reply
            )
            # Consistent messaging for user feedback (JT-223)
            if not user_continues:
                # Determine cancellation message based on what issues exist
                if critical_problems:
                    self.context.app.event_abort(exit_code=1, message="User cancelled due to critical issues.")
                else:
                    self.context.app.event_abort(exit_code=1, message="User cancelled due to validation errors.")
            elif critical_problems and result.report.errors > 0:
                self.context.ui.success("Continuing with critical issues and errors...")
            elif critical_problems:
                self.context.ui.warning("Continuing with critical issues...")
            elif result.report.errors > 0:
                self.context.ui.warning("Continuing with validation errors...")
            else:
                # Defensive fallback
                self.context.ui.success("Continuing...")
        elif self.options.dry_run and (critical_problems or result.report.errors > 0):
            # Dry-run mode: inform user that prompts are skipped (JT-221)
            self.context.ui.info(
                "Dry-run mode: Validation issues found but skipping prompts since no actual output will be generated."
            )

        # 5. Handle dry-run
        if self.options.dry_run:
            return self._dry_run_sink(result)

        # 6. Route to appropriate sink
        if self.context.output_target == "cloud":
            return self._cloud_sink(result)
        elif self.context.output_target == "csv":
            return self._csv_sink(result)
        else:
            self.context.ui.error("Invalid output target.")
            self.context.app.event_abort(exit_code=1, message="Invalid output target.")
            return 1
