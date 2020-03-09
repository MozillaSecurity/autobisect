import re
import tempfile
from configparser import NoOptionError, NoSectionError
from pathlib import Path

import pytest

from autobisect import config


def test_config_init_no_config_file():
    """
    Initialize a config object with default settings
    """
    with tempfile.TemporaryDirectory() as dir_name:
        dir_path = Path(dir_name)
        config.CONFIG_DIR = dir_path
        config.CONFIG_FILE = dir_path / "autobisect.ini"
        config.DEFAULT_CONFIG = re.sub(
            r"(?<=storage-path: )(.+)", str(dir_path), config.DEFAULT_CONFIG
        )
        result = config.BisectionConfig()
        assert result.db_path == dir_path / "autobisect.db"
        assert result.persist is True
        assert result.persist_limit == 31457280000
        assert result.store_path == dir_path


def test_config_init_with_predefined_config():
    """
    Initialize a config object with predefined settings
    """
    with tempfile.NamedTemporaryFile() as file:
        with open(file.name, "w") as f:
            data = re.sub(r"(?<=persist-limit: )(\d+)", "1000", config.DEFAULT_CONFIG)
            f.write(data)
        result = config.BisectionConfig(file.name)
        assert result.persist_limit == 1048576000


def test_config_invalid_config_path():
    """
    Attempts to initialize a config object with a non-existent path
    """
    with tempfile.TemporaryDirectory() as dir_name:
        dead_file = Path(dir_name) / "foobar"
        with pytest.raises(IOError, match="Invalid configuration file specified"):
            config.BisectionConfig(dead_file)


def test_config_init_with_invalid_configuration():
    """
    Attempt to initialize a config object with an invalid configuration
    """
    with tempfile.NamedTemporaryFile() as file:
        with pytest.raises((NoOptionError, NoSectionError)):
            config.BisectionConfig(file.name)


def test_config_init_with_non_existent_dir():
    """
    Attempt to initialize a config object with an invalid configuration
    """
    with tempfile.TemporaryDirectory() as dir_name:
        dir_path = Path(dir_name) / "non-existent"
        config.CONFIG_DIR = dir_path
        config.CONFIG_FILE = dir_path / "autobisect.ini"
        config.BisectionConfig()
        assert Path.is_dir(dir_path)
