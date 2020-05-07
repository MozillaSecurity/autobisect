# coding=utf-8
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Code originally taken from mozregression
# https://github.com/mozilla/mozregression/blob/5b986a3165a5208dd0722d6fc882b47e7fc1b627/mozregression/build_range.py

import copy
import logging
from datetime import timedelta

LOG = logging.getLogger("builds")


class BuildRange(object):
    """
    A class for storing a range of builds or build representations
    """

    def __init__(self, builds):
        """
        Instantiate a new instance

        param builds: A list of Fetcher.BuildTask objects
        """
        self._builds = builds

    def __len__(self):
        return len(self._builds)

    def __getitem__(self, expr):
        if isinstance(expr, slice):
            new_range = copy.copy(self)
            new_range._builds = self._builds[expr]
            return new_range

        return self._builds[expr]

    @property
    def builds(self):
        """
        Returns the "builds" list
        """
        return self._builds

    @property
    def mid_point(self):
        """
        Returns the midpoint of the "builds" list
        """
        if len(self) > 0:
            return self._builds[len(self) // 2]

        return None

    def index(self, build):
        """
        Returns the index of the provided build
        :param build: An object within the "builds" list
        """
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
        for offset in range(delta.days + 1):
            dates.append((start + timedelta(days=offset)).strftime("%Y-%m-%d"))

        return cls(dates)
