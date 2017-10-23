#!/usr/bin/env python
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import, division, print_function

import logging
import os
import shutil
import subprocess
import time
from datetime import timedelta

from fuzzfetch import *

from core.builds import BuildRange
from util import hgCmds

DEVNULL = open(os.devnull, 'wb')
log = logging.getLogger('bisect')


class Bisector(object):
    def __init__(self, args):
        self.target = args.target
        self.repo_dir = args.repo_dir
        self.branch = hgCmds.get_branch_name(self.repo_dir)
        self.build_dir = args.build_dir
        self.build_flags = BuildFlags(asan=args.asan, debug=args.debug, fuzzing=False, coverage=False)

        self.find_fix = args.find_fix
        self.needs_verified = args.verify
        self.mach_reduce = args.mach_reduce

        self.start = Fetcher(self.target, self.branch, args.start, self.build_flags)
        self.end = Fetcher(self.target, self.branch, args.end, self.build_flags)

        self.hg_prefix = ['hg', '-R', self.repo_dir]

        self.evaluator = None
        self.build_range = None

    def bisect(self):
        """
        Main bisection function
        """
        log.info('Begin bisection...')
        log.info('> Start: %s (%s)' % (self.start.changeset, self.start.build_id))
        log.info('> End: %s (%s)' % (self.end.changeset, self.end.build_id))

        if self.needs_verified and not self.verify_bounds():
            log.critical('Unable to validate boundaries.  Cannot bisect!')
            return

        log.info('Attempting to reduce bisection range using taskcluster binaries')
        if self.reduce_range():
            log.info('Reduced build range to:')
            log.info('> Start: %s (%s)' % (self.start.changeset, self.start.build_id))
            log.info('> End: %s (%s)' % (self.end.changeset, self.end.build_id))
        else:
            log.warning('Unable to reduce bisection range using taskcluster binaries!')

        if self.mach_reduce:
            log.info('Continue bisection using mercurial...')
            log.info('Purging all local repository changes')
            subprocess.check_call(self.hg_prefix + ['purge', '--all'], stdout=DEVNULL)
            subprocess.check_call(self.hg_prefix + ['pull'], stdout=DEVNULL)
            subprocess.check_call(self.hg_prefix + ['update', '-C', 'default'], stdout=DEVNULL)

            # Clobber build directory once at start, then rely on AUTOCLOBBER
            self.clobber_build()

            # Set bisection's start and end revisions
            # Start and end revisions are flipped depending on self.find_fix
            subprocess.check_call(self.hg_prefix + ['bisect', '-r'], stdout=DEVNULL)
            good, bad = (self.end, self.start) if self.find_fix else (self.start, self.end)
            subprocess.check_call(self.hg_prefix + ['bisect', '-g', good.changeset])
            bisect_msg = subprocess.check_output(self.hg_prefix + ['bisect', '-b', bad.changeset])
            current = hgCmds.get_full_hash(self.repo_dir, hgCmds.get_bisect_changeset(bisect_msg.splitlines()[0]))

            iter_count = 0
            skip_count = 0

            while current is not None:
                iter_count += 1
                log.info('Begin round %d - %s' % (iter_count, current))
                start_time = time.time()

                try:
                    log.info('Attempting to find build for revision %s' % current)
                    target_build = Fetcher(self.target, self.branch, current, self.build_flags)
                except FetcherException:
                    log.info('Unable to find build for revision %s' % current)
                    # self.clobber_build()
                    subprocess.check_call(self.hg_prefix + ['update', '-r', current], stdout=DEVNULL)
                    result = self.evaluator.test_compilation()
                else:
                    result = self.test_build(target_build)

                if result == 'skip':
                    skip_count += 1
                    # If we use 'skip', we tell hg bisect to do a linear search to get around the skipping.
                    # If the range is large, doing a bisect to find the start and endpoints of compilation
                    # bustage would be faster. 20 total skips being roughly the time that the pair of
                    # bisections would take.
                    if skip_count > 20:
                        log.error('Reached maximum skip attempts! Exiting')
                        summary = subprocess.check_output(
                            self.hg_prefix + ['log', '-r', '"bisect(good) or bisect(bad)"', '--template',
                                              '"Changeset: {rev}, Revision: {node|short} - {bisect}'])
                        log.info('Summary of bisection:\n%s', summary)
                        break

                current = self.update_hg(result, current)

                end_time = time.time()
                elapsed = timedelta(seconds=(int(end_time-start_time)))
                log.info('Round {0} completed in {1}'.format(iter_count, elapsed))
                hgCmds.destroy_pyc(self.repo_dir)

    def reduce_range(self):
        """
        Reduce bisection range using taskcluster builds
        :return: Boolean to identify whether the build range was successfully reduced
        """
        orig_start = self.start.build_date
        orig_end = self.end.build_date

        # Reduce using one build per day
        build_range = BuildRange.new(self.start.build_date + timedelta(days=1), self.end.build_date - timedelta(days=1))
        while len(build_range) > 0:
            next_date = build_range.mid_point
            i = build_range.index(next_date)

            try:
                next_build = Fetcher(self.target, self.branch, next_date, self.build_flags)
            except FetcherException:
                log.warning('Unable to find build for %s' % next_date)
                build_range.builds.pop(i)
            else:
                log.info('Testing build %s' % next_build.build_id)
                status = self.test_build(next_build)
                build_range = self.update_build_range(next_build, i, status, build_range)

        # Further reduce using all available builds for start and end dates
        start_date = self.start.build_date.strftime('%Y-%m-%d')
        builds = list(Fetcher.iterall(self.target, self.branch, start_date, self.build_flags))
        end_date = self.start.build_date.strftime('%Y-%m-%d')
        builds.extend(list(Fetcher.iterall(self.target, self.branch, end_date, self.build_flags)))

        # Sort by date
        build_range.builds.sort(key=lambda x: x.build_date)

        # Remove start and end builds as they've already been tested
        for build in [self.start, self.end]:
            builds = filter(lambda x: x.build_id != build.build_id, builds)

        build_range = BuildRange(builds)
        while len(build_range) > 0:
            next_build = build_range.mid_point
            i = build_range.index(next_build)

            log.info('Testing build %s' % next_build.build_id)
            status = self.test_build(next_build)
            build_range = self.update_build_range(next_build, i, status, build_range)

        # Was reduction successful?
        if orig_start < self.start.build_date:
            return True
        if orig_end > self.end.build_date:
            return True

        return False

    def update_build_range(self, build, index, status, build_range):
        if status == 'good':
            if not self.find_fix:
                self.start = build
                return build_range[index + 1:]
            else:
                self.end = build
                return build_range[:index]
        elif status == 'bad':
            if not self.find_fix:
                self.end = build
                return build_range[:index]
            else:
                self.start = build
                return build_range[index + 1:]
        elif status == 'skip':
            build_range.builds.pop(index)
            return build_range

    def clobber_build(self):
        """
        Delete the build directory and recreate it
        """
        if os.path.exists(self.build_dir):
            log.debug('Clobbering build dir:  %s' % self.build_dir)
            shutil.rmtree(self.build_dir)
            os.makedirs(self.build_dir)

    def test_build(self, build):
        """
        Prepare the build directory and launch the supplied build
        :param build: The build to test
        :type: Fetcher
        :return: The result of the build evaluation
        """
        self.clobber_build()
        build.extract_build(self.build_dir)
        return self.evaluator.evaluate_testcase()

    def verify_bounds(self):
        """
        Verify that the supplied bounds behave as expected
        :return: Boolean
        """
        log.info('Attempting to verify boundaries...')
        status = self.test_build(self.start)
        if status == 'skip':
            log.critical('Unable to launch the start build!')
        elif status == 'bad' and not self.find_fix:
            log.critical('Start revision crashes!')
            return False

        status = self.test_build(self.end)
        if status == 'skip':
            log.critical('Unable to launch the end build!')
        elif status == 'good' and not self.find_fix:
            log.critical('End revision does not crash!')
            return False

        log.info('Verified supplied boundaries!')
        return True

    def update_hg(self, label, current):
        """
        Informs mercurial of bisection result
        :param label: The result of the bisection test
        :param current: The revision to be marked
        :return: The next revision or None
        """
        assert label in ('good', 'bad', 'skip')
        log.info('Marking revision {0} as {1}'.format(current, label))
        results = subprocess.check_output(self.hg_prefix + ['bisect', '--' + label, current])

        # Determine if we should continue
        # e.g. "Testing changeset 52121:573c5fa45cc4 (440 changesets remaining, ~8 tests)"
        bisect_msg = results.splitlines()[0]
        revision = hgCmds.get_bisect_changeset(bisect_msg)
        if revision:
            return hgCmds.get_full_hash(self.repo_dir, revision)

        # Otherwise, return results
        log.info(results)
        return None
