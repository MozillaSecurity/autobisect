# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import logging
import os
import re
from pathlib import Path
from string import Template
from typing import List, Any

import requests
from lithium import interestingness

from ..base import Evaluator, EvaluatorResult

LOG = logging.getLogger("js-eval")

HTTP_SESSION = requests.Session()

FLAGS_URL = Template(
    "https://hg.mozilla.org/mozilla-unified/raw-file/$rev/js/src/shell/js.cpp"
)


def _get_rev(binary: Path) -> str:
    """
    Return either the revision specified in the fuzzmanagerconf or tip
    :param binary: Path to build
    """
    rev = "tip"
    path = binary.with_suffix(".fuzzmanagerconf")
    if path.is_file():
        for line in path.read_text().splitlines():
            if line.startswith("product_version"):
                rev = line.split("-")[1].strip()

    return rev


class JSEvaluatorException(Exception):
    """
    Raised for any JSEvaluator exception
    """


class JSEvaluator(Evaluator):
    """
    Testcase evaluator for SpiderMonkey shells
    """

    target = "js"

    def __init__(self, testcase: Path, **kwargs: Any) -> None:
        self.testcase = testcase
        self.flags = kwargs.get("flags", [])
        self.repeat = kwargs.get("repeat", 1)

        # JS Shell launch arguments
        self.timeout = kwargs.get("timeout", 60)
        self.detect = kwargs.get("detect", "crash")

        if self.detect == "diff":
            if not kwargs.get("arg_1") or not kwargs.get("arg_2"):
                raise JSEvaluatorException("Diff mode requires 'arg_1' and 'arg_2'")
            self._arg_1 = kwargs.get("arg_1")
            self._arg_2 = kwargs.get("arg_2")
        elif self.detect == "match":
            if not kwargs.get("match"):
                raise JSEvaluatorException("Match mode requires a match string")
            self._match = kwargs.get("match")
            self._regex = kwargs.get("regex")

    @staticmethod
    def get_valid_flags(rev: str) -> List[str]:
        """
        Extract list of runtime flags available to the current build
        :param rev:
        """
        # Fuzzing safe is always included but not in the same format as the rest
        flags = []

        try:
            data = HTTP_SESSION.get(FLAGS_URL.substitute(rev=rev), stream=True)
            data.raise_for_status()
            matches = re.findall(r"(?:get\w+Option)\(\"(.[^\"]*)", data.text)
            flags.extend(list(set(matches)))
        except requests.exceptions.RequestException as e:
            LOG.warning("Failed to retrieve build flags %s", e)

        return flags

    def verify_build(self, binary: Path, flags: List[str]) -> bool:
        """
        Verify that build doesn't crash on start
        :param binary: The path to the target binary
        :param flags: Runtime flags
        :return: Boolean
        """
        LOG.info("> Verifying build...")
        args = [binary, *flags, "-e", '"quit()"']
        run_data = interestingness.timed_run.timed_run(args, self.timeout)
        if run_data.sta is not interestingness.timed_run.NORMAL:
            LOG.error(">> Build crashed!")
            return False

        return True

    def evaluate_testcase(self, build_path: Path) -> EvaluatorResult:
        """
        Validate build and launch with supplied testcase
        :return: Result of evaluation
        """
        binary = build_path / "dist" / "bin" / "js"
        if not binary.is_file():
            return EvaluatorResult.BUILD_FAILED
        rev = _get_rev(binary)
        all_flags = self.get_valid_flags(rev)
        flags = []
        for flag in self.flags:
            if flag.lstrip("--").split("=")[0] in all_flags:
                flags.append(flag)

        if self.verify_build(binary, flags):
            common_args = [
                "-t",
                f"{self.timeout}",
                str(binary),
                *flags,
                str(self.testcase),
            ]

            try:
                # Some testcases require setting the cwd to the parent dir
                previous_path = os.getcwd()
                os.chdir(os.path.dirname(os.path.abspath(self.testcase)))

                for _ in range(self.repeat):
                    LOG.info("> Launching build with testcase...")
                    if self.detect == "diff":
                        args = ["-a", self._arg_1, "-b", self._arg_2] + common_args
                        if interestingness.diff_test.interesting(args, None):
                            return EvaluatorResult.BUILD_CRASHED
                    elif self.detect == "output":
                        args = [self._match] + common_args
                        if interestingness.outputs.interesting(args, None):
                            return EvaluatorResult.BUILD_CRASHED
                    elif self.detect == "crash":
                        if interestingness.crashes.interesting(common_args, None):
                            return EvaluatorResult.BUILD_CRASHED
                    elif self.detect == "hang":
                        if interestingness.hangs.interesting(common_args, None):
                            return EvaluatorResult.BUILD_CRASHED
            finally:
                # Reset cwd
                os.chdir(previous_path)

            return EvaluatorResult.BUILD_PASSED

        return EvaluatorResult.BUILD_FAILED
