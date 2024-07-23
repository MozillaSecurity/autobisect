# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import re

import pytest

from autobisect.config import DEFAULT_CONFIG


@pytest.fixture(scope="module")
def vcr_config():
    return {
        "decode_compressed_response": True,
    }


@pytest.fixture
def config_fixture(tmp_path):
    """A mock configuration file."""
    config_data = re.sub(
        r"(?<=storage-path: )(.+)",
        tmp_path.as_posix(),
        DEFAULT_CONFIG,
    )
    config_data = re.sub(r"(?<=persist-limit: )(.+)", "5", config_data)
    config_path = tmp_path / "autobisect.ini"
    config_path.write_text(config_data)

    return config_path
