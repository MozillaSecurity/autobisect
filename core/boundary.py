from __future__ import absolute_import, division, print_function

import os
import re

from util import hgCmds


class Boundary(object):
    def __init__(self, date, revision):
        self.date = date
        self.rev = revision

    @classmethod
    def new(cls, revision, repo_dir):
        if not re.match(r'(tip)|(?=[0-9A-Fa-f]*$)(?:.{12}|.{40})', revision, re.IGNORECASE):
            raise Exception('Invalid revision specified')

        if not os.path.isdir(repo_dir):
            raise Exception('Invalid repository specified')

        revision = hgCmds.get_full_hash(repo_dir, revision)
        date = hgCmds.rev_date(repo_dir, revision)

        return Boundary(date, revision)
