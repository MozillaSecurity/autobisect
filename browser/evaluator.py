#!/usr/bin/env python
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import, division, print_function

import argparse
import logging
import os
import subprocess
import platform

from ffpuppet import FFPuppet, LaunchError

DEBUG = bool(os.getenv('DEBUG'))

log = logging.getLogger('browser-bisect')


class BrowserBisector(object):
    def __init__(self, args):
        self.repo_dir = os.path.abspath(args.repo_dir)
        self.testcase = os.path.abspath(args.testcase)

        self._asan = args.asan
        self._debug = args.debug

        # Mach arguments
        self._moz_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mozconfigs')
        self._moz_config = os.path.join(self._moz_root, self._build_string)

        # FFPuppet arguments
        self._use_gdb = args.gdb
        self._use_valgrind = args.valgrind
        self._use_xvfb = args.xvfb
        self._timeout = args.timeout
        self._launch_timeout = args.launch_timeout
        self._extension = args.ext
        self._prefs = args.prefs
        self._profile = os.path.abspath(args.profile) if args.profile is not None else None
        self._memory = args.memory

    @property
    def _build_string(self):
        return (
            (platform.system().lower()) +
            ('.asan' if self._asan else '') +
            ('.debug' if self._debug else '')
        )

    def verify_build(self, build):
        """
        Verify that build doesn't crash on start
        :return: Boolean
        """
        log.info('Verifying build...')
        if self.launch(build) != 0:
            log.error('Build crashed!')
            return False

        return True

    def compile_build(self, build_path):
        """
        Compile build using mach
        :param build_path: Path to store the build
        """
        env = os.environ.copy()
        env['MOZROOT'] = self._moz_root
        env['MOZCONFIG'] = self._moz_config
        env['MOZ_OBJDIR'] = build_path
        env['ASAN_OPTIONS'] = 'detect_leaks=0'

        mach = os.path.join(self.repo_dir, 'mach')
        stdout = None if DEBUG else open(os.devnull, 'wb')
        stderr = subprocess.STDOUT if DEBUG else open(os.devnull, 'wb')

        try:
            log.info('Running bootstrap process')
            subprocess.check_call(
                [mach, 'bootstrap', '--no-interactive', '--application-choice=browser'],
                cwd=self.repo_dir,
                env=env,
                stdout=stdout,
                stderr=stderr
            )
        except subprocess.CalledProcessError:
            pass

        try:
            log.info('Attempting to compile from source: %s' % self.repo_dir)
            subprocess.check_call(
                [mach, 'build'],
                cwd=self.repo_dir,
                env=env,
                stdout=stdout,
                stderr=stderr
            )
        except subprocess.CalledProcessError:
            pass

    def evaluate_testcase(self, build_path):
        """
        Validate build and launch with supplied testcase
        :return: Result of evaluation
        """
        binary = os.path.join(build_path, 'dist', 'bin', 'firefox')
        if os.path.isfile(binary) and self.verify_build(binary):
            log.info('Launching build with testcase...')
            result = self.launch(binary, os.path.abspath(self.testcase))

            # Return 'bad' if result is anything other than 0
            if result and result != 0:
                return 'bad'
            else:
                return 'good'

        return 'skip'

    def launch(self, binary, testcase=None):
        ffp = FFPuppet(use_gdb=self._use_gdb, use_valgrind=self._use_valgrind, use_xvfb=self._use_xvfb)

        try:
            ffp.launch(
                binary,
                location=testcase,
                launch_timeout=self.launch_timeout,
                memory_limit=self.memory * 1024 * 1024 if self.memory else 0,
                prefs_js=self.prefs,
                extension=self.extension)
            return_code = self.ffp.wait(self.timeout) or 0
            log.debug('Browser execution status: %d' % return_code)
        except LaunchError:
            log.warn('Failed to start browser')
            return_code = None
        finally:
            ffp.clean_up()

        return return_code


def main():
    parser = argparse.ArgumentParser()

    general_args = parser.add_argument_group('General Arguments')
    general_args.add_argument('repo_dir', action='store', help='Path of repository')
    general_args.add_argument('build_dir', action='store', help='Path to store build')
    general_args.add_argument('testcase', action='store', help='Path to testcase')

    build_args = parser.add_argument_group('Build Arguments')
    build_args.add_argument('--config', required=True, action='store', help='Path to .mozconfig file')

    ffp_args = parser.add_argument_group('Launcher Arguments')
    ffp_args.add_argument('--timeout', type=int, default=60,
                          help='Maximum iteration time in seconds (default: %(default)s)')
    ffp_args.add_argument('--launch-timeout', type=int, default=300,
                          help='Maximum launch time in seconds (default: %(default)s)')
    ffp_args.add_argument('--ext', help='Install the fuzzPriv extension (specify path to funfuzz/dom/extension)')
    ffp_args.add_argument('--prefs', help='prefs.js file to use')
    ffp_args.add_argument('--profile', help='Profile to use. (default: a temporary profile is created)')
    ffp_args.add_argument('--memory', type=int, help='Process memory limit in MBs (Requires psutil)')
    ffp_args.add_argument('--gdb', action='store_true', help='Use GDB')
    ffp_args.add_argument('--valgrind', action='store_true', help='Use valgrind')
    ffp_args.add_argument('--xvfb', action='store_true', help='Use xvfb (Linux only)')

    args = parser.parse_args()
    bisector = BrowserBisector(args)
    bisector.evaluate_testcase()


if __name__ == '__main__':
    log_level = logging.INFO
    log_fmt = "[%(asctime)s] %(message)s"
    if bool(os.getenv("DEBUG")):
        log_level = logging.DEBUG
        log_fmt = "%(levelname).1s %(name)s [%(asctime)s] %(message)s"
    logging.basicConfig(format=log_fmt, datefmt="%Y-%m-%d %H:%M:%S", level=log_level)

    main()
