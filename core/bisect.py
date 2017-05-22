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
from util import subprocesses as sps

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
        start_rev = hgCmds.getRepoHashAndId(self.repo_dir, repoRev=self.start_rev)[0]
        end_rev = hgCmds.getRepoHashAndId(self.repo_dir, repoRev=self.end_rev)[0]

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
            subprocess.check_call(self.hg_prefix + ['bisect', '--skip', self.skip_revs])

        # Set bisection's start and end revisions
        subprocess.check_call(self.hg_prefix + ['bisect', '-g', start_rev])
        current_rev = hgCmds.getCsetHashFromBisectMsg(
            fileManipulation.firstLine(
                subprocess.check_output(self.hg_prefix + ['bisect', '-b', end_rev])
            )
        )

        iter_count = 0
        skip_count = 0

        while current_rev is not None:
            iter_count += 1
            log.info('Begin bisection round {0}, revision {1}'.format(iter_count, current_rev))
            start_time = time.time()
            result = self.evaluate_testcase(current_rev)

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
            hgCmds.destroyPyc(self.repo_dir)

    def apply_result(self, label, current_rev):
        """Tell hg what we learned about the revision."""
        assert label in ('good', 'bad', 'skip')
        log.info('Marking current revision as - {0}'.format(label))
        output_result = sps.captureStdout(self.hg_prefix + ['bisect', '--' + label, current_rev])[0]
        output_lines = output_result.split('\n')

        if re.match('Due to skipped revisions, the first (good|bad) revision could be any of:', output_lines[0]):
            log.info(sanitize_msg(output_result, self.repo_dir))
            return None

        r = re.compile("The first (good|bad) revision is:")
        m = r.match(output_lines[0])
        if m:
            log.info('autoBisect shows this is probably related to the following changeset:')
            log.info(sanitize_msg(output_result, self.repo_dir))
            # blamedGoodOrBad = m.group(1)
            # blamedRev = hgCmds.getCsetHashFromBisectMsg(output_lines[1])
            # Call checkBlameParents here
            return None

        # e.g. "Testing changeset 52121:573c5fa45cc4 (440 changesets remaining, ~8 tests)"
        log.info(output_lines[0])

        current_rev = hgCmds.getCsetHashFromBisectMsg(output_lines[0])
        if current_rev is None:
            raise Exception("hg did not suggest a changeset to test!")

        return current_rev


def sanitize_msg(msg, repo):
    """Sanitize changeset messages, removing email addresses."""
    sanitized = []

    for line in msg.splitlines():
        if line.find('<') != -1 and line.find('@') != -1 and line.find('>') != -1:
            line = ' '.join(line.split(' ')[:-1])
        elif line.startswith('changeset:') and 'mozilla-central' in repo:
            line = 'changeset:   https://hg.mozilla.org/mozilla-central/rev/' + line.split(':')[-1]
        sanitized.append(line)

    return '\n'.join(sanitized)
