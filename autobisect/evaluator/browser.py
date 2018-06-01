# coding=utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import os
import tempfile

from ffpuppet import FFPuppet, LaunchError

log = logging.getLogger('browser-bisect')

BUILD_CRASHED = 0
BUILD_PASSED = 1
BUILD_FAILED = 2


class BrowserBisector(object):
    """
    Testcase evaluator for Firefox
    """
    def __init__(self, args):
        self.testcase = os.path.abspath(args.testcase)
        self.count = args.count

        # FFPuppet arguments
        self._use_gdb = args.gdb
        self._use_valgrind = args.valgrind
        self._use_xvfb = args.xvfb
        self._timeout = args.timeout
        self._launch_timeout = args.launch_timeout
        self._abort_token = args.abort_token
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
        _, test_path = tempfile.mkstemp(prefix='autobisect-dummy')
        try:
            with open(test_path, 'w') as f:
                f.write('<html><script>window.close()</script></html>')

            log.info('> Verifying build...')
            status = self.launch(binary, test_path)
        finally:
            os.remove(test_path)

        if status != BUILD_PASSED:
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
            for _ in range(self.count):
                log.info('> Launching build with testcase...')
                result = self.launch(binary, self.testcase)
                if result == BUILD_CRASHED:
                    break

            return result

        return BUILD_FAILED

    def launch(self, binary, testcase=None):
        """
        Launch firefox using the supplied binary and testcase
        :param binary: The path to the firefox binary
        :param testcase: The path to the testcase
        :return: The return code or None
        """
        ffp = FFPuppet(use_gdb=self._use_gdb, use_valgrind=self._use_valgrind, use_xvfb=self._use_xvfb)
        for a_token in self._abort_token:
            ffp.add_abort_token(a_token)

        result = BUILD_PASSED

        try:
            ffp.launch(
                str(binary),
                location=testcase,
                launch_timeout=self._launch_timeout,
                memory_limit=self._memory,
                prefs_js=self._prefs,
                extension=self._extension)
            ffp.wait(self._timeout)

            if not ffp.is_running():
                ffp.close()
                if ffp.reason == FFPuppet.RC_EXITED:
                    log.info(">> Browser closed itself")
                elif ffp.reason == FFPuppet.RC_ALERT:
                    log.info(">> Browser crashed!")
                    result = BUILD_CRASHED
                else:
                    log.info(">> Browser was closed")

            elif not ffp.is_healthy():
                log.info("Browser is alive but has crash reports. Terminating...")
                result = BUILD_CRASHED
                ffp.close()
        except LaunchError:
            log.warn('> Failed to start browser')
            result = BUILD_FAILED
        finally:
            ffp.clean_up()

        return result
