# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import argparse
import logging
import os
import re
import time
from datetime import datetime, timedelta

from .bisect import Bisector
from .evaluator.browser import BrowserEvaluator
from .evaluator.js import JSEvaluator

log = logging.getLogger('autobisect')


class ExpandPath(argparse.Action):
    """
    Expand user and relative-paths
    """

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, os.path.abspath(os.path.expanduser(values)))


def _parse_args(argv=None):
    """
    Argument parser
    """
    parser = argparse.ArgumentParser(description='Autobisection tool for Mozilla Firefox and SpiderMonkey')

    global_args = argparse.ArgumentParser(add_help=False)
    global_args.add_argument('testcase', help='Path to testcase')

    boundary_args = global_args.add_argument_group('boundary arguments (YYYY-MM-DD or SHA1 revision)')
    boundary_args.add_argument('--start', default=(datetime.utcnow() - timedelta(days=364)).strftime('%Y-%m-%d'),
                               help='Start revision (default: earliest available TC build)')
    boundary_args.add_argument('--end', default=datetime.utcnow().strftime('%Y-%m-%d'),
                               help='End revision (default: latest available TC build)')

    bisection_args = global_args.add_argument_group('bisection arguments')
    bisection_args.add_argument('--timeout', type=int, default=60,
                                help='Maximum iteration time in seconds (default: %(default)s)')
    bisection_args.add_argument('--repeat', type=int, default=1,
                                help='Number of times to evaluate testcase (per build)')
    bisection_args.add_argument('--config', action=ExpandPath, help='Path to optional config file')
    bisection_args.add_argument('--find-fix', action='store_true', help='Identify fix date')

    branch_args = global_args.add_argument_group('branch')
    branch_selector = branch_args.add_mutually_exclusive_group()
    branch_selector.add_argument('--inbound', action='store_const', const='inbound', dest='branch',
                                 help='Download from mozilla-inbound')
    branch_selector.add_argument('--central', action='store_const', const='central', dest='branch',
                                 help='Download from mozilla-central (default)')
    branch_selector.add_argument('--release', action='store_const', const='release', dest='branch',
                                 help='Download from mozilla-release')
    branch_selector.add_argument('--beta', action='store_const', const='beta', dest='branch',
                                 help='Download from mozilla-beta')
    branch_selector.add_argument('--esr', action='store_const', const='esr52', dest='branch',
                                 help='Download from mozilla-esr52')

    build_args = global_args.add_argument_group('build arguments')
    build_args.add_argument('--asan', action='store_true', help='Test asan builds')
    build_args.add_argument('--debug', action='store_true', help='Test debug builds')
    build_args.add_argument('--fuzzing', action='store_true', help='Test --enable-fuzzing builds')
    build_args.add_argument('--coverage', action='store_true', help='Test --coverage builds')
    build_args.add_argument('--32', dest='arch_32', action='store_true',
                            help='Test 32 bit version of browser on 64 bit system.')

    subparsers = parser.add_subparsers(dest='target')
    subparsers.required = True

    firefox_sub = subparsers.add_parser('firefox', parents=[global_args], help='Bisect Firefox testcase')
    ffp_args = firefox_sub.add_argument_group('launcher arguments')
    ffp_args.add_argument('--asserts', action='store_true', help='Detect soft assertions')
    ffp_args.add_argument('--detect', choices=['crash', 'memory', 'log', 'timeout'], default='crash',
                          help='Type of failure to detect (default: %(default)s)')
    ffp_args.add_argument('--launch-timeout', type=int, default=300,
                          help='Maximum launch time in seconds (default: %(default)s)')
    ffp_args.add_argument('--ext', action=ExpandPath, help='Path to fuzzPriv extension')
    ffp_args.add_argument('--prefs', action=ExpandPath, help='Path to preference file')
    ffp_args.add_argument('--profile', action=ExpandPath, help='Path to profile directory')
    ffp_args.add_argument('--memory', type=int, help='Process memory limit in MBs (default: no limit)')
    ffp_args.add_argument('--log-limit', type=int, help='Log file size limit in MBs (default: no limit)')
    ffp_args.add_argument('--gdb', action='store_true', help='Use GDB')
    ffp_args.add_argument('--valgrind', action='store_true', help='Use valgrind')
    ffp_args.add_argument('--xvfb', action='store_true', help='Use xvfb (Linux only)')

    js_sub = subparsers.add_parser('js', parents=[global_args], help='Bisect SpiderMonkey testcase')
    js_args = js_sub.add_argument_group('launcher arguments')
    js_args.add_argument('--flags', help='Runtime flags to pass to the binary')
    js_args.add_argument('--detect', choices=['crash', 'diff', 'hang', 'output'], default='crash',
                         help='Type of failure to detect (default: %(default)s)')

    js_diff_args = js_sub.add_argument_group('diff arguments')
    js_diff_args.add_argument('--arg_1', help='Set of arguments to supply to the first run')
    js_diff_args.add_argument('--arg_2', help='Set of arguments to supply to the second run')

    js_hang_args = js_sub.add_argument_group('hang arguments')
    js_hang_args.add_argument('--hang-time', type=int, metavar='TIME',
                              help='Hang time threshold (must be greater than timeout)')

    js_out_args = js_sub.add_argument_group('output arguments')
    js_out_args.add_argument('--match', help='Mark as interesting if string detected in output')
    js_out_args.add_argument('--regex', help='Treat match as a regex')

    args = parser.parse_args(argv)

    if not args.branch:
        args.branch = 'central'

    if not re.match(r'^[0-9[a-f]{12,40}$|^[0-9]{4}-[0-9]{2}-[0-9]{2}$', args.start):
        parser.error('Invalid start value supplied')
    if not re.match(r'^[0-9[a-f]{12,40}$|^[0-9]{4}-[0-9]{2}-[0-9]{2}$', args.end):
        parser.error('Invalid end value supplied')
    if args.timeout <= 0:
        parser.error('Invalid timeout value supplied')

    if args.target == 'firefox':
        if args.detect == 'log' and args.log_limit is None:
            parser.error('Detect mode set to log-limit but no limit set!')
        if args.detect == 'memory' and args.memory is None:
            parser.error('Detect mode set to log-limit but no limit set!')
    elif args.target == 'js':
        if args.detect == 'diff':
            if not args.arg_1 or not args.args_2:
                parser.error('Detect mode set to diff but no arguments supplied!')
        if args.detect == 'hang':
            if args.hang_time is None:
                parser.error('Detect mode set to hang but no hang threshold supplied!')
            if args.hang_time <= 0:
                parser.error('Invalid hangout threshold value supplied!')
            if args.hang_time > args.timeout:
                parser.error('Hang threshold greater than timeout!')
        if args.detect == 'output':
            if args.match is None:
                parser.error('Detect mode set to output but no output string supplied!')

    return args


def main(argv=None):
    """
    Autobisect main entry point
    """
    log_level = logging.INFO
    log_fmt = '[%(asctime)s] %(message)s'
    if bool(os.getenv('DEBUG')):
        log_level = logging.DEBUG
        log_fmt = '%(levelname).1s %(name)s [%(asctime)s] %(message)s'
    logging.basicConfig(format=log_fmt, datefmt='%Y-%m-%d %H:%M:%S', level=log_level)
    logging.getLogger('requests').setLevel(logging.WARNING)

    args = _parse_args(argv)

    if args.target == 'firefox':
        evaluator = BrowserEvaluator(args)
    else:
        evaluator = JSEvaluator(args)

    bisector = Bisector(evaluator, args)
    start_time = time.time()
    bisector.bisect()
    end_time = time.time()
    elapsed = timedelta(seconds=(int(end_time - start_time)))
    log.info('Bisection completed in: %s' % elapsed)
