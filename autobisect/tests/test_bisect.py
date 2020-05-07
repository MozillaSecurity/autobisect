from contextlib import contextmanager
from datetime import datetime, timedelta

import pytest
import requests_mock
from freezegun import freeze_time
from fuzzfetch import BuildFlags, Fetcher, Platform

from .fetcher_callback import fetcher_mock
from .. import EvaluatorResult
from ..bisect import Bisector, get_autoland_range
from ..builds import BuildRange

MOCK_DATE = "2020-01-01"

TARGET = "firefox"
BRANCH = "central"
PLATFORM = Platform("Linux", "x86_64")
FLAGS = BuildFlags(
    asan=False, tsan=False, debug=False, fuzzing=False, coverage=False, valgrind=False,
)


@contextmanager
def init_bisector(start=None, end=None):
    """
    Wrapper for context managers needed to init Bisector
    """
    with freeze_time("2020-01-01"), requests_mock.Mocker() as req:
        # Mock all fetcher requests
        req.register_uri(requests_mock.ANY, requests_mock.ANY, content=fetcher_mock)
        yield Bisector(None, TARGET, BRANCH, start, end, FLAGS, PLATFORM)


def test_bisect_get_daily_builds_simple():
    """
    Simple test for Bisector._get_daily_builds
    """
    with init_bisector() as bisector:
        # pylint: disable=protected-access
        builds = bisector._get_daily_builds()
        assert isinstance(builds, BuildRange)  # Returns BuildRange
        assert all(isinstance(b, str) for b in builds)
        assert len(builds) == 364  # Length 365 - 1


def test_bisect_get_daily_builds_no_builds():
    """
    Test Bisector._get_daily_builds using an empty build range
    """
    with init_bisector(MOCK_DATE, MOCK_DATE) as bisector:
        # pylint: disable=protected-access
        builds = bisector._get_daily_builds()
        assert isinstance(builds, BuildRange)  # Returns BuildRange
        assert len(builds) == 0


def test_bisect_get_pushdate_builds_simple():
    """
    Simple test of Bisector._get_pushdate_builds
    """
    end = datetime.strptime(MOCK_DATE, "%Y-%m-%d")
    start = datetime.strftime(end - timedelta(days=1), "%Y-%m-%d")
    with init_bisector(start, MOCK_DATE) as bisector:
        # pylint: disable=protected-access
        builds = bisector._get_pushdate_builds()
        assert isinstance(builds, BuildRange)  # Returns BuildRange
        assert len(builds) > 1
        for build in builds:
            assert isinstance(build, Fetcher)
            assert datetime.strftime(build.datetime, "%Y-%m-%d") == start


def test_bisect_get_autoland_builds_simple():
    """
    Simple test of Bisector._get_autoland_builds
    """
    start = "03ed5ed6cba7190608c548578e9d79d82b0ccf83"
    end = "a1266665b89b04eaa8c146d0bc91b512945423cb"
    with init_bisector(start, end) as bisector:
        # pylint: disable=protected-access
        builds = bisector._get_autoland_builds()
        assert isinstance(builds, BuildRange)  # Returns BuildRange
        assert len(builds) > 1
        for build in builds:
            assert (
                build.build_info["moz_source_repo"]
                == "https://hg.mozilla.org/integration/autoland"
            )


def test_get_autoland_range_simple():
    """
    Simple test of get_autoland_range()
    """
    with requests_mock.Mocker() as req:
        # Mock all fetcher requests
        req.register_uri(requests_mock.ANY, requests_mock.ANY, content=fetcher_mock)
        start = "03ed5ed6cba7190608c548578e9d79d82b0ccf83"
        end = "a1266665b89b04eaa8c146d0bc91b512945423cb"
        changesets = get_autoland_range(start, end)
        assert len(changesets) == 28
        for changeset in changesets:
            assert isinstance(changeset, str) and len(changeset) == 40


def test_get_autoland_range_invalid_revs():
    """
    Test get_autoland_range using invalid revisions
    """
    with requests_mock.Mocker() as req:
        # Mock all fetcher requests
        req.register_uri(requests_mock.ANY, requests_mock.ANY, content=fetcher_mock)
        assert get_autoland_range("foo", "bar") is None


def test_get_autoland_range_multiple_revs():
    """
    Test that get_autoland_range returns None when multiple changsets identified
    """
    with requests_mock.Mocker() as req:
        # Mock all fetcher requests
        req.register_uri(requests_mock.ANY, requests_mock.ANY, content=fetcher_mock)
        start = "385f49adaf00d02fc8e04da1e0031e3477182d67"
        end = "590613078c743f089f01b3f43118524e9553dd0b"
        assert get_autoland_range(start, end) is None


STATUSES = [
    EvaluatorResult.BUILD_PASSED,
    EvaluatorResult.BUILD_CRASHED,
    EvaluatorResult.BUILD_FAILED,
]
BUILDS = [1, 2, 3]
FIX_OPTIONS = [True, False]


@pytest.mark.parametrize("build", BUILDS)
@pytest.mark.parametrize("status", STATUSES)
@pytest.mark.parametrize("find_fix", FIX_OPTIONS)
def test_update_range_simple(build, status, find_fix):
    """
    Simple test of Bisector.update_range
    """
    with init_bisector() as bisector:
        bisector.find_fix = find_fix
        build_range = BuildRange(BUILDS)
        bisector.update_range(status, build, build_range)
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
