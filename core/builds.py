# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Code originally taken from mozregression
# https://github.com/mozilla/mozregression/blob/5b986a3165a5208dd0722d6fc882b47e7fc1b627/mozregression/build_range.py

from __future__ import absolute_import, division, print_function

import copy
import logging
from datetime import timedelta

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

    def index(self, build):
        return self.builds.index(build)

    @classmethod
    def new(cls, start, end):
        """
        Creates a list of builds between two ranges
        :param start: A starting datetime object
        :type start: datetime.datetime
        :param end: An ending datetime object
        :type end: datetime.datetime
        :return: A BuildRange object
        """
        dates = []
        # Remove time date
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = end.replace(hour=0, minute=0, second=0, microsecond=0)
        delta = end - start
        for n in range(delta.days + 1):
            dates.append((start + timedelta(days=n)).strftime('%Y-%m-%d'))

        return BuildRange(dates)
