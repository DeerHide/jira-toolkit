# isort: skip_file
"""Demo script for testing console formatting and UI components.

Author:
    Julien (@tom4897)
"""

import os
import sys

from jira_importer.console import (  # type: ignore[import]  # pylint: disable=wrong-import-position
    STYLE,
    THEME,
    ConsoleIO,
    ConsoleUI,
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def demo_formatting_text(ui: ConsoleUI):
    """Demo formatting."""
    ui.title_banner("FORMATTING")
    ui.say(ui.fmt.bold("ui.bold(my text)"))
    ui.say(ui.fmt.italic("ui.italic(my text)"))
    ui.say(ui.fmt.code("ui.code(my text)"))
    ui.say(ui.fmt.path("ui.path(my text)"))
    ui.say(ui.fmt.key("ui.key(my text)"))
    ui.say(ui.fmt.value("ui.value(my text)"))
    ui.say(ui.fmt.accent("ui.accent(my text)"))
    ui.say(ui.fmt.dim("ui.dim(my text)"))
    ui.say(ui.fmt.success("ui.success(my text)"))
    ui.say(ui.fmt.warning("ui.warning(my text)"))
    ui.say(ui.fmt.error("ui.error(my text)"))
    ui.say(ui.fmt.info("ui.info(my text)"))
    ui.say(ui.fmt.debug("ui.debug(my text)"))
    ui.say(ui.fmt.prompt("ui.prompt(my text)"))
    ui.say(ui.fmt.hint("ui.hint(my text)"))
    ui.say(ui.fmt.example("ui.example(my text)"))
    ui.say(ui.fmt.default("ui.default(my text)"))
    ui.say(ui.fmt.choice("ui.choice(my text)"))
    ui.say(ui.fmt.hotkey("ui.hotkey(my text)"))
    ui.say(ui.fmt.required("ui.required(my text)"))
    ui.say(ui.fmt.danger("ui.danger(my text)"))
    ui.say(ui.fmt.note("ui.note(my text)"))
    ui.say(ui.fmt.t_h1("ui.t_h1(my text)"))
    ui.say(ui.fmt.t_h2("ui.t_h2(my text)"))
    ui.say(ui.fmt.t_h3("ui.t_h3(my text)"))
    ui.say(ui.fmt.t_note("ui.t_note(my text)"))
    ui.say(ui.fmt.crumb("ui.crumb(my text)"))
    ui.say(ui.fmt.crumb_sep("ui.crumb_sep(my text)"))
    ui.say(ui.fmt.kv("ui.kv(my text)", "ui.kv(my value)"))
    ui.say(ui.fmt.join(["ui.join(my text)", "ui.join(my text)"]))
    ui.say(ui.fmt.esc("ui.esc(my text)"))


def demo_formatting_panels(ui: ConsoleUI):
    """Demo formatting panels."""
    ui.title_banner("PANELS")
    ui.panel("ui.panel(my title)", "ui.panel(my body)")
    ui.full_panel("ui.full_panel(my body)")
    ui.title_h1("ui.title_h1(my text)")
    ui.title_h2("ui.title_h2(my text)")
    ui.title_h3("ui.title_h3(my text)")
    ui.title_banner("ui.title_banner(my text)")


def demo_formatting_prefixes(ui: ConsoleUI):
    """Demo formatting prefixes."""
    ui.title_banner("Prefixes")
    ui.say("ui.say(my text)")
    ui.hint("ui.hint(my text)")
    ui.example("ui.example(my text)")
    ui.default("ui.default(my text)")
    ui.choice("ui.choice(my text)")
    ui.hotkey("ui.hotkey(my text)")
    ui.required("ui.required(my text)")
    ui.danger("ui.danger(my text)")
    ui.note("ui.note(my text)")
    ui.success("ui.success(my text)")
    ui.info("ui.info(my text)")
    ui.warning("ui.warning(my text)")
    ui.error("ui.error(my text)")
    ui.debug("ui.debug(my text)")
    ui.debug("ui.debug(my text)")


def demo_formatting_styles(ui: ConsoleUI):
    """Demo formatting styles."""
    ui.title_banner("STYLES")
    for style_name, style_value in STYLE.__dict__.items():
        ui.say(f"style.{style_name}: {style_value}")


def demo_formatting_themes(ui: ConsoleUI):
    """Demo formatting themes."""
    ui.lf()
    ui.title_banner("THEMES")
    for theme_name, theme_value in THEME.styles.items():
        ui.say(f"theme.{theme_name}: {theme_value}")


def main():
    """Run the console UI demo showcasing formatting, panels, and themes."""
    ui = ConsoleIO.getUI()

    ui.lf()
    demo_formatting_text(ui)

    ui.lf()
    demo_formatting_panels(ui)

    ui.lf()
    demo_formatting_prefixes(ui)

    # ui.lf()
    # demo_formatting_styles(ui)

    # ui.lf()
    # demo_formatting_themes(ui)


if __name__ == "__main__":
    main()
