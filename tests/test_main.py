# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import platform

import pytest

from autobisect.main import parse_args


@pytest.mark.parametrize("target", ("firefox", "js"))
def test_parse_args_simple(tmp_path, target):
    """Test that parse_args works with minimal arguments"""
    testcase = tmp_path / "testcase"
    testcase.touch()
    args = parse_args([target, str(testcase)])
    assert args.target == target


@pytest.mark.parametrize("target", ("firefox", "js"))
def test_parse_args_invalid_testcase_path(tmp_path, target):
    """Test that parse_args raises when using an invalid testcase path"""
    with pytest.raises(SystemExit):
        parse_args([target, str(tmp_path / "non-existent")])


def test_parse_args_invalid_target():
    """Test that parse_args raises when using an invalid target"""
    with pytest.raises(SystemExit):
        parse_args(["foo"])


@pytest.mark.parametrize(
    "args",
    [
        (["firefox", "--log-level", "INVALID"], "Invalid log-level"),
        (["firefox", "--config", "404.ini"], "Cannot access configuration file!"),
        (["firefox", "--fuzzilli"], "Fuzzilli builds are not available for firefox"),
    ],
)
def test_parse_args_raises_with_invalid_args(capsys, tmp_path, args):
    """Test that parse_args raises when using invalid arguments"""
    testcase = tmp_path / "testcase"
    testcase.touch()
    args[0].append(str(testcase))
    with pytest.raises(SystemExit):
        parse_args(args[0])

    _, err = capsys.readouterr()
    assert args[1] in err


@pytest.mark.skipif(platform.system() != "Windows", reason="Windows only")
def test_parse_args_windows_defaults(mocker, tmp_path):
    """Test that parse_args sets the expected windows defaults"""
    testcase = tmp_path / "testcase.html"
    testcase.touch()

    args = parse_args(["firefox", str(testcase)])
    assert not args.pernosco
    assert not args.rr
    assert not args.valgrind


def test_parse_args_prefs_sanity_check(mocker, tmp_path):
    """Test that parse_args exits if the prefs.js file is not accessible."""
    testcase = tmp_path / "testcase.html"
    testcase.touch()
    prefs = tmp_path / "prefs.js"

    with pytest.raises(SystemExit):
        parse_args(["firefox", str(testcase), "--prefs", str(prefs)])
