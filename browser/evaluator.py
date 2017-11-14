#!/usr/bin/env python
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import, division, print_function

import argparse
import logging
import os
import tempfile

from ffpuppet import FFPuppet, LaunchError

log = logging.getLogger('browser-bisect')


class BrowserBisector(object):
    def __init__(self, args):
        self.testcase = os.path.abspath(args.testcase)
        self.count = args.count

        # FFPuppet arguments
        self._use_gdb = args.gdb
        self._use_valgrind = args.valgrind
        self._use_xvfb = args.xvfb
        self._timeout = args.timeout
        self._launch_timeout = args.launch_timeout
        self._extension = args.ext
        self._prefs = args.prefs
        self._profile = os.path.abspath(args.profile) if args.profile is not None else None
        self._memory = args.memory * 1024 * 1024 if args.memory else 0

    def verify_build(self, binary):
        """
        Verify that build doesn't crash on start
        :param binary: The path to the target binary 
        :return: Boolean
        """
        test_fp, test_path = tempfile.mkstemp(prefix='autobisect-dummy')
        try:
            with open(test_path, 'w') as f:
                f.write('<html><script>window.close()</script></html>')

            log.info('> Verifying build...')
            status = self.launch(binary, test_path)
        finally:
            os.remove(test_path
                      )

        if status != 0:
            log.error('>> Build crashed!')
            return False

        return True

    def evaluate_testcase(self, build_path):
        """
        Validate build and launch with supplied testcase
        :return: Result of evaluation
        """
        binary = os.path.join(build_path, 'dist', 'bin', 'firefox')
        if os.path.isfile(binary) and self.verify_build(binary):

            result = 0
            for _ in range(0, self.count):
                log.info('> Launching build with testcase...')
                result = self.launch(binary, self.testcase)
                if result != 0:
                    break

            # Return 'bad' if result is anything other than 0
            if result and result != 0:
                return 'bad'
            else:
                return 'good'

        return 'skip'

    def launch(self, binary, testcase=None):
        """
        Launch firefox using the supplied binary and testcase
        :param binary: The path to the firefox binary
        :param testcase: The path to the testcase
        :return: The return code or None 
        """
        ffp = FFPuppet(use_gdb=self._use_gdb, use_valgrind=self._use_valgrind, use_xvfb=self._use_xvfb)
        try:
            ffp.launch(
                str(binary),
                location=testcase,
                launch_timeout=self._launch_timeout,
                memory_limit=self._memory,
                prefs_js=self._prefs,
                extension=self._extension)
            return_code = ffp.wait(self._timeout) or 0
            log.debug('>> Browser execution status: %d' % return_code)
        except LaunchError:
            log.warn('> Failed to start browser')
            return_code = None
        finally:
            ffp.clean_up()

        return return_code


def main():
    parser = argparse.ArgumentParser()

    global_args = parser.add_argument_group('General Arguments')
    global_args.add_argument('build_dir', action='store', help='Path to store build')
    global_args.add_argument('testcase', action='store', help='Path to testcase')

    bisection_args = global_args.add_argument_group('bisection arguments')
    bisection_args.add_argument('--count', type=int, default=1, help='Number of times to evaluate testcase (per build)')

    ffp_args = global_args.add_argument_group('launcher arguments')
    ffp_args.add_argument('--timeout', type=int, default=60,
                          help='Maximum iteration time in seconds (default: %(default)s)')
    ffp_args.add_argument('--launch-timeout', type=int, default=300,
                          help='Maximum launch time in seconds (default: %(default)s)')
    ffp_args.add_argument('--ext', help='Path to fuzzPriv extension')
    ffp_args.add_argument('--prefs', help='Path to preference file')
    ffp_args.add_argument('--profile', help='Path to profile directory')
    ffp_args.add_argument('--memory', type=int, help='Process memory limit in MBs')
    ffp_args.add_argument('--gdb', action='store_true', help='Use GDB')
    ffp_args.add_argument('--valgrind', action='store_true', help='Use valgrind')
    ffp_args.add_argument('--xvfb', action='store_true', help='Use xvfb (Linux only)')

    args = parser.parse_args()
    bisector = BrowserBisector(args)
    bisector.evaluate_testcase(args.build_dir)


if __name__ == '__main__':
    log_level = logging.INFO
    log_fmt = "[%(asctime)s] %(message)s"
    if bool(os.getenv("DEBUG")):
        log_level = logging.DEBUG
        log_fmt = "%(levelname).1s %(name)s [%(asctime)s] %(message)s"
    logging.basicConfig(format=log_fmt, datefmt="%Y-%m-%d %H:%M:%S", level=log_level)

    main()
