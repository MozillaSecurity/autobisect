import random
from datetime import datetime, timedelta

from autobisect.builds import BuildRange


class MockBuild(object):
    """
    Class used for mocking builds
    """

    def __init__(self, build_info=None):
        self.build_info = build_info


def test_build_range_basic_operation():
    """
    Simple test
    """
    builds = BuildRange([1, 2, 3])
    assert len(builds) == 3
    assert builds.builds == [1, 2, 3]


def test_build_range_build_access_by_index():
    """
    Simple test to ensure build_range's __getitem__ returns the builds build_info property
    """
    info_keys = ["abc", "zyx", "foo", "bar"]
    builds = list(map(MockBuild, info_keys))
    build_range = BuildRange(builds)
    indices = list(range(len(build_range)))
    for index, key in zip(indices, info_keys):
        assert build_range[index] == key


def test_build_range_splice():
    """
    Test splicing of BuildRange
    """
    info_keys = ["abc", "zyx", "foo", "bar"]
    builds = list(map(MockBuild, info_keys))
    build_range = BuildRange(builds)
    copy = build_range[:2]
    assert len(copy) == 2
    assert copy[0] == "abc"
    assert copy[1] == "zyx"


def test_build_range_mid_point():
    """
    Test to ensure proper midpoint is returned
    """
    for i in range(10):
        mid_point = i // 2 if i > 0 else None
        assert BuildRange(list(range(i))).mid_point == mid_point


def test_build_range_indexing():
    """
    Test to ensure proper index is returned
    """
    info_keys = ["abc", "zyx", "foo", "bar"]
    builds = list(map(MockBuild, info_keys))
    build_range = BuildRange(builds)
    for k1, k2 in zip(build_range, info_keys):
        assert k1 == k2
    for index, build in zip(range(len(build_range)), builds):
        assert build_range.index(build) == index


def test_build_range_new_classmethod():
    """
    Simple test to ensure build range is expected length using new method
    """
    days = random.randint(1, 100)
    build_range = BuildRange.new(datetime.now(), datetime.now() + timedelta(days=days))
    assert len(build_range) == days + 1
