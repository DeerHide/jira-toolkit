"""Description: This script contains the console configuration for the Jira Importer.

Author:
    Julien (@tom4897)
"""

from __future__ import annotations

import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Literal

from rich.align import Align
from rich.console import Console
from rich.errors import MissingStyle
from rich.markdown import Markdown
from rich.markup import escape as rich_escape
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.table import Table
from rich.theme import Theme
from rich.traceback import install as install_rich_traceback

THEME = Theme(
    {
        # Base tones
        "text": "white",
        "muted": "grey62",
        "title": "bold white",
        "accent": "bold cyan",
        "accent.dim": "cyan",
        # Message types
        "info": "cyan",
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "debug": "magenta",
        "wip": "bold yellow",
        "info.light": "cyan",
        "success.light": "green",
        "warning.light": "yellow",
        "error.light": "red",
        "debug.light": "magenta",
        "wip.light": "yellow",
        "progress.light": "cyan",
        # Code-ish bits
        "key": "bold white",
        "value": "bold cyan",
        "code": "white on grey15",
        "path": "italic cyan",
        # Prompts / user input semantics
        "prompt": "bold white",
        "hint": "italic grey46",
        "example": "italic cyan",
        "default": "dim",
        "choice": "bold cyan",
        "hotkey": "bold",
        "required": "bold red",
        "danger": "bold red",
        "note": "dim",
        # Title semantics
        "title.h1": "bold white on grey15",
        "title.h2": "bold cyan",
        "title.h3": "bold white",
        "title.note": "italic grey62",
        # Decorations
        "rule.h1": "cyan",
        "rule.h2": "grey46",
        "rule.h3": "grey35",
        "crumb": "italic cyan",
        "crumb.sep": "dim",
    }
)


@dataclass(frozen=True)
class ConsoleStyle:  # pylint: disable=too-many-instance-attributes
    """Console style configuration."""

    prefix_info: str = "ℹ️ "  # noqa: RUF001
    prefix_success: str = "✅ "
    prefix_warning: str = "⚠️ "
    prefix_error: str = "❌ "
    prefix_debug: str = "🐛 "
    prefix_progress: str = "🔄 "
    prefix_wip: str = "🚧 "

    # Panel defaults
    panel_border: str = "accent.dim"
    panel_title_style: str = "title"

    # Table defaults
    table_header_style: str = "accent"
    table_row_style: str = "text"
    table_alt_row_style: str = "text"


STYLE = ConsoleStyle()


class Fmt:  # pylint: disable=too-many-public-methods
    """Centralized markup helpers that use only theme or Rich built-in styles.

    - Use only styles defined in the Theme (or Rich built-ins like 'bold', 'italic')
    """

    _BUILTINS: ClassVar[set[str]] = {"bold", "italic", "underline", "reverse", "strike", "dim"}

    def __init__(self, _console: Console):
        """Initialize the Fmt."""
        self._c = _console

    def _validate(self, style: str) -> None:
        for token in style.split():
            if token in self._BUILTINS:
                continue
            try:
                self._c.get_style(token)
            except MissingStyle as exc:
                raise ValueError(f"Unknown style '{token}'. Add it to THEME or fix the name.") from exc

    def style(self, text: str, style: str) -> str:  # noqa: D102
        self._validate(style)
        return f"[{style}]{text}[/]"

    # Base styles
    def bold(self, text: str) -> str:  # noqa: D102
        return self.style(text, "bold")

    def italic(self, text: str) -> str:  # noqa: D102
        return self.style(text, "italic")

    def code(self, text: str) -> str:  # noqa: D102
        return self.style(text, "code")

    def path(self, text: str) -> str:  # noqa: D102
        return self.style(text, "path")

    def key(self, text: str) -> str:  # noqa: D102
        return self.style(text, "key")

    def value(self, text: str) -> str:  # noqa: D102
        return self.style(text, "value")

    def accent(self, text: str) -> str:  # noqa: D102
        return self.style(text, "accent")

    def dim(self, text: str) -> str:  # noqa: D102
        return self.style(text, "dim")

    def success(self, text: str) -> str:  # noqa: D102
        return self.style(text, "success")

    def warning(self, text: str) -> str:  # noqa: D102
        return self.style(text, "warning")

    def error(self, text: str) -> str:  # noqa: D102
        return self.style(text, "error")

    def info(self, text: str) -> str:  # noqa: D102
        return self.style(text, "info")

    def debug(self, text: str) -> str:  # noqa: D102
        return self.style(text, "debug")

    def prompt(self, text: str) -> str:  # noqa: D102
        return self.style(text, "prompt")

    def hint(self, text: str) -> str:  # noqa: D102
        return self.style(text, "hint")

    def example(self, text: str) -> str:  # noqa: D102
        return self.style(text, "example")

    def default(self, text: str) -> str:  # noqa: D102
        return self.style(text, "default")

    def choice(self, text: str) -> str:  # noqa: D102
        return self.style(text, "choice")

    def hotkey(self, text: str) -> str:  # noqa: D102
        return self.style(text, "hotkey")

    def required(self, text: str) -> str:  # noqa: D102
        return self.style(text, "required")

    def danger(self, text: str) -> str:  # noqa: D102
        return self.style(text, "danger")

    def note(self, text: str) -> str:  # noqa: D102
        return self.style(text, "note")

    def progress(self, text: str) -> str:  # noqa: D102
        return self.style(text, "progress")

    def warning_light(self, text: str) -> str:  # noqa: D102
        return self.style(text, "warning.light")

    def error_light(self, text: str) -> str:  # noqa: D102
        return self.style(text, "error.light")

    def info_light(self, text: str) -> str:  # noqa: D102
        return self.style(text, "info.light")

    def success_light(self, text: str) -> str:  # noqa: D102
        return self.style(text, "success.light")

    def debug_light(self, text: str) -> str:  # noqa: D102
        return self.style(text, "debug.light")

    def progress_light(self, text: str) -> str:  # noqa: D102
        return self.style(text, "progress.light")

    # Titles & ornaments
    def t_h1(self, text: str) -> str:  # noqa: D102
        return self.style(text, "title.h1")

    def t_h2(self, text: str) -> str:  # noqa: D102
        return self.style(text, "title.h2")

    def t_h3(self, text: str) -> str:  # noqa: D102
        return self.style(text, "title.h3")

    def t_note(self, text: str) -> str:  # noqa: D102
        return self.style(text, "title.note")

    def crumb(self, part: str) -> str:  # noqa: D102
        return self.style(part, "crumb")

    def crumb_sep(self, sep: str = "»") -> str:  # noqa: D102
        return self.style(sep, "crumb.sep")

    def kv(self, k: str, v: str, sep: str = ": ") -> str:
        """Format a key/value pair with semantic styles."""
        return f"{self.key(k)}{sep}{self.value(v)}"

    def join(self, parts: Iterable[str], sep: str = " ") -> str:
        """Join pre-styled parts safely."""
        return sep.join(parts)

    def esc(self, text: str) -> str:
        """Escape raw text that may include [brackets] so markup stays valid."""
        return rich_escape(text)


class ConsoleUI:
    """Console UI class."""

    def __init__(
        self, _console: Console | None = None, style: ConsoleStyle = STYLE, formatter: Fmt | None = None
    ) -> None:
        """Initialize the ConsoleUI."""
        self.c = _console or Console(theme=THEME, highlight=True, soft_wrap=False)
        self.style = style
        self.fmt = formatter or Fmt(self.c)

    def say(self, *parts: str, sep: str = " ") -> None:  # noqa: D102
        self.c.print(sep.join(parts))

    def lf(self) -> None:  # noqa: D102
        self.c.print("")

    # --- Messages
    def success(self, msg: str, prefix: bool = True) -> None:  # noqa: D102
        self.c.print(f"[success]{self.style.prefix_success if prefix else ''} {msg}[/]")

    def info(self, msg: str, prefix: bool = True) -> None:  # noqa: D102
        self.c.print(f"[info]{self.style.prefix_info if prefix else ''} {msg}[/]")

    def warning(self, msg: str, prefix: bool = True) -> None:  # noqa: D102
        self.c.print(f"[warning]{self.style.prefix_warning if prefix else ''} {msg}[/]")

    def error(self, msg: str, prefix: bool = True) -> None:  # noqa: D102
        self.c.print(f"[error]{self.style.prefix_error if prefix else ''} {msg}[/]")

    def debug(self, msg: str, prefix: bool = True) -> None:  # noqa: D102
        self.c.print(f"[debug]{self.style.prefix_debug if prefix else ''} {msg}[/]")

    def wip(self, msg: str, prefix: bool = True) -> None:  # noqa: D102
        self.c.print(f"[wip]{self.style.prefix_wip if prefix else ''} {msg}[/]")

    def warning_light(self, msg: str, prefix: bool = True) -> None:  # noqa: D102
        self.c.print(f"[warning.light]{self.style.prefix_warning if prefix else ''} {msg}[/]")

    def error_light(self, msg: str, prefix: bool = True) -> None:  # noqa: D102
        self.c.print(f"[error.light]{self.style.prefix_error if prefix else ''} {msg}[/]")

    def info_light(self, msg: str, prefix: bool = True) -> None:  # noqa: D102
        self.c.print(f"[info.light]{self.style.prefix_info if prefix else ''} {msg}[/]")

    def success_light(self, msg: str, prefix: bool = True) -> None:  # noqa: D102
        self.c.print(f"[success.light]{self.style.prefix_success if prefix else ''} {msg}[/]")

    def debug_light(self, msg: str, prefix: bool = True) -> None:  # noqa: D102
        self.c.print(f"[debug.light]{self.style.prefix_debug if prefix else ''} {msg}[/]")

    def progress_light(self, msg: str, prefix: bool = True) -> None:  # noqa: D102
        self.c.print(f"[progress.light]{self.style.prefix_progress if prefix else ''} {msg}[/]")

    def hint(self, msg: str) -> None:  # noqa: D102
        self.c.print(f"[hint]{msg}[/]")

    def example(self, msg: str) -> None:  # noqa: D102
        self.c.print(f"[example]{msg}[/]")

    def default(self, msg: str) -> None:  # noqa: D102
        self.c.print(f"[default]{msg}[/]")

    def choice(self, msg: str) -> None:  # noqa: D102
        self.c.print(f"[choice]{msg}[/]")

    def hotkey(self, msg: str) -> None:  # noqa: D102
        self.c.print(f"[hotkey]{msg}[/]")

    def required(self, msg: str) -> None:  # noqa: D102
        self.c.print(f"[required]{msg}[/]")

    def danger(self, msg: str) -> None:  # noqa: D102
        self.c.print(f"[danger]{msg}[/]")

    def note(self, msg: str) -> None:  # noqa: D102
        self.c.print(f"[note]{msg}[/]")

    # --- Panels (for grouped info / summaries)
    def panel(
        self,
        title: str,
        body: str,
        *,
        title_align: Literal["left", "center", "right"] = "left",
        style: str = "accent",
        expand: bool = False,
        width: int | None = None,
    ) -> None:
        """Render a panel with a title and body."""
        panel = Panel(
            Align(body, "left"),
            title=f"[title]{title}[/]" if title else None,
            title_align=title_align,
            border_style=style,
            expand=expand,
            width=width,
        )
        self.c.print(panel)

    def full_panel(
        self,
        body: str,
        *,
        title: str | None = None,
        title_align: Literal["left", "center", "right"] = "left",
        style: str = "accent",
    ) -> None:
        """Render a panel that always spans the console width."""
        panel = Panel(
            Align(body, "center"),
            title=f"[title]{title}[/]" if title else None,
            title_align=title_align,
            border_style=style,
            expand=True,  # Force it to occupy console width
        )
        self.c.print(panel)

    def title_h1(self, text: str, *, icon: str = "◆") -> None:
        """Big section title: full-width rule, inverted title chip centered.

        Example:
        ─────────────────────  ◆  PROJECT SETUP  ◆  ─────────────────────
        """
        chip = f" {icon} {self.fmt.t_h1(self.fmt.esc(text.upper()))} {icon} "
        # console.rule centers and stretches to width
        self.c.rule(chip, style="rule.h1")

    def title_h2(self, text: str, *, icon: str = "•") -> None:
        """Medium section title: single line + thin rule below.

        Example:
        • Configuration
        ─────────────────────────────────────────
        """
        self.c.print(f"{icon} {self.fmt.t_h2(self.fmt.esc(text))}")
        self.c.rule(style="rule.h2")

    def title_h3(self, text: str, *, icon: str = "→") -> None:
        """Small section header: inline, with a very light rule (spacer).

        Example:
        → Credentials
        ─────────────
        """
        self.c.print(f"{icon} {self.fmt.t_h3(self.fmt.esc(text))}")
        self.c.rule(style="rule.h3")

    def title_banner(self, text: str, *, sub: str | None = None, icon: str = "🚀") -> None:
        """Emphatic banner (panel) for start/finish milestones.

        Args:
            text: Text to display in the banner.
            sub: Subtext to display below the banner.
            icon: Icon to display in the banner.
        """
        body = f"{icon} {self.fmt.t_h2(self.fmt.esc(text))}"
        if sub:
            body += f"\n{self.fmt.t_note(self.fmt.esc(sub))}"
        panel = Panel(
            Align.center(body),
            border_style="accent",
            expand=True,
        )
        self.c.print(panel)

    def breadcrumb(self, parts: list[str], *, sep: str = "»") -> None:
        """Breadcrumb line, e.g., Setup » Connect » Verify.

        Args:
            parts: List of parts to join with the separator.
            sep: Separator between parts.
        """
        if not parts:
            return
        crumbed = []
        for i, p in enumerate(parts):
            crumbed.append(self.fmt.crumb(p))
            if i < len(parts) - 1:
                crumbed.append(f" {self.fmt.crumb_sep(sep)} ")
        self.c.print("".join(crumbed))

    # Tables
    def table(self, columns: list[str], rows: list[list[str]]) -> None:
        """Render a table with columns and rows.

        Args:
            columns: List of column names.
            rows: List of rows, each row is a list of strings.
        """
        t = Table(show_header=True, header_style=self.style.table_header_style, show_lines=False)
        for col in columns:
            t.add_column(col)
        for i, row in enumerate(rows):
            style = self.style.table_alt_row_style if i % 2 else self.style.table_row_style
            t.add_row(*row, style=style)
        self.c.print(t)

    # Progress
    def progress(self) -> Progress:
        """Create a progress bar.

        Returns:
            Progress: The progress bar.
        """
        return Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(),
            TextColumn("[muted]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self.c,
        )

    # Prompts
    def prompt_input(self, prompt_text: str) -> str:
        """Ask the user for input using Rich's Console.input.

        Exact text shown equals prompt_text (no styling added here).
        Returns empty string if non-interactive or on interrupt.
        """
        if not sys.stdin.isatty():
            return ""
        try:
            return self.c.input(prompt_text)
        except (EOFError, KeyboardInterrupt):
            return ""

    def prompt_yes_no(
        self,
        question: str,
        *,
        default: bool | None = None,
        max_attempts: int = 3,
        auto_reply: bool | None = None,
    ) -> bool:
        """Yes/No confirmation prompt (returns True/False).

        - Accepts y/yes and n/no (case-insensitive). q/quit => False.
        - If default is provided and user presses Enter, returns default.
        - Non-interactive (no TTY): returns default if provided, else False.
        - On EOF/KeyboardInterrupt: returns default if provided, else False.
        - After `max_attempts` invalid tries: returns default if provided, else False.
        """
        if auto_reply is not None:
            if auto_reply:
                self.say(self.fmt.success("Auto-yes flag is set. Continuing..."))
            else:
                self.say(self.fmt.error("Auto-no flag is set. Aborting..."))
            return auto_reply

        # Non-interactive fallback
        if not sys.stdin.isatty():
            if default is not None:
                self.say(self.fmt.note("Non-interactive mode: using default."))
                return default
            self.say(self.fmt.note("Non-interactive mode: no input available."))
            return False

        def _normalize(resp: str) -> bool | None:
            resp = resp.strip().lower()
            if not resp:
                return default
            if resp in ("y", "yes"):
                return True
            if resp in ("n", "no", "q", "quit"):
                return False
            return None

        # Build styled prompt text
        default_hint = ""
        if default is True:
            default_hint = f" {self.fmt.default('[Y/n]')}"
        elif default is False:
            default_hint = f" {self.fmt.default('[y/N]')}"

        prompt_line = f"{self.fmt.prompt(question)}{default_hint}: "

        attempts = 0
        while True:
            try:
                raw = self.c.input(prompt_line)
            except (EOFError, KeyboardInterrupt):
                return default if default is not None else False

            val = _normalize(raw)
            if val is not None:
                return val

            attempts += 1
            if attempts >= max_attempts:
                return default if default is not None else False

            self.warning("Please answer with y/yes or n/no.")

    def prompt_text(
        self,
        question: str,
        *,
        required: bool = False,
        default: str | None = None,
        hint: str | None = None,
    ) -> str:
        """Text input prompt with styled question and robust fallbacks.

        - Shows hint text and default values if provided.
        - If `required=True`, forces non-empty input (unless default is set).
        - Returns default on empty input if given.
        - Non-interactive (no TTY): returns default if provided, else "".
        - On EOF/KeyboardInterrupt: returns default if provided, else "".
        """
        if not sys.stdin.isatty():
            return default or ""

        while True:
            # Build prompt components (escape raw text, then style; do not escape styled output)
            hint_part = f" {self.fmt.hint(self.fmt.esc(hint))}" if hint else ""
            def_part = f" {self.fmt.default(self.fmt.esc(f'(default: {default})'))}" if default else ""
            req_mark = f" {self.fmt.required('*')}" if required else ""

            prompt_text = f"{self.fmt.prompt(self.fmt.esc(question))}{req_mark}{hint_part}{def_part}: "

            try:
                response = self.c.input(prompt_text).strip()
            except (EOFError, KeyboardInterrupt):
                return default or ""

            if not response:
                if default is not None:
                    return default
                if required:
                    self.say(self.fmt.warning("This value is required."))
                    continue
                return ""

            return response

    def prompt_choice(
        self,
        question: str,
        options: Sequence[str],
        *,
        default_idx: int | None = None,  # 1-based for the user (e.g., 2 means options[1])
        hints: Sequence[str] | None = None,
        max_attempts: int = 3,
    ) -> int:
        """Multiple-choice prompt (returns 0-based index).

        - Renders a numbered list 1..N with optional per-option hints.
        - Input expects a number in 1..N (case-insensitive 'q'/'quit' aborts).
        - If default_idx is provided and user presses Enter, returns default_idx-1.
        - Non-interactive (no TTY): returns default_idx-1 if provided, else -1.
        - On EOF/KeyboardInterrupt: returns default_idx-1 if provided, else -1.
        - After `max_attempts` invalid tries: returns default_idx-1 if provided, else -1.

        Returns:
            int: 0-based index of the selected option, or -1 if aborted/unavailable.
        """
        n = len(options)
        if n == 0:
            self.error("No options available.")
            return -1

        # Non-interactive fallback
        if not sys.stdin.isatty():
            if default_idx is not None and 1 <= default_idx <= n:
                return default_idx - 1
            self.say(self.fmt.note("Non-interactive mode: no input available."))
            return -1

        # Render the list once
        self.say(self.fmt.prompt(question))
        for i, label in enumerate(options, start=1):
            hint_txt = ""
            if hints and (i - 1) < len(hints) and hints[i - 1]:
                hint_txt = f"  {self.fmt.hint(hints[i - 1])}"
            self.say(f"  {self.fmt.hotkey(str(i))}) {self.fmt.choice(label)}{hint_txt}")

        # Build the input line
        range_hint = self.fmt.hint(f"1..{n}")
        default_hint = f" {self.fmt.default(f'(default: {default_idx})')}" if default_idx else ""
        prompt_line = f"{self.fmt.prompt('Select')} {range_hint}{default_hint}: "

        attempts = 0
        while True:
            try:
                raw = self.c.input(prompt_line).strip().lower()
            except (EOFError, KeyboardInterrupt):
                return default_idx - 1 if default_idx else -1

            # Abort
            if raw in ("q", "quit"):
                return -1

            # Default
            if raw == "" and default_idx:
                return default_idx - 1

            # Numeric choice
            if raw.isdigit():
                val = int(raw)
                if 1 <= val <= n:
                    return val - 1

            attempts += 1
            if attempts >= max_attempts:
                return default_idx - 1 if default_idx else -1

            self.warning(f"Pick one of {self.fmt.hotkey(f'1..{n}')} or {self.fmt.hotkey('q')} to cancel.")

    def confirm_destructive(self, action: str, *, default: bool = False) -> bool:
        """Confirm a destructive action.

        Args:
            action: The action to confirm.
            default: Whether to default to True.
        """
        self.say(self.fmt.danger("This action cannot be undone."))
        return self.prompt_yes_no(f"{action}? ", default=default)

    def render_markdown(
        self,
        content: str | None = None,
        *,
        file_path: Path | None = None,
        title: str | None = None,
        style: str = "accent",
    ) -> None:
        """Render markdown content in the console.

        Args:
            content: Markdown content as a string. If provided, file_path is ignored.
            file_path: Path to a markdown file to read and render.
            title: Optional title to display above the markdown content.
            style: Style for the title if provided.
        """
        if content is None and file_path is None:
            raise ValueError("Either content or file_path must be provided")

        if content is None:
            try:
                with open(file_path, encoding="utf-8") as f:  # type: ignore[arg-type]
                    content = f.read()
            except FileNotFoundError:
                self.error(f"Markdown file not found: {file_path}")
                return
            except Exception as e:
                self.error(f"Error reading markdown file: {e}")
                return

        if title:
            self.c.print(f"[{style}]{title}[/]")
            self.c.print("")

        markdown = Markdown(content)
        self.c.print(markdown)


_TRACEBACK_INSTALLED = False


class ConsoleIO:
    """Factory class for console instances with singleton-like behavior."""

    _console_instance: Console | None = None
    _ui_instance: ConsoleUI | None = None

    @classmethod
    def get_console(cls) -> Console:
        """Get the raw Rich Console instance, creating it if needed.

        Prefer get_ui() for application code; use this only when you need
        the low-level Console (e.g. for Rich primitives not wrapped by ConsoleUI).
        """
        global _TRACEBACK_INSTALLED  # pylint: disable=global-statement
        if cls._console_instance is None:
            if not _TRACEBACK_INSTALLED:
                install_rich_traceback(show_locals=False, width=120, extra_lines=2, word_wrap=True, theme="monokai")
                _TRACEBACK_INSTALLED = True
            cls._console_instance = Console(theme=THEME, highlight=True, soft_wrap=False)
        return cls._console_instance

    @classmethod
    def get_ui(cls) -> ConsoleUI:
        """Get the ConsoleUI instance, creating it if needed.

        This is the preferred entry point for application code (output, prompts, panels).
        """
        if cls._ui_instance is None:
            console = cls.get_console()
            cls._ui_instance = ConsoleUI(_console=console, style=STYLE, formatter=Fmt(console))
        return cls._ui_instance

    @classmethod
    def get_components(cls) -> tuple[ConsoleUI, Fmt]:  # noqa: D102
        ui = cls.get_ui()
        return ui, ui.fmt

    @classmethod
    def reset(cls) -> None:
        """Reset console and UI instances (useful for testing).

        Only clears the cached Console and ConsoleUI instances. Does not
        uninstall the Rich traceback hook (that is process-wide and remains).
        """
        cls._console_instance = None
        cls._ui_instance = None
