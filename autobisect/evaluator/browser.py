# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import logging
import os
import tempfile

from ffpuppet import FFPuppet, LaunchError

from ..bisect import Bisector

log = logging.getLogger('browser-eval')


class BrowserEvaluator(object):
    """
    Testcase evaluator for Firefox
    """

    def __init__(self, args):
        self.testcase = args.testcase
        self.repeat = args.repeat

        # FFPuppet arguments
        self._asserts = args.asserts
        self._detect = args.detect
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
        _, test_path = tempfile.mkstemp(prefix='autobisect-dummy')
        try:
            with open(test_path, 'w') as f:
                f.write('<html><script>window.close()</script></html>')

            log.info('> Verifying build...')
            status = self.launch(binary, test_path)
        finally:
            os.remove(test_path)

        if status != Bisector.BUILD_PASSED:
            log.error('>> Build crashed!')
            return False

        return True

    def evaluate_testcase(self, build_path):
        """
        Validate build and launch with supplied testcase
        :return: Result of evaluation
        """
        binary = os.path.join(build_path, 'firefox')
        if os.path.isfile(binary) and self.verify_build(binary):
            for _ in range(self.repeat):
                log.info('> Launching build with testcase...')
                result = self.launch(binary, self.testcase)
                if result == Bisector.BUILD_CRASHED:
                    break

            return result

        return Bisector.BUILD_FAILED

    def launch(self, binary, testcase=None):
        """
        Launch firefox using the supplied binary and testcase
        :param binary: The path to the firefox binary
        :param testcase: The path to the testcase
        :return: The return code or None
        """
        ffp = FFPuppet(use_gdb=self._use_gdb, use_valgrind=self._use_valgrind, use_xvfb=self._use_xvfb)
        if self._asserts:
            ffp.add_abort_token('###!!! ASSERTION:')

        result = Bisector.BUILD_PASSED

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
                    log.info('>> Target closed itself')
                elif (ffp.reason == FFPuppet.RC_WORKER
                      and self._detect == 'memory'
                      and 'ffp_worker_memory_limiter' in ffp.available_logs()):
                    log.info('>> Memory limit exceeded')
                    result = Bisector.BUILD_CRASHED
                elif (ffp.reason == FFPuppet.RC_WORKER
                      and self._detect == 'log'
                      and 'ffp_worker_log_size_limiter' in ffp.available_logs()):
                    log.info('>> Log size limit exceeded')
                    result = Bisector.BUILD_CRASHED
                else:
                    log.info('>> Failure detected')
                    result = Bisector.BUILD_CRASHED
            elif not ffp.is_healthy():
                # this should be e10s only
                result = Bisector.BUILD_CRASHED
                log.info('>> Browser is alive but has crash reports. Terminating...')
                ffp.close()
            elif self._detect == 'timeout':
                result = Bisector.BUILD_CRASHED
                log.info('>> Timeout detected')
                ffp.close()
            else:
                log.info('>> Time limit exceeded')
        except LaunchError:
            log.warn('>> Failed to start browser')
            result = Bisector.BUILD_FAILED
        finally:
            ffp.clean_up()

        return result
