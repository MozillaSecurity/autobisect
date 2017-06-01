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
import abc

try:
    # subprocess v3.5
    from subprocess import DEVNULL
except ImportError:
    import os
    DEVNULL = open(os.devnull, 'wb')

from util import fileManipulation
from util import hgCmds
from util.builds import BuildRange
from util.builds import Build

log = logging.getLogger('bisect')


class Bisector(object):
    def __init__(self, repo_dir, start_rev, end_rev, skip_revs, asan, debug):
        self.repo_dir = repo_dir
        self.start_rev = start_rev
        self.end_rev = end_rev
        self.skip_revs = skip_revs
        self.hg_prefix = ['hg', '-R', self.repo_dir]

        self.asan = asan
        self.debug = debug

    @abc.abstractmethod
    def evaluate_testcase(self):
        raise NotImplementedError

    def verify_bounds(self, start, end):
        """
        Verify that the supplied start/end revisions behave as expected
        """
        return True
        # Test that end revision crashes
        subprocess.check_call(self.hg_prefix + ['update', '-r', end], stdout=DEVNULL)
        if not self.try_compile() and self.evaluate_testcase() != "bad":
            return False

        # Test to make sure the start revision doesn't
        subprocess.check_call(self.hg_prefix + ['update', '-r', start], stdout=DEVNULL)
        if not self.try_compile() and self.evaluate_testcase() != "good":
            return False

        return True

    def bisect(self):
        """
        Bisect using mercurial repository
        """
        self.bisect_builds()
        log.info('Purging all local repository changes')
        subprocess.check_call(self.hg_prefix + ['update', '-C', 'default'], stdout=DEVNULL)
        log.info('Purging all local repository changes...')
        subprocess.check_call(self.hg_prefix + ['purge', '--all'], stdout=DEVNULL)

        # Resolve names such as "tip", "default", or "52707" to stable hg hash ids, e.g. "9f2641871ce8".
        start_rev = hgCmds.get_full_hash(self.repo_dir, self.start_rev)
        end_rev = hgCmds.get_full_hash(self.repo_dir, self.end_rev)

        log.info('Begin validation of start ({0}) and end ({1}) revisions'.format(self.start_rev, self.end_rev))
        if self.verify_bounds(start_rev, end_rev):
            log.info('Successfully validated both revisions')
        else:
            log.critical('Unable to validate supplied revisions.  Cannot bisect!')
            return

        log.info('Begin bisection in range: {0} - {1}'.format(start_rev, end_rev))
        # Reset bisect ranges and set skip ranges.
        subprocess.check_call(self.hg_prefix + ['bisect', '-r'], stdout=DEVNULL)
        if self.skip_revs:
            log.info('Skipping revisions matching: {0}'.format(self.skip_revs))
            for rev in self.skip_revs:
                subprocess.check_call(self.hg_prefix + ['bisect', '--skip', rev])

        # Set bisection's start and end revisions
        subprocess.check_call(self.hg_prefix + ['bisect', '-g', start_rev])
        current_rev = hgCmds.get_bisect_changeset(
            fileManipulation.first_line(
                subprocess.check_output(self.hg_prefix + ['bisect', '-b', end_rev])
            )
        )

        iter_count = 0
        skip_count = 0

        while current_rev is not None:
            iter_count += 1
            log.info('Begin bisection round {0}, revision {1}'.format(iter_count, current_rev))
            start_time = time.time()

            if self.try_compile():
                result = self.evaluate_testcase()
            else:
                result = 'skip'

            if result == 'skip':
                skip_count += 1
                # If we use 'skip', we tell hg bisect to do a linear search to get around the skipping.
                # If the range is large, doing a bisect to find the start and endpoints of compilation
                # bustage would be faster. 20 total skips being roughly the time that the pair of
                # bisections would take.
                if skip_count > 20:
                    log.error('Reached maximum skip attempts! Exiting')
                    break

            current_rev = self.apply_result(result, current_rev)

            end_time = time.time()
            elapsed = datetime.timedelta(seconds=(int(end_time-start_time)))
            log.info('Round {0} completed in {1}'.format(iter_count, elapsed))
            hgCmds.destroy_pyc(self.repo_dir)

    def apply_result(self, label, current_rev):
        """
        Tell hg what we learned about the revision.
        """
        assert label in ('good', 'bad', 'skip')
        log.info('Marking current revision as - {0}'.format(label))
        result = subprocess.check_output(self.hg_prefix + ['bisect', '--' + label, current_rev]).splitlines()

        # Determine if we should continue
        # e.g. "Testing changeset 52121:573c5fa45cc4 (440 changesets remaining, ~8 tests)"
        current_rev = hgCmds.get_bisect_changeset(result)
        if current_rev:
            return current_rev

        # Otherwise, return results
        log.info(result)
        return None

    def bisect_builds(self):
        # Convert start and end revisions to dates
        start_date = hgCmds.rev_date(self.repo_dir, self.start_rev) + datetime.timedelta(days=1)
        end_date = hgCmds.rev_date(self.repo_dir, self.end_rev)

        # The oldest available build is 365 days from today
        oldest_build_date = datetime.datetime.now().date() - datetime.timedelta(days=364)

        # Taskcluster only retains builds up to a year old
        # If start_rev is older than that, continue to compiled builds
        if oldest_build_date > end_date:
            log.error('End revision is older than 365 days.  Unable to reduce range using prebuilt binaries!')
            return

        builds = []
        log.info('Identifying available builds between %s and %s' % (oldest_build_date, end_date))
        for i in range((end_date - oldest_build_date).days + 1):
            target_date = oldest_build_date + datetime.timedelta(days=i)

            try:
                builds.append(Build('browser', 'central', target_date, self.asan, self.debug))
            except:
                log.info("Unable to retrieve build for date: %s" % str(target_date))

        build_range = BuildRange(builds)

        while len(build_range) > 2:
            target_build = None