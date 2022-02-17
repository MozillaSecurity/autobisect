# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import logging
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Generator, Optional, List, Union, TypeVar, Callable

import requests
from fuzzfetch import (
    BuildFlags,
    BuildSearchOrder,
    BuildTask,
    Fetcher,
    FetcherException,
    Platform,
)

from .build_manager import BuildManager
from .builds import BuildRange
from .evaluators import Evaluator, EvaluatorResult

T = TypeVar("T")

LOG = logging.getLogger("bisect")


def get_autoland_range(start: str, end: str) -> Union[List[str], None]:
    """
    Retrieve changeset from autoland within supplied boundary

    :param start: Starting revision
    :param end: Ending revision
    """
    url = (
        "https://hg.mozilla.org/mozilla-central/json-pushes"
        f"?fromchange={start}&tochange={end}"
    )
    try:
        data = requests.get(url)
        data.raise_for_status()
    except requests.exceptions.RequestException as exc:
        LOG.error("Failed to retrieve autoland changeset %s", exc)
        return None

    json = data.json()

    changesets = []
    for push_id in json.keys():
        changesets.extend(json[push_id]["changesets"])

    return changesets


class StatusException(Exception):
    """
    Raised when an invalid status is supplied
    """


class VerificationStatus(Enum):
    """
    Class for storing build verification result
    """

    SUCCESS = 0
    START_BUILD_FAILED = 1
    END_BUILD_FAILED = 2
    START_BUILD_CRASHES = 3
    END_BUILD_PASSES = 4
    FIND_FIX_START_BUILD_PASSES = 5
    FIND_FIX_END_BUILD_CRASHES = 6

    @property
    def message(self) -> Optional[str]:
        """
        Return message matching explaining current status
        """
        result = None
        if self == VerificationStatus.SUCCESS:
            result = "Verified supplied boundaries!"
        elif self == VerificationStatus.START_BUILD_FAILED:
            result = "Unable to launch the start build!"
        elif self == VerificationStatus.END_BUILD_FAILED:
            result = "Unable to launch the end build!"
        elif self == VerificationStatus.START_BUILD_CRASHES:
            result = "Testcase reproduces on start build!"
        elif self == VerificationStatus.END_BUILD_PASSES:
            result = "Testcase does not reproduce on end build!"
        elif self == VerificationStatus.FIND_FIX_START_BUILD_PASSES:
            result = "Start build didn't crash!"
        elif self == VerificationStatus.FIND_FIX_END_BUILD_CRASHES:
            result = "End build crashes!"

        return result


class BisectionResult(object):
    """
    Class for storing bisection result
    """

    SUCCESS = 0
    FAILED = 1

    def __init__(
        self,
        status: int,
        start: Fetcher,
        end: Fetcher,
        branch: str,
        message: Optional[str] = None,
    ):
        self.status = status
        self.start = start
        self.end = end
        self.branch = branch
        if status == BisectionResult.SUCCESS:
            if start.build_info["moz_source_repo"] == end.build_info["moz_source_repo"]:
                base = start.build_info["moz_source_repo"]
            else:
                base = "https://hg.mozilla.org/mozilla-unified"

            self.pushlog = (
                f"{base}/pushloghtml?fromchange="
                f"{start.changeset}&tochange={end.changeset}"
            )

        self.message = message


class Bisector(object):
    """
    Taskcluster Bisection Class
    """

    def __init__(
        self,
        evaluator: Evaluator,
        branch: str,
        start: Union[str, None],
        end: Union[str, None],
        flags: BuildFlags,
        platform: Platform,
        find_fix: bool = False,
        config: Optional[Path] = None,
    ):
        """
        Instantiate bisection object
        :param evaluator: Object instance used to evaluate testcase
        :param branch: Mozilla branch to use for finding builds
        :param start: Start revision, date, or buildid
        :param end: End revision, date, or buildid
        :param flags: Build flags (asan, tsan, debug, fuzzing, valgrind)
        :param platform: fuzzfetch.fetch.Platform instance
        :param find_fix: Boolean identifying whether to find a fix or bisect bug
        :param config: Path to config file
        """
        self.evaluator: Evaluator = evaluator
        self.branch = branch
        self.platform: Platform = platform
        self.flags = flags
        self.find_fix = find_fix

        # If no start date is supplied, default to oldest available build
        earliest = (datetime.utcnow() - timedelta(days=364)).strftime("%Y-%m-%d")
        start_id = start if start else earliest
        end_id = end if end else "latest"

        self.start = Fetcher(
            self.branch,
            start_id,
            self.flags,
            self.platform,
            BuildSearchOrder.ASC,
        )
        self.end = Fetcher(
            self.branch,
            end_id,
            self.flags,
            self.platform,
            BuildSearchOrder.DESC,
        )

        self.build_manager = BuildManager(config)

    def _get_daily_builds(self) -> BuildRange[str]:
        """
        Create build range containing one build per day
        """
        start = self.start.datetime + timedelta(days=1)
        end = self.end.datetime - timedelta(days=1)
        LOG.info(f"Enumerating daily builds: {start} - {end}")

        return BuildRange.new(start, end)

    def _get_pushdate_builds(self) -> BuildRange[Fetcher]:
        """
        Create build range containing all builds per pushdate
        """
        start = self.start.datetime
        end = self.end.datetime
        LOG.info(f"Enumerating pushdate builds: {start} - {end}")

        builds = []
        for dt in [start, end]:
            date = dt.strftime("%Y-%m-%d")
            for task in BuildTask.iterall(date, self.branch, self.flags, self.platform):
                # Only keep builds after the start and before the end boundaries
                build = Fetcher(self.branch, task, self.flags, self.platform)
                if self.end.datetime > build.datetime > self.start.datetime:
                    builds.append(build)

        return BuildRange(builds)

    def _get_autoland_builds(self) -> BuildRange[Fetcher]:
        """
        Create build range containing all autoland builds per pushdate
        """
        if self.branch != "central":
            return BuildRange([])

        start = self.start.datetime
        end = self.end.datetime

        LOG.info(f"Enumerating autoland builds: {start} - {end}")
        changesets = get_autoland_range(self.start.changeset, self.end.changeset)
        if changesets is None:
            return BuildRange([])

        builds = []
        for changeset in changesets:
            try:
                build = Fetcher("autoland", changeset, self.flags, self.platform)
                builds.append(build)
            except FetcherException:
                LOG.warning("Unable to find build for %s", changeset)

        return BuildRange(builds)

    def build_iterator(
        self, build_range: BuildRange[Union[str, Fetcher]], random_choice: bool
    ) -> Generator[Fetcher, EvaluatorResult, None]:
        """
        Yields next build to be evaluated until all possibilities consumed
        """
        while build_range:
            if random_choice:
                build = build_range.random
            else:
                build = build_range.mid_point

            assert build is not None
            index = build_range.index(build)
            if not isinstance(build, Fetcher):
                try:
                    build = Fetcher(self.branch, build, self.flags, self.platform)
                except FetcherException:
                    LOG.warning("Unable to find build for %s", build)
                    build_range.builds.remove(build)
                    continue

            status = yield build

            assert isinstance(index, int)
            build_range = self.update_range(status, build, index, build_range)

    def bisect(self, random_choice: bool = False) -> BisectionResult:
        """
        Main bisection function

        :param random_choice: Select builds at random during bisection (QuickSort)

        :return: BisectionResult
        """
        LOG.info("Begin bisection...")
        LOG.info("> Start: %s (%s)", self.start.changeset, self.start.id)
        LOG.info("> End: %s (%s)", self.end.changeset, self.end.id)

        verified = self.verify_bounds()
        if verified == VerificationStatus.SUCCESS:
            LOG.info(verified.message)
        else:
            LOG.critical(verified.message)
            return BisectionResult(
                BisectionResult.FAILED,
                self.start,
                self.end,
                self.branch,
                verified.message,
            )

        LOG.info("Attempting to reduce bisection range using taskcluster binaries")
        strategies: List[Callable[[], Union[BuildRange[str], BuildRange[Fetcher]]]] = [
            self._get_daily_builds,
            self._get_pushdate_builds,
            self._get_autoland_builds,
        ]
        for strategy in strategies:
            build_range = strategy()
            generator = self.build_iterator(build_range, random_choice)  # type: ignore
            try:
                next_build = next(generator)
                while True:
                    status = self.test_build(next_build)
                    next_build = generator.send(status)
            except StopIteration:
                pass

        return BisectionResult(
            BisectionResult.SUCCESS, self.start, self.end, self.branch
        )

    def update_range(
        self,
        status: EvaluatorResult,
        build: Fetcher,
        index: int,
        build_range: BuildRange[T],
    ) -> BuildRange[T]:
        """
        Returns a new build range based on the status of the previously evaluated test

        :param status: The status of the evaluated testcase
        :param build: The evaluated build
        :param index: Index of the build
        :param build_range: The build_range to update
        :return: The adjusted BuildRange object
        """
        if status == EvaluatorResult.BUILD_PASSED:
            if not self.find_fix:
                self.start = build
                return build_range[index + 1 :]

            self.end = build
            return build_range[:index]
        if status == EvaluatorResult.BUILD_CRASHED:
            if not self.find_fix:
                self.end = build
                return build_range[:index]

            self.start = build
            return build_range[index + 1 :]
        if status == EvaluatorResult.BUILD_FAILED:
            range_copy = build_range[:]
            range_copy.builds.pop(index)
            return range_copy

        raise StatusException("Invalid status supplied")

    def test_build(self, build: Fetcher) -> EvaluatorResult:
        """
        Prepare the build directory and launch the supplied build
        :param build: An Fetcher object to prevent duplicate fetching
        :return: The result of the build evaluation
        """
        LOG.info("Testing build %s (%s)", build.changeset, build.id)
        # If persistence is enabled and a build exists, use it
        with self.build_manager.get_build(build, self.evaluator.target) as build_path:
            return self.evaluator.evaluate_testcase(build_path)

    def verify_bounds(self) -> VerificationStatus:
        """Verify that the supplied bounds behave as expected"""
        LOG.info("Attempting to verify boundaries...")
        start_result = self.test_build(self.start)
        if start_result not in set(EvaluatorResult):
            raise StatusException("Invalid status supplied")

        if start_result == EvaluatorResult.BUILD_FAILED:
            return VerificationStatus.START_BUILD_FAILED
        if start_result == EvaluatorResult.BUILD_CRASHED and not self.find_fix:
            return VerificationStatus.START_BUILD_CRASHES
        if start_result == EvaluatorResult.BUILD_PASSED and self.find_fix:
            return VerificationStatus.FIND_FIX_START_BUILD_PASSES

        end_result = self.test_build(self.end)
        if end_result not in set(EvaluatorResult):
            raise StatusException("Invalid status supplied")

        if end_result == EvaluatorResult.BUILD_FAILED:
            return VerificationStatus.END_BUILD_FAILED
        if end_result == EvaluatorResult.BUILD_PASSED and not self.find_fix:
            return VerificationStatus.END_BUILD_PASSES
        if end_result == EvaluatorResult.BUILD_CRASHED and self.find_fix:
            return VerificationStatus.FIND_FIX_END_BUILD_CRASHES

        return VerificationStatus.SUCCESS
