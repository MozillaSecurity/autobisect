# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# Taken from:
#  https://github.com/MozillaSecurity/fuzzfetch/blob/1a930d7/tests/conftest.py
import gzip
import logging
import os
import re
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

import pytest
import requests_mock

from autobisect.config import DEFAULT_CONFIG

BUILD_CACHE = os.getenv("BUILD_CACHE") == "1"  # set BUILD_CACHE=1 to populate cache
CACHE_PATH = Path(__file__).resolve().parent  # store cache alongside this file
LOG = logging.getLogger("fetcher_cb")
# hosts to cache requests for
# this will create directories like f"mock-{key}"
MOCK_HOSTS = {
    "firefoxci": "https://firefox-ci-tc.services.mozilla.com",
    "hg": "https://hg.mozilla.org",
    "product-details": "https://product-details.mozilla.org",
    "queue": "https://queue.taskcluster.net",
}


def _translate_to_path(url):
    assert url.split("://")[0] in {"http", "https"}, f"unhandled protocol: {url}"
    for mock, host in MOCK_HOSTS.items():
        url = url.replace(host, f"mock-{mock}")
    assert url.startswith("mock-"), f"unmocked URL: {url}"
    return CACHE_PATH / quote(url)


def _cache_requests(request, context):
    """
    request handler for requests.mock
    """
    LOG.debug("%s %r", request.method, request.url)
    path = _translate_to_path(request.url)
    if path.is_file():
        context.status_code = 200
        data = path.read_bytes()
        LOG.debug("-> 200 (%d bytes from %s)", len(data), path)
        return data
    if path.is_dir() and (path / ".get").is_file():
        path = path / ".get"
        context.status_code = 200
        data = path.read_bytes()
        LOG.debug("-> 200 (%d bytes from %s)", len(data), path)
        return data
    # download to cache in mock directories
    if BUILD_CACHE:
        folder = path.parent
        try:
            if not folder.is_dir():
                folder.mkdir(parents=True)
        except OSError:
            # see if any of the leaf folders are actually files
            while folder.resolve() != CACHE_PATH:
                if folder.is_file():
                    # need to rename
                    tmp_folder = folder.parent / (folder.name + ".tmp")
                    folder.rename(tmp_folder)
                    path.parent.mkdir(parents=True)
                    tmp_folder.rename(folder / ".get")
                    break
                folder = folder.parent
        urllib_request = Request(
            request.url,
            request.body if request.method == "POST" else None,
            request.headers,
        )
        try:
            with urlopen(urllib_request) as real_http:
                data = real_http.read()
                if data[:2] == b"\x1f\x8b":  # gzip magic number
                    data = gzip.decompress(data)  # pylint: disable=no-member
                path.write_bytes(data)
                context.status_code = real_http.getcode()
                LOG.debug("-> %d (%d bytes from http)", context.status_code, len(data))
                return data
        except HTTPError as exc:
            context.status_code = exc.code
            return None
    context.status_code = 404
    LOG.debug("-> 404 (at %s)", path)
    return None


@pytest.fixture
def requests_mock_cache():
    """create/use a cache of all requests defined in MOCK_HOSTS

    use env BUILD_CACHE=1 to populate the cache

    the cache is stored in CACHE_PATH/mock-*
    """
    with requests_mock.Mocker() as req_mock:
        req_mock.register_uri(
            requests_mock.ANY, requests_mock.ANY, content=_cache_requests
        )
        yield req_mock


@pytest.fixture
def config_fixture(tmp_path):
    """A mock configuration file"""
    config_data = re.sub(
        r"(?<=storage-path: )(.+)", tmp_path.as_posix(), DEFAULT_CONFIG
    )
    config_data = re.sub(r"(?<=persist-limit: )(.+)", "5", config_data)
    config_path = tmp_path / "autobisect.ini"
    config_path.write_text(config_data)

    return config_path
