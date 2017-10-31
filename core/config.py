import os
import platform
import sqlite3
import logging

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

log = logging.getLogger('browser-bisect')

CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.autobisect')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'autobisect.json')
BUILD_DIR = os.path.join(CONFIG_DIR, 'builds')
SKIPDB = os.path.join(CONFIG_DIR, 'skip.db')

DEFAULT_CONFIG = """
[autobisect]
storage-type: local
storage-path: %s
persist: False
persist-limit: 0
skipdb: %s
""" % (BUILD_DIR, SKIPDB)


def create_default_config():
    """
    Create a config file using default options and write to disk
    @return: A path to the newly created configuration file
    """
    if not os.path.isdir(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    if not os.path.isdir(BUILD_DIR):
        os.makedirs(BUILD_DIR)
    if not os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f:
            f.write(DEFAULT_CONFIG)

    return CONFIG_FILE


class BisectionConfig(object):
    """
    Class for accessing configuration data and 'skip' revs
    """
    def __init__(self, target, config_file=None):
        """
        Initializes the object using either the specified config_file or a new database
        :param target: The build target currently being bisected
        :param config_file: A path to custom configuration file
        """
        self._build_type = "%s_%s_%s" % (target, platform.system(), platform.machine())

        if not config_file:
            config_file = create_default_config()

        config_obj = configparser.ConfigParser()
        config_obj.read(config_file)

        try:
            self.persist = config_obj.get('autobisect', 'persist')
            self.perist_limit = config_obj.get('autobisect', 'persist-limit')
            self.build_dir = config_obj.get('autobisect', 'storage-path')
            self.skipdb = SkipDB(config_obj.get('autobisect', 'skipdb'), self._build_type)
        except configparser.NoOptionError as e:
            log.critical('Unable to parser configuration file: %s', e.message)
            raise


class SkipDB(object):
    """
    A wrapper for an sqlite3 database responsbile for storing 'skip' revisions
    """
    def __init__(self, path, build_type):
        self._build_type = build_type
        self.conn = None
        self.cursor = None
        self.open(path)

    def open(self, path):
        """
        Opens and initializes the sqlite3 database
        :param path: Path to the sqlite3 databasse
        :type path: str
        """
        try:
            self.conn = sqlite3.connect(path)
            self.cursor = self.conn.cursor()
            self.cursor.execute('CREATE TABLE IF NOT EXISTS skips (rev TEXT, type TEXT, UNIQUE(rev, type))')
        except sqlite3.Error:
            raise Exception('Error connecting to database!')

    def close(self):
        """
        Closes the sqlite3 database
        """
        if self.conn:
            self.conn.commit()
            self.cursor.close()
            self.conn.close()

    def includes(self, rev):
        """
        Checks if the requested rev has been marked as 'skip' for the selected build_type
        :param rev: SHA1 revision
        :type rev: str
        
        :return: Result of revision check
        :rtype: boolean
        """
        try:
            self.cursor.execute('SELECT COUNT(*) FROM skips WHERE rev = ? AND type = ?', (self._build_type, rev))
            res = self.cursor.fetchone()
            if res[0] > 0:
                return True
        except sqlite3.OperationalError:
            pass

        return False

    def add(self, rev):
        """
        Add 'skip' rev to the skidb
        :param rev: SHA1 revision
        :type rev: str 
        """
        self.cursor.execute('BEGIN TRANSACTION')
        self.cursor.execute('INSERT OR IGNORE INTO skips VALUES (?, ?)', (self._build_type, rev))
        self.conn.commit()
