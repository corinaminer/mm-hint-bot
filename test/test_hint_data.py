import os
import time

import pytest

from consts import BOT_VERSION, VERSION_KEY
from hint_data import DEFAULT_HINT_COOLDOWN_SEC, hint_data_filename
from item_locations import ItemLocations
from utils import HintType, load, store

test_guild_id = "test-guild-id"
hint_data_filename = hint_data_filename(test_guild_id, HintType.ITEM)

serialized_items = {
    "kafeis mask": {
        ItemLocations.NAME_KEY: "Kafei's Mask",
        ItemLocations.RESULTS_KEY: [["location1"], ["location2"]],
    },
    "mask of scents": {
        ItemLocations.NAME_KEY: "Mask of Scents",
        ItemLocations.RESULTS_KEY: [["location3"], ["location4"]],
    },
}
serialized_hint_data = {
    VERSION_KEY: BOT_VERSION,
    ItemLocations.DATA_KEY: serialized_items,
}


@pytest.fixture(autouse=True)
def cleanup():
    yield

    for file in os.listdir():
        if file.startswith(test_guild_id) and file.endswith(".json"):
            os.remove(file)


def test_find_matches():
    item_locs = ItemLocations(test_guild_id)
    with pytest.raises(FileNotFoundError):
        item_locs.find_matches("foo")

    item_locs = ItemLocations(test_guild_id, serialized_items)
    # assert item_locs.find_matches("foo") == []
    # assert item_locs.find_matches("kafeis") == ["Kafei's Mask"]
    # assert item_locs.find_matches("Kafei's") == ["Kafei's Mask"]
    # Alias match
    assert item_locs.find_matches("sniff") == ["Mask of Scents"]


def test_get_item_key():
    item_locs = ItemLocations(test_guild_id, serialized_items)
    assert item_locs.get_item_key("foo") is None
    assert item_locs.get_item_key("kafeis mask") == "kafeis mask"  # exact match
    assert item_locs.get_item_key("sniffa") == "mask of scents"  # alias


def test_get_results():
    item_locs = ItemLocations(test_guild_id)
    with pytest.raises(FileNotFoundError):
        item_locs.get_results(1, "foo")

    item_locs = ItemLocations(test_guild_id, serialized_items)

    # Unrecognized query
    with pytest.raises(
        ValueError, match="Item kafei not recognized. Try !search <keyword> to find it!"
    ):
        item_locs.get_results(1, "kafei")

    # Invalid player numbers
    with pytest.raises(ValueError, match="Invalid player number 0."):
        item_locs.get_results(0, "kafei's mask")
    with pytest.raises(ValueError, match="Invalid player number 3."):
        item_locs.get_results(3, "kafei's mask")

    # Success with literal key and with alias
    res = item_locs.get_results(1, "kafei's mask")
    assert res == (
        "Kafei's Mask",
        ["location1"],
    )
    res = item_locs.get_results(2, "sniffa")
    assert res == (
        "Mask of Scents",
        ["location4"],
    )


def test_unknown_version():
    # If version is unknown, ItemLocations should act like no file exists
    invalid_version_data = {
        VERSION_KEY: "foo",
        ItemLocations.DATA_KEY: serialized_items,
    }
    store(invalid_version_data, hint_data_filename)

    item_locations = ItemLocations(test_guild_id)
    assert item_locations.items == {} and item_locations.aliases == {}
    item_locations.save()
    assert load(hint_data_filename) == {
        VERSION_KEY: BOT_VERSION,
        ItemLocations.DATA_KEY: {},
    }
