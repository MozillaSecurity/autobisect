# coding=utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import platform
from datetime import timedelta

from fuzzfetch import BuildFlags, Fetcher, FetcherException

from browser.evaluator import BrowserBisector
from core.build_manager import BuildManager
from core.builds import BuildRange
from core.config import BisectionConfig

log = logging.getLogger('bisect')

BUILD_CRASHED = 0
BUILD_PASSED = 1
BUILD_FAILED = 2


class Bisector(object):
    """
    Taskcluster Bisection Class
    """
    def __init__(self, args):
        self.target = args.target
        self.branch = args.branch

        self.find_fix = args.find_fix
        self.needs_verified = args.verify

        self.build_flags = BuildFlags(asan=args.asan, debug=args.debug, fuzzing=args.fuzzing, coverage=args.coverage)
        self.build_string = "m-%s-%s%s" % (self.branch[0], platform.system().lower(), self.build_flags.build_string())
        self.start = Fetcher(self.target, self.branch, args.start, self.build_flags)
        self.end = Fetcher(self.target, self.branch, args.end, self.build_flags)

        self.config = BisectionConfig(args.config)
        self.build_manager = BuildManager(self.config, self.build_string)

        if self.target == 'firefox':
            self.evaluator = BrowserBisector(args)
        else:
            self.evaluator = None

    def bisect(self):
        """
        Main bisection function
        """
        log.info('Begin bisection...')
        log.info('> Start: %s (%s)', self.start.changeset, self.start.build_id)
        log.info('> End: %s (%s)', self.end.changeset, self.end.build_id)

        if self.needs_verified and not self.verify_bounds():
            log.critical('Unable to validate boundaries.  Cannot bisect!')
            return

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

        log.info('Reduced build range to:')
        log.info('> Start: %s (%s)', self.start.changeset, self.start.build_id)
        log.info('> End: %s (%s)', self.end.changeset, self.end.build_id)
        log.info('> Pushlog: https://hg.mozilla.org/integration/autoland/pushloghtml?fromchange=%s&tochange=%s',
                 self.start.changeset, self.end.changeset)

    def update_build_range(self, build, index, status, build_range):
        """
        Returns a new build range based on the status of the previously evaluated test
        :param build: A fuzzfetch.Fetcher object
        :param index: The index of build in build_range
        :param status: The status of the evaluated testcase
        :param build_range: The current BuildRange object
        :return: The adjusted BuildRange object
        """
        if status == BUILD_PASSED:
            if not self.find_fix:
                self.start = build
                return build_range[index + 1:]
            else:
                self.end = build
                return build_range[:index]
        elif status == BUILD_CRASHED:
            if not self.find_fix:
                self.end = build
                return build_range[:index]
            else:
                self.start = build
                return build_range[index + 1:]
        elif status == BUILD_FAILED:
            build_range.builds.pop(index)
            return build_range

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
        if status == BUILD_FAILED:
            log.critical('Unable to launch the start build!')
            return False
        elif status == BUILD_CRASHED and not self.find_fix:
            log.critical('Start revision crashes!')
            return False

        status = self.test_build(self.end)
        if status == BUILD_FAILED:
            log.critical('Unable to launch the end build!')
            return False
        elif status == BUILD_PASSED and not self.find_fix:
            log.critical('End revision does not crash!')
            return False

        log.info('Verified supplied boundaries!')
        return True
