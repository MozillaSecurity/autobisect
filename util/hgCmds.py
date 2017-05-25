#!/usr/bin/env python
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import

import os
import re
import subprocess
from datetime import datetime

import configparser

from util import subprocesses as sps


def destroy_pyc(repo_dir):
    # This is roughly equivalent to ['hg', 'purge', '--all', '--include=**.pyc'])
    # but doesn't run into purge's issues (incompatbility with -R, requiring an hg extension)
    for root, dirs, files in os.walk(repo_dir):
        for fn in files:
            if fn.endswith(".pyc"):
                os.remove(os.path.join(root, fn))
        if '.hg' in dirs:
            # Don't visit .hg dir
            dirs.remove('.hg')


def ensure_mg_enabled():
    """Ensure that mq is enabled in the ~/.hgrc file."""
    hgrc_path = os.path.join(os.path.expanduser('~'), '.hgrc')
    assert os.path.isfile(hgrc_path)

    hgrc = configparser.ConfigParser()
    hgrc.read(hgrc_path)

    try:
        hgrc.get('extensions', 'mq')
    except configparser.NoOptionError:
        raise Exception('Please first enable mq in ~/.hgrc by having "mq =" in [extensions].')


def find_common_ancestor(repo_dir, a, b):
    return sps.captureStdout(['hg', '-R', repo_dir, 'log', '-r', 'ancestor(' + a + ',' + b + ')',
                              '--template={node|short}'])[0]


def is_ancestor(repo_dir, a, b):
    """Return true iff |a| is an ancestor of |b|. Throw if |a| or |b| does not exist."""
    return sps.captureStdout(['hg', '-R', repo_dir, 'log', '-r', a + ' and ancestor(' + a + ',' + b + ')',
                              '--template={node|short}'])[0] != ""


def exists_and_is_ancestor(repo_dir, a, b):
    """Return true iff |a| exists and is an ancestor of |b|."""
    # Takes advantage of "id(badhash)" being the empty set, in contrast to just "badhash", which is an error
    out = sps.captureStdout(['hg', '-R', repo_dir, 'log', '-r', a + ' and ancestor(' + a + ',' + b + ')',
                             '--template={node|short}'], combineStderr=True, ignoreExitCode=True)[0]
    return out != "" and out.find("abort: unknown revision") < 0


def get_bisect_changeset(msg):
    # Example bisect msg: "Testing changeset 41831:4f4c01fb42c3 (2 changesets remaining, ~1 tests)"
    r = re.compile(r"(^|.* )(\d+):(\w{12}).*")
    m = r.match(msg)
    if m:
        return m.group(3)

assert get_bisect_changeset("x 12345:abababababab") == "abababababab"
assert get_bisect_changeset("x 12345:123412341234") == "123412341234"
assert get_bisect_changeset("12345:abababababab y") == "abababababab"


def get_full_hash(repo_dir, rev):
    """Return the repository hash and id, and whether it is on default.

    It will also ask what the user would like to do, should the repository not be on default.
    """
    # This returns null if the repository is not on default.
    cmd = ['hg', '-R', repo_dir, 'log', '-l', '1', '--template' '{node}\n' '-r', rev]
    full_hash = sps.captureStdout(cmd)[0]
    assert full_hash != ''
    return full_hash


def get_repo_name(repo_dir):
    """Look in the hgrc file in the .hg directory of the repository and return the name."""
    assert is_valid_repo(repo_dir)
    hgrc = configparser.ConfigParser()
    hgrc.read(sps.normExpUserPath(os.path.join(repo_dir, '.hg', 'hgrc')))
    # Not all default entries in [paths] end with "/".
    return [i for i in hgrc.get('paths', 'default').split('/') if i][-1]


def is_valid_repo(repo):
    """Check that a repository is valid by ensuring that the hgrc file is around."""
    return os.path.isfile(sps.normExpUserPath(os.path.join(repo, '.hg', 'hgrc')))


def patch_repo_using_mg(patch_path, repo_dir=os.getcwdu()):
    # We may have passed in the patch_path with or without the full directory.
    full_patch_path = os.path.abspath(sps.normExpUserPath(patch_path))
    pname = os.path.basename(full_patch_path)
    assert pname != ''
    output, return_code = sps.captureStdout(['hg', '-R', repo_dir, 'qimport', full_patch_path], combineStderr=True,
                                            ignoreStderr=True, ignoreExitCode=True)
    if return_code != 0:
        if 'already exists' in output:
            print "A patch_path with the same name has already been qpush'ed. Please qremove it first."
        raise Exception('Return code from `hg qimport` is: ' + str(return_code))

    print("Patch qimport'ed..."),

    qpush_output, qpush_ret_code = sps.captureStdout(['hg', '-R', repo_dir, 'qpush', pname],
                                                     combineStderr=True, ignoreStderr=True)
    assert ' is empty' not in qpush_output, "Patch to be qpush'ed should not be empty."

    if qpush_ret_code != 0:
        pop_applied_patch(patch_path, repo_dir)
        print 'You may have untracked .rej or .orig files in the repository.'
        print '`hg status` output of the repository of interesting files in ' + repo_dir + ' :'
        subprocess.check_call(['hg', '-R', repo_dir, 'status', '--modified', '--added',
                               '--removed', '--deleted'])
        raise Exception('Return code from `hg qpush` is: ' + str(qpush_ret_code))

    print("Patch qpush'ed. Continuing..."),
    return pname


def pop_applied_patch(patch, repo_dir):
    """Remove applied patch using `hg qpop` and `hg qdelete`."""
    qpop_output, qpop_ret_code = sps.captureStdout(['hg', '-R', repo_dir, 'qpop'], combineStderr=True,
                                                   ignoreStderr=True, ignoreExitCode=True)
    if qpop_ret_code != 0:
        print '`hg qpop` output is: ' + qpop_output
        raise Exception('Return code from `hg qpop` is: ' + str(qpop_ret_code))

    print "Patch qpop'ed...",
    subprocess.check_call(['hg', '-R', repo_dir, 'qdelete', os.path.basename(patch)])
    print "Patch qdelete'd."


def rev_date(repo_dir, rev):
    """
    Return the date of a rev as a date object
    """
    date_string = sps.captureStdout(['hg', '-R', repo_dir, 'log', '-r', rev, '--template', '{date|shortdate}\n'])[0]
    if re.match(r"\d{4}-\d{2}-\d{2}", date_string):
        return datetime.strptime(date_string, '%Y-%m-%d').date()

