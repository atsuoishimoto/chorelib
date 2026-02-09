"""CLI entry point for chorelib build scripts.

Provides the ``Main`` class that parses command-line arguments, selects
targets, and drives the async build execution.
"""

import argparse
import asyncio
import logging
import os
import sys
import textwrap
import traceback
from types import ModuleType

import chorelib
from chorelib.utils import message

from .deprunner import run
from .ruledef import RuleSet

logger = logging.getLogger(__name__)


class Main:
    """CLI driver for chorelib build scripts.

    Parses command-line arguments (targets, verbosity, workers, rebuild
    flags) and runs the async build process. Subclass this to add custom
    arguments via ``add_arguments``.
    """

    def __init__(self, rules: RuleSet | None = None) -> None:
        if rules is None:
            rules = chorelib._default_rules
        self.rules = rules
        self.args: argparse.Namespace
        self._load_args()

    def _load_args(self) -> None:
        self.parser = self._build_parser()
        self.args = self.parse_args(self.parser)

        chorelib.verbose = self.args.verbose
        if self.args.verbose >= 3:
            logging.basicConfig(level=logging.DEBUG, format="%(message)s")

    def parse_args(self, parser: argparse.ArgumentParser) -> argparse.Namespace:
        """Parse command-line arguments. Override to customize parsing."""
        return parser.parse_args()

    def _build_parser(self) -> argparse.ArgumentParser:
        """Create and configure the ArgumentParser with standard options."""
        default_target = self.rules.select_default_target()
        target_names = [n for n in self.rules.get_target_names()]

        parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter, add_help=False
        )

        parser.add_argument(
            "-h",
            "--help",
            dest="showhelp",
            action="store_true",
            help="show this help message and exit",
        )

        parser.add_argument(
            "-C",
            "--directory",
            dest="directory",
            help="Change to DIRECTORY before performing any operations",
        )

        parser.add_argument(
            "-w",
            "--workers",
            type=int,
            default=1,
            help="Allow up to N workers to run simultaneously (default: 1)",
        )

        parser.add_argument(
            "-r", "--rebuild", dest="rebuild", action="store_true", help="Rebuild all"
        )

        parser.add_argument(
            "-l", "--list-targets", dest="list", action="store_true", help="List targets"
        )

        parser.add_argument(
            "-v",
            dest="verbose",
            action="count",
            default=0,
            help="Increase verbosity level (default: 0)",
        )

        parser.add_argument(
            "-V",
            "--version",
            dest="version",
            action="store_true",
            default=False,
            help="Show version",
        )

        targetdesc = "Build targets"
        if target_names:
            targetdesc += ":" + " ".join(f"[{n}]" for n in target_names)
        if default_target:
            targetdesc += f" (Default: {default_target})"

        parser.add_argument("targets", nargs="*", help=targetdesc)

        self.add_arguments(parser)
        return parser

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Hook for subclasses to add custom command-line arguments."""
        pass

    def _get_version(self) -> str:
        """Return the version string for --version output."""
        progname = os.path.basename(sys.argv[0])
        version = getattr(chorelib, "__version__", "unknown")
        return f"{progname} (chorelib version {version})"

    def _list_targets(self) -> None:
        for rule in self.rules.rules:
            print(rule.get_descr())

    def _build_doc(self, module: ModuleType) -> str:
        """Build the help text from the module docstring and rule documentation."""
        moduledoc = (module.__doc__ or "").strip()
        lines: list[str] = []
        for title, doc in self.rules.get_docs():
            text = f"{title}:"
            if doc:
                doc = doc.lstrip("\n")
                doc = textwrap.indent(textwrap.dedent(doc).rstrip(), " " * 4)
                text = f"{text}\n{doc}"
            lines.append(text)
        targetsdoc = ""
        if lines:
            targetsdoc = "\n\n".join(lines)

        return "\n\n".join(s for s in [moduledoc, targetsdoc] if s)

    def _get_command_module(self) -> ModuleType:
        """Return the __main__ module (the user's build script)."""
        return sys.modules["__main__"]

    def build(self, targets: list[str]) -> None:
        """Execute the async build for the given targets."""
        asyncio.run(
            run(self.rules, targets, num_workers=self.args.workers, rebuild=self.args.rebuild)
        )

    def get_default_targets(self) -> list[str]:
        """Return the default target(s) when none are specified on the command line."""
        default_target = self.rules.select_default_target()
        if not default_target:
            return []
        return [str(default_target)]

    def run(self) -> None:
        """Main entry point: parse args, configure logging, and execute the build."""
        if self.args.showhelp:
            doc = self._build_doc(self._get_command_module())
            self.parser.description = doc
            self.parser.print_help()
            sys.exit(0)
            return

        if self.args.version:
            print(self._get_version())
            sys.exit(0)
            return

        if self.args.list:
            self._list_targets()
            sys.exit(0)
            return

        targets: list[str] = self.args.targets
        if not targets:
            targets = self.get_default_targets()
            message(f"No targets specified. Using default targets: {targets}", 2)
            if not targets:
                sys.exit("No default target defined.")
                return

        curdir = os.getcwd()
        if self.args.directory:
            os.chdir(self.args.directory)
            logger.debug(f"Changed directory to {self.args.directory}")

        try:
            self.build(targets)
        except Exception as e:
            print("Error:", e, file=sys.stderr)
            if self.args.verbose >= 3:
                traceback.print_exc()
            sys.exit(1)
        finally:
            if self.args.directory:
                os.chdir(curdir)
