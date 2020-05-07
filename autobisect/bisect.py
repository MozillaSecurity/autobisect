# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import logging
from datetime import datetime, timedelta
from enum import Enum
from string import Template

from fuzzfetch import BuildFlags, Fetcher, FetcherException

from .build_manager import BuildManager
from .builds import BuildRange

LOG = logging.getLogger("bisect")


class BisectException(Exception):
    """
    Exception raised for any Bisection error
    """


class StatusException(BisectException):
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

    URL_TEMPLATE = Template("$base/pushloghtml?fromchange=$start&tochange=$end")

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

    BUILD_CRASHED = 0
    BUILD_PASSED = 1
    BUILD_FAILED = 2

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
        self.find_fix = find_fix

        self.flags = BuildFlags(*flags)

        # If no start date is supplied, default to oldest available build
        earliest = (datetime.utcnow() - timedelta(days=364)).strftime("%Y-%m-%d")
        start_id = start if start else earliest
        end_id = end if end else "latest"

        self.start = Fetcher(
            self.target,
            self.branch,
            start_id,
            self.flags,
            platform,
            Fetcher.BUILD_ORDER_ASC,
        )
        self.end = Fetcher(
            self.target,
            self.branch,
            end_id,
            self.flags,
            platform,
            Fetcher.BUILD_ORDER_DESC,
        )

        self.build_manager = BuildManager(config)

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

        # Initially reduce use 1 build per day for the entire build range
        LOG.info("Attempting to reduce bisection range using taskcluster binaries")
        build_range = BuildRange.new(
            self.start.datetime + timedelta(days=1),
            self.end.datetime - timedelta(days=1),
        )

        while build_range:
            next_date = build_range.mid_point
            index = build_range.index(next_date)

            try:
                build = Fetcher(self.target, self.branch, next_date, self.flags)
            except FetcherException:
                LOG.warning("Unable to find build for %s", next_date)
                build_range.builds.pop(index)
            else:
                status = self.test_build(build)
                build_range = self.update_range(build, index, status, build_range)

        # Further reduce using all available builds associated with the start and end boundaries
        builds = []
        for dt in [self.start.datetime, self.end.datetime]:
            date = dt.strftime("%Y-%m-%d")
            for build in Fetcher.iterall(self.target, self.branch, date, self.flags):
                # Only keep builds after the start and before the end boundaries
                if self.end.datetime > build.datetime > self.start.datetime:
                    builds.append(build)

        build_range = BuildRange(sorted(builds, key=lambda x: x.datetime))
        while build_range:
            build = build_range.mid_point
            index = build_range.index(build)
            status = self.test_build(build)
            build_range = self.update_range(build, index, status, build_range)

        return BisectionResult(
            BisectionResult.SUCCESS, self.start, self.end, self.branch
        )

    def update_range(self, build, index, status, build_range):
        """
        Returns a new build range based on the status of the previously evaluated test
        :param build: A fuzzfetch.Fetcher object
        :param index: The index of build in build_range
        :param status: The status of the evaluated testcase
        :param build_range: The current BuildRange object
        :return: The adjusted BuildRange object
        """
        if status == self.BUILD_PASSED:
            if not self.find_fix:
                self.start = build
                return build_range[index + 1 :]

            self.end = build
            return build_range[:index]
        if status == self.BUILD_CRASHED:
            if not self.find_fix:
                self.end = build
                return build_range[:index]

            self.start = build
            return build_range[index + 1 :]
        if status == self.BUILD_FAILED:
            build_range.builds.pop(index)
            return build_range

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
        status = self.test_build(self.start)
        if status == self.BUILD_FAILED:
            return VerificationStatus.START_BUILD_FAILED
        if status == self.BUILD_CRASHED and not self.find_fix:
            return VerificationStatus.START_BUILD_CRASHES
        if status != self.BUILD_CRASHED and self.find_fix:
            return VerificationStatus.FIND_FIX_START_BUILD_PASSES

        status = self.test_build(self.end)
        if status == self.BUILD_FAILED:
            return VerificationStatus.END_BUILD_FAILED
        if status == self.BUILD_PASSED and not self.find_fix:
            return VerificationStatus.END_BUILD_PASSES
        if status == self.BUILD_CRASHED and self.find_fix:
            return VerificationStatus.FIND_FIX_END_BUILD_CRASHES

        return VerificationStatus.SUCCESS
