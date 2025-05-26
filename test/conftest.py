import os

import pytest

TEST_GUILD_ID = "test-guild-id"


@pytest.fixture(autouse=True)
def cleanup():
    yield

    for file in os.listdir():
        if file.startswith(TEST_GUILD_ID) and file.endswith(".json"):
            os.remove(file)
