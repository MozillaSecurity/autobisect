# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# pylint: disable=protected-access
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fuzzfetch import BuildFlags, Fetcher, Platform

from autobisect import EvaluatorResult, BrowserEvaluator
from autobisect.bisect import (
    Bisector,
    StatusException,
    VerificationStatus,
    get_autoland_range,
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


@pytest.mark.freeze_time("2024-05-30")
@pytest.mark.vcr()
def test_bisect_get_pushdate_builds_simple():
    """Test that get_daily_builds returns the expected build range."""
    start_date = datetime.now(tz=timezone.utc) - timedelta(days=1)
    end_date = datetime.now(tz=timezone.utc)
    bisector = MockBisector(start_date, end_date)

    builds = bisector._get_pushdate_builds()

    assert len(builds) == 3
    assert isinstance(builds, BuildRange)
    for build in builds:
        assert isinstance(build, Fetcher)


@pytest.mark.freeze_time("2024-05-30")
@pytest.mark.vcr()
@pytest.mark.skip(reason="Cassette is too large")
def test_bisect_get_autoland_builds_simple(browser_evaluator, opt_flags, platform):
    """Test that get_autoland_builds returns the expected build range."""
    start = "abdb14987e23f88107f437b130d0817eea873199"
    end = "b05a24f158503b7ea175520ef383fa005a4c41b7"
    bisector = Bisector(
        browser_evaluator,
        "central",
        start,
        end,
        opt_flags,
        platform,
    )
    builds = bisector._get_autoland_builds()
    repo_url = "https://hg.mozilla.org/integration/autoland"

    assert isinstance(builds, BuildRange)
    assert len(builds) == 10
    assert all(b.build_info["moz_source_repo"] == repo_url for b in builds)


@pytest.mark.vcr()
def test_get_autoland_range_simple():
    """Test that get_autoland_range returns a list of changesets."""
    start = "abdb14987e23f88107f437b130d0817eea873199"
    end = "b05a24f158503b7ea175520ef383fa005a4c41b7"
    changesets = get_autoland_range(start, end)

    assert isinstance(changesets, list)
    assert len(changesets) == 35
    assert all(isinstance(c, str) and len(c) == 40 for c in changesets)


@pytest.mark.vcr()
def test_get_autoland_range_invalid_revs():
    """Test that get_autoland_range returns None when using invalid revisions."""
    assert get_autoland_range("foo", "bar") is None


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
