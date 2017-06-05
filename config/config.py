#!/usr/bin/env python
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import, division, print_function
import platform


class Config(object):
    def __init__(self, target):
        self.target = target

        self._last_known_good = None
        self._known_broken = None

    @property
    def last_known_good(self):
        if self._last_known_good is not None:
            return self._last_known_good

        if self.target == 'firefox':
            if platform.system() == 'Linux':
                self._last_known_good = '942b0d89bef0'
            else:
                raise OSError('Platform is unsupported')

        return self._last_known_good

    @property
    def known_broken(self):
        if self._known_broken is not None:
            return self._known_broken

        if platform.system() == "Linux":
            self._known_broken = [
                'b9caaf6c527f:54654348e033'
            ]
        else:
            raise OSError('Platform is unsupported')

        return self._known_broken

