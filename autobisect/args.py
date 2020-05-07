# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# pylint: disable=protected-access
import argparse
import os

from fuzzfetch import FetcherArgs


def _remove_arg(parser, arg):
    """
    Remove args from existing parser
    :param parser: Target parser
    :param arg: Dest of arg to remove
    """
    # Remove defaults
    if arg in parser._defaults:
        del parser._defaults[arg]

    # Identify actions to be removed
    action_queue = []
    for a in parser._actions:
        if (a.option_strings and a.option_strings[0] == arg) or a.dest == arg:
            action_queue.append(a)

    # Remove actions
    for a in action_queue:
        parser._remove_action(a)

    # Identify action_groups to be removed
    empty_groups = []
    for a in parser._action_groups:
        action_group_queue = []
        for x in a._group_actions:
            if x.dest == arg:
                action_group_queue.append(x)
        for x in action_group_queue:
            a._group_actions.remove(x)
            if len(a._group_actions) == 0 and a not in empty_groups:
                empty_groups.append(a)

    # Remove now emptied groups
    for group in empty_groups:
        parser._action_groups.remove(group)


def _suppress_arg(parser, dest):
    """
    Suppress help messages from existing parser
    :param parser: Target parser
    :param dest: Dest of arg to remove
    """
    for action in parser._actions:
        if action.dest == dest:
            action.help = argparse.SUPPRESS


class ExpandPath(argparse.Action):
    """
    Expand user and relative-paths
    """

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, os.path.abspath(os.path.expanduser(values)))


class BisectCommonArgs(FetcherArgs):
    """
    Arguments common to all bisection targets
    """

    CONFLICTING_ARGS = [
        "build",
        "dry_run",
        "name",
        "nearest",
        "out",
        "target",
        "tests",
        "full_symbols",
    ]

    def __init__(self):
        if not hasattr(self, "parser"):
            self.parser = argparse.ArgumentParser(
                description="Autobisection tool for Mozilla Firefox and SpiderMonkey",
                conflict_handler="resolve",
            )
        super().__init__()

        self.parser.add_argument("testcase", help="Path to testcase")
        boundary_args = self.parser.add_argument_group(
            "Boundary Arguments (YYYY-MM-DD or SHA1 revision)"
        )
        boundary_args.add_argument(
            "--start", help="Start build id (default: earliest available build)"
        )
        boundary_args.add_argument(
            "--end", help="End build id (default: latest available build)"
        )

        bisection_args = self.parser.add_argument_group("Bisection Arguments")
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
            "--config", action=ExpandPath, help="Path to optional config file"
        )
        bisection_args.add_argument(
            "--find-fix", action="store_true", help="Identify fix date"
        )

        for arg in BisectCommonArgs.CONFLICTING_ARGS:
            _remove_arg(self.parser, arg)

    def sanity_check(self, args):
        """
        Validate supplied args
        :param args: Arguments
        """
        if args.branch is None:
            args.branch = "central"

    def parse_args(self, argv=None):
        """
        Parse and validate supplied args
        :param argv: Arguments
        """
        args = self.parser.parse_args(argv)
        self.sanity_check(args)

        return args


if __name__ == "__main__":
    print(BisectCommonArgs().parse_args())
