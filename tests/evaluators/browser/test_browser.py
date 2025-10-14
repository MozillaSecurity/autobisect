# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from pathlib import Path
from platform import system
from unittest.mock import MagicMock

import pytest
from grizzly.common.frontend import Exit

from autobisect.evaluators import BrowserEvaluator, EvaluatorResult
from autobisect.evaluators.browser.browser import BrowserEvaluatorException
from grizzly.common.storage import TestCase


def not_linux():
    """Simple fixture for skipping parameters when not run on Linux."""
    return pytest.mark.skipif(not system().startswith("Linux"), reason="linux only")


def test_verify_build_status(mocker):
    """Test that verify_build returns the correct status."""
    mocker.patch(
        "autobisect.BrowserEvaluator.launch",
        side_effect=(
            EvaluatorResult.BUILD_CRASHED,
            EvaluatorResult.BUILD_PASSED,
            EvaluatorResult.BUILD_FAILED,
        ),
    )
    browser = BrowserEvaluator(Path("testcase.html"))

    assert browser.verify_build(Path("firefox")) is False
    assert browser.verify_build(Path("firefox")) is True
    assert browser.verify_build(Path("firefox")) is False


@pytest.mark.parametrize("scan_dir", (True, False))
def test_evaluate_testcase_simple(mocker, tmp_path, scan_dir):
    """Test that evaluate_testcase works correctly and passes scan_dir to launch."""
    mock_launch = mocker.patch(
        "autobisect.BrowserEvaluator.launch",
        return_value=EvaluatorResult.BUILD_PASSED,
    )
    browser = BrowserEvaluator(Path("testcase.html"), scan_dir=scan_dir)
    binary_name = "firefox.exe" if system() == "Windows" else "firefox"
    (tmp_path / binary_name).touch()

    assert browser.evaluate_testcase(tmp_path) == EvaluatorResult.BUILD_PASSED

    # Verify launch was called with correct scan_dir parameter
    # Second call is the actual testcase evaluation (first is verify_build)
    assert mock_launch.call_count == 2
    second_call_kwargs = mock_launch.call_args_list[1][1]
    assert second_call_kwargs.get("scan_dir") == scan_dir


def test_evaluate_testcase_non_existent_binary(tmp_path):
    """Test that the binary path is calculated as "firefox.exe" on windows."""
    browser = BrowserEvaluator(Path("testcase.html"))

    assert browser.evaluate_testcase(tmp_path) == EvaluatorResult.BUILD_FAILED


def test_evaluate_testcase_system_windows(mocker, tmp_path):
    """Simple test of evaluate_testcase on windows."""
    evaluator = BrowserEvaluator(Path("testcase.html"))

    # Mock the system function to simulate running in Windows
    mocker.patch("autobisect.evaluators.browser.browser.system", return_value="Windows")

    # Mock the binary_path to an existing path
    binary_path = tmp_path / "firefox.exe"
    binary_path.touch()

    # Mock the verify_build method to return False
    spy = MagicMock(wraps=evaluator.verify_build, return_value=False)
    mocker.patch.object(evaluator, "verify_build", spy)

    evaluator.evaluate_testcase(tmp_path)

    # Assert that verify_build was called with the expected file path
    spy.assert_called_once_with(binary_path)


@pytest.mark.parametrize("scan_dir", (True, False))
def test_launch_simple(mocker, tmp_path, scan_dir):
    """Test that launch returns the expected evaluator result and handles scan_dir correctly."""
    mocker.patch(
        "grizzly.replay.ReplayManager.main",
        side_effect=(Exit.SUCCESS, Exit.FAILURE),
    )

    # Create test structure
    test_dir = tmp_path / "tests" if scan_dir else tmp_path
    test_dir.mkdir(exist_ok=True)
    binary = tmp_path / "firefox"
    binary.touch()
    testcase = test_dir / "testcase.html"
    testcase.touch()

    # Mock TestCase.load to verify correct behavior
    testcase_spy = mocker.spy(TestCase, "load")

    evaluator = BrowserEvaluator(testcase, scan_dir=scan_dir)

    assert (
        evaluator.launch(binary, testcase, scan_dir=scan_dir)
        == EvaluatorResult.BUILD_CRASHED
    )

    # Verify TestCase.load behavior based on scan_dir
    testcase_spy.assert_called_once_with(test_dir, testcase, catalog=scan_dir)
    assert testcase_spy.spy_return.entry_point == str(testcase.name)

    assert (
        evaluator.launch(binary, testcase, scan_dir=scan_dir)
        == EvaluatorResult.BUILD_PASSED
    )


def test_launch_non_existent_binary(tmp_path):
    """Test that launch fails when using a non-existent build path."""
    binary = tmp_path / "firefox"
    testcase = tmp_path / "testcase.html"
    testcase.touch()

    browser = BrowserEvaluator(testcase)

    with pytest.raises(BrowserEvaluatorException):
        browser.launch(binary, testcase)


@pytest.mark.parametrize("harness", (True, False))
@pytest.mark.parametrize(
    "headless", ("default", pytest.param("xvfb", marks=not_linux()))
)
@pytest.mark.parametrize("ignore", ("log-limit", "memory", "timeout"))
@pytest.mark.parametrize("pernosco", (False, pytest.param(True, marks=not_linux())))
@pytest.mark.parametrize("valgrind", (False, pytest.param(True, marks=not_linux())))
@pytest.mark.parametrize("scan_dir", (True, False))
def test_grizzly_arg_parsing(
    mocker,
    tmp_path: Path,
    harness: bool,
    headless: bool,
    ignore: str,
    pernosco: bool,
    valgrind: bool,
    scan_dir: bool,
):
    """Ensure that args are accepted by grizzly."""
    binary = tmp_path / "firefox"
    binary.touch()
    testcase = tmp_path / "testcase.html"
    testcase.touch()
    prefs = tmp_path / "prefs.js"
    prefs.touch()

    original_read_text = Path.read_text

    def read_text_bypass(self: Path, *args, **kwargs):
        """'rr needs /proc/sys/kernel/perf_event_paranoid <= 1, but it is 2'"""
        if self.absolute() == Path("/proc/sys/kernel/perf_event_paranoid"):
            return "1"
        else:
            return original_read_text(self, *args, **kwargs)

    mocker.patch(
        "grizzly.args.Path.read_text",
        autospec=True,
        side_effect=read_text_bypass,
    )

    evaluator = BrowserEvaluator(
        testcase,
        headless=headless,
        ignore=[ignore],
        launch_timeout=300,
        prefs=prefs,
        relaunch=1,
        scan_dir=scan_dir,
        use_harness=harness,
        use_valgrind=valgrind,
        logs=tmp_path,
        pernosco=pernosco,
        repeat=10,
    )
    evaluator.parse_args(binary, tmp_path, verify=False)

    # Verify scan_dir attribute is set correctly
    assert evaluator.scan_dir == scan_dir


def test_grizzly_arg_parsing_no_pernosco_on_verify(tmp_path: Path):
    """Test that pernosco is not used when verifying build."""
    binary = tmp_path / "firefox"
    binary.touch()
    testcase = tmp_path / "testcase.html"
    testcase.touch()
    kwargs = {
        "pernosco": True,
        "logs": "/foo/bar",
        "repeat": 100,
    }
    evaluator = BrowserEvaluator(testcase, **kwargs)
    args = evaluator.parse_args(binary, tmp_path, verify=True)

    assert not args.pernosco
