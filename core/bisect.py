#!/usr/bin/env python
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import, division, print_function

import datetime
import logging
import subprocess
import time
import shutil

try:
    # subprocess v3.5
    from subprocess import DEVNULL
except ImportError:
    import os
    DEVNULL = open(os.devnull, 'wb')

from util import hgCmds
from core.builds import BuildRange
from core.builds import Build
from core.boundary import Boundary

log = logging.getLogger('bisect')


class Bisector(object):
    def __init__(self, args):
        self.target = args.target
        self.repo_dir = args.repo_dir
        self.build_dir = args.build_dir
        self.start = Boundary.new(args.start, self.repo_dir)
        self.end = Boundary.new(args.end, self.repo_dir)
        self.skip_revs = args.skip
        self.hg_prefix = ['hg', '-R', self.repo_dir]
        self.asan = args.asan
        self.debug = args.debug

        self.evaluator = None
        self.build_range = None

    def bisect(self):
        """
        Bisect using mercurial repository
        """
        log.info('Begin bisection...')
        log.info('> Start: %s (%s)' % (self.start.rev, self.start.date))
        log.info('> End: %s (%s)' % (self.end.rev, self.end.date))

        log.info('Purging all local repository changes')
        subprocess.check_call(self.hg_prefix + ['update', '-C', 'default'], stdout=DEVNULL)
        subprocess.check_call(self.hg_prefix + ['purge', '--all'], stdout=DEVNULL)

        # If we were unable to reduce bisection range using builds, validate start/end revisions 
        if not self.reduce_range():
            log.info('Attempting to validate boundaries')
            if not self.verify_bounds(self.start.rev, self.end.rev):
                log.critical('Unable to validate supplied revisions.  Cannot bisect!')
                return

        log.info('Continue bisection using mercurial...')

        # Reset bisect ranges and set skip ranges.
        subprocess.check_call(self.hg_prefix + ['bisect', '-r'], stdout=DEVNULL)
        if self.skip_revs:
            log.info('Skipping revisions matching: {0}'.format(self.skip_revs))
            for rev in self.skip_revs:
                subprocess.check_call(self.hg_prefix + ['bisect', '--skip', rev])

        # Set bisection's start and end revisions
        subprocess.check_call(self.hg_prefix + ['bisect', '-g', self.start.rev])
        bisect_msg = subprocess.check_output(self.hg_prefix + ['bisect', '-b', self.end.rev])
        current = Boundary.new(
            hgCmds.get_bisect_changeset(
                bisect_msg.splitlines()[0]
            ),
            self.repo_dir
        )

        iter_count = 0
        skip_count = 0

        while current is not None:
            iter_count += 1
            log.info('Begin round {0}: {1} ({2})'.format(iter_count, current.rev, current.date))
            start_time = time.time()

            self.clobber_build()
            result = self.test_revision(current.rev)

            if result == 'skip':
                skip_count += 1
                # If we use 'skip', we tell hg bisect to do a linear search to get around the skipping.
                # If the range is large, doing a bisect to find the start and endpoints of compilation
                # bustage would be faster. 20 total skips being roughly the time that the pair of
                # bisections would take.
                if skip_count > 20:
                    log.error('Reached maximum skip attempts! Exiting')
                    break

            current = self.apply_result(result, current)

            end_time = time.time()
            elapsed = datetime.timedelta(seconds=(int(end_time-start_time)))
            log.info('Round {0} completed in {1}'.format(iter_count, elapsed))
            hgCmds.destroy_pyc(self.repo_dir)

    def reduce_range(self):
        """
        Reduce bisection range using taskcluster builds
        """
        log.info('Attempting to reduce bisection range using taskcluster builds')
        # The oldest available build is 365 days from today
        oldest_build_date = datetime.datetime.now().date() - datetime.timedelta(days=365)

        # Taskcluster only retains builds up to a year old
        # If self.end.date is older than a year, continue to compiled builds
        if self.end.date < oldest_build_date:
            log.error('End revision is more than a year old!')
            log.error('Unable to reduce range using prebuilt binaries')
            return False
        if self.start.date < oldest_build_date:
            log.warn('Start revision is more than a year old! Reducing with a start of %s' % oldest_build_date)

        # If the start date is newer than the oldest available build, begin with that
        if self.start.date > oldest_build_date:
            oldest_build_date = self.start.date

        builds = []
        log.info('Identifying available builds between %s and %s' % (oldest_build_date, self.end.date))
        for i in range((self.end.date - oldest_build_date).days + 1):
            target_date = oldest_build_date + datetime.timedelta(days=i)
            try:
                builds.append(Build(self.target, 'central', target_date, self.asan, self.debug))
            except:
                log.debug("Unable to retrieve build for date: %s" % str(target_date))

        self.build_range = BuildRange(builds)

        while len(self.build_range) != 0:
            self.clobber_build()
            next_build = self.build_range.mid_point
            log.info('Testing build from %s' % next_build.date)
            next_build.build_info.extract_build(self.build_dir)
            self.update_build_range(next_build.date)

        log.info('Reduced build range to %s - %s' % (self.start.date, self.end.date))

        return True

    def clobber_build(self):
        """
        Delete and recreate build_dir
        """
        if os.path.exists(self.build_dir):
            log.debug('Clobbering build dir:  %s' % self.build_dir)
            shutil.rmtree(self.build_dir)
            os.makedirs(self.build_dir)

    def update_build_range(self, date):
        """
        Update the build_range based on the results returned by the evaluator
        Also update the start/end boundaries if later/newer than the previous value
        """
        i = self.build_range.get_index(date)
        status = self.evaluator.test_build()
        revision = self.build_range.builds[i].build_info.changeset

        if status == "good" and date >= self.start.date:
            self.start = Boundary.new(revision, self.repo_dir)
            if self.start.date != date:
                log.warn('The taskcluster revision or date is incorrect for this build!')
                log.warn('Setting the start date to the value associated with the hg revision (%s)' % self.start.date)
                i = self.build_range.get_index(self.end.date)
            self.build_range = self.build_range[i+1:]
        elif status == "bad" and date <= self.end.date:
            self.end = Boundary.new(revision, self.repo_dir)
            if self.end.date != date:
                log.warn('The taskcluster revision or date is incorrect for this build!')
                log.warn('Setting the end date to the value associated with the hg revision (%s)' % self.end.date)
                i = self.build_range.get_index(self.end.date)
            self.build_range = self.build_range[:i]
        elif status == "skip":
            del self.build_range[i]
        else:
            raise Exception('wtf')

    def verify_bounds(self, start, end):
        """
        Verify that the supplied start/end revisions behave as expected
        """
        # Test that end revision crashes
        self.clobber_build()
        if self.test_revision(end) != "bad":
            return False

        # Test to make sure the start revision doesn't
        self.clobber_build()
        if self.test_revision(start) != "good":
            return False

        return True

    def apply_result(self, label, current):
        """
        Tell hg what we learned about the revision.
        """
        assert label in ('good', 'bad', 'skip')
        log.info('Marking revision {0} as {1}'.format(current.rev, label))
        results = subprocess.check_output(self.hg_prefix + ['bisect', '--' + label, current.rev])

        # Determine if we should continue
        # e.g. "Testing changeset 52121:573c5fa45cc4 (440 changesets remaining, ~8 tests)"
        bisect_msg = results.splitlines()[0]
        revision = hgCmds.get_bisect_changeset(bisect_msg)
        if revision:
            log.info(bisect_msg)
            return Boundary.new(revision, self.repo_dir)

        # Otherwise, return results
        log.info(results)
        return None

    def test_revision(self, rev):
        try:
            log.info('Attempting to find build for revision %s' % rev)
            target_build = Build(self.target, 'central', rev, self.asan, self.debug)
            target_build.build_info.extract_build(self.build_dir)
            result = self.evaluator.test_build()
            return result
        except:
            log.warn('Unable to find build.  Falling back to compilation')

        subprocess.check_call(self.hg_prefix + ['update', '-r', rev], stdout=DEVNULL)
        result = self.evaluator.test_compilation()

        return result
