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

def findBlamedCset(options, repoDir, testRev):
    log.info("Begin bisection on {0}".format(repoDir))

    hgPrefix = ['hg', '-R', repoDir]

    # Resolve names such as "tip", "default", or "52707" to stable hg hash ids, e.g. "9f2641871ce8".
    realStartRepo = sRepo = hgCmds.getRepoHashAndId(repoDir, repoRev=options.startRepo)[0]
    realEndRepo = eRepo = hgCmds.getRepoHashAndId(repoDir, repoRev=options.endRepo)[0]
    log.info("Bisecting in range: {0} - {1}".format(sRepo, eRepo))

    # Refresh source directory (overwrite all local changes) to default tip if required.
    if options.resetRepoFirst:
        subprocess.check_call(hgPrefix + ['update', '-C', 'default'])
        # Throws exit code 255 if purge extension is not enabled in .hgrc:
        subprocess.check_call(hgPrefix + ['purge', '--all'])

    # Reset bisect ranges and set skip ranges.
    sps.captureStdout(hgPrefix + ['bisect', '-r'])
    if options.skipRevs:
        sps.captureStdout(hgPrefix + ['bisect', '--skip', options.skipRevs])

    labels = {}
    # Specify `hg bisect` ranges.
    if options.testInitialRevs:
        currRev = eRepo  # If testInitialRevs mode is set, compile and test the latest rev first.
    else:
        labels[sRepo] = ('good', 'assumed start rev is good')
        labels[eRepo] = ('bad', 'assumed end rev is bad')
        subprocess.check_call(hgPrefix + ['bisect', '-U', '-g', sRepo])
        currRev = hgCmds.getCsetHashFromBisectMsg(fileManipulation.firstLine(
            sps.captureStdout(hgPrefix + ['bisect', '-U', '-b', eRepo])[0]))

    iterNum = 1
    if options.testInitialRevs:
        iterNum -= 2

    skipCount = 0
    blamedRev = None

    while currRev is not None:
        startTime = time.time()
        label = testRev(currRev)
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

        if iterNum <= 0:
            log.info("Finished testing the initial boundary revisions...")
        else:
            # Revisit this
            """print "Bisecting for the n-th round where n is", iterNum, "and 2^n is", \
                  str(2**iterNum), "...",
        (blamedGoodOrBad, blamedRev, currRev, sRepo, eRepo) = \
            bisectLabel(hgPrefix, options, label[0], currRev, sRepo, eRepo)"""

        if options.testInitialRevs:
            options.testInitialRevs = False
            assert currRev is None
            currRev = sRepo  # If options.testInitialRevs is set, test earliest possible rev next.

        iterNum += 1
        endTime = time.time()
        elapsed = datetime.timedelta(seconds=(int(endTime-startTime)))
        log.info("This iteration completed in {0}".format(elapsed))

    if blamedRev is not None:
        checkBlameParents(repoDir, blamedRev, blamedGoodOrBad, labels, testRev, realStartRepo,
                          realEndRepo)

    sps.vdump("Resetting bisect")
    subprocess.check_call(hgPrefix + ['bisect', '-U', '-r'])

    sps.vdump("Resetting working directory")
    sps.captureStdout(hgPrefix + ['update', '-C', '-r', 'default'], ignoreStderr=True)
    hgCmds.destroyPyc(repoDir)


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


def checkBlameParents(repoDir, blamedRev, blamedGoodOrBad, labels, testRev, startRepo, endRepo):
    """If bisect blamed a merge, try to figure out why."""
    bisectLied = False
    missedCommonAncestor = False

    parents = sps.captureStdout(["hg", "-R", repoDir] + ["parent", '--template={node|short},',
                                                         "-r", blamedRev])[0].split(",")[:-1]

    if len(parents) == 1:
        return

    for p in parents:
        # Ensure we actually tested the parent.
        if labels.get(p) is None:
            print ""
            print ("Oops! We didn't test rev %s, a parent of the blamed revision! " +
                   "Let's do that now.") % str(p)
            if not hgCmds.isAncestor(repoDir, startRepo, p) and \
                    not hgCmds.isAncestor(repoDir, endRepo, p):
                print ('We did not test rev %s because it is not a descendant of either ' +
                       '%s or %s.') % (str(p), startRepo, endRepo)
                # Note this in case we later decide the bisect result is wrong.
                missedCommonAncestor = True
            label = testRev(p)
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
            ca = hgCmds.findCommonAncestor(repoDir, parents[0], parents[1])
            print ""
            print "Bisect blamed the merge because our initial range did not include one"
            print "of the parents."
            print "The common ancestor of %s and %s is %s." % (parents[0], parents[1], ca)
            label = testRev(ca)
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


def bisectLabel(hgPrefix, options, hgLabel, currRev, startRepo, endRepo):
    """Tell hg what we learned about the revision."""
    assert hgLabel in ("good", "bad", "skip")
    outputResult = sps.captureStdout(hgPrefix + ['bisect', '-U', '--' + hgLabel, currRev])[0]
    outputLines = outputResult.split("\n")

    repoDir = options.buildOptions.repoDir if options.buildOptions else options.browserOptions.repoDir

    if re.compile("Due to skipped revisions, the first (good|bad) revision could be any of:").match(outputLines[0]):
        print '\n' + sanitizeCsetMsg(outputResult, repoDir) + '\n'
        return None, None, None, startRepo, endRepo

    r = re.compile("The first (good|bad) revision is:")
    m = r.match(outputLines[0])
    if m:
        print '\n\nautoBisect shows this is probably related to the following changeset:\n'
        print sanitizeCsetMsg(outputResult, repoDir) + '\n'
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
        subprocess.check_call(hgPrefix + ['update', '-C', 'default'])
        hgCmds.destroyPyc(repoDir)
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
