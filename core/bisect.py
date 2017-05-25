#!/usr/bin/env python
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import, division, print_function

import datetime
import logging
import re
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

log = logging.getLogger('bisect')


class Bisector(object):
    def __init__(self, repo_dir, start_rev, end_rev, skip_revs):
        self.repo_dir = repo_dir
        self.start_rev = start_rev
        self.end_rev = end_rev
        self.skip_revs = skip_revs
        self.hg_prefix = ['hg', '-R', self.repo_dir]

    @abc.abstractmethod
    def evaluate_testcase(self):
        raise NotImplementedError

    def verify_bounds(self, start, end):
        return True
        subprocess.check_call(self.hg_prefix + ['update', '-r', end], stdout=DEVNULL)
        if self.evaluate_testcase() != "bad":
            return False

        # Test to make sure the start revision doesn't
        subprocess.check_call(self.hg_prefix + ['update', '-r', start], stdout=DEVNULL)
        if self.evaluate_testcase() != "good":
            return False

        return True

    def bisect(self):
        # Refresh source directory (overwrite all local changes) to tip
        log.info('Purging all local repository changes')
        subprocess.check_call(self.hg_prefix + ['update', '-C', 'default'], stdout=DEVNULL)
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
            result = self.evaluate_testcase()

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
        """Tell hg what we learned about the revision."""
        assert label in ('good', 'bad', 'skip')
        log.info('Marking current revision as - {0}'.format(label))
        result = subprocess.check_output(self.hg_prefix + ['bisect', '--' + label, current_rev]).splitlines()

        # e.g. "Testing changeset 52121:573c5fa45cc4 (440 changesets remaining, ~8 tests)"
        m = re.match(r"(Testing changeset \d+:)([a-fA-F0-9]+)( .*)", result)
        if m:
            current_rev = m.group(2)
            return current_rev

        # If no further test suggested, return bisect message
        log.info(result)
        return None
