# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from argparse import ArgumentParser

from ...args import BisectCommonArgs


class JSArgs(BisectCommonArgs):
    """Arguments for the JSEvaluator"""

    def __init__(self, parser: ArgumentParser):
        self.parser = parser
        super().__init__(parser)

        launcher = self.parser.add_argument_group("Launcher Arguments")
        launcher.add_argument("--flags", help="Runtime flags to pass to the binary")
        launcher.add_argument(
            "--detect",
            choices=["crash", "diff", "hang", "output"],
            default="crash",
            help="Type of failure to detect (default: %(default)s)",
        )

        diff = self.parser.add_argument_group("Diff Arguments")
        diff.add_argument("--arg_1", help="Arguments to supply to the first run")
        diff.add_argument("--arg_2", help="Arguments to supply to the second run")

        output = self.parser.add_argument_group("Output Arguments")
        output.add_argument("--match", help="String to detect in output")
        output.add_argument("--regex", help="Treat match as a regex")
