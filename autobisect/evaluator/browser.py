# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import logging
import os
import tempfile
from contextlib import contextmanager

from ffpuppet import FFPuppet, LaunchError
from prefpicker import PrefPicker

from ..bisect import Bisector

log = logging.getLogger("browser-eval")


class BrowserEvaluator(object):
    """
    Testcase evaluator for Firefox
    """

    # asserts=False, detect=None, gdb=False, valgrind=False, xvfb=True, timeout=60,
    #                  launch_timeout=300, ext=None, prefs=None, memory=None

    def __init__(self, testcase, **kwargs):
        self.testcase = testcase
        self.repeat = kwargs.get("repeat", 1)

        # FFPuppet arguments
        self._asserts = kwargs.get("asserts", False)
        self._detect = kwargs.get("detect", "crash")
        self._use_gdb = kwargs.get("gdb", False)
        self._use_valgrind = kwargs.get("valgrind", False)
        self._use_xvfb = kwargs.get("xvfb", True)
        self._timeout = kwargs.get("timeout", 60)
        self._launch_timeout = kwargs.get("launch_timeout", 300)
        self._extension = kwargs.get("ext", None)
        self._prefs = kwargs.get("prefs", None)
        self._memory = kwargs.get("memory", 0) * 1024 * 1024
        self._env_vars = kwargs.get("env", None)

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
                pick = PrefPicker.load_template(template)
                with tempfile.NamedTemporaryFile(suffix=".js") as temp:
                    pick.create_prefsjs(temp.name)
                    yield temp.name
            else:
                yield None

    def verify_build(self, binary, prefs=None):
        """
        Verify that build doesn't crash on start
        :param binary: The path to the target binary
        :return: Boolean
        """
        with tempfile.NamedTemporaryFile() as temp:
            with open(temp.name, "w") as f:
                f.write("<html><script>window.close()</script></html>")

            log.info("> Verifying build...")
            status = self.launch(binary, temp.name, prefs)

        if status != Bisector.BUILD_PASSED:
            log.error(">> Build crashed!")
            return False

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
                for _ in range(self.repeat):
                    log.info("> Launching build with testcase...")
                    result = self.launch(binary, self.testcase, prefs_file)
                    if result == Bisector.BUILD_CRASHED:
                        break

        return result

    def launch(self, binary, testcase, prefs=None):
        """
        Launch firefox using the supplied binary and testcase
        :param binary: The path to the firefox binary
        :param testcase: The path to the testcase
        :param prefs: The path to the prefs file
        :return: The return code or None
        """
        ffp = FFPuppet(
            use_gdb=self._use_gdb,
            use_valgrind=self._use_valgrind,
            use_xvfb=self._use_xvfb,
        )
        if self._asserts:
            ffp.add_abort_token("###!!! ASSERTION:")

        result = Bisector.BUILD_PASSED

        try:
            ffp.launch(
                str(binary),
                env_mod=self._env_vars,
                location=testcase,
                launch_timeout=self._launch_timeout,
                memory_limit=self._memory,
                prefs_js=prefs,
                extension=self._extension,
            )
            ffp.wait(self._timeout)

            if not ffp.is_running():
                ffp.close()
                if ffp.reason == FFPuppet.RC_EXITED:
                    log.info(">> Target closed itself")
                elif (
                    ffp.reason == FFPuppet.RC_WORKER
                    and self._detect == "memory"
                    and "ffp_worker_memory_limiter" in ffp.available_logs()
                ):
                    log.info(">> Memory limit exceeded")
                    result = Bisector.BUILD_CRASHED
                elif (
                    ffp.reason == FFPuppet.RC_WORKER
                    and self._detect == "log"
                    and "ffp_worker_log_size_limiter" in ffp.available_logs()
                ):
                    log.info(">> Log size limit exceeded")
                    result = Bisector.BUILD_CRASHED
                else:
                    log.info(">> Failure detected")
                    result = Bisector.BUILD_CRASHED
            elif not ffp.is_healthy():
                # this should be e10s only
                result = Bisector.BUILD_CRASHED
                log.info(">> Browser is alive but has crash reports. Terminating...")
                ffp.close()
            elif self._detect == "timeout":
                result = Bisector.BUILD_CRASHED
                log.info(">> Timeout detected")
                ffp.close()
            else:
                log.info(">> Time limit exceeded")
        except LaunchError:
            log.warn(">> Failed to start browser")
            result = Bisector.BUILD_FAILED
        finally:
            ffp.clean_up()

        return result
