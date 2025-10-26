"""Description: This script contains the reporting for the Jira Importer.

Author:
    Julien (@tom4897)
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from .models import Problem, ProblemSeverity, ProcessorResult
from .sinks.cloud_sink import CloudSubmitReport

# Emojis consistent with the rest of the tool
EMO_ERROR = "❌ "
EMO_WARN = "⚠️ "
EMO_FIX = "🔧 "


@dataclass(slots=True)
class ReportOptions:
    """Tuning knobs for display."""

    show_details: bool = True  # show per-problem rows
    max_problem_rows: int = 50  # truncate detail rows
    show_aggregate_by_code: bool = True  # show counts grouped by problem code
    max_code_rows: int = 25  # truncate code aggregation rows


class ProblemReporter:
    """Render ProcessorResult to a human-friendly report.

    - Uses Rich tables if 'rich' is installed, else prints plaintext.
    - Always shows an emoji summary header.
    - Optionally shows per-problem detail rows and an aggregate-by-code table.
    """

    def __init__(self, *, options: ReportOptions | None = None) -> None:
        """Initialize the ProblemReporter class."""
        self.opt = options or ReportOptions()
        # Lazy import Rich if present
        # TODO: Change this to use ui instance of consoleIO
        try:
            from rich.console import Console  # pylint: disable=import-outside-toplevel

            # TODO: Change this to use ui instance of consoleIO
            from rich.table import Table  # pylint: disable=import-outside-toplevel

            self._Console = Console  # pylint: disable=invalid-name
            self._Table = Table  # pylint: disable=invalid-name
            self._rich_available = True
        except Exception:
            self._Console = None  # type: ignore
            self._Table = None  # type: ignore
            self._rich_available = False

    # api public

    def render(self, result: ProcessorResult) -> None:
        """Print the full report to stdout."""
        if self._rich_available:
            self._render_rich(result)
        else:
            self._render_plain(result)

    def build_summary_line(self, result: ProcessorResult) -> str:
        """Return a short one-line summary string."""
        e = result.report.errors
        w = result.report.warnings
        f = result.report.fixes
        total = len(result.problems)
        return f"{EMO_ERROR} {e}  {EMO_WARN} {w}  {EMO_FIX} {f}  • total findings: {total}"

    # internals, Rich rendering

    def _render_rich(self, result: ProcessorResult) -> None:
        Console = self._Console  # pylint: disable=invalid-name
        Table = self._Table  # pylint: disable=invalid-name
        console = Console()

        console.print("")
        console.print("[bold]Validation Report[/bold]")
        console.print("")
        console.print(self._summary_rich(result))

        if self.opt.show_aggregate_by_code:
            by_code = _aggregate_by_code(result.problems)
            table = Table(show_lines=False, expand=False, title="Findings by Code")
            table.add_column("Code", style="bold")
            table.add_column("Severity")
            table.add_column("Count", justify="right")
            for i, (code, sev, count) in enumerate(by_code):
                if i >= self.opt.max_code_rows:
                    break
                table.add_row(code, _sev_label(sev), str(count))
            console.print(table)

        if self.opt.show_details and result.problems:
            table = Table(show_lines=False, expand=False, title="")
            table.add_column("Row", justify="right")
            table.add_column("Severity")
            table.add_column("Code")
            table.add_column("Column")
            table.add_column("Message", no_wrap=False)
            for i, p in enumerate(result.problems):
                if i >= self.opt.max_problem_rows:
                    table.add_row("…", "", "", "", f"(truncated at {self.opt.max_problem_rows} rows)")
                    break
                row = str(p.row_index or "")
                sev_label = _sev_label(p.severity)
                code = p.code
                col = p.col_key or ""
                msg = p.message
                table.add_row(row, sev_label, code, col, msg)
            console.print(table)

        console.rule()

    def _summary_rich(self, result: ProcessorResult) -> str:
        e = result.report.errors
        w = result.report.warnings
        f = result.report.fixes
        total = len(result.problems)
        if total > 0:
            return (
                f"[bold]{EMO_ERROR} {e}  {EMO_WARN} {w}  {EMO_FIX} {f}[/bold]  • total findings: [bold]{total}[/bold]"
            )
        return "[bold]No issues found[/bold]"

    # internals, plain rendering
    def _render_plain(self, result: ProcessorResult) -> None:
        print("=== Validation Report ===")
        print(self.build_summary_line(result))

        if self.opt.show_aggregate_by_code:
            print("\nFindings by Code")
            print("----------------")
            for i, (code, sev, count) in enumerate(_aggregate_by_code(result.problems)):
                if i >= self.opt.max_code_rows:
                    print(f"... (truncated at {self.opt.max_code_rows} rows)")
                    break
                print(f"{code:40}  {_sev_label(sev):7}  {count:5}")

        if self.opt.show_details and result.problems:
            print("\nProblem Details")
            print("---------------")
            print(f"{'Row':>5}  {'Severity':7}  {'Code':30}  {'Column':12}  Message")
            for i, p in enumerate(result.problems):
                if i >= self.opt.max_problem_rows:
                    print(f"... (truncated at {self.opt.max_problem_rows} rows)")
                    break
                row = f"{p.row_index or '':>5}"
                sev_label = f"{_sev_label(p.severity):7}"
                code = f"{p.code:30.30}"
                col = f"{(p.col_key or ''):12.12}"
                msg = p.message
                print(f"{row}  {sev_label}  {code}  {col}  {msg}")
        print("====================================")


# helpers


def _sev_label(sev: ProblemSeverity) -> str:
    if sev == ProblemSeverity.ERROR:
        return f"{EMO_ERROR} error"
    if sev == ProblemSeverity.WARNING:
        return f"{EMO_WARN} warning"
    if sev == ProblemSeverity.CRITICAL:
        return f"{EMO_ERROR} critical"
    return f"{EMO_FIX} fix"


def _aggregate_by_code(problems: Sequence[Problem]) -> list[tuple[str, ProblemSeverity, int]]:
    """Return a list of (code, severity, count) sorted by count desc then code.

    If a code appears with multiple severities, they are treated as distinct buckets.
    """
    counter: Counter[tuple[str, ProblemSeverity]] = Counter()
    for p in problems:
        counter[(p.code, p.severity)] += 1
    items = [(code, sev, cnt) for (code, sev), cnt in counter.items()]
    items.sort(key=lambda x: (-x[2], x[0], x[1].value))
    return items


class CloudReportReporter:
    """Render CloudSubmitReport to a human-friendly format.

    Follows the same pattern as ProblemReporter but for cloud-specific results.
    """

    def __init__(self, *, max_errors: int = 5) -> None:
        """Initialize the CloudReportReporter.

        Args:
            max_errors: Maximum number of errors to display in detail
        """
        self.max_errors = max_errors

    def render_errors(self, report: CloudSubmitReport, ui) -> None:
        """Display error details in a user-friendly format."""
        if not report.errors:
            return

        ui.warning("Some issues failed to import. See details below:")
        # Display first N errors with details
        for _, err in enumerate(report.errors[: self.max_errors]):
            if isinstance(err, dict):
                # Handle Jira API error format
                element_errors = err.get("elementErrors", {})
                error_messages = element_errors.get("errorMessages", [])
                field_errors = element_errors.get("errors", {})
                failed_element = err.get("failedElementNumber", "Unknown")
                status = err.get("status", "Unknown")

                if error_messages:
                    ui.error(f"  Row {failed_element}: {', '.join(error_messages)}")
                elif field_errors:
                    for field, msg in field_errors.items():
                        ui.error(f"  Row {failed_element} - {field}: {msg}")
                else:
                    ui.error(f"  Row {failed_element}: {status} - {err}")
            else:
                ui.error(f"  {err}")

        if len(report.errors) > self.max_errors:
            ui.say(f"  ... and {len(report.errors) - self.max_errors} more errors.")
