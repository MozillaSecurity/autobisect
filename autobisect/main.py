# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import logging
import time
from argparse import ArgumentParser, Namespace
from datetime import timedelta
from typing import Union

from fuzzfetch import BuildFlags, Platform
from grizzly.main import configure_logging

from .bisect import BisectionResult, Bisector
from .evaluators import BrowserArgs, BrowserEvaluator, JSArgs, JSEvaluator

LOG = logging.getLogger("autobisect")


def parse_args() -> Namespace:
    """
    Argument parser
    """
    parser = ArgumentParser(description="Firefox and Spidermonkey Bisection Tool")
    subparsers = parser.add_subparsers(dest="target", required=True)
    firefox_parser = BrowserArgs(subparsers.add_parser("firefox"))
    js_parser = JSArgs(subparsers.add_parser("js"))

    args = parser.parse_args()
    if args.target == "firefox":
        firefox_parser.sanity_check(args)
    elif args.target == "js":
        js_parser.sanity_check(args)

    return args


def main(args: Namespace) -> int:
    """Autobisect main entry point

    Args:
        args: Parsed arguments
    """
    configure_logging(args.log_level)

    evaluator: Union[BrowserEvaluator, JSEvaluator]
    if args.target == "firefox":
        evaluator = BrowserEvaluator(**vars(args))
    else:
        args.flags = [] if args.flags is None else args.flags.split(" ")
        evaluator = JSEvaluator(**vars(args))

    flags = BuildFlags(
        args.asan,
        args.tsan,
        args.debug,
        args.fuzzing,
        args.coverage,
        args.valgrind,
        args.no_opt,
        args.fuzzilli,
    )
    platform = Platform(args.os, args.cpu)
    bisector = Bisector(
        evaluator,
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

    return 0
