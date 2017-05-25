#!/usr/bin/env python
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import


def first_line(s):
    """Return the first line of any series of text with / without line breaks."""
    return s.split('\n')[0]


def fuzz_dice(filename):
    """Return the lines of the file, except for the one line containing DICE."""
    before = []
    after = []
    with open(filename, 'rb') as f:
        for line in f:
            if line.find("DICE") != -1:
                break
            before.append(line)
        for line in f:
            after.append(line)
    return [before, after]


def fuzz_splice(filename):
    """Return the lines of a file, minus the ones between the two lines containing SPLICE."""
    before = []
    after = []
    with open(filename, 'rb') as f:
        for line in f:
            before.append(line)
            if line.find("SPLICE") != -1:
                break
        for line in f:
            if line.find("SPLICE") != -1:
                after.append(line)
                break
        for line in f:
            after.append(line)
    return [before, after]


def lines_with(lines, search):
    """Return the lines from an array that contain a given string."""
    matches = []
    for line in lines:
        if line.find(search) != -1:
            matches.append(line)
    return matches


def lines_starting_with(lines, search):
    """Return the lines from an array that start with a given string."""
    matches = []
    for line in lines:
        if line.startswith(search):
            matches.append(line)
    return matches


def truncate_mid(a, limit, insert):
    """Return a list with the middle portion removed, if it has more than limit*2 items."""
    if len(a) <= limit + limit:
        return a
    return a[0:limit] + insert + a[-limit:]


def write_lines_to_file(lines, filename):
    """Write lines to a given filename."""
    with open(filename, 'wb') as f:
        f.writelines(lines)
