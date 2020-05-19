import re
from datetime import datetime, timedelta

import pytest
import requests_mock
from freezegun import freeze_time
from fuzzfetch import BuildFlags, Platform

from .fetcher_callback import fetcher_mock
from .. import EvaluatorResult
from ..bisect import Bisector, StatusException, VerificationStatus, get_autoland_range
from ..builds import BuildRange


# pylint: disable=protected-access


class MockFetcher:
    """
    Class for mocking Fetcher objects
    """

    def __init__(self, dt=None, changeset=None):
        self.datetime = dt
        self.changeset = changeset


class MockBisector(Bisector):
    """
    Class for mocking Bisector objects
    """

    # pylint: disable=super-init-not-called
    def __init__(self, start, end):
        self.start = MockFetcher(dt=start)
        self.end = MockFetcher(dt=end)
        self.target = "firefox"
        self.branch = "central"
        self.find_fix = False
        self.flags = BuildFlags(
            asan=False,
            tsan=False,
            debug=False,
            fuzzing=False,
            coverage=False,
            valgrind=False,
        )
        self.platform = Platform("Linux", "x86_64")


def test_bisect_get_daily_builds_simple():
    """
    Simple test for Bisector._get_daily_builds
    """
    start_date = datetime.now() - timedelta(days=10 + 1)
    end_date = datetime.now()

    bisector = MockBisector(start_date, end_date)
    builds = bisector._get_daily_builds()

    assert isinstance(builds, BuildRange)  # Returns BuildRange
    assert all(re.match(r"\d{4}-\d{2}-\d{2}", b) is not None for b in builds)
    assert len(builds) == 10  # Length 365 - 1


def test_bisect_get_daily_builds_no_builds():
    """
    Test Bisector._get_daily_builds using an empty build range
    """
    start_date = datetime.now()
    bisector = MockBisector(start_date, start_date)
    builds = bisector._get_daily_builds()

    assert isinstance(builds, BuildRange)  # Returns BuildRange
    assert len(builds) == 0  # Length 365 - 1


def test_bisect_get_pushdate_builds_simple(mocker):
    """
    Simple test of Bisector._get_pushdate_builds
    """
    end_date = datetime(2020, 1, 1, 0, 0)
    start_date = end_date - timedelta(days=1)
    bisector = MockBisector(start_date, end_date)

    # Generate fake pushdates
    pushdates = []
    for dt in [start_date, end_date]:
        group = []
        end_of_day = dt.replace(hour=23, minute=59, second=59)
        delta = (end_of_day - dt) / 10
        current = dt
        while current < end_of_day:
            group.append(MockFetcher(dt=current))
            current = current + delta
        pushdates.append(group)

    mocker.patch("autobisect.bisect.Fetcher.iterall", side_effect=pushdates)
    builds = bisector._get_pushdate_builds()

    assert isinstance(builds, BuildRange)
    assert len(builds) == 9


def test_bisect_get_autoland_builds_simple():
    """
    Simple test of Bisector._get_autoland_builds
    """
    bisector = MockBisector(None, None)
    bisector.start = MockFetcher(dt=datetime(2019, 12, 30), changeset="03ed5ed6cba7")
    bisector.end = MockFetcher(dt=datetime(2019, 12, 31), changeset="a1266665b89b")

    with requests_mock.Mocker() as req:
        req.register_uri(requests_mock.ANY, requests_mock.ANY, content=fetcher_mock)
        builds = bisector._get_autoland_builds()
        repo_url = "https://hg.mozilla.org/integration/autoland"

        assert isinstance(builds, BuildRange)
        assert len(builds) > 1
        assert all(b.build_info["moz_source_repo"] == repo_url for b in builds)


def test_get_autoland_range_simple():
    """
    Simple test of get_autoland_range()
    """
    with freeze_time("2020-01-01"), requests_mock.Mocker() as req:
        req.register_uri(requests_mock.ANY, requests_mock.ANY, content=fetcher_mock)
        changesets = get_autoland_range("03ed5ed6cba7", "a1266665b89b")

        assert len(changesets) == 28
        for changeset in changesets:
            assert isinstance(changeset, str) and len(changeset) == 40


def test_get_autoland_range_invalid_revs():
    """
    Test get_autoland_range using invalid revisions
    """
    with requests_mock.Mocker() as req:
        req.register_uri(requests_mock.ANY, requests_mock.ANY, content=fetcher_mock)
        assert get_autoland_range("foo", "bar") is None


def test_get_autoland_range_multiple_revs():
    """
    Test that get_autoland_range returns None when multiple changsets identified
    """
    with requests_mock.Mocker() as req:
        req.register_uri(requests_mock.ANY, requests_mock.ANY, content=fetcher_mock)
        assert get_autoland_range("385f49adaf00", "590613078c74") is None


@pytest.mark.parametrize("status", EvaluatorResult)
@pytest.mark.parametrize("find_fix", [True, False])
def test_update_range_simple(status, find_fix):
    """
    Simple test of Bisector.update_range
    """
    builds = []
    for _ in range(10):
        next_date = datetime(2020, 1, 1, 0, 0) + timedelta(days=1)
        builds.append(MockFetcher(dt=next_date))

    for index, build in enumerate(builds):
        bisector = MockBisector(builds[0], builds[-1])
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
    """
    Verify expected verify bounds status
    """
    bisector = MockBisector(None, None)
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
        return VerificationStatus.END_BUILD_PASSES
    elif end_result == EvaluatorResult.BUILD_CRASHED and find_fix:
        return VerificationStatus.FIND_FIX_END_BUILD_CRASHES
    else:
        assert result == VerificationStatus.SUCCESS


@pytest.mark.parametrize(
    "test_results",
    [[EvaluatorResult.BUILD_PASSED, None], [None, EvaluatorResult.BUILD_CRASHED]],
)
def test_verify_bounds_invalid_status(mocker, test_results):
    """
    Verify that invalid test results throw a StatusException
    """
    bisector = MockBisector(None, None)
    mocker.patch("autobisect.bisect.Bisector.test_build", side_effect=test_results)
    with pytest.raises(StatusException):
        bisector.verify_bounds()
