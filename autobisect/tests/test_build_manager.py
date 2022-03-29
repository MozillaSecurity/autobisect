import sqlite3
from pathlib import Path
from time import sleep

import pytest
from fuzzfetch import Fetcher, BuildFlags

from autobisect.build_manager import (
    BuildManager,
    DatabaseManager,
    BuildManagerException,
)


def test_database_manager_init_new_db(tmp_path):
    """Initialize new database instance"""
    db_path = tmp_path / "foo.db"
    db = DatabaseManager(db_path)
    assert db_path.is_file()
    assert isinstance(db.con, sqlite3.Connection)
    assert isinstance(db.cur, sqlite3.Cursor)


def test_database_manager_close(tmp_path):
    """Test that the connection is closed"""
    db = DatabaseManager(tmp_path / "foo.db")
    db.close()
    with pytest.raises(sqlite3.ProgrammingError) as e:
        db.cur.execute("SELECT * FROM FOO")

    assert str(e.value) == "Cannot operate on a closed database."


def test_database_manager_destructor(tmp_path):
    """Test that the database cursor is cleaned up on destruction"""
    db = DatabaseManager(tmp_path / "foo.db")
    ref = db.con
    del db

    with pytest.raises(sqlite3.ProgrammingError) as e:
        ref.execute("SELECT * FROM FOO")

    assert str(e.value) == "Cannot operate on a closed database."


def test_build_manager_init():
    """Initialize new BuildManager instance"""
    manager = BuildManager()
    assert manager.build_dir.is_dir()
    assert isinstance(manager.pid, int)
    assert isinstance(manager.db, DatabaseManager)


def test_build_manager_init_with_config(config_fixture):
    """Initialize new BuildManager instance with a config"""
    manager = BuildManager(config_fixture)
    assert manager.build_dir.is_dir()


def test_build_manager_build_size(config_fixture):
    """Simple test of BuildManager.build_size"""
    manager = BuildManager(config_fixture)
    total = 10
    for i in range(total):
        build_dir = Path(manager.build_dir / str(i))
        build_dir.mkdir()
        with Path(build_dir / "firefox").open("w+") as handler:
            handler.seek(1024 - 1)
            handler.write("x")
    assert manager.current_build_size == (4096 * total) + (1024 * total)


def test_build_manager_enumerate_builds(config_fixture):
    """Simple test of BuildManager.enumerate_builds"""
    manager = BuildManager(config_fixture)
    builds = []
    total = 10
    for i in range(total):
        build_dir = manager.build_dir / f"firefox_{i}"
        sleep(0.1)
        build_dir.mkdir()
        builds.append(build_dir)

    enumerated = manager.enumerate_builds()
    assert len(enumerated) == total
    for x, y in zip(enumerated, builds):
        assert x == y


def test_build_manager_remove_old_builds(config_fixture):
    """Simple test of BuildManager.remove_old_builds"""
    manager = BuildManager(config_fixture)
    total = 10
    for i in range(total):
        build_dir = manager.build_dir / f"firefox_{i}"
        build_dir.mkdir()
        with Path(build_dir / "firefox").open("w+") as handler:
            handler.seek(1024 * 1024 - 1)
            handler.write("x")

    manager.remove_old_builds()
    # With the total file size and directory size,
    # the result should be one less than half
    expected = total / 2 - 1
    assert len(manager.enumerate_builds()) == expected
    assert manager.current_build_size == (4096 * expected) + (1024 * 1024 * expected)


def test_build_manager_remove_old_builds_in_use(config_fixture):
    """Test that in_use builds are not removed"""
    manager = BuildManager(config_fixture)
    total = 5
    for i in range(total):
        build_dir = manager.build_dir / f"firefox_{i}"
        build_dir.mkdir()
        build_path = build_dir / "firefox"
        with build_path.open("w+") as handler:
            handler.seek(1024 * 1024 - 1)
            handler.write("x")
        if i != 0:
            # Mark all builds other than the first as in_use
            manager.db.cur.execute(
                "INSERT INTO in_use VALUES (?, ?)", (str(build_dir), 1)
            )
            manager.db.con.commit()

    manager.remove_old_builds()
    assert manager.build_dir / "firefox_0" not in manager.enumerate_builds()


@pytest.mark.usefixtures("requests_mock_cache")
def test_build_manager_get_build(mocker, config_fixture):
    """Simple test of BuildManager.get_build"""
    manager = BuildManager(config_fixture)
    flags = BuildFlags(*[False for _ in range(8)])
    fetcher = Fetcher("central", "latest", flags)
    extract_build = mocker.patch.object(Fetcher, "extract_build")

    execute = manager.db.cur.execute
    with manager.get_build(fetcher, "firefox") as build:
        assert build is not None
        assert extract_build.call_count == 1
        # The build should be marked as in_use
        res = execute("SELECT * FROM in_use WHERE build_path == ?", (str(build),))
        assert res.fetchone() is not None

    # The build should no longer be marked as in_use
    res = execute("SELECT * FROM in_use WHERE build_path == ?", (str(build),))
    assert res.fetchone() is None


def test_database_manager_fails_to_extract(config_fixture):
    """Test that the build manager raised the proper exception when failing to extract target"""
    manager = BuildManager(config_fixture)
    flags = BuildFlags(*[False for _ in range(8)])
    build = "gecko.v2.mozilla-central.latest.firefox.sm-linux64-asan-opt"
    fetcher = Fetcher("central", build, flags)
    with pytest.raises(BuildManagerException) as e:
        with manager.get_build(fetcher, "firefox") as build:
            pass

    assert str(e.value) == "Failed to extract build."
