# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import logging
import platform
from datetime import datetime, timedelta
from enum import Enum
from string import Template

import requests

from fuzzfetch import BuildFlags, Fetcher, FetcherException

from .build_manager import BuildManager
from .builds import BuildRange
from .config import BisectionConfig

log = logging.getLogger('bisect')


class BisectException(Exception):
    """
    Exception raised for any Bisection error
    """


class StatusException(BisectException):
    """
    Raised when an invalid status is supplied
    """
    pass


class VerificationStatus(Enum):
    SUCCESS = 0
    START_BUILD_FAILED = 1
    END_BUILD_FAILED = 2
    START_BUILD_CRASHES = 3
    END_BUILD_PASSES = 4
    FIND_FIX_START_BUILD_PASSES = 5
    FIND_FIX_END_BUILD_CRASHES = 6

    @property
    def message(self):
        if self == self.SUCCESS:
            return 'Verified supplied boundaries!'
        elif self == self.START_BUILD_FAILED:
            return 'Unable to launch the start build!'
        elif self == self.END_BUILD_FAILED:
            return 'Unable to launch the end build!'
        elif self == self.START_BUILD_CRASHES:
            return 'Start build crashes!'
        elif self == self.END_BUILD_PASSES:
            return 'End build does not crash!'
        elif self == self.START_BUILD_CRASHES:
            return 'Start build crashes!'
        elif self == self.FIND_FIX_START_BUILD_PASSES:
            return "Start build didn't crash!"
        elif self == self.FIND_FIX_END_BUILD_CRASHES:
            return 'End build crashes!'


class BisectionResult(object):
    BASE_URL = Template('https://hg.mozilla.org/mozilla-$branch/pushloghtml?fromchange=$start&tochange=$end')

    SUCCESS = 0
    FAILED = 1

    def __init__(self, status, **kwargs):
        self.status = status

        if self.status != BisectionResult.SUCCESS:
            self.message = kwargs.get('message')
        else:
            start = kwargs.get('start')
            end = kwargs.get('end')
            if isinstance(start, Fetcher) and isinstance(end, Fetcher):
                self.start = start
                self.end = end
                self.pushlog = self.BASE_URL.substitute(branch=branch, start=start.changeset, end=end.changeset)
            else:
                raise BisectionException('Bisection succeeded but invalid start or end value supplied!')


class Bisector(object):
    """
    Taskcluster Bisection Class
    """
    BUILD_CRASHED = 0
    BUILD_PASSED = 1
    BUILD_FAILED = 2

    def __init__(self, evaluator, args):
        """
        Instantiate bisection object

        :param evaluator: Evaluator instance for executing tests
        :param args:
        """
        self.evaluator = evaluator
        self.target = args.target
        self.branch = Fetcher.resolve_esr(args.branch) if args.branch.startswith('esr') else args.branch

        self.find_fix = args.find_fix

        self.build_flags = BuildFlags(asan=args.asan, debug=args.debug, fuzzing=args.fuzzing, coverage=args.coverage,
                                      valgrind=args.valgrind)
        self.build_string = 'm-%s-%s%s' % (self.branch[0], platform.system().lower(), self.build_flags.build_string())

        # If no start date is supplied, default to oldest available build
        start_id = args.start if args.start else (datetime.utcnow() - timedelta(days=364))
        end = args.end if args.end else datetime.utcnow()

        self.start = self.get_build(start_id, end)
        self.end = self.get_build(end, start_id, False)

        self.config = BisectionConfig(args.config)
        self.build_manager = BuildManager(self.config, self.build_string)

    @staticmethod
    def get_rev_date(rev):
        try:
            data = requests.get('https://hg.mozilla.org/mozilla-central/json-rev/%s' % rev)
            data.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise BisectionError(exc)
        json = data.json()
        push_date = json['pushdate'][0]
        return datetime.fromtimestamp(push_date)

    def get_build(self, start, end, asc=True):
        """
        Attempt to fetch the build and, if it fails, try to find the next available
        """
        original = start

        try:
            build_id = start.strftime('%Y-%m-%d') if isinstance(start, datetime) else start
            return Fetcher(self.target, self.branch, build_id, self.build_flags)
        except FetcherException:
            log.warn('Unable to find build for %s', build_id)

        # If the start is a datetime object, retrieval has already failed so increment the date
        # If it's not a datetime object, we assume it's a rev and we need to convert it to datetime
        if isinstance(start, datetime):
            start = start + timedelta(days=1) if asc else start - timedelta(days=1)
        else:
            start = Bisector.get_rev_date(start)

        # In order to compare the two, the end also needs to be a datetime object
        if not isinstance(end, datetime):
            end = Bisector.get_rev_date(end)

        while start < end if asc else start > end:
            try:
                return Fetcher(self.target, self.branch, start.strftime('%Y-%m-%d'), self.build_flags)
            except FetcherException:
                start = start + timedelta(days=1) if asc else start - timedelta(days=1)
                log.warn('Unable to find build for %s' % start.strftime('%Y-%m-%d'))
        else:
            raise BisectionError('Failed to find build near %s' % original)

    def bisect(self):
        """
        Main bisection function

        :return: BisectionResult
        """
        log.info('Begin bisection...')
        log.info('> Start: %s (%s)', self.start.changeset, self.start.build_id)
        log.info('> End: %s (%s)', self.end.changeset, self.end.build_id)

        verification_status = self.verify_bounds()
        if verification_status == VerificationStatus.SUCCESS:
            log.info(verification_status.message)
        else:
            log.critical(verification_status.message)
            return BisectionResult(BisectionResult.FAILED, message=verification_status.message)

        # Initially reduce use 1 build per day for the entire build range
        log.info('Attempting to reduce bisection range using taskcluster binaries')
        build_range = BuildRange.new(
            self.start.build_datetime + timedelta(days=1),
            self.end.build_datetime - timedelta(days=1))

        while build_range:
            next_date = build_range.mid_point
            i = build_range.index(next_date)

            try:
                next_build = Fetcher(self.target, self.branch, next_date, self.build_flags)
            except FetcherException:
                log.warning('Unable to find build for %s', next_date)
                build_range.builds.pop(i)
            else:
                status = self.test_build(next_build)
                build_range = self.update_build_range(next_build, i, status, build_range)

        # Further reduce using all available builds associated with the start and end boundaries
        builds = []
        for dt in [self.start.build_datetime, self.end.build_datetime]:
            for build in Fetcher.iterall(self.target, self.branch, dt.strftime('%Y-%m-%d'), self.build_flags):
                # Only keep builds after the start and before the end boundaries
                if self.end.build_datetime > build.build_datetime > self.start.build_datetime:
                    builds.append(build)

        build_range = BuildRange(sorted(builds, key=lambda x: x.build_datetime))
        while build_range:
            next_build = build_range.mid_point
            i = build_range.index(next_build)
            status = self.test_build(next_build)
            build_range = self.update_build_range(next_build, i, status, build_range)

        return BisectionResult(BisectionResult.SUCCESS, start=self.start, end=self.end, branch=self.branch)

    def update_build_range(self, build, index, status, build_range):
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
                return build_range[index + 1:]

            self.end = build
            return build_range[:index]
        elif status == self.BUILD_CRASHED:
            if not self.find_fix:
                self.end = build
                return build_range[:index]

            self.start = build
            return build_range[index + 1:]
        elif status == self.BUILD_FAILED:
            build_range.builds.pop(index)
            return build_range
        else:
            raise StatusException('Invalid status supplied')

    def test_build(self, build):
        """
        Prepare the build directory and launch the supplied build
        :param build: An Fetcher object to prevent duplicate fetching
        :return: The result of the build evaluation
        """
        log.info('Testing build %s (%s)', build.changeset, build.build_id)
        # If persistence is enabled and a build exists, use it
        with self.build_manager.get_build(build) as build_path:
            return self.evaluator.evaluate_testcase(build_path)

    def verify_bounds(self):
        """
        Verify that the supplied bounds behave as expected
        :return: Boolean
        """
        log.info('Attempting to verify boundaries...')
        status = self.test_build(self.start)
        if status == self.BUILD_FAILED:
            return VerificationStatus.START_BUILD_FAILED
        elif status == self.BUILD_CRASHED and not self.find_fix:
            return VerificationStatus.START_BUILD_CRASHES
        elif status != self.BUILD_CRASHED and self.find_fix:
            return VerificationStatus.FIND_FIX_START_BUILD_PASSES

        status = self.test_build(self.end)
        if status == self.BUILD_FAILED:
            return VerificationStatus.END_BUILD_FAILED
        elif status == self.BUILD_PASSED and not self.find_fix:
            return VerificationStatus.END_BUILD_PASSES
        elif status == self.BUILD_CRASHED and self.find_fix:
            return VerificationStatus.FIND_FIX_END_BUILD_CRASHES

        return VerificationStatus.SUCCESS
