import pytest

from consts import BOT_VERSION, VERSION_KEY
from item_location_handler import ItemLocations

test_guild_id = "test-guild-id"

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


@pytest.fixture
def fh():
    yield ItemLocations.fh
    import os

    filename = ItemLocations.fh._get_filename(test_guild_id)
    if os.path.exists(filename):
        os.remove(filename)


def test_find_matching_items(fh):
    item_locs = ItemLocations(test_guild_id)
    with pytest.raises(FileNotFoundError):
        item_locs.find_matches("foo")

    item_locs = ItemLocations(test_guild_id, v1_items)
    assert item_locs.find_matches("foo") == []
    assert item_locs.find_matches("kafeis") == ["Kafei's Mask"]
    assert item_locs.find_matches("Kafei's") == ["Kafei's Mask"]


def test_unknown_version(fh):
    # If version is unknown, ItemLocations should act like no file exists
    invalid_version_data = {
        VERSION_KEY: "foo",
        ItemLocations.DATA_KEY: v1_items,
    }
    fh.store(invalid_version_data, test_guild_id)

    item_locations = ItemLocations(test_guild_id)
    assert item_locations.items == {} and item_locations.aliases == {}
    item_locations.save()
    assert fh.load(test_guild_id) == {
        VERSION_KEY: BOT_VERSION,
        ItemLocations.DATA_KEY: {},
    }
