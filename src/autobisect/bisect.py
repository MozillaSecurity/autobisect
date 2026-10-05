# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import logging
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Generator, List, Optional, TypeVar, Union

import requests
from fuzzfetch import (
    BuildFlags,
    BuildSearchOrder,
    BuildTask,
    Fetcher,
    FetcherException,
    Platform,
    Product,
)

from .build_manager import BuildManager, BuildManagerException
from .builds import BuildRange
from .evaluators import Evaluator, EvaluatorResult

T = TypeVar("T", str, Fetcher)

LOG = logging.getLogger(__name__)


def get_autoland_range(start: str, end: str) -> Union[List[str], None]:
    """
    Retrieve the first-parent Autoland path between two revisions.

    :param start: Starting revision.
    :param end: Ending revision.
    :return: List of changesets.
    """
    url = (
        "https://hg.mozilla.org/integration/autoland/json-pushes"
        f"?fromchange={start}&tochange={end}&full=1"
    )
    try:
        data = requests.get(url, timeout=30)
        data.raise_for_status()
    except requests.exceptions.RequestException as exc:
        LOG.error("Failed to retrieve autoland changeset %s", exc)
        return None

    try:
        changesets = {
            changeset["node"]: changeset
            for push in data.json().values()
            for changeset in push["changesets"]
        }
        path = []
        current = end
        while current != start:
            revision = changesets[current]
            path.append(current)
            current = revision["parents"][0]
    except (ValueError, KeyError, IndexError, TypeError):
        return None

    path.reverse()
    return path


def get_merge_second_parent(changeset: str) -> Optional[str]:
    """Find the second parent of a central merge.

    :param changeset: Central merge revision.
    :return: Second parent, or None if the revision is not a merge.
    """
    url = f"https://hg.mozilla.org/mozilla-central/json-rev/{changeset}"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        LOG.warning("Failed to inspect central merge %s: %s", changeset, exc)
        return None

    try:
        parents = response.json()["parents"]
    except (ValueError, KeyError, TypeError):
        LOG.warning("Invalid central revision metadata for %s", changeset)
        return None

    if isinstance(parents, list) and len(parents) == 2 and isinstance(parents[1], str):
        return parents[1]
    return None


class StatusException(Exception):
    """Raised when an invalid status is supplied."""


class VerificationStatus(Enum):
    """Class for storing build verification result."""

    SUCCESS = 0
    START_BUILD_FAILED = 1
    END_BUILD_FAILED = 2
    START_BUILD_CRASHES = 3
    END_BUILD_PASSES = 4
    FIND_FIX_START_BUILD_PASSES = 5
    FIND_FIX_END_BUILD_CRASHES = 6

    @property
    def message(self) -> Optional[str]:
        """Return message matching explaining current status."""
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
    """Class for storing bisection result."""

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
        self.message = message
        if status == BisectionResult.SUCCESS:
            base = start.build_info["moz_source_repo"]
            if base != end.build_info["moz_source_repo"]:
                self.status = BisectionResult.FAILED
                self.message = "Bisection bounds belong to different repositories"
                return

            self.pushlog = (
                f"{base}/pushloghtml?fromchange="
                f"{start.changeset}&tochange={end.changeset}"
            )


class Bisector(object):
    """Taskcluster Bisection Class."""

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
        Instantiate bisection object.

        :param evaluator: Object instance used to evaluate testcase.
        :param branch: Mozilla branch to use for finding builds.
        :param start: Start revision, date, or buildid.
        :param end: End revision, date, or buildid.
        :param flags: Build flags (asan, tsan, debug, fuzzing, valgrind).
        :param platform: fuzzfetch.fetch.Platform instance.
        :param find_fix: Boolean identifying whether to find a fix or bisect bug.
        :param config: Path to config file.
        """
        self.evaluator: Evaluator = evaluator
        self.branch = branch
        self.platform: Platform = platform
        self.flags = flags
        self.find_fix = find_fix

        # If no start date is supplied, default to the oldest available build
        max_days = 364 if evaluator.target == "firefox" else 89
        earliest = (datetime.utcnow() - timedelta(days=max_days)).strftime("%Y-%m-%d")

        start_id = start if start else earliest
        end_id = end if end else "latest"

        self.start = Fetcher(
            self.branch,
            start_id,
            self.flags,
            targets=[self.evaluator.target],
            platform=self.platform,
            nearest=BuildSearchOrder.ASC,
        )
        self.end = Fetcher(
            self.branch,
            end_id,
            self.flags,
            targets=[self.evaluator.target],
            platform=self.platform,
            nearest=BuildSearchOrder.DESC,
        )

        self.build_manager = BuildManager(config)

    def _get_daily_builds(self) -> BuildRange[str]:
        """Create build range containing one build per day."""
        start = self.start.datetime + timedelta(days=1)
        end = self.end.datetime - timedelta(days=1)
        LOG.info(f"Enumerating daily builds: {start} - {end}")

        return BuildRange.new(start, end)

    def _get_pushdate_builds(self) -> BuildRange[Fetcher]:
        """Create build range containing all builds per pushdate."""
        start = self.start.datetime
        end = self.end.datetime
        LOG.info(f"Enumerating pushdate builds: {start} - {end}")

        builds = []
        for dt in [start, end]:
            date = dt.strftime("%Y-%m-%d")
            for task in BuildTask.iterall(
                date, self.branch, self.flags, Product("firefox"), self.platform
            ):
                # Ignore "latest" as these are aliases for the most recent build
                if hasattr(task, "url") and ".latest." in str(task.url):
                    continue

                # Only keep builds after the start and before the end boundaries
                build = Fetcher(
                    self.branch,
                    task,
                    self.flags,
                    targets=[self.evaluator.target],
                    platform=self.platform,
                )
                if self.end.datetime > build.datetime > self.start.datetime:
                    if build.changeset not in (
                        self.start.changeset,
                        self.end.changeset,
                    ):
                        builds.append(build)

        return BuildRange(builds)

    def _get_autoland_builds(self, start: str, end: str) -> BuildRange[Fetcher]:
        """Find available builds on the Autoland first-parent path.

        :param start: Verified Autoland start revision.
        :param end: Autoland revision at the other central boundary.
        :return: Available builds in ancestry order.
        """
        LOG.info("Enumerating autoland builds: %s - %s", start, end)
        changesets = get_autoland_range(start, end)
        if changesets is None:
            return BuildRange([])

        builds = []
        for changeset in changesets:
            try:
                build = Fetcher(
                    "autoland",
                    changeset,
                    self.flags,
                    targets=[self.evaluator.target],
                    platform=self.platform,
                )
                builds.append(build)
            except FetcherException:
                LOG.warning("Unable to find build for %s", changeset)

        return BuildRange(builds)

    def _bisect_autoland(self, random_choice: bool) -> None:
        """Verify Autoland bounds before bisecting that branch.

        :param random_choice: Select random builds instead of midpoints.
        """
        start_parent = get_merge_second_parent(self.start.changeset)
        end_parent = get_merge_second_parent(self.end.changeset)
        if start_parent is None or end_parent is None:
            return

        try:
            autoland_start = Fetcher(
                "autoland",
                start_parent,
                self.flags,
                targets=[self.evaluator.target],
                platform=self.platform,
            )
        except FetcherException:
            return

        expected_start = (
            EvaluatorResult.BUILD_CRASHED
            if self.find_fix
            else EvaluatorResult.BUILD_PASSED
        )
        expected_end = (
            EvaluatorResult.BUILD_PASSED
            if self.find_fix
            else EvaluatorResult.BUILD_CRASHED
        )
        if self.test_build(autoland_start) != expected_start:
            return

        builds = self._get_autoland_builds(start_parent, end_parent)
        while builds:
            autoland_end = builds.builds.pop()
            result = self.test_build(autoland_end)
            if result == EvaluatorResult.BUILD_FAILED:
                continue
            if result != expected_end:
                return

            self.start, self.end = autoland_start, autoland_end
            self._bisect_build_range(builds, random_choice)
            return

    def build_iterator(
        self,
        build_range: BuildRange[T],
        random_choice: bool,
    ) -> Generator[Fetcher, EvaluatorResult, None]:
        """Yields next build to be evaluated until all possibilities consumed."""
        while build_range:
            item = build_range.random if random_choice else build_range.mid_point

            assert item is not None
            index = build_range.index(item)
            build: Fetcher
            if isinstance(item, Fetcher):
                build = item
            else:
                try:
                    build = Fetcher(
                        self.branch,
                        item,
                        self.flags,
                        targets=[self.evaluator.target],
                        platform=self.platform,
                    )
                except FetcherException:
                    LOG.warning("Unable to find build for %s", item)
                    build_range.builds.remove(item)
                    continue

            status = yield build

            assert isinstance(index, int)
            build_range = self.update_range(status, build, index, build_range)

    def _bisect_build_range(
        self, build_range: BuildRange[T], random_choice: bool
    ) -> None:
        """Evaluate and narrow a range of candidate dates or builds.

        :param build_range: Candidate dates or builds.
        :param random_choice: Select random candidates instead of midpoints.
        """
        generator = self.build_iterator(build_range, random_choice)
        try:
            next_build = next(generator)
            while True:
                status = self.test_build(next_build)
                next_build = generator.send(status)
        except StopIteration:
            pass

    def bisect(self, random_choice: bool = False) -> BisectionResult:
        """
        Main bisection function.

        :param random_choice: Select builds at random during bisection (QuickSort).
        :returns: Bisection result.
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
        self._bisect_build_range(self._get_daily_builds(), random_choice)
        self._bisect_build_range(self._get_pushdate_builds(), random_choice)

        if self.branch == "central":
            self._bisect_autoland(random_choice)

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
        Returns a new build range based on the status of the previously evaluated test.

        :param status: The status of the evaluated testcase.
        :param build: The evaluated build.
        :param index: Index of the build.
        :param build_range: The build_range to update.
        :returns: New build range.
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
        Prepare the build directory and launch the supplied build.

        :param build: A Fetcher object to prevent duplicate fetching
        :return: The result of the build evaluation
        """
        LOG.info("Testing build %s (%s)", build.changeset, build.id)
        # If persistence is enabled and a build exists, use it
        try:
            with self.build_manager.get_build(build, self.evaluator.target) as path:
                return self.evaluator.evaluate_testcase(path)
        except BuildManagerException:
            return EvaluatorResult.BUILD_FAILED

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
