"""Description: This script is the main application for the Jira Importer.

Author:
    Julien (@tom4897)
"""

import argparse
import logging
import sys
from pathlib import Path

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

    def event_abort(self, exit_code: int = -1, message: str = "Execution aborted.") -> None:
        """Event abort, when the script is aborted."""
        ui.error(message)
        logger.critical(message)
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
            ui.error(f"Error code: {exit_code}")
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

        if "--credentials" in argv:
            mini = argparse.ArgumentParser(add_help=False)
            mini.add_argument("--credentials", nargs="?", choices=["run", "show", "clear", "test"], const="run")
            parsed, _ = mini.parse_known_args(argv)
            if getattr(parsed, "credentials", None):
                # For "test" action, we need full args parsing to get config options
                # So skip fast-path and let the full parser handle it
                if parsed.credentials == "test":
                    return None
                return argparse.Namespace(
                    credentials=parsed.credentials, input_file=None, version=False, show_config=False
                )

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
            allow_abbrev=False,
        )
        parser.add_argument("input_file", nargs="?", help="Excel XLSX file", default="import.xlsx")

        App._add_config_args(parser)
        App._add_output_args(parser)
        App._add_confirmation_args(parser)
        App._add_feature_flags(parser)
        App._add_credentials_args(parser)
        App._add_misc_args(parser)
        App._add_debug_args(parser)

        return parser

    @staticmethod
    def _add_config_args(parser: argparse.ArgumentParser) -> None:
        config_group = parser.add_argument_group(
            title="Configuration Options", description="Choose how to load configuration settings"
        )
        config_group_exclusive = config_group.add_mutually_exclusive_group()
        config_group_exclusive.add_argument(
            "-ci",
            "--config-input",
            # help="Get the configuration path from the input file location",
            help=argparse.SUPPRESS,
            action="store_true",
        )
        config_group_exclusive.add_argument(
            "-ce",
            "--config-excel",
            help="Use the input Excel file as configuration source (sheet: Config)",
            action="store_true",
        )
        config_group_exclusive.add_argument(
            "-cd",
            "--config-default",
            help=argparse.SUPPRESS,
            # help="Get the configuration path from the application location",
            action="store_true",
        )
        config_group_exclusive.add_argument(
            "-c", "--config", help="Configuration file path", default=DEFAULT_CONFIG_FILENAME, type=str
        )

    @staticmethod
    def _add_output_args(parser: argparse.ArgumentParser) -> None:
        output_group = parser.add_argument_group(
            title="Output Options", description="Control where and how output is generated"
        )
        output_group_exclusive = output_group.add_mutually_exclusive_group()
        output_group_exclusive.add_argument(
            "-o",
            "--output",
            default=None,
            help="Output CSV path (default: <input>.processed.csv)",
            type=str,
        )
        output_group_exclusive.add_argument(
            "-oi",
            "--output-is-input",
            default=None,
            help=argparse.SUPPRESS,
            # help="Output CSV path in the input file location (default: <input>.processed.csv)",
            action="store_true",
        )
        output_group_exclusive.add_argument(
            "--cloud",
            dest="output_target_cloud",
            action="store_true",
            help="Shortcut to select Jira Cloud API as the output target",
        )
        output_group.add_argument(
            "--cloud-debug-payloads",
            action="store_true",
            help=argparse.SUPPRESS,
            # help="Write Jira Cloud API payloads to JSON files for debugging (automatically enabled with -d)",
        )

    @staticmethod
    def _add_confirmation_args(parser: argparse.ArgumentParser) -> None:
        confirmation_group = parser.add_argument_group(
            title="Confirmation Options", description="Control whether to auto-confirm prompts"
        )
        auto_yes_group = confirmation_group.add_mutually_exclusive_group()
        auto_yes_group.add_argument("-y", "--auto-yes", default=None, action="store_true", help="Auto-yes all prompts")
        auto_yes_group.add_argument("-n", "--auto-no", default=None, action="store_true", help="Auto-no all prompts")

    @staticmethod
    def _add_feature_flags(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--data-sheet", default="Dataset", help="XLSX data sheet name (default: Dataset)")
        parser.add_argument(
            "--enable-excel-rules",
            default=False,
            action="store_true",
            # help="Enable loading rules from Excel (scaffold only; safe to leave off).",
            help=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--auto-fix",
            default=False,
            action="store_true",
            help="Enable safe auto-fixes (priority normalization, estimates, project key, etc.).",
        )
        parser.add_argument(
            "--no-report",
            action="store_true",
            # help="Do not print the validation report (useful for CI/CD pipelines)."
            help=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--fix-cloud-estimates",
            default=False,
            action="store_true",
            help="Apply Jira Cloud x60 estimate quirk IN THE SINK (kept out of rules/fixes).",
        )

    @staticmethod
    def _add_credentials_args(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--credentials",
            nargs="?",
            choices=["run", "show", "clear", "test"],
            const="run",
            metavar="ACTION",
            help="Manage Jira API credentials. Default action is 'run' if no action specified. Actions: run (interactive setup), show (display current), clear (remove stored), test (verify connection)",
        )

    @staticmethod
    def _add_misc_args(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("-v", "--version", help="Show version", action="store_true")

    @staticmethod
    def _add_debug_args(parser: argparse.ArgumentParser) -> None:
        """Add debug-specific arguments that are hidden from main help."""
        debug_group = parser.add_argument_group("Debug Options")
        debug_group.add_argument("-d", "--debug", help="Enable debug logging", action="store_true")
        debug_group.add_argument("--show-config", help="Show configuration and exit", action="store_true")
        debug_group.add_argument("--dry-run", help="Process data but stop before writing output", action="store_true")

    @staticmethod
    def show_version() -> int:
        """Handle --version flag and exit early.

        Returns:
            Exit code (always 0 for version display).
        """
        from jira_importer.config.minimal_config import MinimalConfig  # pylint: disable=import-outside-toplevel

        minimal_config = MinimalConfig()
        artifact_manager = ArtifactManager(minimal_config)
        app = App(artifact_manager)
        app.print_version()
        app.event_close(exit_code=0, cleanup=False)
        return 0

    @staticmethod
    def show_config(args: argparse.Namespace) -> int:
        """Handle --show-config flag and exit early.

        Args:
            args: Parsed command line arguments.

        Returns:
            Exit code (0 on success, 1 on error).
        """
        from jira_importer.config.utils import (  # pylint: disable=import-outside-toplevel
            determine_config_path,
            display_config,
        )
        from jira_importer.errors import (  # pylint: disable=import-outside-toplevel
            ConfigurationError,
            format_error_for_display,
        )

        ui_instance, _ = ConsoleIO.getComponents()

        try:
            if not hasattr(args, "input_file") or not args.input_file:
                # Provide dummy input_file for config determination
                args.input_file = "dummy.xlsx"
            config_path = determine_config_path(args)
            display_config(config_path)
            return 0
        except ConfigurationError as exc:
            # Domain configuration error: show a clear message
            ui_instance.error(format_error_for_display(exc))
            return 1
        except Exception as exc:  # pylint: disable=broad-except
            # Unexpected internal error
            ui_instance.error(f"Failed to load configuration for show-config: {exc}")
            return 1

    @staticmethod
    def graceful_exit(exit_code: int, do_cleanup: bool = False) -> None:
        """Exit gracefully with cleanup using minimal config.

        Args:
            exit_code: Exit code to use.
            do_cleanup: Whether to perform cleanup operations.
        """
        from jira_importer.config.minimal_config import MinimalConfig  # pylint: disable=import-outside-toplevel

        ui_instance, _ = ConsoleIO.getComponents()
        ui_instance.lf()
        minimal_config = MinimalConfig()
        app = App(ArtifactManager(minimal_config))
        app.event_close(exit_code=exit_code, cleanup=do_cleanup)

    @staticmethod
    def get_autoreply_from_args(args: argparse.Namespace) -> bool | None:
        """Get the autoreply flag based on the command line arguments.

        Args:
            args: Parsed command line arguments.

        Returns:
            True for -y/--yes, False for -n/--no, None otherwise.
        """
        if getattr(args, "auto_yes", False):
            return True
        if getattr(args, "auto_no", False):
            return False
        return None

    @staticmethod
    def get_output_dir_from_args(args: argparse.Namespace) -> Path:
        """Get the output directory path based on the command line arguments.

        Args:
            args: Parsed command line arguments.

        Returns:
            Output directory path.
        """
        if args.output:
            return Path(args.output)
        return Path(args.input_file).parent

    @staticmethod
    def get_output_target_from_args(args: argparse.Namespace) -> str:
        """Get the output target based on the command line arguments.

        Args:
            args: Parsed command line arguments.

        Returns:
            Output target: "cloud" or "csv".
        """
        if getattr(args, "output_target_cloud", False):
            return "cloud"
        return "csv"
