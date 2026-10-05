# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# pylint: disable=protected-access
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
from fuzzfetch import BuildFlags, Fetcher, FetcherException, Platform

from autobisect import BrowserEvaluator, EvaluatorResult
from autobisect.bisect import (
    BisectionResult,
    Bisector,
    StatusException,
    VerificationStatus,
    get_autoland_range,
    get_merge_second_parent,
)
from autobisect.builds import BuildRange


class MockFetcher:
    """Class for mocking Fetcher objects."""

    def __init__(self, dt=None, changeset=None):
        self.datetime = dt
        self.changeset = changeset


class MockBisector(Bisector):
    """Class for mocking Bisector objects."""

    # pylint: disable=super-init-not-called
    def __init__(self, start: datetime, end: datetime):
        self.start = MockFetcher(dt=start)
        self.end = MockFetcher(dt=end)
        self.branch = "central"
        self.find_fix = False
        self.flags = BuildFlags()
        self.platform = Platform("Linux", "x86_64")
        self.evaluator = BrowserEvaluator(Path("testcase.html"))


@pytest.mark.freeze_time("2024-05-30")
@pytest.mark.parametrize("delta, expected", [[0, 0], [11, 10]])
@pytest.mark.vcr()
def test_bisect_get_daily_builds_simple(delta, expected):
    """Test that get_daily_builds returns the expected build range."""
    start_date = datetime.now(tz=timezone.utc) - timedelta(days=delta)
    end_date = datetime.now(tz=timezone.utc)
    bisector = MockBisector(start_date, end_date)
    builds = bisector._get_daily_builds()

    assert isinstance(builds, BuildRange)
    assert all(re.match(r"\d{4}-\d{2}-\d{2}", b) is not None for b in builds)
    assert len(builds) == expected


@pytest.mark.freeze_time("2025-06-18")
@pytest.mark.vcr()
def test_bisect_get_pushdate_builds_simple():
    """Test that get_daily_builds returns the expected build range."""
    start_date = datetime.now(tz=timezone.utc) - timedelta(days=1)
    end_date = datetime.now(tz=timezone.utc)
    bisector = MockBisector(start_date, end_date)

    builds = bisector._get_pushdate_builds()

    assert len(builds) == 2
    assert isinstance(builds, BuildRange)
    for build in builds:
        assert isinstance(build, Fetcher)


def test_get_autoland_builds_uses_lineage(mocker):
    bisector = MockBisector(datetime.now(), datetime.now())
    mocker.patch("autobisect.bisect.get_autoland_range", return_value=["middle", "end"])
    builds = [mocker.Mock(spec=Fetcher), mocker.Mock(spec=Fetcher)]
    fetcher = mocker.patch("autobisect.bisect.Fetcher", side_effect=builds)

    result = bisector._get_autoland_builds("start", "end")

    assert result is not None
    assert result.builds == builds
    assert [call.args[1] for call in fetcher.call_args_list] == ["middle", "end"]


def test_get_autoland_range_first_parent(mocker):
    response = mocker.Mock()
    response.json.return_value = {
        "1": {"changesets": [{"node": "middle", "parents": ["start"]}]},
        "2": {"changesets": [{"node": "end", "parents": ["middle"]}]},
    }
    request = mocker.patch("autobisect.bisect.requests.get", return_value=response)

    assert get_autoland_range("start", "end") == ["middle", "end"]
    assert "integration/autoland/json-pushes" in request.call_args.args[0]


def test_get_autoland_range_rejects_divergent_history(mocker):
    response = mocker.Mock()
    response.json.return_value = {
        "2": {"changesets": [{"node": "end", "parents": ["other-branch"]}]}
    }
    mocker.patch("autobisect.bisect.requests.get", return_value=response)

    assert get_autoland_range("start", "end") is None


def test_get_autoland_range_invalid_revs(mocker):
    mocker.patch(
        "autobisect.bisect.requests.get", side_effect=requests.exceptions.HTTPError
    )

    assert get_autoland_range("foo", "bar") is None


def test_get_merge_second_parent(mocker):
    response = mocker.Mock()
    response.json.return_value = {
        "parents": ["central-parent", "autoland-parent"],
    }
    mocker.patch("autobisect.bisect.requests.get", return_value=response)

    assert get_merge_second_parent("merge") == "autoland-parent"
    response.json.return_value = {"parents": ["central-parent"]}
    assert get_merge_second_parent("non-merge") is None


@pytest.mark.parametrize(
    "metadata", [ValueError("invalid JSON"), None, {"parents": None}, {"parents": "ab"}]
)
def test_get_merge_second_parent_invalid_metadata(mocker, metadata):
    response = mocker.Mock()
    if isinstance(metadata, Exception):
        response.json.side_effect = metadata
    else:
        response.json.return_value = metadata
    mocker.patch("autobisect.bisect.requests.get", return_value=response)

    assert get_merge_second_parent("merge") is None


@pytest.mark.parametrize(
    "find_fix, start_result, end_result, expected_success",
    [
        (True, EvaluatorResult.BUILD_CRASHED, EvaluatorResult.BUILD_PASSED, True),
        (True, EvaluatorResult.BUILD_PASSED, EvaluatorResult.BUILD_PASSED, False),
        (True, EvaluatorResult.BUILD_CRASHED, EvaluatorResult.BUILD_CRASHED, False),
        (False, EvaluatorResult.BUILD_PASSED, EvaluatorResult.BUILD_CRASHED, True),
    ],
)
def test_bisect_autoland_verifies_bounds_first(
    mocker, find_fix, start_result, end_result, expected_success
):
    bisector = MockBisector(datetime.now(), datetime.now())
    bisector.find_fix = find_fix
    central_start = mocker.Mock(spec=Fetcher)
    central_end = mocker.Mock(spec=Fetcher)
    central_start.changeset = "central-start"
    central_end.changeset = "central-end"
    bisector.start, bisector.end = central_start, central_end
    autoland_start = mocker.Mock(spec=Fetcher)
    autoland_end = mocker.Mock(spec=Fetcher)
    middle = mocker.Mock(spec=Fetcher)
    events = []
    mocker.patch(
        "autobisect.bisect.get_merge_second_parent", side_effect=["base", "tip"]
    )
    mocker.patch("autobisect.bisect.Fetcher", return_value=autoland_start)
    builds = BuildRange([middle, autoland_end])

    def get_builds(start, end):
        events.append("range")
        assert (start, end) == ("base", "tip")
        return builds

    mocker.patch.object(bisector, "_get_autoland_builds", side_effect=get_builds)
    outcomes = [start_result, end_result]

    def test_build(build):
        events.append(build)
        return outcomes.pop(0)

    mocker.patch.object(bisector, "test_build", side_effect=test_build)
    run_range = mocker.patch.object(bisector, "_bisect_build_range")

    bisector._bisect_autoland(False)

    assert events[0] is autoland_start
    if start_result == (
        EvaluatorResult.BUILD_CRASHED if find_fix else EvaluatorResult.BUILD_PASSED
    ):
        assert events[1:] == ["range", autoland_end]
    else:
        assert events == [autoland_start]
    if expected_success:
        assert (bisector.start, bisector.end) == (autoland_start, autoland_end)
        assert run_range.call_args.args[0].builds == [middle]
    else:
        assert (bisector.start, bisector.end) == (central_start, central_end)
        run_range.assert_not_called()


def test_unavailable_autoland_parent_preserves_central_bounds(mocker):
    bisector = MockBisector(datetime.now(), datetime.now())
    central_start = mocker.Mock(spec=Fetcher)
    central_end = mocker.Mock(spec=Fetcher)
    central_start.changeset = "central-start"
    central_end.changeset = "central-end"
    bisector.start, bisector.end = central_start, central_end
    mocker.patch(
        "autobisect.bisect.get_merge_second_parent", side_effect=["base", "tip"]
    )
    mocker.patch("autobisect.bisect.Fetcher", side_effect=FetcherException("missing"))
    run_range = mocker.patch.object(bisector, "_bisect_build_range")

    bisector._bisect_autoland(False)

    assert (bisector.start, bisector.end) == (central_start, central_end)
    run_range.assert_not_called()


def test_mixed_repository_result_is_not_reported_as_success(mocker):
    start = mocker.Mock(spec=Fetcher)
    end = mocker.Mock(spec=Fetcher)
    start.build_info = {"moz_source_repo": "https://hg.mozilla.org/mozilla-central"}
    end.build_info = {"moz_source_repo": "https://hg.mozilla.org/integration/autoland"}

    result = BisectionResult(BisectionResult.SUCCESS, start, end, "central")

    assert result.status == BisectionResult.FAILED


@pytest.mark.parametrize("status", EvaluatorResult)
@pytest.mark.parametrize("find_fix", [True, False])
def test_update_range_simple(status, find_fix):
    """Test that update_range returns the correct build range based on status."""
    builds = []
    for _ in range(10):
        next_date = datetime(2020, 1, 1, 0, 0) + timedelta(days=1)
        builds.append(MockFetcher(dt=next_date))

    for index, build in enumerate(builds):
        bisector = MockBisector(builds[0].datetime, builds[-1].datetime)
        bisector.find_fix = find_fix
        build_range = BuildRange(builds)
        bisector.update_range(status, build, index, build_range)
        if status == EvaluatorResult.BUILD_PASSED:
            if find_fix:
                assert bisector.end == build
            else:
                assert bisector.start == build
        elif status == EvaluatorResult.BUILD_CRASHED:
            if find_fix:
                assert bisector.start == build
            else:
                assert bisector.end == build


@pytest.mark.parametrize("find_fix", [True, False])
@pytest.mark.parametrize("end_result", EvaluatorResult)
@pytest.mark.parametrize("start_result", EvaluatorResult)
# pylint: disable=inconsistent-return-statements
def test_verify_bounds_simple(mocker, start_result, end_result, find_fix):
    """Test that verify_bounds returns the expected status."""
    bisector = MockBisector(datetime.now(), datetime.now())
    bisector.find_fix = find_fix

    mocker.patch(
        "autobisect.bisect.Bisector.test_build", side_effect=[start_result, end_result]
    )
    result = bisector.verify_bounds()

    if start_result == EvaluatorResult.BUILD_FAILED:
        assert result == VerificationStatus.START_BUILD_FAILED
    elif start_result == EvaluatorResult.BUILD_CRASHED and not find_fix:
        assert result == VerificationStatus.START_BUILD_CRASHES
    elif start_result == EvaluatorResult.BUILD_PASSED and find_fix:
        assert result == VerificationStatus.FIND_FIX_START_BUILD_PASSES
    elif end_result == EvaluatorResult.BUILD_FAILED:
        assert result == VerificationStatus.END_BUILD_FAILED
    elif end_result == EvaluatorResult.BUILD_PASSED and not find_fix:
        assert VerificationStatus.END_BUILD_PASSES
    elif end_result == EvaluatorResult.BUILD_CRASHED and find_fix:
        assert VerificationStatus.FIND_FIX_END_BUILD_CRASHES
    else:
        assert result == VerificationStatus.SUCCESS


@pytest.mark.parametrize(
    "test_results",
    [[EvaluatorResult.BUILD_PASSED, None], [None, EvaluatorResult.BUILD_CRASHED]],
)
def test_verify_bounds_invalid_status(mocker, test_results):
    """
    Test that verify_bounds throw a StatusException when start build passes or end
    build crashes.
    """
    bisector = MockBisector(datetime.now(), datetime.now())
    mocker.patch("autobisect.bisect.Bisector.test_build", side_effect=test_results)
    with pytest.raises(StatusException):
        bisector.verify_bounds()


def test_build_iterator_random(mocker):
    """Test that builds are selected at random when random_choice arg is set."""
    builds = BuildRange([])
    for _ in range(1, 4):
        builds._builds.append(mocker.Mock(spec=Fetcher))
    spy = mocker.patch("autobisect.builds.random.choice", side_effect=builds)

    bisector = MockBisector(datetime.now(), datetime.now())
    generator = bisector.build_iterator(builds, True)
    try:
        next(generator)
        while True:
            generator.send(EvaluatorResult.BUILD_PASSED)
    except StopIteration:
        pass

    assert spy.call_count == 3


def test_verification_status_message():
    """Test that VerificationStatus always returns a message."""
    assert len(VerificationStatus) == 7
    for entry in VerificationStatus:
        assert isinstance(VerificationStatus[entry.name].message, str)
