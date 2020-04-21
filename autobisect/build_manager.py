# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import logging
import os
import shutil
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from .config import BisectionConfig

LOG = logging.getLogger("build-manager")


class DatabaseManager(object):
    """
    Sqlite3 wrapper class
    """

    def __init__(self, db_path):
        self.con = None
        self.cur = None
        self.open(str(db_path))

    def open(self, db_path):
        """
        Opens and initializes the sqlite3 database
        :param db_path: Path to the sqlite3 database
        :type db_path: str
        """
        self.con = sqlite3.connect(db_path)
        self.cur = self.con.cursor()
        self.cur.execute("CREATE TABLE IF NOT EXISTS in_use (build_path, pid INT)")
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS download_queue (build_path TEXT primary key, pid INT)"
        )

    def close(self):
        """
        Closes the sqlite3 database
        """
        if self.con:
            self.con.commit()
            self.con.close()

    def __del__(self):
        self.close()


class BuildManager(object):
    """
    A class for managing downloaded builds
    """

    def __init__(self, config=None):
        self.config = config or BisectionConfig()
        self.build_dir = self.config.store_path / "builds"
        if not Path.is_dir(self.build_dir):
            os.makedirs(self.build_dir)

        self.pid = os.getpid()
        self.db = DatabaseManager(self.config.db_path)

    @property
    def current_build_size(self):
        """
        Recursively enumerate the size of the supplied build
        """
        return sum(
            [os.path.getsize(f) for f in self.build_dir.rglob("*") if os.path.isfile(f)]
        )

    def enumerate_builds(self):
        """
        Enumerate all available builds including their size and stats
        """
        builds = [os.fspath(x) for x in self.build_dir.iterdir() if x.is_dir()]
        return sorted(builds, key=lambda b: os.stat(b).st_atime)

    def remove_old_builds(self):
        """
        Removes stored builds to make room for newer builds
        """
        while self.current_build_size > self.config.persist_limit:
            builds = self.enumerate_builds()
            for build_path in builds:
                if self.current_build_size < self.config.persist_limit:
                    break

                res = self.db.cur.execute(
                    "SELECT * FROM in_use, download_queue "
                    "WHERE in_use.build_path = ? OR download_queue.build_path = ?",
                    (build_path, build_path),
                )
                if res.fetchone() is None:
                    LOG.debug("Removing build: %s", build_path)
                    shutil.rmtree(build_path)
                self.db.con.commit()

            time.sleep(0.1)

    @contextmanager
    def get_build(self, build):
        """
        Retrieve the build matching the supplied revision
        :param build: A fuzzFetch.Fetcher build object
        """
        # pylint: disable=protected-access
        target = "js" if build._memo["_target"] == "js" else "ff"
        branch = "m-%s" % build._branch[0]
        platform = build._platform.system
        flags = build._flags.build_string()
        rev = build.changeset[:12]
        build_name = "%s-%s-%s%s-%s" % (target, branch, platform, flags, rev)
        target_path = self.build_dir / build_name.lower()
        path_string = os.fspath(target_path)

        try:
            # Insert build_path into in_use to prevent deletion
            self.db.cur.execute(
                "INSERT INTO in_use VALUES (?, ?)", (path_string, self.pid)
            )
            self.db.con.commit()

            # Try to insert the build_path into download_queue
            # If the insert fails, another process is already downloading it
            # Poll the database until it complete
            try:
                self.db.cur.execute(
                    "INSERT into download_queue VALUES (?, ?)", (path_string, self.pid)
                )
                self.db.con.commit()
                # If the build doesn't exist on disk, download it
                if not Path.is_dir(target_path):
                    self.remove_old_builds()
                    build.extract_build(target_path)
            except sqlite3.IntegrityError:
                LOG.warning(
                    "Another process is attempting to download the build. Waiting"
                )
                while True:
                    res = self.db.cur.execute(
                        "SELECT * FROM download_queue WHERE build_path = ?",
                        (path_string,),
                    )
                    if res.fetchone() is None:
                        break

                    time.sleep(0.1)
            finally:
                self.db.cur.execute(
                    "DELETE FROM download_queue WHERE build_path = ? AND pid = ?",
                    (path_string, self.pid),
                )
                self.db.con.commit()

            yield target_path
        finally:
            self.db.cur.execute(
                "DELETE FROM in_use WHERE build_path = ? AND pid = ?",
                (path_string, self.pid),
            )
            self.db.con.commit()
