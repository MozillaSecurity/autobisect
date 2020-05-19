# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import logging
from datetime import datetime, timedelta
from enum import Enum

import requests
from fuzzfetch import BuildFlags, Fetcher, FetcherException

from .build_manager import BuildManager
from .builds import BuildRange
from .evaluators import EvaluatorResult

LOG = logging.getLogger("bisect")


def get_autoland_range(start, end):
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
    key_len = len(json.keys())
    if key_len == 1:
        push_id = list(json.keys())[0]
        return json[push_id]["changesets"]

    LOG.warning(f"Detected {key_len} top-level changes.  Cannot bisect into autoland.")
    return None


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
    def message(self):
        """
        Return message matching explaining current status
        """
        result = None
        if self == self.SUCCESS:
            result = "Verified supplied boundaries!"
        elif self == self.START_BUILD_FAILED:
            result = "Unable to launch the start build!"
        elif self == self.END_BUILD_FAILED:
            result = "Unable to launch the end build!"
        elif self == self.START_BUILD_CRASHES:
            result = "Start build crashes!"
        elif self == self.END_BUILD_PASSES:
            result = "End build does not crash!"
        elif self == self.START_BUILD_CRASHES:
            result = "Start build crashes!"
        elif self == self.FIND_FIX_START_BUILD_PASSES:
            result = "Start build didn't crash!"
        elif self == self.FIND_FIX_END_BUILD_CRASHES:
            result = "End build crashes!"

        return result


class BisectionResult(object):
    """
    Class for storing bisection result
    """

    SUCCESS = 0
    FAILED = 1

    def __init__(self, status, start, end, branch, message=None):
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
        evaluator,
        target,
        branch,
        start,
        end,
        flags,
        platform,
        find_fix=False,
        config=None,
    ):
        """
        Instantiate bisection object
        :param evaluator: Object instance used to evaluate testcase
        :param target: Type of builds to fetch
        :param branch: Mozilla branch to use for finding builds
        :param start: Start revision, date, or buildid
        :param end: End revision, date, or buildid
        :param flags: Build flags (asan, tsan, debug, fuzzing, valgrind)
        :param platform: fuzzfetch.fetch.Platform instance
        :param find_fix: Boolean identifying whether to find a fix or bisect bug
        :param config: Path to config file
        """
        self.evaluator = evaluator
        self.target = target
        self.branch = (
            Fetcher.resolve_esr(branch) if branch.startswith("esr") else branch
        )
        self.platform = platform
        self.flags = BuildFlags(*flags)
        self.find_fix = find_fix

        # If no start date is supplied, default to oldest available build
        earliest = (datetime.utcnow() - timedelta(days=364)).strftime("%Y-%m-%d")
        start_id = start if start else earliest
        end_id = end if end else "latest"

        self.start = Fetcher(
            self.target,
            self.branch,
            start_id,
            self.flags,
            self.platform,
            Fetcher.BUILD_ORDER_ASC,
        )
        self.end = Fetcher(
            self.target,
            self.branch,
            end_id,
            self.flags,
            self.platform,
            Fetcher.BUILD_ORDER_DESC,
        )

        self.build_manager = BuildManager(config)

    def _get_daily_builds(self):
        """
        Create build range containing one build per day
        """
        start = self.start.datetime + timedelta(days=1)
        end = self.end.datetime - timedelta(days=1)
        LOG.info(f"Enumerating daily builds: {start} - {end}")

        return BuildRange.new(start, end)

    def _get_pushdate_builds(self):
        """
        Create build range containing all builds per pushdate
        """
        start = self.start.datetime
        end = self.end.datetime
        LOG.info(f"Enumerating pushdate builds: {start} - {end}")

        builds = []
        for dt in [start, end]:
            date = dt.strftime("%Y-%m-%d")
            for build in Fetcher.iterall(self.target, self.branch, date, self.flags):
                # Only keep builds after the start and before the end boundaries
                if self.end.datetime > build.datetime > self.start.datetime:
                    builds.append(build)

        return BuildRange(builds)

    def _get_autoland_builds(self):
        """
        Create build range containing all autoland builds per pushdate
        """
        if self.branch != "central":
            return []

        start = self.start.datetime
        end = self.end.datetime

        LOG.info(f"Enumerating autoland builds: {start} - {end}")
        changesets = get_autoland_range(self.start.changeset, self.end.changeset)
        if changesets is None:
            return []

        builds = []
        for changeset in changesets:
            try:
                build = Fetcher(
                    self.target, "autoland", changeset, self.flags, self.platform
                )
                builds.append(build)
            except FetcherException:
                LOG.warning("Unable to find build for %s", changeset)

        return BuildRange(builds)

    def build_iterator(self, build_range):
        """
        Yields next build to be evaluated until all possibilities consumed
        """
        while build_range:
            build = build_range.mid_point
            index = build_range.index(build)
            if not isinstance(build, Fetcher):
                try:
                    build = Fetcher(
                        self.target, self.branch, build, self.flags, self.platform
                    )
                except FetcherException:
                    LOG.warning("Unable to find build for %s", build)
                    build_range.builds.remove(build)
                    continue

            status = yield build
            build_range = self.update_range(status, build, index, build_range)

        yield None

    def bisect(self):
        """
        Main bisection function

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
        strategies = [
            self._get_daily_builds,
            self._get_pushdate_builds,
            self._get_autoland_builds,
        ]
        for strategy in strategies:
            build_range = strategy()
            generator = self.build_iterator(build_range)
            next_build = next(generator)
            while next_build is not None:
                status = self.test_build(next_build)
                next_build = generator.send(status)

        return BisectionResult(
            BisectionResult.SUCCESS, self.start, self.end, self.branch
        )

    def update_range(self, status, build, index, build_range):
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

    def test_build(self, build):
        """
        Prepare the build directory and launch the supplied build
        :param build: An Fetcher object to prevent duplicate fetching
        :return: The result of the build evaluation
        """
        LOG.info("Testing build %s (%s)", build.changeset, build.id)
        # If persistence is enabled and a build exists, use it
        with self.build_manager.get_build(build) as build_path:
            return self.evaluator.evaluate_testcase(build_path)

    def verify_bounds(self):
        """
        Verify that the supplied bounds behave as expected
        :return: Boolean
        """
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
