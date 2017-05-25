#!/usr/bin/env python
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import, division, print_function

import logging
import os
import re
import subprocess
from datetime import datetime

import configparser

from util import subprocesses as sps

log = logging.getLogger(__name__)


def destroy_pyc(repo_dir):
    """
    Remove *.pyc files from repo_dir
    Roughly equivalent to hg purge --all --include=**.pyc without requiring the purge extension
    """

    for root, dirs, files in os.walk(repo_dir):
        for fn in files:
            if fn.endswith(".pyc"):
                os.remove(os.path.join(root, fn))
        if '.hg' in dirs:
            # Don't visit .hg dir
            dirs.remove('.hg')


def ensure_mg_enabled():
    """
    Ensure that mq is enabled in the ~/.hgrc file.
    """

    hgrc_path = os.path.join(os.path.expanduser('~'), '.hgrc')
    assert os.path.isfile(hgrc_path)

    hgrc = configparser.ConfigParser()
    hgrc.read(hgrc_path)

    try:
        hgrc.get('extensions', 'mq')
    except configparser.NoOptionError:
        raise Exception('Please first enable mq in ~/.hgrc by having "mq =" in [extensions].')


def find_common_ancestor(repo_dir, a, b):
    """
    Find a common ancestor of two revisions 
    """

    return sps.captureStdout(['hg', '-R', repo_dir, 'log', '-r', 'ancestor(' + a + ',' + b + ')',
                              '--template={node|short}'])[0]


def is_ancestor(repo_dir, a, b):
    """
    Determine if "a" is an ancestor of "b". 
    Throws an exception if either rev doesn't exist
    """

    return sps.captureStdout(['hg', '-R', repo_dir, 'log', '-r', a + ' and ancestor(' + a + ',' + b + ')',
                              '--template={node|short}'])[0] != ""


def exists_and_is_ancestor(repo_dir, a, b):
    """
    Determine if "a" is an ancestor of "b"
    Throws an exception if either rev doesn't exist 
    """

    out = sps.captureStdout(['hg', '-R', repo_dir, 'log', '-r', a + ' and ancestor(' + a + ',' + b + ')',
                             '--template={node|short}'], combineStderr=True, ignoreExitCode=True)[0]
    return out != "" and out.find("abort: unknown revision") < 0


def get_bisect_changeset(msg):
    """
    Extracts the current changeset from a bisect message
    I.e. - "Testing changeset 41831:4f4c01fb42c3 (2 changesets remaining, ~1 tests)"
    """
    m = re.match(r"(Testing changeset \d+:)([a-fA-F0-9]+)( .*)", msg)
    if m:
        return m.group(2)


def get_full_hash(repo_dir, rev):
    """
    Converts a partial hash to a full one
    """

    cmd = ['hg', '-R', repo_dir, 'log', '-l', '1', '--template' '{node}\n' '-r', rev]
    full_hash = sps.captureStdout(cmd)[0]
    assert full_hash != ''
    return full_hash


def get_repo_name(repo_dir):
    """
    Extract the repository name from the hgrc file
    """
    assert is_valid_repo(repo_dir)
    hgrc = configparser.ConfigParser()
    hgrc.read(sps.normExpUserPath(os.path.join(repo_dir, '.hg', 'hgrc')))
    # Not all default entries in [paths] end with "/".
    return [i for i in hgrc.get('paths', 'default').split('/') if i][-1]


def is_valid_repo(repo):
    """
    Validate repository by checking for the existence of repo_dir/.hg/hgrc
    """

    return os.path.isfile(sps.normExpUserPath(os.path.join(repo, '.hg', 'hgrc')))


def patch_repo_using_mg(patch_path, repo_dir=os.getcwdu()):
    """
    Apply a patch using the mg extension
    """

    full_patch_path = os.path.abspath(sps.normExpUserPath(patch_path))
    pname = os.path.basename(full_patch_path)
    assert pname != ''
    output, return_code = sps.captureStdout(['hg', '-R', repo_dir, 'qimport', full_patch_path], combineStderr=True,
                                            ignoreStderr=True, ignoreExitCode=True)
    if return_code != 0:
        if 'already exists' in output:
            log.error("A patch_path with the same name has already been qpush'ed. Please qremove it first.")
        raise Exception('Return code from `hg qimport` is: ' + str(return_code))

    print("Patch qimport'ed..."),

    qpush_output, qpush_ret_code = sps.captureStdout(['hg', '-R', repo_dir, 'qpush', pname],
                                                     combineStderr=True, ignoreStderr=True)
    assert ' is empty' not in qpush_output, "Patch to be qpush'ed should not be empty."

    if qpush_ret_code != 0:
        pop_applied_patch(patch_path, repo_dir)
        log.error('You may have untracked .rej or .orig files in the repository.')
        log.error('`hg status` output of the repository of interesting files in ' + repo_dir + ' :')
        subprocess.check_call(['hg', '-R', repo_dir, 'status', '--modified', '--added',
                               '--removed', '--deleted'])
        raise Exception('Return code from `hg qpush` is: %s' % qpush_ret_code)

    log.info("Patch qpush'ed. Continuing...")
    return pname


def pop_applied_patch(patch, repo_dir):
    """
    Remove an applied patch
    """

    qpop_output, qpop_ret_code = sps.captureStdout(['hg', '-R', repo_dir, 'qpop'], combineStderr=True,
                                                   ignoreStderr=True, ignoreExitCode=True)
    log.info("Patch qpop'ed...")

    if qpop_ret_code != 0:
        log.error('`hg qpop` output is: %s' % qpop_output)
        raise Exception('Return code from `hg qpop` is: ' + str(qpop_ret_code))

    subprocess.check_call(['hg', '-R', repo_dir, 'qdelete', os.path.basename(patch)])
    log.error("Patch qdelete'd.")


def rev_date(repo_dir, rev):
    """
    Return the date of a rev as a date object
    """
    date_string = sps.captureStdout(['hg', '-R', repo_dir, 'log', '-r', rev, '--template', '{date|shortdate}\n'])[0]
    if re.match(r"\d{4}-\d{2}-\d{2}", date_string):
        return datetime.strptime(date_string, '%Y-%m-%d').date()
