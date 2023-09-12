import re
from configparser import NoOptionError, NoSectionError

import pytest

from autobisect import config


def test_config_init_no_config_file(tmp_path):
    """
    Initialize a config object with default settings
    """
    config.APP_CONFIG_DIR = tmp_path
    config.APP_CONFIG_FILE = tmp_path / "autobisect.ini"
    config.APP_CACHE_DIR = tmp_path

    config.DEFAULT_CONFIG = re.sub(
        r"(?<=storage-path: )(.+)", tmp_path.as_posix(), config.DEFAULT_CONFIG
    )
    result = config.BisectionConfig()
    assert result.db_path == tmp_path / "autobisect.db"
    assert result.persist is True
    assert result.persist_limit == 31457280000
    assert result.store_path == tmp_path


def test_config_init_with_predefined_config(tmp_path):
    """
    Initialize a config object with predefined settings
    """
    conf = tmp_path / "autobisect.ini"
    conf.write_text(re.sub(r"(?<=persist-limit: )(\d+)", "1000", config.DEFAULT_CONFIG))
    result = config.BisectionConfig(conf)
    assert result.persist_limit == 1048576000


def test_config_invalid_config_path(tmp_path):
    """
    Attempts to initialize a config object with a non-existent path
    """
    with pytest.raises(IOError, match="Invalid configuration file specified"):
        config.BisectionConfig(tmp_path / "foobar")


def test_config_init_with_invalid_configuration(tmp_path):
    """
    Attempt to initialize a config object with an invalid configuration
    """
    invalid = tmp_path / "invalid"
    invalid.touch()
    with pytest.raises((NoOptionError, NoSectionError)):
        config.BisectionConfig(invalid)


def test_config_init_with_non_existent_dir(tmp_path):
    """
    Attempt to initialize a config object with an invalid configuration
    """
    dir_path = tmp_path / "non-existent"
    config.APP_CONFIG_DIR = dir_path
    config.APP_CONFIG_FILE = dir_path / "autobisect.ini"
    config.APP_CACHE_DIR = dir_path
    config.BisectionConfig()
    assert dir_path.is_dir()
