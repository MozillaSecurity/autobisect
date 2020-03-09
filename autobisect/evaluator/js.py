# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import logging
import os

from lithium import interestingness

from ..bisect import Bisector

log = logging.getLogger("js-eval")


class JSEvaluatorException(Exception):
    """
    Raised for any JSEvaluator exception
    """

    pass


class JSEvaluator(object):
    """
    Testcase evaluator for SpiderMonkey shells
    """

    def __init__(self, testcase, **kwargs):
        self.testcase = testcase
        self.flags = kwargs.get("flags", None)
        self.repeat = kwargs.get("repeat", 1)

        # JS Shell launch arguments
        self.timeout = kwargs.get("timeout", 60)
        self.detect = kwargs.get("detect", "crash")

        if self.detect == "diff":
            if not kwargs.get("arg_1") or not kwargs.get("arg_2"):
                raise JSEvaluatorException(
                    "Detect mode is set to diff but not enough args supplied"
                )
            self._arg_1 = kwargs.get("arg_1")
            self._arg_2 = kwargs.get("arg_2")
        elif self.detect == "match":
            if not kwargs.get("match"):
                raise JSEvaluatorException(
                    "Detect mode is set to match but a match string wasn't supplied"
                )
            self._match = kwargs.get("match")
            self._regex = kwargs.get("regex")

    def verify_build(self, binary):
        """
        Verify that build doesn't crash on start
        :param binary: The path to the target binary
        :return: Boolean
        """
        log.info("> Verifying build...")
        args = [binary, "-e", '"quit()"']
        if self.flags is not None:
            args.extend(self.flags)
        run_data = interestingness.timed_run.timed_run(args, self.timeout, None)
        if run_data.sta is not interestingness.timed_run.NORMAL:
            log.error(">> Build crashed!")
            return False

        return True

    def evaluate_testcase(self, build_path):
        """
        Validate build and launch with supplied testcase
        :return: Result of evaluation
        """
        binary = os.path.join(build_path, "dist", "bin", "js")
        common_args = ["-t", "%s" % self.timeout, binary]
        if self.flags is not None:
            common_args.extend(self.flags)

        # These args are global to all detect types
        common_args.append(self.testcase)

        if self.verify_build(binary):
            for _ in range(self.repeat):
                log.info("> Launching build with testcase...")
                if self.detect == "diff":
                    args = ["-a", self._arg_1, "-b", self._arg_2] + common_args
                    if interestingness.diff_test.interesting(args, None):
                        return Bisector.BUILD_CRASHED
                elif self.detect == "output":
                    args = [self._match, self.testcase] + common_args
                    if interestingness.outputs.interesting(args, None):
                        return Bisector.BUILD_CRASHED
                elif self.detect == "crash":
                    if interestingness.crashes.interesting(common_args, None):
                        return Bisector.BUILD_CRASHED
                elif self.detect == "hang":
                    if interestingness.hangs.interesting(common_args, None):
                        return Bisector.BUILD_CRASHED

            return Bisector.BUILD_PASSED

        return Bisector.BUILD_FAILED
