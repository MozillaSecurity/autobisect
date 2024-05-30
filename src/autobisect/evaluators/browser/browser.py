# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import argparse
import logging
import os
from pathlib import Path
from platform import system
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Optional, NoReturn, Any, List, cast

from grizzly.common.storage import TestCase
from grizzly.common.utils import Exit
from grizzly.replay import ReplayArgs, ReplayManager

from autobisect.evaluators.base import Evaluator, EvaluatorResult

LOG = logging.getLogger(__name__)

# Disable sub loggers
logging.getLogger("grizzly.replay").setLevel(logging.WARNING)


class ArgParserNoExit(argparse.ArgumentParser):
    """Override default ArgParser SystemExit Behavior"""

    def exit(self, status: int = 0, message: Optional[str] = None) -> NoReturn:  # type: ignore
        pass

    def error(self, message: str) -> NoReturn:
        raise BrowserEvaluatorException(message)


class ReplayArgsNoExit(ReplayArgs):  # type: ignore
    """Set parser to ArgParserNoExit instance"""

    def __init__(self) -> None:
        self.parser = ArgParserNoExit()
        super().__init__()


class BrowserEvaluatorException(Exception):
    """Simple exception handler for BrowserEvaluator"""


class BrowserEvaluator(Evaluator):
    """Testcase evaluator for Firefox"""

    target = "firefox"

    def __init__(self, testcase: Path, **kwargs: Any) -> None:
        self.testcase = testcase

        # Grizzly arguments
        self.env_vars = kwargs.get("env", None)
        self.headless = kwargs.get("headless", None)
        self.ignore = kwargs.get("ignore", None)
        self.launch_timeout = kwargs.get("launch_timeout", None)
        self.logs = kwargs.get("logs", None)
        self.pernosco = kwargs.get("pernosco", False)
        self.prefs = kwargs.get("prefs", None)
        self.relaunch = kwargs.get("relaunch", None)
        self.repeat = kwargs.get("repeat", None)
        self.timeout = kwargs.get("timeout", None)
        self.time_limit = kwargs.get("time_limit", None)
        self.use_harness = kwargs.get("use_harness", None)
        self.valgrind = kwargs.get("valgrind", False)

        if logging.getLogger().level != logging.DEBUG:
            logging.getLogger("grizzly").setLevel(logging.WARNING)

    def parse_args(
        self,
        binary: Path,
        test_dir: Path,
        verify: Optional[bool] = False,
    ) -> argparse.Namespace:
        """Parse arguments destined for grizzly.
        :param binary: The path to the firefox binary
        :param test_dir: The path to the testcase
        :param verify: Indicates if we're running a testcase or verifying the browser stability
        :return: The return code or None
        """
        raw_args: List[Any] = [binary, test_dir]

        if self.ignore:
            raw_args.extend(["--ignore"] + self.ignore)
        if self.launch_timeout:
            raw_args.extend(["--launch-timeout", self.launch_timeout])
        if self.prefs:
            raw_args.extend(["--prefs", self.prefs])
        if self.relaunch:
            raw_args.extend(["--relaunch", self.relaunch])
        if self.timeout:
            raw_args.extend(["--timeout", self.timeout])
        if self.time_limit:
            raw_args.extend(["--time-limit", self.time_limit])
        if not self.use_harness:
            raw_args.append("--no-harness")
        if self.valgrind:
            raw_args.append("--valgrind")
        if self.headless:
            raw_args.extend(["--headless", self.headless])

        if not verify:
            if self.logs is not None:
                raw_args.extend(["--logs", self.logs])
            if self.pernosco:
                raw_args.extend(["--pernosco"])
            if self.repeat is not None:
                raw_args.extend(["--repeat", self.repeat])

        args = ReplayArgsNoExit().parse_args([str(arg) for arg in raw_args])
        return cast(argparse.Namespace, args)

    def verify_build(self, binary: Path) -> bool:
        """Verify that build doesn't crash on start
        :param binary: The path to the target binary
        :return: Boolean
        """
        with NamedTemporaryFile(suffix=".html", mode="w", delete=False) as temp:
            temp.write("<html><script>window.close()</script></html>")

        try:
            LOG.info("> Verifying build...")
            status = self.launch(binary, Path(temp.name), verify=True)

            if status != EvaluatorResult.BUILD_PASSED:
                LOG.error(">> Failed to validate build!")
                return False

            LOG.info(">> Build verified!")
            return True
        finally:
            os.unlink(temp.name)

    def evaluate_testcase(self, build_path: Path) -> EvaluatorResult:
        """Validate build and launch with supplied testcase
        :return: Result of evaluation
        """
        binary = "firefox.exe" if system() == "Windows" else "firefox"
        binary_path = build_path / binary
        result = EvaluatorResult.BUILD_FAILED
        if not binary_path.is_file():
            LOG.error("Cannot find build path!")
            return result

        if self.verify_build(binary_path):
            LOG.info("> Launching build with testcase...")
            result = self.launch(binary_path, self.testcase, scan_dir=True)

            if result == EvaluatorResult.BUILD_CRASHED:
                LOG.info(">> Build crashed!")
            else:
                LOG.info(">> Build did not crash!")

        return result

    def launch(
        self,
        binary: Path,
        test_path: Path,
        verify: Optional[bool] = False,
        scan_dir: Optional[bool] = False,
    ) -> EvaluatorResult:
        """Launch firefox using the supplied binary and testcase
        :param binary: The path to the firefox binary
        :param test_path: The path to the testcase
        :param verify: Indicates if we're running a testcase or verifying the browser stability
        :param scan_dir: Scan subdirectory for additional files to serve
        :return: The return code or None
        """
        if not binary.is_file():
            raise BrowserEvaluatorException(f"Binary path does not exist ({binary})!")

        # Create testcase
        testcase = TestCase.load_single(test_path, scan_dir)
        if self.env_vars:
            for key, value in self.env_vars.items():
                testcase.env_vars[key] = value

        with TemporaryDirectory() as test_dir:
            testcase.dump(test_dir, include_details=True)
            args = self.parse_args(binary, Path(test_dir), verify)
            success = ReplayManager.main(args)

            if success == Exit.SUCCESS:
                return EvaluatorResult.BUILD_CRASHED
            if success == Exit.FAILURE:
                return EvaluatorResult.BUILD_PASSED

            return EvaluatorResult.BUILD_FAILED
