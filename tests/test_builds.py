import random
from datetime import datetime, timedelta

from autobisect.builds import BuildRange


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
    builds = ["abc", "zyx", "foo", "bar"]
    build_range = BuildRange(builds)
    for index, key in enumerate(builds, start=0):
        assert build_range[index] == key


def test_build_range_splice():
    """
    Test splicing of BuildRange
    """
    builds = ["abc", "zyx", "foo", "bar"]
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
    builds = ["abc", "zyx", "foo", "bar"]
    build_range = BuildRange(builds)
    for k1, k2 in zip(build_range, builds):
        assert k1 == k2
    for index, build in enumerate(builds, start=0):
        assert build_range.index(build) == index


def test_build_range_new_classmethod():
    """
    Simple test to ensure build range is expected length using new method
    """
    days = random.randint(1, 100)
    build_range = BuildRange.new(datetime.now(), datetime.now() + timedelta(days=days))
    assert len(build_range) == days + 1
