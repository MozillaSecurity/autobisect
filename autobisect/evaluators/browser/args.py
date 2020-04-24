# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from grizzly.replay import ReplayArgs

from ...args import BisectCommonArgs, _remove_arg, _suppress_arg


class BrowserArgs(BisectCommonArgs, ReplayArgs):
    """
    Argparser for BrowserEvaluator
    """

    CONFLICTING_ARGS = [
        "binary",
        "fuzzmanager",
        "include_test",
        "input",
        "logs",
        "no_harness",
        "relaunch",
        "rr",
        "tool",
    ]

    IGNORED_ARGS = [
        "min_crashes",
        "platform",
        "sig",
        "working_path",
    ]

    def __init__(self, parser):
        self.parser = parser
        super().__init__()

        # Remove conflicting args
        for arg in BrowserArgs.CONFLICTING_ARGS:
            self._sanity_skip.add(arg)
            _remove_arg(self.parser, arg)

        # Suppress help output for unused args
        for arg in BrowserArgs.IGNORED_ARGS:
            self._sanity_skip.add(arg)
            _suppress_arg(self.parser, arg)

    def parse_args(self, argv=None):
        args = self.parser.parse_args(argv)
        self.sanity_check(args)
        return args
