# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import logging
import os

from lithium import interestingness

from ..bisect import Bisector

log = logging.getLogger('js-eval')


class LaunchError(Exception):
    """
    Raised when the browser process does not appear to be in a functional state during launch
    """
    pass


class JSEvaluator(object):
    """
    Testcase evaluator for SpiderMonkey shells
    """

    def __init__(self, args):
        self.testcase = os.path.abspath(args.testcase)
        self.repeat = args.repeat

        # JS Shell launch arguments
        self._detect = args.detect
        self._flags = args.flags
        self._timeout = args.timeout
        self._arg_1 = args.arg_1
        self._arg_2 = args.arg_2
        self._hang_time = args.hang_time
        self._match = args.match
        self._regex = args.regex

    def verify_build(self, binary):
        """
        Verify that build doesn't crash on start
        :param binary: The path to the target binary
        :return: Boolean
        """
        log.info('> Verifying build...')
        args = [binary, '-e', '"quit()"']
        run_data = interestingness.timed_run.timed_run(args, self._timeout, None)
        if run_data.sta is not interestingness.timed_run.NORMAL:
            log.error('>> Build crashed!')
            return False

        return True

    def evaluate_testcase(self, build_path):
        """
        Validate build and launch with supplied testcase
        :return: Result of evaluation
        """
        binary = os.path.join(build_path, 'js')
        common_args = ['-t', '%s' % self._timeout, binary]
        if self._flags is not None:
            common_args.extend(self._flags.split(' '))

        # These args are global to all detect types
        common_args.append(self.testcase)

        if self.verify_build(binary):
            for _ in range(self.repeat):
                log.info('> Launching build with testcase...')
                if self._detect == 'diff':
                    args = ['-a', self._arg_1, '-b', self._arg_2] + common_args
                    if interestingness.diff_test.interesting(args, None):
                        return Bisector.BUILD_CRASHED
                elif self._detect == 'output':
                    args = [self._match, self.testcase] + common_args
                    if interestingness.outputs.interesting(args, None):
                        return Bisector.BUILD_CRASHED
                elif self._detect == 'crash':
                    if interestingness.crashes.interesting(common_args, None):
                        return Bisector.BUILD_CRASHED
                elif self._detect == 'hang':
                    if interestingness.hangs.interesting(common_args, None):
                        return Bisector.BUILD_CRASHED

            return Bisector.BUILD_PASSED

        return Bisector.BUILD_FAILED
