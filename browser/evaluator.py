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

from ffpuppet import FFPuppet, LaunchError
from core.bisect import Bisector

if bool(os.getenv("DEBUG")):
    OUTPUT = None
else:
    OUTPUT = open(os.devnull, 'wb')

log = logging.getLogger('browser-bisect')


class BrowserBisector(Bisector):
    def __init__(self, args):
        self.repo_dir = args.repo_dir
        self.build_dir = args.build_dir
        self.testcase = args.testcase

        # ToDo: Automatically select platform
        self._autobisect_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._mozconfig_base = os.path.join(self._autobisect_base, 'config', 'mozconfigs')
        if args.asan and args.debug:
            self.moz_config = os.path.join(self._mozconfig_base, 'mozconfig.mi-asan-debug')
        elif args.asan:
            self.moz_config = os.path.join(self._mozconfig_base, 'mozconfig.mi-asan-release')
        # elif args.debug:
        #     self.moz_config = os.path.join(self._mozconfig_base, 'mozconfig.mi-asan-debug')
        # else:
        #     self.moz_config = os.path.join(self._mozconfig_base, 'mozconfig.mi-asan-debug')

        # FFPuppet arguments
        self.binary = os.path.join(self.build_dir, 'dist', 'bin', 'firefox')
        self.extension = args.extension
        self.timeout = args.timeout
        self.launch_timeout = args.launch_timeout
        self.prefs = args.prefs
        self.memory = args.memory
        self.gdb = args.gdb
        self.valgrind = args.valgrind
        self.windbg = args.windbg
        self.xvfb = args.xvfb

    def test_compilation(self):
        """
        Compile from source and evaluate testcase
        """
        # Ensure that the build_dir is empty
        assert os.listdir(self.build_dir) == []

        env = os.environ.copy()
        env['AB_ROOT'] = self._autobisect_base
        env['MOZCONFIG'] = self.moz_config
        env['MOZ_OBJDIR'] = self.build_dir
        env['ASAN_OPTIONS'] = 'detect_leaks=0'

        mach = os.path.join(self.repo_dir, 'mach')

        try:
            log.info('Attempting to compile from source: {0}'.format(self.repo_dir))
            subprocess.check_call(
                [mach, 'build'],
                cwd=self.repo_dir,
                env=env,
                stdout=OUTPUT,
                stderr=OUTPUT,
            )
        except subprocess.CalledProcessError:
            log.error('Compilation failed!')
            return 'skip'

        if not os.path.exists(self.build_dir):
            log.error('Compilation failed!')
            return 'skip'

        if not self.verify_build():
            return 'skip'

        return self.evaluate_testcase()

    def test_build(self):
        """
        Verify downloaded build and evaluate testcase
        """
        if not self.verify_build():
            return 'skip'

        return self.evaluate_testcase()

    def verify_build(self):
        """
        Verify that build doesn't crash
        """
        log.info('Verifying build')
        if self.launch() == 0:
            log.debug('Build verified successfully!')
            return True
        else:
            log.error('Build crashed!')

    def evaluate_testcase(self):
        log.info('Attempting to launch with testcase: {0}'.format(self.testcase))
        result = self.launch(os.path.abspath(self.testcase))

        # Return 'bad' if result is anything other than 0
        if result and result != 0:
            return 'bad'
        else:
            return 'good'

    def launch(self, testcase=None):
        ffp = FFPuppet(
            use_gdb=self.gdb,
            use_valgrind=self.valgrind,
            use_xvfb=self.xvfb)

        try:
            ffp.launch(
                self.binary,
                location=testcase,
                launch_timeout=self.launch_timeout,
                memory_limit=self.memory,
                prefs_js=self.prefs,
                extension=self.extension)

            return_code = ffp.wait(self.timeout) or 0
            log.debug('Browser execution status: {0}'.format(return_code))
        except LaunchError:
            log.warn('Failed to start browser')
            return_code = None
        finally:
            ffp.close()
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
    ffp_args.add_argument('--extension',
                          help='Install the fuzzPriv extension (specify path to funfuzz/dom/extension)')
    ffp_args.add_argument('--timeout', type=int, default=60,
                          help='Iteration timeout in seconds (default: %(default)s)')
    ffp_args.add_argument('--launch-timeout', type=int, default=300,
                          help='Number of seconds to wait for firefox to become responsive after launching.'
                          '(default: %(default)s)')
    ffp_args.add_argument('--prefs', help='prefs.js file to use')
    ffp_args.add_argument('--profile', help='Profile to use. (default: a temporary profile is created)')
    ffp_args.add_argument('--memory', type=int, help='Process memory limit in MBs (Requires psutil)')
    ffp_args.add_argument('--gdb', action='store_true', help='Use GDB')
    ffp_args.add_argument('--valgrind', action='store_true', help='Use valgrind')
    ffp_args.add_argument('--windbg', action='store_true', help='Use WinDBG (Windows only)')
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
