# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from pathlib import Path
from platform import system
from unittest.mock import MagicMock

import pytest
from grizzly.common.utils import Exit

from autobisect.evaluators import BrowserEvaluator, EvaluatorResult
from autobisect.evaluators.browser.browser import BrowserEvaluatorException


def not_linux():
    """Simple fixture for skipping parameters when not run on Linux"""
    return pytest.mark.skipif(not system().startswith("Linux"), reason="linux only")


def test_verify_build_status(mocker):
    """
    Test that BrowserEvaluator.verify_build() returns the correct status
    """
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


def test_evaluate_testcase_simple(mocker, tmp_path):
    """
    Simple test of BrowserEvaluator.evaluate_testcase()
    """
    mocker.patch(
        "autobisect.BrowserEvaluator.launch",
        autospec=True,
        return_value=EvaluatorResult.BUILD_PASSED,
    )
    browser = BrowserEvaluator(Path("testcase.html"))
    binary_name = "firefox.exe" if system() == "Windows" else "firefox"
    (tmp_path / binary_name).touch()
    assert browser.evaluate_testcase(tmp_path) == EvaluatorResult.BUILD_PASSED


def test_evaluate_testcase_non_existent_binary(tmp_path):
    """
    Test that BrowserEvaluator.evaluate_testcase fails when using a non-existent build path
    """
    browser = BrowserEvaluator(Path("testcase.html"))
    assert browser.evaluate_testcase(tmp_path) == EvaluatorResult.BUILD_FAILED


def test_evaluate_testcase_system_windows(mocker, tmp_path):
    """Test that the binary path is calculated as firefox.exe on windows"""
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


def test_launch_simple(mocker, tmp_path):
    """Simple test of BrowserEvaluator.launch()"""
    mocker.patch(
        "grizzly.replay.ReplayManager.main",
        side_effect=(Exit.SUCCESS, Exit.FAILURE),
    )

    binary = tmp_path / "firefox"
    binary.touch()
    testcase = tmp_path / "testcase.html"
    testcase.touch()

    browser = BrowserEvaluator(testcase)
    assert browser.launch(binary, testcase) == EvaluatorResult.BUILD_CRASHED
    assert browser.launch(binary, testcase) == EvaluatorResult.BUILD_PASSED


def test_launch_non_existent_binary(tmp_path):
    """Simple test of BrowserEvaluator.launch()"""
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
def test_grizzly_arg_parsing(
    mocker,
    tmp_path: Path,
    harness: bool,
    headless: bool,
    ignore: str,
    pernosco: bool,
    valgrind: bool,
):
    """Ensure that args are accepted by grizzly"""
    binary = tmp_path / "firefox"
    binary.touch()
    testcase = tmp_path / "testcase.html"
    testcase.touch()
    prefs = tmp_path / "prefs.js"
    prefs.touch()

    # 'rr needs /proc/sys/kernel/perf_event_paranoid <= 1, but it is 2'
    mocker.patch.object(Path, "read_text", return_value=1)

    evaluator = BrowserEvaluator(
        testcase,
        headless=headless,
        ignore=[ignore],
        launch_timeout=300,
        prefs=prefs,
        relaunch=1,
        use_harness=harness,
        use_valgrind=valgrind,
        logs=tmp_path,
        pernosco=pernosco,
        repeat=10,
    )
    evaluator.parse_args(binary, tmp_path, verify=False)


def test_grizzly_arg_parsing_no_pernosco_on_verify(tmp_path: Path):
    """Ensure that args are accepted by grizzly"""
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

    for k, v in kwargs.items():
        assert args.__dict__[k] != v
