# coding=utf-8
from collections import namedtuple
from contextlib import contextmanager
import logging
import os
import shutil
import sqlite3
import time

log = logging.getLogger('browser-bisect')
Build = namedtuple('Build', ('path', 'stats'))


class DatabaseManager(object):
    """
    Sqlite3 wrapper class
    """
    def __init__(self, db_path):
        self.con = None
        self.cur = None
        self.open(db_path)

    def open(self, db_path):
        """
        Opens and initializes the sqlite3 database
        :param db_path: Path to the sqlite3 database
        :type db_path: str
        """
        self.con = sqlite3.connect(db_path)
        self.cur = self.con.cursor()
        self.cur.execute('CREATE TABLE IF NOT EXISTS in_use (build_path, pid INT)')
        self.cur.execute('CREATE TABLE IF NOT EXISTS download_queue (build_path TEXT primary key, pid INT)')

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
    def __init__(self, config, build_string):
        self.config = config
        self.build_prefix = build_string

        self.build_dir = os.path.join(self.config.store_path, 'builds')
        if not os.path.isdir(self.build_dir):
            os.makedirs(self.build_dir)

        self.pid = os.getpid()
        self.db = DatabaseManager(self.config.db_path)

    @property
    def current_build_size(self):
        """
        Recursively enumerate the size of the supplied build
        """
        total_size = 0
        for dirpath, _, filenames in os.walk(self.build_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total_size += os.path.getsize(fp)
                except OSError:
                    log.debug('Directory became inaccessible while iterating: %s', fp)

        return total_size

    def enumerate_builds(self):
        """
        Enumerate all available builds including their size and stats
        """
        builds = []
        for build in os.listdir(self.build_dir):
            build_path = os.path.join(self.build_dir, build)
            build_stats = os.stat(build_path)
            builds.append(Build(build_path, build_stats))

        return sorted(builds, key=lambda b: b.stats.st_atime)

    def remove_old_builds(self):
        """
        Removes stored builds to make room for newer builds
        """
        while self.current_build_size > self.config.persist_limit:
            builds = self.enumerate_builds()
            for build in builds:
                if self.current_build_size < self.config.persist_limit:
                    break

                self.db.cur.execute('BEGIN TRANSACTION')
                res = self.db.cur.execute('SELECT * FROM in_use, download_queue '
                                          'WHERE in_use.build_path = ? OR download_queue.build_path = ?',
                                          (build.path, build.path))
                if res.fetchone() is None:
                    shutil.rmtree(build.path)
                self.db.con.commit()

            time.sleep(0.1)

    @contextmanager
    def get_build(self, build):
        """
        Retrieve the build matching the supplied revision
        :param build: A fuzzFetch.Fetcher build object
        """
        target_path = os.path.join(self.build_dir, '%s-%s' % (self.build_prefix, build.changeset))

        try:
            # Insert build_path into in_use to prevent deletion
            self.db.cur.execute('INSERT INTO in_use VALUES (?, ?)', (target_path, self.pid))

            # Try to insert the build_path into download_queue
            # If the insert fails, another process is already downloading it
            # Poll the database until it complete
            try:
                self.db.cur.execute('INSERT OR IGNORE INTO download_queue VALUES (?, ?)', (target_path, self.pid))
                if self.db.cur.rowcount == 1:
                    # If the build doesn't exist on disk, download it
                    if not os.path.isdir(target_path):
                        self.remove_old_builds()
                        while True:
                            # Hackish - FuzzFetch can fail when downloading - try until success
                            try:
                                build.extract_build(target_path)
                                break
                            except:  # ToDo: Add the correct exception to catch
                                pass
                else:
                    while True:
                        res = self.db.cur.execute('SELECT * FROM download_queue WHERE build_path = ?', (target_path,))
                        if res.fetchone() is None:
                            break
                        else:
                            time.sleep(0.1)
            finally:
                self.db.cur.execute('DELETE FROM download_queue WHERE build_path = ? AND pid = ?',
                                    (target_path, self.pid))

            yield target_path
        finally:
            self.db.cur.execute('DELETE FROM in_use WHERE build_path = ? AND pid = ?', (target_path, self.pid))
