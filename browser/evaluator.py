#!/usr/bin/env python
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import, division, print_function

import argparse
import logging
import os
import shutil
import subprocess

try:
    # subprocess v3.5
    from subprocess import DEVNULL
except ImportError:
    import os
    DEVNULL = open(os.devnull, 'wb')

from ffpuppet import FFPuppet

log = logging.getLogger('browser-bisect')


class BrowserEvaluator:
    def __init__(self, args):
        self.repo_dir = args.repo_dir
        self.build_dir = args.build_dir
        self.testcase = args.testcase

        self.moz_config = args.config

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

    def try_compile(self):
        assert os.path.isdir(self.repo_dir)
        assert os.path.isfile(self.moz_config)

        env = os.environ.copy()
        env['MOZCONFIG'] = self.moz_config
        env['MOZ_OBJDIR'] = self.build_dir
        env['ASAN_OPTIONS'] = "detect_leaks=0"

        mach = os.path.join(self.repo_dir, 'mach')

        try:
            subprocess.check_call(
                [mach, 'build'],
                cwd=self.repo_dir,
                env=env,
                # stdout=DEVNULL,
                # stderr=subprocess.STDOUT,
            )
        except subprocess.CalledProcessError as e:
            log.error(e.output)
            return False

        if not os.path.exists(self.build_dir):
            return False

        return True

    def test_rev(self):
        if os.path.exists(self.build_dir):
            log.info('Clobbering build dir: {0}'.format(self.build_dir))
            shutil.rmtree(self.build_dir)
            os.makedirs(self.build_dir)

        # If compilation fails, skip it during bisection
        log.info('Attempting to compile {0}'.format(self.repo_dir))
        if not self.try_compile():
            log.error('Compilation failed!')
            return 'skip'
        else:
            log.info('Compilation succeeded!')

        result = self.launch()

        # Return 'bad' if result is anything other than 0
        if result != 0 or "Timeout":
                return 'bad'
        else:
            return 'good'

    def launch(self):
        ffp = FFPuppet(
            use_gdb=self.gdb,
            use_valgrind=self.valgrind,
            use_windbg=self.windbg,
            use_xvfb=self.xvfb)

        try:
            log.info('Attempting to launch browser with testcase: {0}'.format(self.testcase))
            ffp.launch(
                self.binary,
                location=os.path.abspath(self.testcase),
                launch_timeout=self.launch_timeout,
                memory_limit=self.memory,
                prefs_js=self.prefs,
                extension=self.extension)

            return_code = ffp.wait(self.timeout)

            status = return_code or '0'
            log.info('Browser execution status: {0}'.format(status))
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
                          help='Number of seconds to wait for the browser to become responsive after launching.'
                          '(default: %(default)s)')
    ffp_args.add_argument('--prefs', help='prefs.js file to use')
    ffp_args.add_argument('--profile', help='Profile to use. (default: a temporary profile is created)')
    ffp_args.add_argument('--memory', type=int, help='Process memory limit in MBs (Requires psutil)')
    ffp_args.add_argument('--gdb', action='store_true', help='Use GDB')
    ffp_args.add_argument('--valgrind', action='store_true', help='Use valgrind')
    ffp_args.add_argument('--windbg', action='store_true', help='Use WinDBG (Windows only)')
    ffp_args.add_argument('--xvfb', action='store_true', help='Use xvfb (Linux only)')

    args = parser.parse_args()
    bisector = BrowserEvaluator(args)
    bisector.test_rev()


if __name__ == '__main__':
    log_level = logging.INFO
    log_fmt = "[%(asctime)s] %(message)s"
    if bool(os.getenv("DEBUG")):
        log_level = logging.DEBUG
        log_fmt = "%(levelname).1s %(name)s [%(asctime)s] %(message)s"
    logging.basicConfig(format=log_fmt, datefmt="%Y-%m-%d %H:%M:%S", level=log_level)

    main()
