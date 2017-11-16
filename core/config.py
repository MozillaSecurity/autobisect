import logging
import os

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

log = logging.getLogger('browser-bisect')

CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.autobisect')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'autobisect.ini')

DEFAULT_CONFIG = """
[autobisect]
storage-path: %s
persist: true
; size in MBs
persist-limit: 5000
""" % CONFIG_DIR


class BisectionConfig(object):
    """
    Class for accessing configuration data and 'skip' revs
    """

    def __init__(self, config_file=None):
        """
        Initializes the object using either the specified config_file or creates a new database using default values
        :param config_file: A path to custom configuration file
        """

        if not config_file:
            config_file = self.create_default_config()

        if not os.path.isfile(config_file):
            raise IOError('Invalid configuration file specified')

        config_obj = configparser.ConfigParser()
        config_obj.read(config_file)

        try:
            self.persist = config_obj.getboolean('autobisect', 'persist')
            self.persist_limit = config_obj.getint('autobisect', 'persist-limit') * 1024 * 1024
            self.store_path = config_obj.get('autobisect', 'storage-path')
        except configparser.NoOptionError as e:
            log.critical('Unable to parser configuration file: %s', e.message)
            raise

        self.db_path = os.path.join(self.store_path, 'autobisect.db')

    @staticmethod
    def create_default_config():
        """
        Create a config file using default options and write to disk
        @return: A path to the newly created configuration file
        """
        if not os.path.isdir(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
        if not os.path.isfile(CONFIG_FILE):
            with open(CONFIG_FILE, 'w') as f:
                f.write(DEFAULT_CONFIG)

        return CONFIG_FILE
