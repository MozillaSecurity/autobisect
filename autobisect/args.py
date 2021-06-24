# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# pylint: disable=protected-access
import itertools
import os
import platform as std_platform
from argparse import ArgumentParser, Namespace
from logging import CRITICAL, DEBUG, ERROR, INFO, WARNING
from pathlib import Path

from fuzzfetch import Fetcher, Platform

CPU_CHOICES = sorted(
    set(
        itertools.chain(
            itertools.chain.from_iterable(Platform.SUPPORTED.values()),
            Platform.CPU_ALIASES,
        )
    )
)

LOG_LEVELS = {
    "CRIT": CRITICAL,
    "ERROR": ERROR,
    "WARN": WARNING,
    "INFO": INFO,
    "DEBUG": DEBUG,
}


class BisectCommonArgs:
    """Arguments common to all bisection targets"""

    def __init__(self, parser: ArgumentParser):
        """Add common args to parser

        Args:
            parser:
        """
        self.parser = parser
        self.parser.add_argument(
            "testcase",
            type=Path,
            help="Path to testcase",
        )

        self.parser.add_argument(
            "--log-level",
            default="INFO",
            help="Configure console logging. Options: %s (default: %%(default)s)"
            % ", ".join(k for k, v in sorted(LOG_LEVELS.items(), key=lambda x: x[1])),
        )

        boundary_args = self.parser.add_argument_group(
            title="Boundary Arguments",
            description="Accepts revision or build date in YYYY-MM-DD format)",
        )
        boundary_args.add_argument(
            "--start",
            help="Start build id (default: earliest available build)",
        )
        boundary_args.add_argument(
            "--end",
            help="End build id (default: latest available build)",
        )

        bisection_args = self.parser.add_argument_group(title="Bisection Arguments")
        bisection_args.add_argument(
            "--timeout",
            type=int,
            default=60,
            help="Maximum iteration time in seconds (default: %(default)s)",
        )
        bisection_args.add_argument(
            "--repeat",
            type=int,
            default=1,
            help="Number of times to evaluate testcase (per build)",
        )
        bisection_args.add_argument(
            "--config",
            type=Path,
            help="Path to optional config file",
        )
        bisection_args.add_argument(
            "--find-fix",
            action="store_true",
            help="Identify fix date",
        )

        target_group = self.parser.add_argument_group("Target Arguments")
        target_group.add_argument(
            "--os",
            choices=sorted(Platform.SUPPORTED),
            help=f"Specify the target system. (default: {std_platform.system()})",
        )
        target_group.add_argument(
            "--cpu",
            choices=CPU_CHOICES,
            help=f"Specify the target CPU. (default: {std_platform.machine()})",
        )

        branch_group = self.parser.add_argument_group("Branch Arguments")
        branch_args = branch_group.add_mutually_exclusive_group()
        branch_args.add_argument(
            "--central",
            action="store_const",
            const="central",
            dest="branch",
            help="Download from mozilla-central (default)",
        )
        branch_args.add_argument(
            "--release",
            action="store_const",
            const="release",
            dest="branch",
            help="Download from mozilla-release",
        )
        branch_args.add_argument(
            "--beta",
            action="store_const",
            const="beta",
            dest="branch",
            help="Download from mozilla-beta",
        )
        branch_args.add_argument(
            "--esr-stable",
            action="store_const",
            const="esr-stable",
            dest="branch",
            help="Download from esr-stable",
        )
        branch_args.add_argument(
            "--esr-next",
            action="store_const",
            const="esr-next",
            dest="branch",
            help="Download from esr-next",
        )
        branch_args.add_argument(
            "--try",
            action="store_const",
            const="try",
            dest="branch",
            help="Download from try",
        )
        branch_args.add_argument(
            "--autoland",
            action="store_const",
            const="autoland",
            dest="branch",
            help="Download from autoland",
        )

        build_group = self.parser.add_argument_group("Build Arguments")
        build_group.add_argument(
            "-d",
            "--debug",
            action="store_true",
            help="Get debug builds w/ symbols (default=optimized).",
        )
        build_group.add_argument(
            "-a",
            "--asan",
            action="store_true",
            help="Download AddressSanitizer builds.",
        )
        build_group.add_argument(
            "-t",
            "--tsan",
            action="store_true",
            help="Download ThreadSanitizer builds.",
        )
        build_group.add_argument(
            "--fuzzing",
            action="store_true",
            help="Download --enable-fuzzing builds.",
        )
        build_group.add_argument(
            "--fuzzilli",
            action="store_true",
            help="Download --enable-js-fuzzilli builds.",
        )
        build_group.add_argument(
            "--coverage",
            action="store_true",
            help="Download --coverage builds.",
        )
        build_group.add_argument(
            "--valgrind",
            action="store_true",
            help="Download Valgrind builds.",
        )
        build_group.add_argument(
            "--no-opt",
            action="store_true",
            help="Download non-optimized builds.",
        )

        self.parser.set_defaults(branch="central")

    def sanity_check(self, args: Namespace) -> None:
        """Perform Sanity Checks

        Args:
            args: Parsed arguments
        """
        args.testcase = args.testcase.expanduser()
        if not args.testcase.is_file() or not os.access(args.testcase, os.R_OK):
            self.parser.error("Cannot access testcase!")

        log_level = LOG_LEVELS.get(args.log_level.upper(), None)
        if log_level is None:
            self.parser.error("Invalid log-level %r" % (args.log_level,))
        args.log_level = log_level

        if args.config is not None:
            args.config = args.config.expanduser()
            if not args.config.is_file() or not os.access(args.config, os.R_OK):
                self.parser.error("Cannot access configuration file!")

        if args.branch is None:
            args.branch = "central"
        elif args.branch.startswith("esr"):
            args.branch = Fetcher.resolve_esr(args.branch)

        if args.target == "firefox" and args.fuzzilli:
            self.parser.error("Fuzzilli builds are not available for firefox")
