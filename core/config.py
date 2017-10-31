import logging
import os
import platform
import shutil
import sqlite3

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

log = logging.getLogger('browser-bisect')

CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.autobisect')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'autobisect.ini')
STORAGE_PATH = os.path.join(CONFIG_DIR, 'builds')

DEFAULT_CONFIG = """
[autobisect]
storage-type: local
storage-path: %s
persist: true
persist-limit: 0
""" % STORAGE_PATH


def create_default_config():
    """
    Create a config file using default options and write to disk
    @return: A path to the newly created configuration file
    """
    if not os.path.isdir(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    if not os.path.isdir(STORAGE_PATH):
        os.makedirs(STORAGE_PATH)
    if not os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f:
            f.write(DEFAULT_CONFIG)

    return CONFIG_FILE


class BisectionConfig(object):
    """
    Class for accessing configuration data and 'skip' revs
    """
    def __init__(self, target, branch, config_file=None):
        """
        Initializes the object using either the specified config_file or creates a new database using default values
        :param target: The build target currently being bisected
        :param config_file: A path to custom configuration file
        """

        if not config_file:
            config_file = create_default_config()

        config_obj = configparser.ConfigParser()
        config_obj.read(config_file)

        try:
            persist = config_obj.getboolean('autobisect', 'persist')
            limit = config_obj.get('autobisect', 'persist-limit')
            store_path = config_obj.get('autobisect', 'storage-path')
        except configparser.NoOptionError as e:
            log.critical('Unable to parser configuration file: %s', e.message)
            raise

        self.persist = Persistence(store_path, target, branch, limit) if persist else None
        self.skipdb = SkipDB(store_path, target, branch)


class SkipDB(object):
    """
    A wrapper for an sqlite3 database responsbile for storing 'skip' revisions
    """
    def __init__(self, path, target, branch):
        self.target = target
        self.branch = branch
        self.platform = platform.system().lower()

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
            self.conn = sqlite3.connect(os.path.join(path, 'skip.db'))
            self.cursor = self.conn.cursor()
            self.cursor.execute('CREATE TABLE IF NOT EXISTS skips'
                                '(target TEXT, platform TEXT, branch TEXT, rev TEXT, '
                                'UNIQUE(target, platform, branch, rev))')
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
            self.cursor.execute('SELECT COUNT(*) FROM skips '
                                'WHERE target = ? AND platform = ? AND branch = ? AND rev = ?',
                                (self.target, self.platform, self.branch, rev))
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
        self.cursor.execute('INSERT OR IGNORE INTO skips VALUES (?, ?, ?, ?)',
                            (self.target, self.platform, self.branch, rev))
        self.conn.commit()


class Persistence(object):
    def __init__(self, root, target, branch, limit):
        self.root = root
        self.target = target
        self.branch = branch
        self.platform = platform.system().lower()
        self.store_path = os.path.join(self.root, self.target, self.platform, self.branch)

        if not os.path.isdir(self.store_path):
            os.makedirs(self.store_path)

    def get_build(self, rev):
        # ToDo: This approach will not work with concurrent instances!
        # Available builds need to be stored in a database in order to prevent race conditions
        build_path = os.path.join(self.store_path, rev)
        if os.path.isdir(build_path):
            return str(build_path)

    def save_build(self, rev, src_path):
        build_path = os.path.join(self.store_path, rev)
        if not os.path.isdir(build_path):
            shutil.copytree(src_path, build_path, symlinks=True)
