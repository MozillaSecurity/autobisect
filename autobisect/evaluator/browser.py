# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import logging
import os
import tempfile
from contextlib import contextmanager

from grizzly.common import TestCase
from grizzly.replay import ReplayManager
from grizzly.target import TargetLaunchError, TargetLaunchTimeout, load as load_target
from prefpicker import PrefPicker
from sapphire import Sapphire

from ..bisect import Bisector

log = logging.getLogger("browser-eval")


class BrowserEvaluator(object):
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

    @contextmanager
    def prefs(self):
        """
        Use prefpicker to generate default prefs file
        :return: Path
        """
        if self._prefs is not None:
            yield self._prefs
        else:
            template_path = None
            for template in PrefPicker.templates():
                if template.endswith("browser-fuzzing.yml"):
                    template_path = template

            if template_path is not None:
                pick = PrefPicker.load_template(template_path)
                with tempfile.NamedTemporaryFile(suffix=".js") as temp:
                    pick.create_prefsjs(temp.name)
                    yield temp.name
            else:
                yield None

    def verify_build(self, binary, prefs=None):
        """
        Verify that build doesn't crash on start
        :param binary: The path to the target binary
        :param prefs: The path to the prefs file
        :return: Boolean
        """
        with tempfile.NamedTemporaryFile(suffix=".html", mode="w") as temp:
            temp.write("<html><script>window.close()</script></html>")
            temp.flush()
            log.info("> Verifying build...")
            status = self.launch(binary, temp.name, prefs)

        if status != Bisector.BUILD_PASSED:
            log.error(">> Build crashed!")
            return False

        log.error(">> Build verified!")
        return True

    def evaluate_testcase(self, build_path):
        """
        Validate build and launch with supplied testcase
        :return: Result of evaluation
        """
        binary = os.path.join(build_path, "firefox")
        result = Bisector.BUILD_FAILED
        with self.prefs() as prefs_file:
            if os.path.isfile(binary) and self.verify_build(binary, prefs=prefs_file):
                log.info("> Launching build with testcase...")
                result = self.launch(binary, self.testcase, prefs_file, scan_dir=True)

        return result

    def launch(self, binary, test_path, prefs, scan_dir=False):
        """
        Launch firefox using the supplied binary and testcase
        :param binary: The path to the firefox binary
        :param test_path: The path to the testcase
        :param prefs: The path to the prefs file
        :param scan_dir: Scan subdirectory for additional files to serve
        :return: The return code or None
        """
        replay = None
        target = None
        testcase = TestCase.load_path(test_path, scan_dir)
        if self._env_vars:
            for key, value in self._env_vars:
                testcase.add_environ_var(key, value)

        try:
            target = load_target("ffpuppet")(
                binary,
                extension=None,
                log_limit=None,
                memory_limit=None,
                relaunch=1,
                launch_timeout=self._launch_timeout,
                prefs=prefs,
                valgrind=self._use_valgrind,
                xvfb=self._use_xvfb,
            )

            with Sapphire(auto_close=1, timeout=self._timeout) as server:
                target.reverse(server.port, server.port)
                replay = ReplayManager(
                    self._ignore,
                    server,
                    target,
                    testcase,
                    any_crash=False,
                    signature=None,
                    use_harness=False,
                )
                success = replay.run(repeat=self._repeat)

            if success:
                return Bisector.BUILD_CRASHED

            return Bisector.BUILD_PASSED

        except (TargetLaunchError, TargetLaunchTimeout):
            return Bisector.BUILD_FAILED

        finally:
            if replay is not None:
                replay.cleanup()
            if target is not None:
                target.cleanup()
            if testcase is not None:
                testcase.cleanup()
