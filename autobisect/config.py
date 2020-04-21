# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import configparser
import logging
from pathlib import Path

LOG = logging.getLogger("browser-bisect")

CONFIG_DIR = Path.home() / ".autobisect"
CONFIG_FILE = CONFIG_DIR / "autobisect.ini"

DEFAULT_CONFIG = (
    """
[autobisect]
storage-path: %s
persist: true
; size in MBs
persist-limit: 30000
"""
    % CONFIG_DIR
)


class BisectionConfig(object):
    """
    Class for accessing configuration data and 'skip' revs
    """

    def __init__(self, config_file=None):
        """
        Initializes the object using either the specified config_file or creates a new
        database using default values
        :param config_file: A path to custom configuration file
        :type config_file: str
        """

        if not config_file:
            config_file = self.create_default_config()
        elif not Path(config_file).is_file():
            raise IOError("Invalid configuration file specified")

        config_obj = configparser.ConfigParser()
        config_obj.read(config_file)

        try:
            self.persist = config_obj.getboolean("autobisect", "persist")
            persist_limit = (
                config_obj.getint("autobisect", "persist-limit") * 1024 * 1024
            )
            self.persist_limit = persist_limit if self.persist else 0
            self.store_path = Path(config_obj.get("autobisect", "storage-path"))
        except (configparser.NoOptionError, configparser.NoSectionError) as e:
            LOG.critical("Unable to parse configuration file: %s", e.message)
            raise

        self.db_path = self.store_path / "autobisect.db"

    @staticmethod
    def create_default_config():
        """
        Create a config file using default options and write to disk
        :return: A path to the newly created configuration file
        :rtype: str
        """
        if not CONFIG_DIR.is_dir():
            CONFIG_DIR.mkdir(parents=True)
        if not CONFIG_FILE.is_file():
            CONFIG_FILE.write_text(DEFAULT_CONFIG)

        return str(CONFIG_FILE)
