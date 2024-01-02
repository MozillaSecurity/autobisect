# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import configparser
import logging
from pathlib import Path
from typing import Optional

from platformdirs import user_config_dir, user_cache_dir

LOG = logging.getLogger("browser-bisect")

APP_CONFIG_DIR = Path(user_config_dir("autobisect"))
APP_CONFIG_FILE = APP_CONFIG_DIR / "autobisect.ini"
APP_CACHE_DIR = Path(user_cache_dir("autobisect"))

DEFAULT_CONFIG = f"""
[autobisect]
storage-path: {APP_CACHE_DIR}
persist: true
; size in MBs
persist-limit: 30000
"""


class BisectionConfig(object):
    """
    Class for accessing configuration data and 'skip' revs
    """

    def __init__(self, config_file: Optional[Path] = None):
        """
        Initializes the object using either the specified config_file or creates a new
        database using default values
        :param config_file: A path to custom configuration file
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
    def create_default_config() -> Path:
        """
        Create a config file using default options and write to disk
        :return: A path to the newly created configuration file
        :rtype: str
        """
        if not APP_CONFIG_DIR.is_dir():
            APP_CONFIG_DIR.mkdir(parents=True)
        if not APP_CONFIG_FILE.is_file():
            APP_CONFIG_FILE.write_text(DEFAULT_CONFIG)

        return APP_CONFIG_FILE
