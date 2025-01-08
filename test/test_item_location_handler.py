import os

import pytest

from consts import BOT_VERSION, VERSION_KEY
from hint_data import hint_data_filename
from item_locations import ItemLocations
from utils import HintType, load, store

test_guild_id = "test-guild-id"
item_locs_file = hint_data_filename(test_guild_id, HintType.ITEM)

v0_item_location_data = {
    "item1": {"name": "Kafei's Mask", "locations": [["location1"], ["location2"]]},
    "mask of scents": {
        "name": "Mask of Scents",
        "locations": [["location3"], ["location4"]],
    },
}

v1_items = {
    "kafeis mask": {
        ItemLocations.NAME_KEY: "Kafei's Mask",
        ItemLocations.RESULTS_KEY: [["location1"], ["location2"]],
    },
    "mask of scents": {
        ItemLocations.NAME_KEY: "Mask of Scents",
        ItemLocations.RESULTS_KEY: [["location3"], ["location4"]],
    },
}
v1_aliases = {
    "sniffa": "mask of scents",  # taken from STANDARD_ALIASES
    "kafei mask": "kafeis mask",  # added from generate_item_aliases
}
v1_item_location_data = {
    VERSION_KEY: BOT_VERSION,
    ItemLocations.DATA_KEY: v1_items,
}


@pytest.fixture(autouse=True)
def cleanup():
    yield

    for file in os.listdir():
        if file.startswith(test_guild_id) and file.endswith(".json"):
            os.remove(file)


def test_find_matching_items():
    item_locs = ItemLocations(test_guild_id)
    with pytest.raises(FileNotFoundError):
        item_locs.find_matches("foo")

    item_locs = ItemLocations(test_guild_id, v1_items)
    assert item_locs.find_matches("foo") == []
    assert item_locs.find_matches("kafeis") == ["Kafei's Mask"]
    assert item_locs.find_matches("Kafei's") == ["Kafei's Mask"]


def test_unknown_version():
    # If version is unknown, ItemLocations should act like no file exists
    invalid_version_data = {
        VERSION_KEY: "foo",
        ItemLocations.DATA_KEY: v1_items,
    }
    store(invalid_version_data, item_locs_file)

    item_locations = ItemLocations(test_guild_id)
    assert item_locations.items == {} and item_locations.aliases == {}
    item_locations.save()
    assert load(item_locs_file) == {
        VERSION_KEY: BOT_VERSION,
        ItemLocations.DATA_KEY: {},
    }
