# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from argparse import ArgumentParser, Action
import logging
import os
import time
from datetime import timedelta

from fuzzfetch import BuildFlags
from fuzzfetch.fetch import Platform

from .bisect import BisectionResult, Bisector
from .evaluators import BrowserArgs, BrowserEvaluator, JSEvaluator, JSArgs

LOG = logging.getLogger("autobisect")


class ExpandPath(Action):
    """
    Expand user and relative-paths
    """

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, os.path.abspath(os.path.expanduser(values)))


def console_init_logging():
    """
    Enable logging when called from console
    """
    log_level = logging.INFO
    log_fmt = "[%(asctime)s] %(message)s"
    if bool(os.getenv("DEBUG")):
        log_level = logging.DEBUG
        log_fmt = "%(levelname).1s %(name)s [%(asctime)s] %(message)s"
    logging.basicConfig(format=log_fmt, datefmt="%Y-%m-%d %H:%M:%S", level=log_level)
    logging.getLogger("requests").setLevel(logging.WARNING)


def parse_args():
    """
    Argument parser
    """
    parser = ArgumentParser(description="Firefox and Spidermonkey Bisection Tool",)
    subparsers = parser.add_subparsers(dest="target")
    subparsers.required = True

    ff_sub = BrowserArgs(subparsers.add_parser("firefox", conflict_handler="resolve"))
    js_sub = JSArgs(subparsers.add_parser("js", conflict_handler="resolve"))

    args = parser.parse_args()
    if args.target == "firefox":
        ff_sub.sanity_check(args)
    elif args.target == "js":
        js_sub.sanity_check(args)

    return args


def main(args):
    """
    Autobisect main entry point
    """
    if args.target == "firefox":
        evaluator = BrowserEvaluator(**vars(args))
    else:
        if args.flags is not None:
            args.flags = args.flags.split(" ")
        evaluator = JSEvaluator(**vars(args))

    flags = BuildFlags(
        args.asan, args.tsan, args.debug, args.fuzzing, args.coverage, args.valgrind
    )
    platform = Platform(args.os, args.cpu)
    bisector = Bisector(
        evaluator,
        args.target,
        args.branch,
        args.start,
        args.end,
        flags,
        platform,
        args.find_fix,
        args.config,
    )
    start_time = time.time()
    result = bisector.bisect()
    end_time = time.time()
    if result.status == BisectionResult.SUCCESS:
        LOG.info("Reduced build range to:")
        LOG.info("> Start: %s (%s)", result.start.changeset, result.start.id)
        LOG.info("> End: %s (%s)", result.end.changeset, result.end.id)
        LOG.info("> %s", result.pushlog)
    else:
        LOG.error("Bisection failed!")

    elapsed = timedelta(seconds=(int(end_time - start_time)))
    LOG.info("Bisection completed in: %s", elapsed)
