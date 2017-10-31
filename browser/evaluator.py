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

if bool(os.getenv("DEBUG")):
    OUTPUT = None
else:
    OUTPUT = open(os.devnull, 'wb')

log = logging.getLogger('browser-bisect')


class BrowserBisector(object):
    def __init__(self, args):
        self.repo_dir = os.path.abspath(args.repo_dir)
        self.testcase = os.path.abspath(args.testcase)

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
        self.ffp = FFPuppet(use_gdb=args.gdb, use_valgrind=args.valgrind, use_xvfb=args.xvfb)
        self.timeout = args.timeout
        self.launch_timeout = args.launch_timeout
        self.extension = args.ext
        self.prefs = args.prefs
        self.profile = os.path.abspath(args.profile) if args.profile is not None else None
        self.memory = args.memory

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
        env['AB_ROOT'] = self._autobisect_base
        env['MOZCONFIG'] = self.moz_config
        env['MOZ_OBJDIR'] = build_path
        env['ASAN_OPTIONS'] = 'detect_leaks=0'

        mach = os.path.join(self.repo_dir, 'mach')

        try:
            log.info('Attempting to compile from source: %s' % self.repo_dir)
            subprocess.check_call(
                [mach, 'build'],
                cwd=self.repo_dir,
                env=env,
                stdout=OUTPUT,
                stderr=OUTPUT,
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
        try:
            self.ffp.launch(
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
            self.ffp.close()
            self.ffp.clean_up()

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
