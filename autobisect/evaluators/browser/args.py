# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import os
from argparse import ArgumentParser, Namespace
from pathlib import Path

from ...args import BisectCommonArgs


class BrowserArgs(BisectCommonArgs):
    """Arguments for the BrowserEvaluator"""

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
        launcher_grp.add_argument(
            "--xvfb",
            action="store_true",
            help="Use Xvfb (Linux only)",
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
            help="Space separated list of issue types to ignore. Valid options: %s"
            " (default: %s)"
            % (" ".join(BrowserArgs.IGNORABLE), " ".join(BrowserArgs.IGNORABLE)),
        )

    def sanity_check(self, args: Namespace) -> None:
        """Perform Sanity Checks

        Args:
            args: Parsed arguments
        """
        super().sanity_check(args)
        if args.prefs:
            args.prefs = args.prefs.expanduser()
            if not (args.prefs.is_file() and os.access(args.prefs, os.R_OK)):
                self.parser.error("Cannot read the prefs.js file!")
