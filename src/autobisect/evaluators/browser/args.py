# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import os
from os import access
from platform import system
from argparse import ArgumentParser, Namespace
from pathlib import Path

from autobisect.args import BisectCommonArgs


class BrowserArgs(BisectCommonArgs):
    """Arguments for the BrowserEvaluator."""

    IGNORABLE = ("log-limit", "memory", "timeout")

    def __init__(self, parser: ArgumentParser) -> None:
        super().__init__(parser)
        self.parser = parser
        launcher_grp = self.parser.add_argument_group("Launcher Arguments")
        launcher_grp.add_argument(
            "--launch-timeout",
            type=int,
            default=300,
            help="Number of seconds to wait before LaunchError is raised"
            " (default: %(default)s)",
        )
        launcher_grp.add_argument(
            "-p",
            "--prefs",
            type=Path,
            help="Optional prefs.js file to use",
        )
        headless_choices = ["default"]
        if system().startswith("Linux"):
            headless_choices.append("xvfb")
        launcher_grp.add_argument(
            "--headless",
            choices=headless_choices,
            const="default",
            default=None,
            nargs="?",
            help="Headless mode. 'default' uses browser's built-in headless mode.",
        )
        launcher_grp.add_argument(
            "--no-harness",
            action="store_true",
            help="Don't use the harness for redirection.  Browser will relaunch on every attempt.",
        )

        reporter_grp = self.parser.add_argument_group("Reporter Arguments")
        reporter_grp.add_argument(
            "--ignore",
            nargs="*",
            default=list(BrowserArgs.IGNORABLE),
            help="Space separated list of issue types to ignore. Valid options: "
            f"{' '.join(BrowserArgs.IGNORABLE)} (default: {' '.join(BrowserArgs.IGNORABLE)})",
        )

        if system().startswith("Linux"):
            dbg_group = launcher_grp.add_mutually_exclusive_group()
            dbg_group.add_argument(
                "--pernosco",
                action="store_true",
                help="Use rr. Trace intended to be used with Pernosco.",
            )
            dbg_group.add_argument("--rr", action="store_true", help="Use rr.")
        else:
            self.parser.set_defaults(
                pernosco=False,
                rr=False,
                valgrind=False,
            )

    def sanity_check(self, args: Namespace) -> None:
        """
        Perform Sanity Checks.

        :param args: Parsed arguments.
        """
        super().sanity_check(args)
        if args.prefs:
            args.prefs = args.prefs.expanduser()
            if not (args.prefs.is_file() and access(args.prefs, os.R_OK)):
                self.parser.error("Cannot read the prefs.js file!")
