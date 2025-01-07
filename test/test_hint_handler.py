import os
import time

import pytest

from consts import BOT_VERSION, VERSION_KEY
from hint_data import DEFAULT_HINT_COOLDOWN_SEC, HintTimes
from hint_handler import get_hint_response
from item_location_handler import ItemLocations
from utils import HintType

test_guild_id = "test-guild-id"
test_hint_times = HintTimes(test_guild_id, HintType.ITEM)


@pytest.fixture
def hint_times_fh():
    yield test_hint_times.fh


item_key = "kafeis mask"
item_name = "Kafei's Mask"
item_alias = "kafei mask"
player1_locs = ["Location 1"]
player2_locs = ["Location 2", "Location 3"]
player3_locs = []
item_locs_dict = {
    item_key: {
        ItemLocations.NAME_KEY: item_name,
        ItemLocations.RESULTS_KEY: [
            player1_locs,
            player2_locs,
            player3_locs,
        ],
    }
}


@pytest.fixture(autouse=True)
def cleanup():
    yield

    item_locs_filename = ItemLocations.fh._get_filename(test_guild_id)
    hint_times_filename = test_hint_times.fh._get_filename(test_guild_id)
    if os.path.exists(item_locs_filename):
        os.remove(item_locs_filename)
    if os.path.exists(hint_times_filename):
        os.remove(hint_times_filename)


def test_get_hint_failures(hint_times_fh):
    item_locs = ItemLocations(test_guild_id, {})
    response = get_hint_response("playerx", "foo", 0, item_locs)
    assert (
        response
        == f'Unrecognized player playerx. (Did you format without spaces as in "player5"?)'
    )

    response = get_hint_response("player1", "foo", 0, item_locs)
    assert (
        response
        == "No data is currently stored. (Use !set-log to upload a spoiler log.)"
    )

    item_locs = ItemLocations(test_guild_id, item_locs_dict)

    response = get_hint_response("player1", "foo", 0, item_locs)
    assert response == "Item foo not recognized. Try !search <keyword> to find it!"

    response = get_hint_response("player0", item_key, 0, item_locs)
    assert response == "Invalid player number 0."
    response = get_hint_response("player4", item_key, 0, item_locs)
    assert response == "Invalid player number 4."

    response = get_hint_response("player3", item_key, 0, item_locs)
    assert (
        response
        == f"For some reason there are no locations listed for player3's {item_name}........ sorry!!! There must be something wrong with me :( Please report."
    )

    # None of these should have triggered a hint timestamp to be recorded
    with pytest.raises(FileNotFoundError):
        hint_times_fh.load(test_guild_id)


def test_get_hint_response(hint_times_fh):
    item_locs = ItemLocations(test_guild_id, item_locs_dict)

    # First hint success
    response = get_hint_response("player1", item_key, 0, item_locs)
    assert response == player1_locs[0]  # player1 has one location

    # Successful hint should trigger creation of hint timestamps file, and result in cooldown response
    hint_times_data = hint_times_fh.load(test_guild_id)
    assert hint_times_data[HintTimes.COOLDOWN_KEY] == DEFAULT_HINT_COOLDOWN_SEC
    assert hint_times_data[HintTimes.ASKERS_KEY].keys() == {"0"}
    response = get_hint_response("player1", item_key, 0, item_locs)
    assert response.startswith("Whoa nelly! You can't get another item hint until <t:")

    # New author should be successful with the same hint request, once
    response = get_hint_response("player1", item_key, 1, item_locs)
    assert response == player1_locs[0]
    response = get_hint_response("player1", item_key, 1, item_locs)
    assert response.startswith("Whoa nelly! You can't get another item hint until <t:")

    # Test response with item name and alias
    response = get_hint_response("player1", item_name, 2, item_locs)
    assert response == player1_locs[0]
    response = get_hint_response("player1", item_alias, 3, item_locs)
    assert response == player1_locs[0]

    # Test response with multiple locations
    response = get_hint_response("player2", item_key, 4, item_locs)
    assert response == "\n".join(player2_locs)  # player2 has two locations


def test_unknown_version(hint_times_fh):
    # If version is unknown, HintTimes should fall back on default values
    hint_times = {
        VERSION_KEY: "foo",
        HintTimes.COOLDOWN_KEY: 101,
        HintTimes.ASKERS_KEY: {
            "0": time.time(),
        },
    }
    hint_times_fh.store(hint_times, test_guild_id)

    expected_updated_data = {
        VERSION_KEY: BOT_VERSION,
        HintTimes.COOLDOWN_KEY: DEFAULT_HINT_COOLDOWN_SEC,
        HintTimes.ASKERS_KEY: {},
    }
    hint_times = HintTimes(test_guild_id, HintType.ITEM)
    assert hint_times.cooldown == DEFAULT_HINT_COOLDOWN_SEC and hint_times.askers == {}
    hint_times.save()
    assert hint_times_fh.load(test_guild_id) == expected_updated_data
