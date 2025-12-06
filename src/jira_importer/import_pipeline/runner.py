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
from .models import ProblemSeverity, ProcessorResult
from .processor import ImportProcessor
from .reporting import CloudReportReporter, ProblemReporter, ReportOptions
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
        self.context.ui.success(f"Dry-run completed successfully. {len(result.rows)} rows processed.")
        self.context.ui.hint("Remove --dry-run flag to run with actual output")
        result_code = self._calculate_exit_code(result)
        self.context.ui.lf()
        self.context.ui.full_panel(self.context.ui.fmt.success("Dry-run complete. You can close this window now."))
        self.context.app.event_close(exit_code=result_code, cleanup=True)
        return result_code

    def _cloud_sink(self, result: ProcessorResult) -> int:
        """Handle cloud output and return exit code."""
        self.context.ui.info("Output target: Jira Cloud API")

        # Check for critical assignee errors before proceeding
        critical_assignee_errors = [
            p for p in result.problems if p.severity == ProblemSeverity.CRITICAL and p.code.startswith("assignee.")
        ]
        if critical_assignee_errors:
            self.context.ui.error("Critical assignee errors found - cannot proceed with cloud import:")
            for error in critical_assignee_errors:
                self.context.ui.error(f"  Row {error.row_index}: {error.message}")
            App.event_fatal(exit_code=4, message="Critical assignee errors prevent cloud import")

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
            App.event_fatal(exit_code=3, message=f"Cloud import failed: {exc}")

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

    def run(self) -> int:
        """Execute the complete pipeline and return exit code."""
        # 1. Create and run processor
        processor = self._create_processor()
        result = processor.process()

        # 2. Report problems
        if not self.options.no_report:
            ProblemReporter(options=ReportOptions(show_details=True, show_aggregate_by_code=False)).render(result)
        else:
            ProblemReporter(options=ReportOptions(show_details=False, show_aggregate_by_code=True)).render(result)

        # 3. Handle auto-fix warnings
        if not processor.enable_auto_fix:
            if result.report.errors > 0:
                self.context.ui.warning("Auto-fix is disabled. Please fix the issues manually.")
            self.context.ui.hint(
                "You can enable auto-fix by adding the following to your configuration file or by using the --auto-fix flag."
            )

        # 4. Check critical problems
        critical_problems = [p for p in result.problems if p.severity == ProblemSeverity.CRITICAL]
        if critical_problems:
            # If --auto-yes and --cloud, terminate immediately
            if self.options.auto_reply is True and self.context.output_target == "cloud":
                self.context.ui.error("Cannot proceed with --auto-yes and --cloud when critical issues are present.")
                self.context.app.event_abort(
                    exit_code=1, message="Critical validation issues with --auto-yes and --cloud"
                )

            # Skip critical validation prompt for dry-run mode since we never reach sinks
            if not self.options.dry_run:
                # For all other cases, ask user whether to continue
                if not self.context.ui.prompt_yes_no(
                    "Critical validation issues found. Do you want to continue?",
                    default=False,
                    auto_reply=self.options.auto_reply,
                ):
                    self.context.app.event_abort(exit_code=1, message="User cancelled due to critical issues.")
                else:
                    self.context.ui.success("Continuing despite critical issues...")

        if result.report.errors > 0:
            if not self.context.ui.prompt_yes_no(
                "Do you want to continue?", default=False, auto_reply=self.options.auto_reply
            ):
                self.context.app.event_abort(exit_code=1, message="User cancelled the Execution.")
            else:
                self.context.ui.success("Continuing...")

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
