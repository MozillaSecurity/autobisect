from pathlib import Path

import pytest
from grizzly.session import Session

from autobisect.evaluators import BrowserEvaluator, EvaluatorResult
from autobisect.evaluators.browser.browser import BrowserEvaluatorException


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
    (tmp_path / "firefox").touch()
    assert browser.evaluate_testcase(tmp_path) == EvaluatorResult.BUILD_PASSED


def test_evaluate_testcase_non_existent_binary(tmp_path):
    """
    Test that BrowserEvaluator.evaluate_testcase fails when using a non-existent build path
    """
    browser = BrowserEvaluator(Path("testcase.html"))
    assert browser.evaluate_testcase(tmp_path) == EvaluatorResult.BUILD_FAILED


def test_launch_simple(mocker, tmp_path):
    """
    Simple test of BrowserEvaluator.launch()
    """
    mocker.patch(
        "grizzly.replay.ReplayManager.main",
        side_effect=(Session.EXIT_SUCCESS, Session.EXIT_FAILURE),
    )

    binary = tmp_path / "firefox"
    binary.touch()
    testcase = tmp_path / "testcase.html"
    testcase.touch()

    browser = BrowserEvaluator(testcase)
    assert browser.launch(binary, testcase, 1) == EvaluatorResult.BUILD_CRASHED
    assert browser.launch(binary, testcase, 1) == EvaluatorResult.BUILD_PASSED


def test_launch_non_existent_binary(tmp_path):
    """
    Simple test of BrowserEvaluator.launch()
    """
    binary = tmp_path / "firefox"
    testcase = tmp_path / "testcase.html"
    testcase.touch()

    browser = BrowserEvaluator(testcase)

    with pytest.raises(BrowserEvaluatorException):
        browser.launch(binary, testcase, 1)
