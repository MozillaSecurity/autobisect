# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import argparse
import logging
import os
import tempfile

from grizzly.common import TestCase
from grizzly.replay import ReplayArgs, ReplayManager

from ..base import Evaluator, EvaluatorResult

LOG = logging.getLogger("browser-eval")

# Disable sub loggers
logging.getLogger("grizzly.replay").setLevel(logging.WARNING)


class ArgParserNoExit(argparse.ArgumentParser):
    """ Override default ArgParser SystemExit Behavior """

    def exit(self, status=0, message=None):
        pass

    def error(self, message):
        raise BrowserEvaluatorException(message)


class ReplayArgsNoExit(ReplayArgs):
    """ Set parser to ArgParserNoExit instance """

    def __init__(self, *args, **kwds):
        self.parser = ArgParserNoExit()
        super().__init__(*args, **kwds)


class BrowserEvaluatorException(Exception):
    """ Simple exception handler for BrowserEvaluator """


class BrowserEvaluator(Evaluator):
    """
    Testcase evaluator for Firefox
    """

    def __init__(self, testcase, **kwargs):
        self.testcase = testcase

        # FFPuppet arguments
        self._repeat = kwargs.get("repeat", 1)
        self._ignore = kwargs.get("ignore", ["log-limit", "memory", "timeout"])
        self._use_valgrind = kwargs.get("valgrind", False)
        self._use_xvfb = kwargs.get("xvfb", True)
        self._timeout = kwargs.get("timeout", 60)
        self._launch_timeout = kwargs.get("launch_timeout", 300)
        self._prefs = kwargs.get("prefs", None)
        self._env_vars = kwargs.get("env", None)

        if logging.getLogger().level != logging.DEBUG:
            logging.getLogger("grizzly").setLevel(logging.WARNING)

    def verify_build(self, binary):
        """
        Verify that build doesn't crash on start
        :param binary: The path to the target binary
        :return: Boolean
        """
        with tempfile.NamedTemporaryFile(suffix=".html", mode="w") as temp:
            temp.write("<html><script>window.close()</script></html>")
            temp.flush()
            LOG.info("> Verifying build...")

            status = self.launch(binary, temp.name, 1)

        if status != EvaluatorResult.BUILD_PASSED:
            LOG.error(">> Build crashed!")
            return False

        LOG.info(">> Build verified!")
        return True

    def evaluate_testcase(self, build_path):
        """
        Validate build and launch with supplied testcase
        :return: Result of evaluation
        """
        binary = os.path.join(build_path, "firefox")
        result = EvaluatorResult.BUILD_FAILED
        if os.path.isfile(binary) and self.verify_build(binary):
            LOG.info("> Launching build with testcase...")
            result = self.launch(binary, self.testcase, self._repeat, scan_dir=True)

        if result == EvaluatorResult.BUILD_CRASHED:
            LOG.info(">> Build crashed!")
        else:
            LOG.info(">> Build did not crash!")

        return result

    def launch(self, binary, test_path, repeat, scan_dir=False):
        """
        Launch firefox using the supplied binary and testcase
        :param binary: The path to the firefox binary
        :param test_path: The path to the testcase
        :param repeat: The number of times to launch the browser
        :param scan_dir: Scan subdirectory for additional files to serve
        :return: The return code or None
        """
        # Create testcase
        testcase = TestCase.load_single(test_path, load_prefs=True, adjacent=scan_dir)
        if self._env_vars:
            for key, value in self._env_vars.items():
                testcase.add_environ_var(key, value)

        with tempfile.TemporaryDirectory() as test_dir:
            testcase.dump(test_dir, include_details=True)

            raw_args = [
                binary,
                test_dir,
                "--timeout",
                self._timeout,
                "--launch-timeout",
                self._launch_timeout,
                "--repeat",
                repeat,
                "--relaunch",
                1,
                "--no-harness",
                "--ignore",
                *self._ignore,
            ]

            if self._prefs:
                raw_args.extend(["--prefs", self._prefs])
            if self._use_valgrind:
                raw_args.append("--valgrind")
            if self._use_xvfb:
                raw_args.append("--xvfb")

            args = ReplayArgsNoExit().parse_args([str(arg) for arg in raw_args])
            success = ReplayManager.main(args)

            if not success:
                return EvaluatorResult.BUILD_CRASHED

            return EvaluatorResult.BUILD_PASSED
