import pytest

from autobisect.evaluators import BrowserEvaluator
from autobisect.evaluators import EvaluatorResult


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
    browser = BrowserEvaluator("testcase.html")
    assert browser.verify_build(None) is False
    assert browser.verify_build(None) is True
    assert browser.verify_build(None) is False


def test_evaluate_testcase_simple(mocker, tmp_path):
    """
    Simple test of BrowserEvaluator.evaluate_testcase()
    """
    mocker.patch(
        "autobisect.BrowserEvaluator.launch",
        autospec=True,
        return_value=EvaluatorResult.BUILD_PASSED,
    )
    browser = BrowserEvaluator("testcase.html")
    (tmp_path / "firefox").touch()
    assert browser.evaluate_testcase(str(tmp_path)) == EvaluatorResult.BUILD_PASSED


def test_evaluate_testcase_non_existent_binary(tmp_path):
    """
    Test that BrowserEvaluator.evaluate_testcase fails when using a non-existent build path
    """
    browser = BrowserEvaluator("testcase.html")
    assert browser.evaluate_testcase(str(tmp_path)) == EvaluatorResult.BUILD_FAILED


def test_launch_simple(mocker, tmp_path):
    """
    Simple test of BrowserEvaluator.launch()
    """
    mocker.patch(
        "grizzly.replay.ReplayManager.run", autospec=True, side_effect=(True, False)
    )

    binary = tmp_path / "firefox"
    binary.touch()
    testcase = tmp_path / "testcase.html"
    testcase.touch()

    browser = BrowserEvaluator(testcase)
    assert browser.launch(binary, testcase, None, 1) == EvaluatorResult.BUILD_CRASHED
    assert browser.launch(binary, testcase, None, 1) == EvaluatorResult.BUILD_PASSED


def test_launch_non_existent_binary(mocker, tmp_path):
    """
    Simple test of BrowserEvaluator.launch()
    """
    mocker.patch("grizzly.replay.ReplayManager.run", side_effect=(True, False))

    binary = tmp_path / "firefox"
    testcase = tmp_path / "testcase.html"
    testcase.touch()

    browser = BrowserEvaluator(testcase)

    with pytest.raises(AssertionError):
        browser.launch(binary, testcase, None, 1)
