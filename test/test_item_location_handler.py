import pytest

from consts import BOT_VERSION, ITEM_LOCATIONS_FILENAME_SUFFIX, VERSION_KEY
from item_location_handler import (
    ALIASES_KEY,
    ITEM_LOCATIONS_KEY,
    ITEM_NAME_KEY,
    ITEMS_KEY,
    get_item_location_data,
)
from utils import FileHandler

test_guild_id = "test-guild-id"

v0_item_location_data = {
    "item1": {"name": "Kafei's Mask", "locations": [["location1"], ["location2"]]},
    "mask of scents": {
        "name": "Mask of Scents",
        "locations": [["location3"], ["location4"]],
    },
}


@pytest.fixture
def fh():
    fh = FileHandler(ITEM_LOCATIONS_FILENAME_SUFFIX)
    yield fh
    import os

    filename = fh._get_filename(test_guild_id)
    if os.path.exists(filename):
        os.remove(filename)


def test_update_version(fh):
    # Calling get_item_location_data should gracefully update old data formats to the current version format
    fh.store(v0_item_location_data, test_guild_id)
    expected_updated_data = {
        VERSION_KEY: BOT_VERSION,
        ITEMS_KEY: {
            "kafeis mask": {
                ITEM_NAME_KEY: "Kafei's Mask",
                ITEM_LOCATIONS_KEY: [["location1"], ["location2"]],
            },
            "mask of scents": {
                "name": "Mask of Scents",
                "locations": [["location3"], ["location4"]],
            },
        },
        ALIASES_KEY: {
            "sniffa": "mask of scents",  # taken from STANDARD_ALIASES
            "kafei mask": "kafeis mask",  # added from generate_item_aliases
        },
    }
    assert get_item_location_data(test_guild_id) == expected_updated_data
    assert fh.load(test_guild_id) == expected_updated_data
