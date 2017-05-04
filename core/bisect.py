#!/usr/bin/env python
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import, division, print_function

import os
import re
import subprocess
import tempfile
import datetime
import time
import logging

from util import ximport
from util import inspectShell
from util import fileManipulation
from util import hgCmds
from util import subprocesses as sps

INCOMPLETE_NOTE = 'incompleteBuild.txt'
MAX_ITERATIONS = 100

log = logging.getLogger("bisect")

class Bisector:
    def __init__(self, args):
        self.repo_dir = args.repo_dir
        self.start_rev = args.start
        self.end_rev = args.end
        self.hg_prefix = ['hg', '-R', self.repo_dir]
        
        self.evaluator = None

        self.baseline = None

    def establish_baseline(self, start, end):
        log.info('Attempting to establish baseline for testcase')
        subprocess.check_call(self.hg_prefix + ['update', '-r', end])
        self.baseline = self.evaluate_testcase(end)

        # Test to make sure the end revision crashes
        if self.baseline is None or self.baseline == "skip":
            log.error("Unable to establish baseline!")
            return False

        # Test to make sure the start revision doesn't
        # This might be incorrect - We shoud probably just check that the return code is different
        subprocess.check_call(self.hg_prefix + ['update', '-r', start])
        start_result = self.evaluate_testcase(start)

        if start_result is None:
            return True
        else:
            return False

    def bisect(self, options):
        # Refresh source directory (overwrite all local changes) to tip
        log.info("Purging all local repository changes")
        subprocess.check_call(self.hg_prefix + ['update', '-C', 'default'])
        subprocess.check_call(self.hg_prefix + ['purge', '--all'])

        # Resolve names such as "tip", "default", or "52707" to stable hg hash ids, e.g. "9f2641871ce8".
        realStartRepo = sRepo = hgCmds.getRepoHashAndId(self.repo_dir, repoRev=self.start_rev)[0]
        realEndRepo = eRepo = hgCmds.getRepoHashAndId(self.repo_dir, repoRev=self.end_rev)[0]

        # Establish baseline
        # All future runs must match this baseline to be considered 'good'
        if self.establish_baseline(sRepo, eRepo):
            log.info("Established baseline.  All future runs must return: {0}".format(self.baseline))
        else:
            log.error("Unable to perform bisection because the we were unable to establish a baseline.  Exiting!")
            return

        log.info("Bisecting in range: {0} - {1}".format(sRepo, eRepo))

        # Reset bisect ranges and set skip ranges.
        sps.captureStdout(self.hg_prefix + ['bisect', '-r'])
        if options.skipRevs:
            sps.captureStdout(self.hg_prefix + ['bisect', '--skip', options.skipRevs])

        labels = {}

        iterNum = 1
        skipCount = 0
        blamedRev = None
        currRev = self.baseline

        while currRev is not None:
            startTime = time.time()
            label = self.evaluator(currRev)
            labels[currRev] = label
            if label[0] == 'skip':
                skipCount += 1
                # If we use "skip", we tell hg bisect to do a linear search to get around the skipping.
                # If the range is large, doing a bisect to find the start and endpoints of compilation
                # bustage would be faster. 20 total skips being roughly the time that the pair of
                # bisections would take.
                if skipCount > 20:
                    logging.error("Reached maximum skip attempts! Exiting")
                    break
            logging.info(label[0] + " (" + label[1] + ") ")

            # Revisit this
            """print "Bisecting for the n-th round where n is", iterNum, "and 2^n is", \
                  str(2**iterNum), "...",
        (blamedGoodOrBad, blamedRev, currRev, sRepo, eRepo) = \
            bisectLabel(self.hg_prefix, options, label[0], currRev, sRepo, eRepo)"""

            iterNum += 1
            endTime = time.time()
            elapsed = datetime.timedelta(seconds=(int(endTime-startTime)))
            log.info("This iteration completed in {0}".format(elapsed))

        if blamedRev is not None:
            checkBlameParents(self.repo_dir, blamedRev, blamedGoodOrBad, labels, self.evaluator, realStartRepo,
                              realEndRepo)

        sps.vdump("Resetting bisect")
        subprocess.check_call(self.hg_prefix + ['bisect', '-U', '-r'])

        sps.vdump("Resetting working directory")
        sps.captureStdout(self.hg_prefix + ['update', '-C', '-r', 'default'], ignoreStderr=True)
        hgCmds.destroyPyc(self.repo_dir)


    def internalTestAndLabel(options):
        """Use autoBisectJs without interestingness tests to examine the revision of the js shell."""
        def inner(shellFilename, _hgHash):
            (stdoutStderr, exitCode) = inspectShell.testBinary(shellFilename, options.paramList,
                                                               options.buildOptions.runWithVg)

            if (stdoutStderr.find(options.output) != -1) and (options.output != ''):
                return ('bad', 'Specified-bad output')
            elif options.watchExitCode is not None and exitCode == options.watchExitCode:
                return ('bad', 'Specified-bad exit code ' + str(exitCode))
            elif options.watchExitCode is None and 129 <= exitCode <= 159:
                return ('bad', 'High exit code ' + str(exitCode))
            elif exitCode < 0:
                # On Unix-based systems, the exit code for signals is negative, so we check if
                # 128 + abs(exitCode) meets our specified signal exit code.
                if options.watchExitCode is not None and 128 - exitCode == options.watchExitCode:
                    return ('bad', 'Specified-bad exit code ' + str(exitCode) +
                            ' (after converting to signal)')
                elif (stdoutStderr.find(options.output) == -1) and (options.output != ''):
                    return ('good', 'Bad output, but not the specified one')
                elif options.watchExitCode is not None and 128 - exitCode != options.watchExitCode:
                    return ('good', 'Negative exit code, but not the specified one')
                else:
                    return ('bad', 'Negative exit code ' + str(exitCode))
            elif exitCode == 0:
                return ('good', 'Exit code 0')
            elif (exitCode == 1 or exitCode == 2) and (options.output != '') and \
                    (stdoutStderr.find('usage: js [') != -1 or
                     stdoutStderr.find('Error: Short option followed by junk') != -1 or
                     stdoutStderr.find('Error: Invalid long option:') != -1 or
                     stdoutStderr.find('Error: Invalid short option:') != -1):
                return ('good', 'Exit code 1 or 2 - js shell quits ' +
                        'because it does not support a given CLI parameter')
            elif 3 <= exitCode <= 6:
                return ('good', 'Acceptable exit code ' + str(exitCode))
            elif options.watchExitCode is not None:
                return ('good', 'Unknown exit code ' + str(exitCode) + ', but not the specified one')
            else:
                return ('bad', 'Unknown exit code ' + str(exitCode))
        return inner


    def externalTestAndLabel(options, interestingness):
        """Make use of interestingness scripts to decide whether the changeset is good or bad."""
        conditionScript = ximport.importRelativeOrAbsolute(interestingness[0])
        conditionArgPrefix = interestingness[1:]

        def inner(shellFilename, hgHash):
            conditionArgs = conditionArgPrefix + [shellFilename] + options.paramList
            tempDir = tempfile.mkdtemp(prefix="abExtTestAndLabel-" + hgHash)
            tempPrefix = os.path.join(tempDir, 't')
            if hasattr(conditionScript, "init"):
                # Since we're changing the js shell name, call init() again!
                conditionScript.init(conditionArgs)
            if conditionScript.interesting(conditionArgs, tempPrefix):
                innerResult = ('bad', 'interesting')
            else:
                innerResult = ('good', 'not interesting')
            if os.path.isdir(tempDir):
                sps.rmTreeIncludingReadOnly(tempDir)
            return innerResult
        return inner


    def checkBlameParents(self.repo_dir, blamedRev, blamedGoodOrBad, labels, self.evaluator, startRepo, endRepo):
        """If bisect blamed a merge, try to figure out why."""
        bisectLied = False
        missedCommonAncestor = False

        parents = sps.captureStdout(["hg", "-R", self.repo_dir] + ["parent", '--template={node|short},',
                                                             "-r", blamedRev])[0].split(",")[:-1]

        if len(parents) == 1:
            return

        for p in parents:
            # Ensure we actually tested the parent.
            if labels.get(p) is None:
                print ""
                print ("Oops! We didn't test rev %s, a parent of the blamed revision! " +
                       "Let's do that now.") % str(p)
                if not hgCmds.isAncestor(self.repo_dir, startRepo, p) and \
                        not hgCmds.isAncestor(self.repo_dir, endRepo, p):
                    print ('We did not test rev %s because it is not a descendant of either ' +
                           '%s or %s.') % (str(p), startRepo, endRepo)
                    # Note this in case we later decide the bisect result is wrong.
                    missedCommonAncestor = True
                label = self.evaluator(p)
                labels[p] = label
                print label[0] + " (" + label[1] + ") "
                print "As expected, the parent's label is the opposite of the blamed rev's label."

            # Check that the parent's label is the opposite of the blamed merge's label.
            if labels[p][0] == "skip":
                print "Parent rev %s was marked as 'skip', so the regression window includes it." % str(p)
            elif labels[p][0] == blamedGoodOrBad:
                print "Bisect lied to us! Parent rev %s was also %s!" % (str(p), blamedGoodOrBad)
                bisectLied = True
            else:
                assert labels[p][0] == {'good': 'bad', 'bad': 'good'}[blamedGoodOrBad]

        # Explain why bisect blamed the merge.
        if bisectLied:
            if missedCommonAncestor:
                ca = hgCmds.findCommonAncestor(self.repo_dir, parents[0], parents[1])
                print ""
                print "Bisect blamed the merge because our initial range did not include one"
                print "of the parents."
                print "The common ancestor of %s and %s is %s." % (parents[0], parents[1], ca)
                label = self.evaluator(ca)
                print label[0] + " (" + label[1] + ") "
                print "Consider re-running autoBisect with -s %s -e %s" % (ca, blamedRev)
                print "in a configuration where earliestWorking is before the common ancestor."
            else:
                print ""
                print "Most likely, bisect's result was unhelpful because one of the"
                print "tested revisions was marked as 'good' or 'bad' for the wrong reason."
                print "I don't know which revision was incorrectly marked. Sorry."
        else:
            print ""
            print "The bug was introduced by a merge (it was not present on either parent)."
            print "I don't know which patches from each side of the merge contributed to the bug. Sorry."


    def sanitizeCsetMsg(msg, repo):
        """Sanitize changeset messages, removing email addresses."""
        msgList = msg.split('\n')
        sanitizedMsgList = []
        for line in msgList:
            if line.find('<') != -1 and line.find('@') != -1 and line.find('>') != -1:
                line = ' '.join(line.split(' ')[:-1])
            elif line.startswith('changeset:') and 'mozilla-central' in repo:
                line = 'changeset:   https://hg.mozilla.org/mozilla-central/rev/' + line.split(':')[-1]
            sanitizedMsgList.append(line)
        return '\n'.join(sanitizedMsgList)


    def bisectLabel(self.hg_prefix, options, hgLabel, currRev, startRepo, endRepo):
        """Tell hg what we learned about the revision."""
        assert hgLabel in ("good", "bad", "skip")
        outputResult = sps.captureStdout(self.hg_prefix + ['bisect', '-U', '--' + hgLabel, currRev])[0]
        outputLines = outputResult.split("\n")

        self.repo_dir = options.buildOptions.self.repo_dir if options.buildOptions else options.browserOptions.self.repo_dir

        if re.compile("Due to skipped revisions, the first (good|bad) revision could be any of:").match(outputLines[0]):
            print '\n' + sanitizeCsetMsg(outputResult, self.repo_dir) + '\n'
            return None, None, None, startRepo, endRepo

        r = re.compile("The first (good|bad) revision is:")
        m = r.match(outputLines[0])
        if m:
            print '\n\nautoBisect shows this is probably related to the following changeset:\n'
            print sanitizeCsetMsg(outputResult, self.repo_dir) + '\n'
            blamedGoodOrBad = m.group(1)
            blamedRev = hgCmds.getCsetHashFromBisectMsg(outputLines[1])
            return blamedGoodOrBad, blamedRev, None, startRepo, endRepo

        if options.testInitialRevs:
            return None, None, None, startRepo, endRepo

        # e.g. "Testing changeset 52121:573c5fa45cc4 (440 changesets remaining, ~8 tests)"
        sps.vdump(outputLines[0])

        currRev = hgCmds.getCsetHashFromBisectMsg(outputLines[0])
        if currRev is None:
            print 'Resetting to default revision...'
            subprocess.check_call(self.hg_prefix + ['update', '-C', 'default'])
            hgCmds.destroyPyc(self.repo_dir)
            raise Exception("hg did not suggest a changeset to test!")

        # Update the startRepo/endRepo values.
        start = startRepo
        end = endRepo
        if hgLabel == 'bad':
            end = currRev
        elif hgLabel == 'good':
            start = currRev
        elif hgLabel == 'skip':
            pass

        return None, None, currRev, start, end
