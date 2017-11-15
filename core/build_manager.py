from contextlib import contextmanager
import logging
import os
import shutil
import sqlite3

log = logging.getLogger('browser-bisect')


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
        try:
            self.con = sqlite3.connect(db_path)
            self.cur = self.con.cursor()
            self.cur.execute('BEGIN TRANSACTION')
            # Create table for tracking revisions to skip
            self.cur.execute('CREATE TABLE IF NOT EXISTS skips'
                             '(build_string TEXT, rev TEXT, UNIQUE(build_string, rev))')
            # Create table for tracking saved builds
            self.cur.execute('CREATE TABLE IF NOT EXISTS builds '
                             '(build_string TEXT, rev TEXT, size INT, use_count INT, UNIQUE(build_string, rev))')
            self.con.commit()
        except sqlite3.Error:
            raise Exception('Error connecting to database!')

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
        self._config = config
        self._build_string = build_string
        self.db = DatabaseManager(self._config.db_path)

    @staticmethod
    def get_build_size(build_path):
        """
        Recursively enumerate the size of the supplied build
        """
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(build_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return total_size

    def get_total_build_size(self):
        """
        Return the total size of all stored builds
        """
        res = self.db.cur.execute('SELECT SUM(size) FROM builds')
        size = res.fetchone()[0]

        return size if size else 0

    def get_build_count(self):
        """
        Return the total number of stored builds
        """
        res = self.db.cur.execute('SELECT COUNT(*) FROM builds')
        count = res.fetchone()[0]
        return count if count else 0

    def free_space(self, build_size):
        """
        Removes stored builds to make room for newer builds
        """
        self.db.cur.execute('BEGIN TRANSACTION')
        while self.get_total_build_size() + build_size > self._config.persist_limit:
            if self.get_build_count() == 0:
                break

            res = self.db.cur.execute('SELECT build_string, rev FROM builds WHERE use_count = 0')
            build_string, rev = res.fetchone()
            self.db.cur.execute('DELETE FROM builds WHERE build_string = ? AND rev = ?', (build_string, rev))
            build_dir = '%s-%s' % (build_string, rev)
            shutil.rmtree(os.path.join(self._config.store_path, build_dir))

        self.db.con.commit()

    @contextmanager
    def get_build(self, rev):
        """
        Retrieve the build matching the supplied revision
        :param rev: Revision of the requested build
        """
        self.db.cur.execute('UPDATE builds '
                            'SET use_count = use_count + 1 '
                            'WHERE build_string = ? AND rev = ?',
                            (self._build_string, rev))
        if self.db.cur.rowcount == 1:
            try:
                yield os.path.join(self._config.store_path, '%s-%s' % (self._build_string, rev))
            finally:
                self.db.cur.execute('UPDATE builds '
                                    'SET use_count = use_count - 1 '
                                    'WHERE build_string = ? AND rev = ?',
                                    (self._build_string, rev))
        else:
            yield None

    def store_build(self, rev, build_path):
        """
        Store the provided build
        :param rev: Revision of the supplied build
        :param build_path: Path to the supplied build
        """
        build_size = self.get_build_size(build_path)
        self.free_space(build_size)

        if self.get_total_build_size() + build_size < self._config.persist_limit:
            build_dest = os.path.join(self._config.store_path, '%s-%s' % (self._build_string, rev))
            self.db.cur.execute('INSERT INTO builds VALUES (?, ?, ?, ?)', (self._build_string, rev, build_size, 0))
            shutil.copytree(build_path, build_dest, symlinks=True)
