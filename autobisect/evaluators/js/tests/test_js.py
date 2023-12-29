# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from pathlib import Path
from platform import system

import pytest
from lithium.interestingness.timed_run import ExitStatus, RunData
from requests import RequestException

from autobisect import EvaluatorResult
from autobisect.evaluators.js.js import _get_rev, JSEvaluator, JSEvaluatorException
from autobisect.tests.conftest import requests_mock_cache  # noqa


def test_get_rev_with_valid_fuzzmanagerconf(tmp_path):
    """Test that _get_rev returns the correct revision"""
    binary_path = tmp_path / "firefox.exe"
    fm_conf_path = binary_path.with_suffix(".fuzzmanagerconf")
    fm_conf_path.write_text("product_version = 20230908-3096b15a785a")
    assert _get_rev(binary_path) == "3096b15a785a"


def test_get_rev_with_missing_fuzzmanagerconf(tmp_path):
    """Test that _get_rev returns tip when it cannot find the product_version"""
    binary_path = tmp_path / "test_binary.exe"
    binary_path.with_suffix(".fuzzmanagerconf").touch()

    assert _get_rev(binary_path) == "tip"


def test_js_evaluator_init(tmp_path):
    """Test the initialization of JSEvaluator with valid arguments"""
    test = tmp_path / "testcase.js"
    evaluator = JSEvaluator(test, flags=["--x"], repeat=2, timeout=30, detect="crash")
    assert evaluator.testcase == test
    assert evaluator.flags == ["--x"]
    assert evaluator.repeat == 2
    assert evaluator.timeout == 30
    assert evaluator.detect == "crash"


def test_js_evaluator_init_diff_mode(tmp_path):
    """Test initialization of diff mode"""
    test = tmp_path / "testcase.js"
    evaluator = JSEvaluator(test, detect="diff", arg_1="a", arg_2="b")
    assert evaluator.detect == "diff"
    assert evaluator._arg_1 == "a"
    assert evaluator._arg_2 == "b"


def test_js_evaluator_init_diff_mode_invalid_args(tmp_path):
    """Test initialization of diff mode without supplying arg_1 or arg_2"""
    error_message = "Diff mode requires 'arg_1' and 'arg_2'"
    with pytest.raises(JSEvaluatorException, match=error_message):
        JSEvaluator(tmp_path / "testcase.js", detect="diff")


def test_js_evaluator_init_match_mode(tmp_path):
    """Test initialization of "output" (match) mode"""
    test = tmp_path / "testcase.js"
    evaluator = JSEvaluator(test, detect="output", match="expected_output")
    assert evaluator.testcase == test
    assert evaluator.detect == "output"
    assert evaluator._match == "expected_output"


def test_js_evaluator_init_match_mode_invalid_args():
    """Test initialization in "output" (match) mode without providing match string"""
    error_message = "Match mode requires a match string"
    with pytest.raises(JSEvaluatorException, match=error_message):
        JSEvaluator(Path("/path/to/testcase.js"), detect="output")


@pytest.mark.usefixtures("requests_mock_cache")
def test_js_evaluator_get_valid_flags(tmp_path):
    test = tmp_path / "testcase.js"
    evaluator = JSEvaluator(test, detect="crash")
    flags = evaluator.get_valid_flags("tip")
    assert sorted(flags) == [
        "arm-asm-nop-fill",
        "arm-hwcap",
        "arm-sim-icache-checks",
        "arm-sim-stop-at",
        "asm-pool-max-offset",
        "async-stacks-capture-debuggee-only",
        "available-memory",
        "baseline-eager",
        "baseline-warmup-threshold",
        "blinterp",
        "blinterp-eager",
        "blinterp-warmup-threshold",
        "cache-ir-stubs",
        "code-coverage",
        "cpu-count",
        "debug-sim",
        "delazification-mode",
        "differential-testing",
        "disable-bailout-loop-check",
        "disable-jithints",
        "disable-oom-functions",
        "disable-property-error-message-fix",
        "disable-tosource",
        "disable-wasm-huge-memory",
        "disable-watchtower",
        "disable-weak-refs",
        "dll",
        "dump-entrained-variables",
        "emit-interpreter-entry",
        "enable-array-grouping",
        "enable-arraybuffer-transfer",
        "enable-avx",
        "enable-ic-frame-pointers",
        "enable-import-assertions",
        "enable-iterator-helpers",
        "enable-new-set-methods",
        "enable-parallel-marking",
        "enable-shadow-realms",
        "enable-watchtower",
        "enable-well-formed-unicode-strings",
        "fast-warmup",
        "fuzzing-safe",
        "gc-param",
        "gc-zeal",
        "inlining-entry-threshold",
        "ion-check-range-analysis",
        "ion-eager",
        "ion-edgecase-analysis",
        "ion-extra-checks",
        "ion-gvn",
        "ion-inlining",
        "ion-instruction-reordering",
        "ion-iterator-indices",
        "ion-licm",
        "ion-limit-script-size",
        "ion-offthread-compile",
        "ion-optimize-gcbarriers",
        "ion-optimize-shapeguards",
        "ion-osr",
        "ion-parallel-compile",
        "ion-pruning",
        "ion-range-analysis",
        "ion-regalloc",
        "ion-scalar-replacement",
        "ion-shared-stubs",
        "ion-sink",
        "ion-warmup-threshold",
        "less-debug-code",
        "loong64-sim-icache-checks",
        "loong64-sim-stop-at",
        "marking-threads",
        "mips-sim-icache-checks",
        "mips-sim-stop-at",
        "module-load-path",
        "more-compartments",
        "no-asmjs",
        "no-async-stacks",
        "no-avx",
        "no-baseline",
        "no-blinterp",
        "no-cgc",
        "no-emit-interpreter-entry",
        "no-ggc",
        "no-incremental-gc",
        "no-ion",
        "no-ion-for-main-context",
        "no-jit-backend",
        "no-native-regexp",
        "no-source-pragmas",
        "no-sse3",
        "no-sse4",
        "no-sse41",
        "no-sse42",
        "no-ssse3",
        "no-threads",
        "no-wasm-",
        "not-implemented-watchfile",
        "nursery-bigints",
        "nursery-size",
        "nursery-strings",
        "only-inline-selfhosted",
        "regexp-warmup-threshold",
        "reprl",
        "riscv-debug",
        "riscv-sim-stop-at",
        "riscv-trap-to-simulator-debugger",
        "selfhosted-xdr-mode",
        "selfhosted-xdr-path",
        "shared-memory",
        "small-function-length",
        "smoosh",
        "spectre-mitigations",
        "suppress-minidump",
        "telemetry-dir",
        "test-wasm-await-tier2",
        "thread-count",
        "trace-regexp-assembler",
        "trace-regexp-interpreter",
        "trace-regexp-parser",
        "trace-regexp-peephole",
        "trace-sim",
        "trial-inlining-warmup-threshold",
        "use-fdlibm-for-sin-cos-tan",
        "wasm-",
        "wasm-compile-and-serialize",
        "wasm-compiler",
        "wasm-verbose",
        "write-protect-code",
    ]


def test_js_evaluator_get_valid_flags_bad_rev(caplog, mocker, tmp_path):
    """Test that _get_valid_flags fails gracefully when using an invalid revision"""
    # Mock HTTP_SESSION.get to raise a RequestException
    mocker.patch(
        "autobisect.evaluators.js.js.HTTP_SESSION.get",
        side_effect=RequestException("404 Client Error"),
    )

    # Call the get_valid_flags function with a sample 'rev'
    test = tmp_path / "testcase.js"
    evaluator = JSEvaluator(test, detect="crash")
    rev = "sample_rev"
    flags = evaluator.get_valid_flags(rev)

    # Assert that the function returns an empty list
    assert flags == []

    # Assert that a warning message is logged with the expected exception message
    assert "Failed to retrieve build flags: " in caplog.text


@pytest.mark.parametrize("status", [True, False])
def test_js_evaluator_verify_build(mocker, tmp_path, status):
    """Test that verify build calls timed_run with the expected arguments"""
    test = tmp_path / "testcase.js"
    evaluator = JSEvaluator(test, detect="crash", timeout=30)

    # Mock the timed_run function
    mock_timed_run = mocker.patch("lithium.interestingness.timed_run.timed_run")

    # Configure the mock return value for timed_run
    mock_run_data = mocker.MagicMock(RunData)
    mock_run_data.status = ExitStatus.NORMAL if status else ExitStatus.CRASH
    mock_timed_run.return_value = mock_run_data

    # Call the verify_build method
    binary = tmp_path / "js"
    flags = ["-flag1", "-flag2"]
    result = evaluator.verify_build(binary, flags)

    # Assert that the mock timed_run was called with the expected arguments
    mock_timed_run.assert_called_once_with([str(binary), *flags, "-e", '"quit()"'], 30)

    # Assert that the result is True because the mock timed_run returned NORMAL
    assert result is status


@pytest.mark.parametrize("verified", (True, False))
@pytest.mark.parametrize(
    "mode, ext_args",
    (
        ("crash", {}),
        ("diff", {"arg_1": "a", "arg_2": "b"}),
        ("hang", {}),
        ("output", {"match": "magic string"}),
    ),
)
def test_js_evaluator_evaluate_testcase(mocker, tmp_path, mode, ext_args, verified):
    """Simple test of JSEvaluator.evaluate_testcase()"""
    (tmp_path / "dist" / "bin").mkdir(parents=True)
    binary = "js.exe" if system() == "Windows" else "js"
    (tmp_path / "dist" / "bin" / binary).touch()
    test = tmp_path / "testcase.js"

    # Set additional args required by each mode
    evaluator = JSEvaluator(test, detect=mode, flags=["--fuzzing-safe"], **ext_args)

    mocker.patch("autobisect.evaluators.js.js._get_rev", return_value="tip")
    mocker.patch.object(evaluator, "get_valid_flags", return_value=["fuzzing-safe"])
    mocker.patch.object(evaluator, "verify_build", return_value=verified)

    # Mock the timed_run function

    # Configure RunData return value for timed_run
    mock_run_data = mocker.MagicMock(RunData)
    mock_run_data.elapsedtime = 10

    mock_run_data.status = ExitStatus.NORMAL
    if mode == "diff":
        type(mock_run_data).return_code = mocker.PropertyMock(side_effect=[1, 2])
        patch_path = "lithium.interestingness.diff_test.timed_run"
    elif mode == "hang":
        mock_run_data.status = ExitStatus.TIMEOUT
        patch_path = "lithium.interestingness.hangs.timed_run"
    elif mode == "output":
        mock_run_data.err = b""
        mock_run_data.out = b"magic string"
        patch_path = "lithium.interestingness.outputs.timed_run"
    else:
        mock_run_data.err = b""
        mock_run_data.status = ExitStatus.CRASH
        patch_path = "lithium.interestingness.timed_run.timed_run"

    mocker.patch(patch_path, return_value=mock_run_data)

    result = evaluator.evaluate_testcase(tmp_path)
    if not verified:
        assert result == EvaluatorResult.BUILD_FAILED
    else:
        assert result == EvaluatorResult.BUILD_CRASHED


def test_js_evaluator_evaluate_testcase_invalid_binary(tmp_path):
    """Test that evaluate_testcase returns BUILD_FAILED when a bad binary path is supplied"""
    binary = tmp_path / "dist" / "bin" / "js"
    test = tmp_path / "testcase.js"
    evaluator = JSEvaluator(test, detect="crash")
    assert evaluator.evaluate_testcase(binary) == EvaluatorResult.BUILD_FAILED
