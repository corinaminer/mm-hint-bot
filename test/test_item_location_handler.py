import pytest

from consts import BOT_VERSION, VERSION_KEY
from item_location_handler import ItemLocations, get_item_locations, set_item_locations

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
        ItemLocations.ITEM_NAME_KEY: "Kafei's Mask",
        ItemLocations.ITEM_LOCATIONS_KEY: [["location1"], ["location2"]],
    },
    "mask of scents": {
        "name": "Mask of Scents",
        "locations": [["location3"], ["location4"]],
    },
}
v1_aliases = {
    "sniffa": "mask of scents",  # taken from STANDARD_ALIASES
    "kafei mask": "kafeis mask",  # added from generate_item_aliases
}
v1_item_location_data = {
    VERSION_KEY: BOT_VERSION,
    ItemLocations.ITEMS_KEY: v1_items,
    ItemLocations.ALIASES_KEY: v1_aliases,
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
        item_locs.find_matching_items("foo")

    set_item_locations(v1_items, test_guild_id)
    item_locs = get_item_locations(test_guild_id)
    assert item_locs.find_matching_items("foo") == []
    assert item_locs.find_matching_items("kafeis") == ["Kafei's Mask"]
    assert item_locs.find_matching_items("Kafei's") == ["Kafei's Mask"]


def test_update_version_v0(fh):
    # Initiating ItemLocations should gracefully update old data formats to the current version format
    fh.store(v0_item_location_data, test_guild_id)
    item_locations = ItemLocations(test_guild_id)
    assert item_locations.items == v1_items
    assert item_locations.aliases == v1_aliases
    assert fh.load(test_guild_id) == v1_item_location_data


def test_unknown_version(fh):
    # If version is unknown, ItemLocations should act like no file exists
    invalid_version_data = {
        VERSION_KEY: "foo",
        ItemLocations.ITEMS_KEY: v1_items,
        ItemLocations.ALIASES_KEY: v1_aliases,
    }
    fh.store(invalid_version_data, test_guild_id)

    item_locations = ItemLocations(test_guild_id)
    assert item_locations.items == {} and item_locations.aliases == {}
    item_locations.save()
    assert fh.load(test_guild_id) == {
        VERSION_KEY: BOT_VERSION,
        ItemLocations.ITEMS_KEY: {},
        ItemLocations.ALIASES_KEY: {},
    }
