import gzip
import logging
import os

LOG = logging.getLogger("fetcher_cb")

BUILD_CACHE = False

if BUILD_CACHE:
    assert str is not bytes, "cache update requires Python 3"
    from urllib.error import HTTPError  # pylint: disable=import-error,no-name-in-module
    from urllib.request import (
        Request,
        urlopen,
    )  # pylint: disable=import-error,no-name-in-module


def fetcher_mock(request, context):
    """
    request handler for requests.mock

    Taken from:
    https://github.com/MozillaSecurity/fuzzfetch/blob/3ab3121a5192e5e9aaa251caedd6d6e413996ec5/tests/test_fetch.py#L119
    """
    LOG.debug("%s %r", request.method, request.url)
    assert request.url.startswith("https://")
    current_path = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(
        current_path,
        request.url.replace(
            "https://firefox-ci-tc.services.mozilla.com", "mock-firefoxci"
        )
        .replace("https://hg.mozilla.org", "mock-hg")
        .replace("https://index.taskcluster.net", "mock-index")
        .replace("https://product-details.mozilla.org", "mock-product-details")
        .replace("https://queue.taskcluster.net", "mock-queue")
        .replace("/", os.sep),
    )
    if os.path.isfile(path):
        context.status_code = 200
        with open(path, "rb") as resp_fp:
            data = resp_fp.read()
        LOG.debug("-> 200 (%d bytes from %s)", len(data), path)
        return data
    if os.path.isdir(path) and os.path.isfile(os.path.join(path, ".get")):
        path = os.path.join(path, ".get")
        context.status_code = 200
        with open(path, "rb") as resp_fp:
            data = resp_fp.read()
        LOG.debug("-> 200 (%d bytes from %s)", len(data), path)
        return data
    # download to cache in mock directories
    if BUILD_CACHE:
        folder = os.path.dirname(path)
        try:
            if not os.path.isdir(folder):
                os.makedirs(folder)
        except OSError:
            # see if any of the leaf folders are actually files
            orig_folder = folder
            while os.path.abspath(folder) != os.path.abspath(current_path):
                if os.path.isfile(folder):
                    # need to rename
                    os.rename(folder, folder + ".tmp")
                    os.makedirs(orig_folder)
                    os.rename(folder + ".tmp", os.path.join(folder, ".get"))
                    break
                folder = os.path.dirname(folder)
        urllib_request = Request(
            request.url,
            request.body if request.method == "POST" else None,
            request.headers,
        )
        try:
            real_http = urlopen(urllib_request)
        except HTTPError as exc:
            context.status_code = exc.code
            return None
        data = real_http.read()
        if data[:2] == b"\x1f\x8b":  # gzip magic number
            data = gzip.decompress(data)  # pylint: disable=no-member
        with open(path, "wb") as resp_fp:
            resp_fp.write(data)
        context.status_code = real_http.getcode()
        LOG.debug("-> %d (%d bytes from http)", context.status_code, len(data))
        return data
    context.status_code = 404
    LOG.debug("-> 404 (at %s)", path)
    return None
