# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Code originally taken from mozregression
# https://github.com/mozilla/mozregression/blob/5b986a3165a5208dd0722d6fc882b47e7fc1b627/mozregression/build_range.py

from __future__ import absolute_import, division, print_function

import copy
import logging

from util.fetch import Fetcher

log = logging.getLogger('builds')


class BuildRange(object):
    def __init__(self, builds):
        self._builds = builds

    def __len__(self):
        return len(self._builds)

    def __getslice__(self, smin, smax):
        new_range = copy.copy(self)
        new_range._builds = self._builds[smin:smax]
        return new_range

    def __getitem__(self, i):
        return self._builds[i].build_info

    @property
    def builds(self):
        return self._builds

    @property
    def mid_point(self):
        i = len(self) // 2
        return self._builds[i]

    def get_index(self, date):
        for build in self.builds:
            if build.date == date:
                i = self.builds.index(build)
                break

        assert(i is not None)

        return i


class Build(object):
    # ToDo: This should be updated to support more platforms, bits, repos, and build types
    def __init__(self, target, branch, date, asan, debug):
        self.date = date
        self.build_info = Fetcher(target, branch, str(date), asan, debug)
