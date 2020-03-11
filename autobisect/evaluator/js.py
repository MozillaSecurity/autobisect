# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import logging
import os
from string import Template

import requests
from lithium import interestingness

from ..bisect import Bisector

log = logging.getLogger("js-eval")

HTTP_SESSION = requests.Session()

FLAGS_URL = Template(
    "https://hg.mozilla.org/mozilla-unified/raw-file/$rev/js/src/shell/fuzz-flags.txt"
)


def _get_rev(binary):
    """
    Return either the revision specified in the fuzzmanagerconf
    :param binary: Path to build
    """
    path = f"{os.path.splitext(binary)[0]}.fuzzmanagerconf"
    if os.path.isfile(path):
        with open(path) as file:
            for line in file.readlines():
                if line.startswith("product_version"):
                    return line.split("-")[1].strip()


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

    @staticmethod
    def get_valid_flags(rev):
        """
        Extract list of runtime flags available to the current build
        :param rev:
        """
        flags = []

        try:
            data = HTTP_SESSION.get(FLAGS_URL.substitute(rev=rev), stream=True)
            data.raise_for_status()
            for line in data.text.split("\n"):
                flag = line.strip()
                if flag and not flag.startswith("#"):
                    flags.append(flag)
        except requests.exceptions.RequestException as e:
            log.warn("Failed to retrieve build flags", e)

        return flags

    def verify_build(self, binary, flags=None):
        """
        Verify that build doesn't crash on start
        :param binary: The path to the target binary
        :param flags: Runtime flags
        :return: Boolean
        """
        log.info("> Verifying build...")
        args = [binary, "-e", '"quit()"']
        if flags is not None:
            args.extend(flags)
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

        flags = self.flags
        if self.flags is not None:
            rev = _get_rev(binary)
            all_flags = JSEvaluator.get_valid_flags(rev)
            if all_flags:
                flags = [flag for flag in self.flags if flag in all_flags]

        if flags is not None:
            common_args.extend(flags)

        # These args are global to all detect types
        common_args.append(self.testcase)

        if self.verify_build(binary, flags):
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
