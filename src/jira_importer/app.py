"""Description: This script is the main application for the Jira Importer.

Author:
    Julien (@tom4897)
"""

import argparse
import logging
import sys

from rich_argparse import RichHelpFormatter

from . import DEFAULT_CONFIG_FILENAME
from .artifacts import ArtifactManager
from .console import ConsoleIO

try:
    from .version import __build_date__, __git_branch__, __git_revision__, __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0)
    __git_revision__ = "HASH"
    __git_branch__ = "local"
    __build_date__ = "2035-01-01"

ui, fmt = ConsoleIO.getComponents()
logger = logging.getLogger(__name__)


class App:
    """App class."""

    # Class variable to store command line arguments
    _args = None

    def __init__(self, artifact_manager: ArtifactManager):
        """Initialize the App class."""
        self.artifact_manager = artifact_manager
        self.version_info = __version_info__
        self.git_revision = __git_revision__
        self.git_branch = __git_branch__
        self.build_date = __build_date__

    @staticmethod
    def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
        """Parse the command line arguments.

        Accepts an optional argv for testability; defaults to sys.argv[1:].
        """
        provided_argv = argv if argv is not None else sys.argv[1:]

        # Fast-path preprocessing for lightweight options
        fast_args = App._preparse_shortcuts(provided_argv)
        if fast_args is not None:
            return fast_args

        parser = App._build_parser()
        args = parser.parse_args(provided_argv)
        # Store args in class variable for access by event_fatal
        App._args = args
        return args

    def print_version(self) -> None:
        """Print the version of the App, as declared during the build process."""
        ui.say(f"Jira Importer {self.version_info}")
        ui.say(f"Git revision: {self.git_revision}")
        ui.say(f"Git branch: {self.git_branch}")
        ui.say(f"Build date: {self.build_date}")

    def event_close(self, exit_code: int = 0, cleanup: bool = True) -> None:
        """Event close, when the script is finished."""
        if cleanup:
            self.artifact_manager.delete_all()
        logger.info("Jira Importer finished.")
        sys.exit(exit_code)

    def event_abort(self, exit_code: int = -1) -> None:
        """Event abort, when the script is aborted."""
        ui.error("You have aborted the script.")
        logger.critical("Aborted script.")
        self.event_close(exit_code=exit_code)

    @staticmethod
    def event_fatal(exit_code: int = -1, message: str = "Fatal error!") -> None:
        """Event fatal, when the script is finished with a fatal error."""
        logger.debug("event_fatal")

        # Show arguments if available
        if App._args:
            logger.critical("Script failed with the following arguments - Error code: %s", exit_code)
            logger.critical(f"  Input file: {App._args.input_file}")
            logger.critical(f"  Configuration: {App._args.config}")
            logger.critical(f"  Debug mode: {App._args.debug}")
            # logging.critical(f"  Import to cloud: {App._args.import_to_cloud}")
            if App._args.config_default:
                logger.critical(f"  Config default: {App._args.config_default}")
            if App._args.config_input:
                logger.critical(f"  Config input: {App._args.config_input}")
            if App._args.version:
                logger.critical(f"  Version: {App._args.version}")
            logger.critical(f" args: {App._args}")
            ui.error("Fatal event raised!")
            _str = "\n" + ui.fmt.kv("Input file", ui.fmt.path(App._args.input_file)) + "\n"
            _str += ui.fmt.kv("Configuration", ui.fmt.path(App._args.config)) + "\n"
            _str += ui.fmt.kv("Debug mode", App._args.debug) + "\n"
            _str += ui.fmt.kv("Version", App._args.version) + "\n"
            _str += ui.fmt.kv("Config default", App._args.config_default) + "\n"
            _str += ui.fmt.kv("Config input", App._args.config_input) + "\n"
            for arg, value in App._args.__dict__.items():
                _str += ui.fmt.kv(arg, value) + "\n"
            ui.panel("Script failed with the following arguments:", _str)
            ui.error(f"Error code: {exit_code}")

        logger.critical(message)
        sys.exit(exit_code)

    @staticmethod
    def _preparse_shortcuts(argv: list[str]) -> argparse.Namespace | None:
        """Handle fast-path flags without building the full parser.

        Returns an argparse.Namespace when a shortcut is handled, otherwise None.
        """
        if "--version" in argv or "-v" in argv:
            mini = argparse.ArgumentParser(add_help=False)
            mini.add_argument("-v", "--version", action="store_true")
            parsed, _ = mini.parse_known_args(argv)
            if parsed.version:
                return argparse.Namespace(version=True, input_file=None)

        if "--config-check" in argv:
            mini = argparse.ArgumentParser(add_help=False)
            mini.add_argument("--config-check", type=str, metavar="CONFIG_FILE")
            parsed, _ = mini.parse_known_args(argv)
            if getattr(parsed, "config_check", None):
                return argparse.Namespace(config_check=parsed.config_check, input_file=None, version=False)

        return None

    @staticmethod
    def _build_parser() -> argparse.ArgumentParser:
        """Construct and return the main ArgumentParser."""
        parser = argparse.ArgumentParser(
            prog="jira-importer",
            description="This script formats a CSV file for Jira import, validating and correcting data according to specified rules.",
            formatter_class=RichHelpFormatter,
            epilog="""
            Examples:
            jira-importer dataset.xlsx -c config_importer.json -d -y
            jira-importer dataset.xlsx -ce -y --auto-fix
            """,
        )
        parser.add_argument("input_file", help="Excel XLSX file", default="import.xlsx")

        App._add_config_args(parser)
        App._add_output_args(parser)
        App._add_confirmation_args(parser)
        App._add_feature_flags(parser)
        App._add_misc_args(parser)

        return parser

    @staticmethod
    def _add_config_args(parser: argparse.ArgumentParser) -> None:
        config_group = parser.add_mutually_exclusive_group()
        config_group.add_argument(
            "-ci", "--config-input", help="Get the configuration path from the input file location", action="store_true"
        )
        config_group.add_argument(
            "-ce",
            "--config-excel",
            help="Use the input Excel file as configuration source (sheet: Config)",
            action="store_true",
        )
        config_group.add_argument(
            "-cd",
            "--config-default",
            help="Get the configuration path from the application location",
            action="store_true",
        )
        config_group.add_argument(
            "-c", "--config", help="Configuration file path", default=DEFAULT_CONFIG_FILENAME, type=str
        )

    @staticmethod
    def _add_output_args(parser: argparse.ArgumentParser) -> None:
        output_group = parser.add_mutually_exclusive_group()
        output_group.add_argument(
            "-o",
            "--output",
            default=None,
            help="Output CSV path (default: <input>.processed.csv)",
            type=str,
        )
        output_group.add_argument(
            "-oi",
            "--output-is-input",
            default=None,
            help="Output CSV path in the input file location (default: <input>.processed.csv)",
            action="store_true",
        )
        parser.add_argument(
            "--cloud",
            dest="output_target_cloud",
            action="store_true",
            help="Shortcut to select Jira Cloud API as the output target",
        )

    @staticmethod
    def _add_confirmation_args(parser: argparse.ArgumentParser) -> None:
        auto_yes_group = parser.add_mutually_exclusive_group()
        auto_yes_group.add_argument(
            "-y", "-f", "--auto-yes", default=None, action="store_true", help="Auto-yes all prompts"
        )
        auto_yes_group.add_argument("-n", "--auto-no", default=None, action="store_true", help="Auto-no all prompts")

    @staticmethod
    def _add_feature_flags(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--data-sheet", default="Dataset", help="XLSX data sheet name (default: Dataset)")
        parser.add_argument(
            "--enable-excel-rules",
            default=False,
            action="store_true",
            help="Enable loading rules from Excel (scaffold only; safe to leave off).",
        )
        parser.add_argument(
            "--auto-fix",
            default=False,
            action="store_true",
            help="Enable safe auto-fixes (priority normalization, estimates, project key, etc.).",
        )
        parser.add_argument("--no-report", action="store_true", help="Do not print the validation report.")
        parser.add_argument(
            "--fix-cloud-estimates",
            default=False,
            action="store_true",
            help="Apply Jira Cloud x60 estimate quirk IN THE SINK (kept out of rules/fixes).",
        )

    @staticmethod
    def _add_misc_args(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("-v", "--version", help="Show version", action="store_true")
        parser.add_argument("-d", "--debug", help="Enable debug mode", action="store_true")
        # parser.add_argument("-i", "--import-to-cloud", dest="import_to_cloud", help="Import to Atlassian Cloud via the API", default='none')
